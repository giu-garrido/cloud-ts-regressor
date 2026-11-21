import io
import os
from pathlib import Path

from dotenv import load_dotenv
import pandas as pd
import requests
import streamlit as st
import json

import crypto as cp

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


API_URL = os.getenv("API_URL", " http://127.0.0.1:8000").rstrip("/")

def df_para_csv_bytes(df: pd.DataFrame, nome_arquivo: str) -> tuple[str, bytes, str]:
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return (nome_arquivo, buffer.getvalue().encode("utf-8"), "text/csv")


def enviar_train(df_treino: pd.DataFrame, coluna_alvo: str) -> dict:
    if not API_URL:
        raise RuntimeError("Variável de ambiente API_URL não configurada no .env.")

    df_cifrado = cp.criptografar(df_treino)
    files = {"arquivo": df_para_csv_bytes(df_cifrado, "treino_cifrado.csv")}
    data = {"coluna_alvo": coluna_alvo,
            "cifrado": "true",}

    response = requests.post(
        f"{API_URL}/train",
        files=files,
        data=data,
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def enviar_predict(df_features: pd.DataFrame) -> dict:
    if not API_URL:
        raise RuntimeError("Variável de ambiente API_URL não configurada no .env.")

    df_cifrado = cp.criptografar(df_features)
    files = {"arquivo": df_para_csv_bytes(df_cifrado, "predict_cifrado.csv")}
    data = {"cifrado": "true"}

    response = requests.post(
        f"{API_URL}/predict",
        files=files,
        data=data,
        timeout=120,
    )
    if not response.ok:
        raise RuntimeError(f"Erro {response.status_code} no /predict: {response.text}")

    content_type = response.headers.get("content-type", "")
    if "text/csv" in content_type:
        return {
            "csv_texto": response.text,
            "metricas_esperadas": json.loads(response.headers.get("X-Metricas-Esperadas", "null")),
            "metricas_reais": json.loads(response.headers.get("X-Metricas-Reais", "null")),
        }
    return response.json()

def decifrar_resposta(dados_resposta) -> pd.DataFrame | None:
    if not isinstance(dados_resposta, dict):
        return None

    # Caso 1: API retorna {"predicoes": [...]} (cifradas ou numéricas)
    if "predicoes" in dados_resposta:
        df_pred = pd.DataFrame({"predicao": dados_resposta["predicoes"]})
        return cp.decriptografar(df_pred)

    # Caso 2: API retorna estrutura tabular {"columns": [...], "records": [...]}
    if "records" in dados_resposta:
        colunas = dados_resposta.get("columns")
        df_cifrado = pd.DataFrame(dados_resposta["records"], columns=colunas)
        return cp.decriptografar(df_cifrado)
    
    if "csv_texto" in dados_resposta:
        df_csv = pd.read_csv(io.StringIO(dados_resposta["csv_texto"]))
        try:
            return cp.decriptografar(df_csv)
        except Exception:
            # Se o /predict devolveu o CSV já em valores numéricos/texto sem cifrar
            return df_csv
    return None

def resetar_modelo() -> dict:
    if not API_URL:
        raise RuntimeError("Variável de ambiente API_URL não configurada no .env.")

    response = requests.post(f"{API_URL}/reset", timeout=60)
    response.raise_for_status()
    return response.json()

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
                if rota == "train":
                    resposta = enviar_train(df_entrada, coluna_alvo)
                else:
                    resposta = enviar_predict(df_entrada)

            df_decifrado = decifrar_resposta(resposta)
            st.session_state["ultima_resposta"] = resposta
            st.session_state["ultimo_df_decifrado"] = df_decifrado
            st.session_state["ultima_rota"] = rota
            st.success("Requisição concluída!")

        except requests.RequestException as exc:
            st.error(f"Erro na comunicação com a API: {exc}")
        except Exception as exc:
            st.error(f"Erro ao processar os dados: {exc}")

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

        csv_saida = df_salvo.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Baixar CSV decifrado",
            data=csv_saida,
            file_name=f"resultado_{rota_salva}.csv",
            mime="text/csv",
        )
    else:
        st.subheader("Resposta da API")
        st.json(resposta_salva)