from pathlib import Path
import json
import os
from dotenv import load_dotenv
import random

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

raw_alpha = os.getenv("alpha")
if not raw_alpha:
    raise RuntimeError(
        f"Variável 'alpha' não encontrada. Verifique se o arquivo existe em: {env_path}"
    )

TABELA = json.loads(raw_alpha)

SEPARADOR = ";"
MARCADOR_NEGATIVO = "~"
random.seed(100)


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


def descriptografar(df):
    def descriptografar_valor(valor):
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

    return df.copy().apply(
        lambda coluna: coluna.map(descriptografar_valor)
    )