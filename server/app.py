from fastapi import FastAPI, Form, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from sklearn.preprocessing import StandardScaler
import model
import dotenv
import storage
import crypto as cp
import pandas as pd
import io
import numpy as np

# IMPORTANTE 
# para o codigo ficar mais entendivel, coloquei um traçado que separa os tipoes de requisições
# coloquei um marcador "<!>" para coisas que enventuamenlte irao mudar durante o desenvolvimento

# Rode isso aqui no terminal

#python -m uvicorn server.app:app --reload

#depois cole no navegador: http://127.0.0.1:8000/docs


app = FastAPI(
    title="API de integração para model de regressão",
    description="Para receber uma predição, jogue o arquivo CSV na parte de upload e escreve o nome da coluna alvo.", #<!>
    version="0.0.3" # <!>
)


def calcular_metricas(y_real: np.ndarray, y_pred: np.ndarray) -> dict:
    # Calcula métricas básicas de regressão (R², RMSE e MAE)
    erro = y_real - y_pred
    mse = float(np.mean(erro ** 2))
    rmse = float(np.sqrt(mse))
    mae = float(np.mean(np.abs(erro)))
    sst = float(np.sum((y_real - np.mean(y_real)) ** 2))
    sse = float(np.sum(erro ** 2))
    r2 = float(1.0 - (sse / sst)) if sst != 0 else 0.0
    return {"r2": r2, "rmse": rmse, "mae": mae}


async def ler_csv(arquivo: UploadFile, cifrado: bool = False) -> pd.DataFrame:
    # Lê o CSV em memória com BytesIO sem precisar salvar arquivo no disco
    if not arquivo.filename or not arquivo.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Envie um arquivo .csv válido.")

    conteudo = await arquivo.read()
    try:
        df = pd.read_csv(io.BytesIO(conteudo))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao ler o CSV: {e}")

    if cifrado:
        # <!> alinhar com o grupo o formato cifrado na entrada
        try:
            df = cp.decriptografar(df)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Erro ao decriptografar CSV: {e}")

    return df


# ---------------------------------------------------------------------------
# GET
# ---------------------------------------------------------------------------

@app.get(
    "/health",
    summary="Verificar status da API",
    description="Retorna o status atual de funcionamento do servidor para checar se ele está online."
)
def health():
    return {"status": "online"}


@app.get(
    "/status",
    summary="Consultar estado do modelo",
    description="Consulta o storage para informar se há modelo treinado e retorna os metadados."
)
def status():
    if not storage.has_model():
        return {"treinado": False, "meta": None}

    try:
        meta = storage.load_meta()
    except storage.ModelNotFound:
        return {"treinado": False, "meta": None}

    return {"treinado": True, "meta": meta}


# ---------------------------------------------------------------------------
# POST
# ---------------------------------------------------------------------------

@app.post(
    "/train",
    summary="Treinar o modelo com arquivo CSV",
    description="Recebe um CSV de treino e a coluna alvo, treina o modelo, calcula métricas no teste e salva no storage."
)
async def train(
    arquivo: UploadFile = File(description="Arquivo CSV de treino contendo as variáveis explicativas e o alvo."),
    coluna_alvo: str = Form(description="Nome exato da coluna alvo no arquivo CSV."),
    cifrado: bool = Form(False, description="Marque True se o CSV enviado estiver cifrado.") # <!>
):
    df = await ler_csv(arquivo, cifrado=cifrado)

    if coluna_alvo not in df.columns:
        raise HTTPException(
            status_code=400,
            detail=f"Coluna alvo '{coluna_alvo}' não encontrada. Colunas disponíveis: {list(df.columns)}"
        )

    # Prepara os dados (mantendo prepare_data e ajustando scaler só no X_train para não vazar dados)
    X_train, X_test, y_train, y_test, X_val, y_val = model.prepare_data(df, coluna_alvo)
    if X_train is None:
        raise HTTPException(status_code=400, detail="Erro ao preparar os dados. Verifique se todas as colunas são numéricas.")

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    regressor = model.Regressor()
    regressor.fit(X_train_scaled, y_train, X_val_scaled, y_val)

    # Métricas esperadas no conjunto de teste
    y_pred_test = regressor.predict(X_test_scaled)
    metricas_esperadas = calcular_metricas(y_test, y_pred_test)

    features = [col for col in df.columns if col != coluna_alvo]
    pacote = {"regressor": regressor, "scaler": scaler}
    meta = {
        "features": features,
        "coluna_alvo": coluna_alvo,
        "metricas_esperadas": metricas_esperadas,
    }
    storage.save_model(pacote, meta)

    return {
        "mensagem": "Sucesso ao treinar modelo.",
        "metricas_esperadas": metricas_esperadas,
    }


@app.post(
    "/predict",
    summary="Realizar predição com novos dados",
    description="Carrega o modelo do storage, aplica o scaler, gera o CSV de previsões e devolve métricas se houver coluna alvo."
)
async def predict(
    arquivo: UploadFile = File(description="Arquivo CSV contendo as colunas de features utilizadas no treinamento."),
    cifrado: bool = Form(False, description="Marque True se o CSV enviado estiver cifrado.") # <!>
):
    try:
        pacote, meta = storage.load_model()
    except storage.ModelNotFound:
        raise HTTPException(status_code=400, detail="Modelo não encontrado. Treine primeiro em /train.")

    df = await ler_csv(arquivo, cifrado=cifrado)

    features = meta.get("features", [])
    faltando = [col for col in features if col not in df.columns]
    if faltando:
        raise HTTPException(status_code=400, detail=f"Colunas faltando no CSV: {faltando}")

    try:
        X_novos = np.array(df[features], dtype=float)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao converter features para número: {e}")

    scaler = pacote.get("scaler")
    regressor = pacote.get("regressor")
    if scaler is not None:
        X_novos = scaler.transform(X_novos)

    predicoes = regressor.predict(X_novos)

    df_resultado = df.copy()
    df_resultado["predicao"] = predicoes

    # Se o CSV tiver a coluna alvo (ex: "time"), calcula métricas reais junto das esperadas
    coluna_alvo = meta.get("coluna_alvo", "time")
    metricas_esperadas = meta.get("metricas_esperadas")
    metricas_reais = None

    if coluna_alvo in df.columns:
        try:
            y_real = np.array(df[coluna_alvo], dtype=float)
            metricas_reais = calcular_metricas(y_real, predicoes)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Coluna '{coluna_alvo}' inválida para calcular métricas: {e}")

    # <!> Se o cliente precisar de saída cifrada, combinar função de cifrar no cp.py
    buffer_csv = io.StringIO()
    df_resultado.to_csv(buffer_csv, index=False)
    buffer_csv.seek(0)

    headers = {"Content-Disposition": 'attachment; filename="predicoes.csv"'}
    if metricas_esperadas is not None:
        headers["X-Metricas-Esperadas"] = str(metricas_esperadas)
    if metricas_reais is not None:
        headers["X-Metricas-Reais"] = str(metricas_reais)

    return StreamingResponse(
        iter([buffer_csv.getvalue()]),
        media_type="text/csv",
        headers=headers,
    )


@app.post(
    "/reset",
    summary="Resetar o modelo",
    description="Remove o modelo e os metadados salvos no storage."
)
def reset():
    storage.delete_model()
    return {"mensagem": "Resetado com sucesso."}