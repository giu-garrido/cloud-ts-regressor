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