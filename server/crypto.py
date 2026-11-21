import os
import json
from pathlib import Path
from dotenv import load_dotenv, dotenv_values
import random
import pandas as pd
import numpy as np

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

TABELA = json.loads(raw_alpha)

SEPARADOR = ";"
MARCADOR_NEGATIVO = "~"
MARCADOR_NAN = "__NaN__"

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