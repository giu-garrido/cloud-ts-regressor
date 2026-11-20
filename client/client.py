import pandas as pd
import numpy as np
import streamlit as st
import seaborn as sns
import matplotlib.pyplot as plt
import plotly.express as px
import crypto as cp

st.title("AAA")

df = ""

criptografado = cp.criptografar(df)

df = cp.descriptografar(criptografado)

col1, col2, col3 = st.columns(3)

columns_list = list(df.columns)

with col1:
    x_column = st.selectbox(
        "Escolha a coluna X", columns_list, key="secao_alpha"
    )
with col2:
    y_column = st.selectbox(
        "Escolha a coluna Y", columns_list, key="secao_beta"
    )
with col3:
    graphic_type = st.selectbox(
        "Tipo de gráfico", ["Dispersão (Scatter)", "Linha (Line)"], key="secao_grafico"
    )

# 2. Lógica de criação do gráfico usando apenas Plotly Express
if graphic_type == "Dispersão (Scatter)":
    # Adiciona o 'None' no início como padrão para evitar gráficos poluídos logo de cara
    color_options = [None] + columns_list
    color_column = st.selectbox(
        "Agrupar por cor (opcional)",
        color_options,
        format_func=lambda x: "Nenhuma opção" if x is None else x,
        key="secao_cor",
    )

    fig = px.scatter(
        df,
        x=x_column,
        y=y_column,
        color=color_column,  # O Plotly aceita None nativamente!
        title=f"{y_column} por {x_column}",
    )

else:
    fig = px.line(
        df,
        x=x_column,
        y=y_column,
        title=f"Evolução de {y_column} por {x_column}",
    )

st.plotly_chart(fig, use_container_width=True)
