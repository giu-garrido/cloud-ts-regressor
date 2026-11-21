import os
import json
from pathlib import Path
from dotenv import load_dotenv, dotenv_values
import random

env_path = Path(__file__).resolve().parent.parent / ".env"

dados = dotenv_values(
    dotenv_path=env_path,
    encoding="utf-8"
)
env_path = Path(__file__).resolve().parent.parent / ".env"

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

def criptografar(df):
    df = (df.copy() * 100).round().astype(int)

    def criptografar_valor(valor):
        valor = int(valor)
        sinal = f"{MARCADOR_NEGATIVO}{SEPARADOR}" if valor < 0 else ""
        hexadecimal = format(abs(valor), "X")
        simbolos = (
            random.choice(TABELA[digito])
            for digito in hexadecimal
        )
        return sinal + SEPARADOR.join(simbolos)

    return df.apply(lambda coluna: coluna.map(criptografar_valor))