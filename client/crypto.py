import os
import json
from pathlib import Path
from dotenv import load_dotenv, dotenv_values
import random
import pandas as pd
import numpy as np
import ast

env_path = Path(__file__).resolve().parent.parent / ".env"

dados = dotenv_values(
    dotenv_path=env_path,
    encoding="utf-8"
)


print("Chaves encontradas:", list(dados.keys()))
print("Alpha encontrada:", "alpha" in dados)
print("Arquivo existe:", env_path.exists())


load_dotenv(
    dotenv_path=env_path,
    override=True,
    encoding="utf-8",
    verbose = True
) 
raw_alpha = os.getenv("alpha")

if raw_alpha is None:
    raise RuntimeError(
        f"Variável 'alpha' não encontrada. Verifique se o arquivo existe em: {env_path}"
    )

texto = raw_alpha.strip()

# Remove um par de aspas simples ou duplas externas, se existirem
if len(texto) >= 2 and (
    (texto.startswith("'") and texto.endswith("'"))
    or (texto.startswith('"') and texto.endswith('"'))
):
    texto = texto[1:-1].strip()

try:
    TABELA = json.loads(texto)
except json.JSONDecodeError:
    # Fallback caso venha como literal Python (ex.: aspas simples no conteúdo)
    TABELA = ast.literal_eval(texto)

if not isinstance(TABELA, dict):
    raise RuntimeError(f"'alpha' deveria ser um dicionário/objeto, mas virou {type(TABELA).__name__}.")

SEPARADOR = ";"
MARCADOR_NEGATIVO = "~"
MARCADOR_NAN = "__NaN__"

def criptografar(df: pd.DataFrame) -> pd.DataFrame:
    def criptografar_valor(valor):
        if pd.isna(valor) or np.isinf(float(valor)):
            return MARCADOR_NAN

        centavos = int(round(float(valor) * 100))
        sinal = f"{MARCADOR_NEGATIVO}{SEPARADOR}" if centavos < 0 else ""
        hexadecimal = format(abs(centavos), "x")
        simbolos = (random.choice(TABELA[digito]) for digito in hexadecimal)
        return sinal + SEPARADOR.join(simbolos)

    return df.apply(lambda coluna: coluna.map(criptografar_valor))

def descriptografar(df: pd.DataFrame) -> pd.DataFrame:
    def descriptografar_valor(valor):
        if pd.isna(valor) or str(valor) == MARCADOR_NAN:
            return np.nan

        partes = str(valor).split(SEPARADOR)
        sinal = -1 if partes[0] == MARCADOR_NEGATIVO else 1

        if sinal < 0:
            partes = partes[1:]

        digitos = []
        for simbolo in partes:
            correspondencias = [
                digito
                for digito, opcoes in TABELA.items()
                if simbolo in opcoes
            ]
            if len(correspondencias) != 1:
                raise ValueError(f"Símbolo desconhecido ou ambíguo: {simbolo!r}")
            digitos.append(correspondencias[0])

        return sinal * int("".join(digitos), 16) / 100

    return df.copy().apply(lambda coluna: coluna.map(descriptografar_valor))