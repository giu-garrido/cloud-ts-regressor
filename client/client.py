import io
import json
import os
from pathlib import Path

from dotenv import load_dotenv
import matplotlib.pyplot as plt
import pandas as pd
import requests
import streamlit as st

import crypto as cp

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

API_URL = (
    os.getenv("API_URL", "http://host.docker.internal:8000").strip().strip('"').strip("'").rstrip("/")
)


def _endpoint(rota: str) -> str:
    if not API_URL:
        raise RuntimeError("Variável de ambiente API_URL não configurada.")
    return f"{API_URL}{rota}"

<<<<<<< HEAD
=======
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").strip(" /")

>>>>>>> 24766fa (cifrando csv de saida do /predic)

def df_para_csv_bytes(df: pd.DataFrame, nome_arquivo: str) -> tuple[str, bytes, str]:
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return (nome_arquivo, buffer.getvalue().encode("utf-8"), "text/csv")


def enviar_train(df_treino: pd.DataFrame, coluna_alvo: str) -> dict:
    df_cifrado = cp.criptografar(df_treino)
<<<<<<< HEAD
=======
    files = {"arquivo": df_para_csv_bytes(df_cifrado, "treino_cifrado.csv")}
    data = {
        "coluna_alvo": coluna_alvo,
        "cifrado": "true",
    }

