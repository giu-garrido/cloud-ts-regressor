from fastapi import FastAPI, Form, UploadFile, File, HTTPException
import model 
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
    description = "Para receber uma predição, jogue o arquivo CSV na parte de upload e escreve o nome da coluna alvo.", #<!>
    version ="0.0.2" # <!>
)


# preset basico para o servidor guardar 
estado = {"treinado": False, "features": None}
regressor = model.Regressor()

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
    description="Informa se o regressor já passou pelo treinamento e está pronto para receber predições."
)
def status():
    return {"treinado": estado["treinado"]}

@app.post(
    "/train", 
    summary="Treinar o modelo com arquivo CSV",
    description="Recebe um arquivo CSV de treino e o nome da coluna alvo, executa o pré-processamento e treina o regressor."
)
async def train(
    arquivo: UploadFile = File(description="Arquivo CSV de treino contendo as variáveis explicativas e o alvo."), 
    coluna_alvo: str = Form(description="Nome exato da coluna alvo no arquivo CSV.")
):
    # le o csv 
    conteudo = await arquivo.read()
    df = pd.read_csv(io.BytesIO(conteudo))

    # prepara para o treino
    X_train, X_test, y_train, y_test, X_val, y_val = model.prepare_data(df, coluna_alvo)
    
    # Guarda as featires para o treino menos a "coluan alvo"
    estado["features"] = [col for col in df.columns if col != coluna_alvo]
    
    # Clear and train the friends model hihihi
    regressor.clear_model()
    regressor.fit(X_train, y_train, X_val, y_val)
    estado["treinado"] = True
    
    return {"mensagem": "Sucesso ao treinar modelo."}

@app.post(
    "/predict", 
    summary="Realizar predição com novos dados",
    description="Recebe um arquivo CSV contendo apenas as features, valida se o modelo foi treinado e retorna a lista de previsões."
)
async def predict(
    arquivo: UploadFile = File(description="Arquivo CSV contendo as colunas de features utilizadas no treinamento (sem o alvo).")
):
    if not estado["treinado"]:
        raise HTTPException(status_code=400, detail="Treine o modelo primeiro!")
        
    # Ler o csv da predicao
    conteudo = await arquivo.read()
    df = pd.read_csv(io.BytesIO(conteudo))
    
    # Pega apenas as colunas que foram usadas no treino
    X_novos = np.array(df[estado["features"]], dtype=float)
    
    # Execução
    predicoes = regressor.predict(X_novos)
    
    return {"predicoes": predicoes.tolist()}

@app.post(
    "/reset", 
    summary="Resetar o modelo", 
    description="Limpa os pesos da memória, apaga o estado guardado e reinicia o regressor."
)
def reset():
    regressor.clear_model()
    estado["treinado"] = False
    estado["features"] = None
    return {"mensagem": "Resetado com sucesso."}