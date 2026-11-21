import os
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
import streamlit as st

import crypto as cp

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

API_URL = os.getenv("API_URL", " http://127.0.0.1:8501").rstrip("/")


def enviar_para_rota(rota: str, df: pd.DataFrame) -> pd.DataFrame:
    if not API_URL:
        raise RuntimeError("Variável de ambiente API_URL não configurada.")

    df_cifrado = cp.criptografar(df)
    payload = {
        "columns": list(df_cifrado.columns),
        "records": df_cifrado.to_dict(orient="records"),
    }

    response = requests.post(
        f"{API_URL}/{rota.lstrip('/')}",
        json=payload,
        timeout=120,
    )
    response.raise_for_status()

    dados_resposta = response.json()

    # Se a API retornar registros cifrados, decifra de volta para DataFrame
    if isinstance(dados_resposta, dict) and "records" in dados_resposta:
        colunas = dados_resposta.get("columns")
        df_resp_cifrado = pd.DataFrame(dados_resposta["records"], columns=colunas)
        return cp.descriptografar(df_resp_cifrado)

    return pd.DataFrame([dados_resposta])


st.title("Cliente - Treino e Predição")

arquivo_csv = st.file_uploader("Envie sua planilha CSV", type=["csv"])
acao = st.selectbox("O que você quer enviar para a API?", ["Treinar (/train)", "Prever (/predict)"])

if arquivo_csv is not None:
    df_entrada = pd.read_csv(arquivo_csv)
    st.write("Prévia dos dados enviados:", df_entrada.head())

    if st.button("Enviar para a API"):
        with st.spinner("Cifrando e enviando para a API..."):
            rota = "train" if acao.startswith("Treinar") else "predict"
            df_resultado = enviar_para_rota(rota, df_entrada)

        st.success("Concluído!")
        st.write("Resultado decifrado:", df_resultado.head())

        csv_bytes = df_resultado.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Baixar resultado (CSV)",
            data=csv_bytes,
            file_name=f"resultado_{rota}.csv",
            mime="text/csv",
        )