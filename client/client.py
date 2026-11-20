import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import crypto as cp

df = pd.read_csv("C:/Users/caraf/Downloads/PI_application-1.csv")

# Se quiser exibir ou validar o ciclo completo, mantenha; caso contrário, use df direto
df = cp.criptografar(df)
df = cp.descriptografar(df)

columns_list = list(df.columns)

col1, col2, col3 = st.columns(3)

check_box_regressao = st.checkbox("Mostrar Regressão", key="regressao_linear")

with col1:
    x_column = st.selectbox("Escolha a coluna X", columns_list, key="secao_alpha")
with col2:
    y_column = st.selectbox("Escolha a coluna Y", columns_list, key="secao_beta")

if check_box_regressao:
    with col3:
        graphic_type = st.selectbox(
            "Tipo de gráfico",
            ["Dispersão (Scatter)", "Linha (Line)"],
            key="secao_grafico",
        )
else:
    graphic_type = "Linha (Line)"


def ajustar_regressao_linear(x_series: pd.Series, y_series: pd.Series):
    dados = pd.DataFrame({"x": x_series, "y": y_series}).dropna()
    x_num = pd.to_numeric(dados["x"], errors="coerce")
    y_num = pd.to_numeric(dados["y"], errors="coerce")
    valido = pd.DataFrame({"x": x_num, "y": y_num}).dropna()

    if len(valido) < 2:
        return None, None, None

    coef = np.polyfit(valido["x"].to_numpy(), valido["y"].to_numpy(), 1)
    y_pred = np.polyval(coef, valido["x"].to_numpy())
    return valido["x"].to_numpy(), y_pred, coef


fig = None
tipo_fig = "plotly"

if graphic_type == "Dispersão (Scatter)":
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
        color=color_column,
        title=f"{y_column} por {x_column}",
    )
    tipo_fig = "plotly"

else:
    if check_box_regressao:
        x_val, y_fit, coef = ajustar_regressao_linear(df[x_column], df[y_column])

        if x_val is None:
            st.warning("As colunas selecionadas precisam ter ao menos 2 valores numéricos válidos para calcular a regressão.")
        else:
            fig, ax = plt.subplots(figsize=(7, 3.5))
            ax.plot(df[x_column], df[y_column], color="blue", label="Dados")
            ax.plot(x_val, y_fit, color="red", label=f"Regressão (y = {coef[0]:.2f}x + {coef[1]:.2f})")
            ax.set_title(f"{y_column} vs {x_column}")
            ax.set_xlabel(x_column)
            ax.set_ylabel(y_column)
            ax.grid(True, alpha=0.3)
            ax.legend()
            tipo_fig = "matplotlib"
    else:
        fig = px.line(
            df,
            x=x_column,
            y=y_column,
            title=f"Evolução de {y_column} por {x_column}",
        )
        tipo_fig = "plotly"

if fig is not None:
    if tipo_fig == "matplotlib":
        st.pyplot(fig)
        plt.close(fig)
    else:
        st.plotly_chart(fig, use_container_width=True)