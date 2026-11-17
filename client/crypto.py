import random
import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
TABELA = json.loads(os.environ["alpha"])

SEPARADOR = ";"
MARCADOR_NEGATIVO = "~"
random.seed(100)


def criptografar(df):
    df = (df.copy() * 100).astype(int)

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