>>>>>>> 24766fa (cifrando csv de saida do /predic)
    response = requests.post(
        _endpoint("/train"),
        files={"arquivo": df_para_csv_bytes(df_cifrado, "treino_cifrado.csv")},
        data={"coluna_alvo": coluna_alvo, "cifrado": "true"},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def enviar_predict(df_features: pd.DataFrame) -> dict:
    df_cifrado = cp.criptografar(df_features)
    response = requests.post(
        _endpoint("/predict"),
        files={"arquivo": df_para_csv_bytes(df_cifrado, "predict_cifrado.csv")},
        data={"cifrado": "true"},
        timeout=120,
    )
    if not response.ok:
        raise RuntimeError(f"Erro {response.status_code} no /predict: {response.text}")

    if "text/csv" in response.headers.get("content-type", ""):
        return {
            "csv_texto": response.text,
            "metricas_esperadas": json.loads(response.headers.get("X-Metricas-Esperadas", "null")),
            "metricas_reais": json.loads(response.headers.get("X-Metricas-Reais", "null")),
        }
    return response.json()


def decifrar_resposta(dados_resposta) -> pd.DataFrame | None:
    if not isinstance(dados_resposta, dict):
        return None

<<<<<<< HEAD
=======
    # Caso 1: API retorna {"predicoes": [...]} cifradas
>>>>>>> 24766fa (cifrando csv de saida do /predic)
    if "predicoes" in dados_resposta:
        return cp.decriptografar(pd.DataFrame({"predicao": dados_resposta["predicoes"]}))

<<<<<<< HEAD
    if "records" in dados_resposta:
        df_cifrado = pd.DataFrame(dados_resposta["records"], columns=dados_resposta.get("columns"))
        return cp.decriptografar(df_cifrado)

    if "csv_texto" in dados_resposta:
        df_csv = pd.read_csv(io.StringIO(dados_resposta["csv_texto"]))
        return cp.decriptografar(df_csv)
=======
    # Caso 2: API retorna estrutura tabular {"columns": [...], "records": [...]} cifrada
    if "records" in dados_resposta:
        colunas = dados_resposta.get("columns")
        df_cifrado = pd.DataFrame(dados_resposta["records"], columns=colunas)
        return cp.descriptografar(df_cifrado)

    # Caso 3: API retorna CSV cifrado em texto
    if "csv_texto" in dados_resposta:
        df_cifrado = pd.read_csv(io.StringIO(dados_resposta["csv_texto"]))
        return cp.descriptografar(df_cifrado)
>>>>>>> 24766fa (cifrando csv de saida do /predic)

    return None


def resetar_modelo() -> dict:
    response = requests.post(_endpoint("/reset"), timeout=60)
    response.raise_for_status()
    return response.json()


def _plot_linhas(
    x,
    series: list[tuple[pd.Series, str, str | None]],
    titulo: str,
    ylabel: str,
    figsize: tuple[int, int] = (10, 4),
    linha_zero: bool = False,
) -> None:
    fig, ax = plt.subplots(figsize=figsize)
    for y, rotulo, estilo in series:
        kwargs = {"label": rotulo}
        if estilo:
            kwargs["linestyle"] = estilo
        ax.plot(x, y, **kwargs)
    if linha_zero:
        ax.axhline(0, linestyle=":", linewidth=1)
    ax.set_title(titulo)
    ax.set_xlabel("Observação / Índice")
    ax.set_ylabel(ylabel)
    ax.legend()
    ax.grid(True, alpha=0.3)
    st.pyplot(fig)
    plt.close(fig)


st.title("Cliente - Treino e Predição")

arquivo_csv = st.file_uploader("Envie o arquivo CSV", type=["csv"])
rota = st.selectbox("Endpoint da API", ["train", "predict"])

if arquivo_csv is not None:
    df_entrada = pd.read_csv(arquivo_csv)
    st.subheader("Prévia dos dados enviados")
    st.dataframe(df_entrada.head())

    coluna_alvo = None
    if rota == "train":
        colunas = list(df_entrada.columns)
        if not colunas:
            st.error("O CSV enviado não possui colunas.")
            st.stop()
        coluna_alvo = st.selectbox("Selecione a coluna alvo", colunas)

    if st.button("Enviar para API"):
        try:
            with st.spinner("Cifrando e enviando para a API..."):
                resposta = enviar_train(df_entrada, coluna_alvo) if rota == "train" else enviar_predict(df_entrada)

            df_decifrado = decifrar_resposta(resposta)
            st.session_state["ultima_resposta"] = resposta
            st.session_state["ultimo_df_decifrado"] = df_decifrado
            st.session_state["ultima_rota"] = rota
            st.success("Requisição concluída!")
        except requests.RequestException as exc:
            st.error(f"Erro na comunicação com a API: {exc}")
        except Exception as exc:
            st.error(f"Erro ao processar os dados ({type(exc).__name__}): {exc}")

if st.button("Resetar modelo"):
    try:
        with st.spinner("Resetando modelo na API..."):
            res_reset = resetar_modelo()
        for chave in ("ultima_resposta", "ultimo_df_decifrado", "ultima_rota"):
            st.session_state.pop(chave, None)
        st.success(res_reset.get("mensagem", "Modelo resetado com sucesso!"))
    except requests.RequestException as exc:
        st.error(f"Erro ao resetar o modelo: {exc}")
    except Exception as exc:
        st.error(f"Erro inesperado ao resetar: {exc}")

if "ultima_resposta" in st.session_state:
    resposta_salva = st.session_state["ultima_resposta"]
    df_salvo = st.session_state.get("ultimo_df_decifrado")
    rota_salva = st.session_state.get("ultima_rota", "resultado")

    if df_salvo is not None:
        st.subheader("Resultado decifrado")
        st.dataframe(df_salvo.head())

        st.download_button(
            label="Baixar CSV decifrado",
            data=df_salvo.to_csv(index=False).encode("utf-8"),
            file_name=f"resultado_{rota_salva}.csv",
            mime="text/csv",
        )

        st.subheader("Visualizações")
        if isinstance(resposta_salva, dict):
            if resposta_salva.get("metricas_esperadas"):
                st.caption("Métricas esperadas (validação/teste do treino)")
                st.json(resposta_salva["metricas_esperadas"])
            if resposta_salva.get("metricas_reais"):
                st.caption("Métricas reais (avaliação do teste)")
                st.json(resposta_salva["metricas_reais"])

        x = df_salvo.index
        if "predicao" in df_salvo.columns:
            alvo = next((c for c in ("time", "target", "y") if c in df_salvo.columns), None)
            if alvo and pd.api.types.is_numeric_dtype(df_salvo[alvo]):
                _plot_linhas(
                    x,
                    [
                        (df_salvo[alvo], f"Real ({alvo})", None),
                        (df_salvo["predicao"], "Predição", "--"),
                    ],
                    titulo="Real vs. Predição",
                    ylabel="Valor",
                )
                _plot_linhas(
                    x,
                    [(df_salvo[alvo] - df_salvo["predicao"], "Erro (real - predicao)", None)],
                    titulo="Erro Residual",
                    ylabel="Erro",
                    figsize=(10, 3),
                    linha_zero=True,
                )
            else:
                _plot_linhas(
                    x,
                    [(df_salvo["predicao"], "Predição", None)],
                    titulo="Curva de Predições",
                    ylabel="Predição",
                )
        else:
            colunas_numericas = list(df_salvo.select_dtypes(include="number").columns)
            if colunas_numericas:
                opcoes_plot = st.multiselect(
                    "Selecione colunas para plotar juntas",
                    colunas_numericas,
                    default=colunas_numericas[: min(3, len(colunas_numericas))],
                )
                if opcoes_plot:
                    _plot_linhas(
                        x,
                        [(df_salvo[col], col, None) for col in opcoes_plot],
                        titulo="Séries Numéricas Selecionadas",
                        ylabel="Valor",
                    )
    else:
        st.subheader("Resposta da API")
        st.json(resposta_salva)