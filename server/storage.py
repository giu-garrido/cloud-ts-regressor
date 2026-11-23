"""

"Dois" backends, escolhidos pela variável de ambiente STORAGE_BACKEND:

- "local" (padrão): salva em uma pasta do disco. Serve para desenvolver na
  própria máquina e para o Docker Compose local (plano B).
- "azure": salva no Azure Blob Storage, autenticando com a identidade
  gerenciada do Container App (sem senha nem connection string).

Variáveis de ambiente:

    STORAGE_BACKEND          "local" ou "azure" (padrão: "local")
    LOCAL_MODEL_DIR          pasta do backend local (padrão: ./data/modelo)
    AZURE_STORAGE_ACCOUNT    nome da Storage Account (backend azure)
    AZURE_STORAGE_CONTAINER  nome do container de blobs (padrão: "modelos")
    AZURE_CLIENT_ID          client id da identidade gerenciada (no Azure)

Uso no resto do servidor:

    import storage
    storage.save_model(pipeline, {"colunas": [...], "metricas_esperadas": {...}})
    pipeline, meta = storage.load_model()     # ModelNotFound se não houver
    storage.has_model()                       # True / False
    storage.delete_model()                    # usado pelo /reset

O modelo é lido do armazenamento a cada uso, nunca guardado em variável
global: assim todos os workers e réplicas enxergam o mesmo /train e /reset.
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
from typing import Any

import joblib

MODEL_NAME = "model.joblib"
META_NAME = "meta.json"


class ModelNotFound(Exception):
    """Nenhum modelo treinado salvo (ainda não houve /train, ou houve /reset)."""


############################################


class _LocalBackend:
    def __init__(self, folder: str):
        self.folder = Path(folder)

    def write(self, name: str, data: bytes) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        tmp = self.folder / f".{name}.tmp"
        tmp.write_bytes(data)
        tmp.replace(self.folder / name) # troca atômica pra nunca ficar meio escrito

    def read(self, name: str) -> bytes:
        path = self.folder / name
        if not path.exists():
            raise ModelNotFound(name)
        return path.read_bytes()

    def delete(self, name: str) -> None:
        (self.folder / name).unlink(missing_ok=True)

    def exists(self, name: str) -> bool:
        return (self.folder / name).exists()


class _AzureBlobBackend:
    def __init__(self, account: str, container: str, client_id: str | None):
        # imports aqui dentro pq quem usa só o backend local não precisa do SDK
        from azure.identity import DefaultAzureCredential
        from azure.storage.blob import BlobServiceClient

        credential = DefaultAzureCredential(managed_identity_client_id=client_id)
        service = BlobServiceClient(
            account_url=f"https://{account}.blob.core.windows.net",
            credential=credential,
        )
        self.container = service.get_container_client(container)

    def write(self, name: str, data: bytes) -> None:
        self.container.upload_blob(name, data, overwrite=True)

    def read(self, name: str) -> bytes:
        from azure.core.exceptions import ResourceNotFoundError

        try:
            return self.container.download_blob(name).readall()
        except ResourceNotFoundError as exc:
            raise ModelNotFound(name) from exc

    def delete(self, name: str) -> None:
        from azure.core.exceptions import ResourceNotFoundError

        try:
            self.container.delete_blob(name)
        except ResourceNotFoundError:
            pass

    def exists(self, name: str) -> bool:
        return self.container.get_blob_client(name).exists()


def _backend():
    kind = os.getenv("STORAGE_BACKEND", "local").lower()
    if kind == "azure":
        account = os.environ["AZURE_STORAGE_ACCOUNT"]
        container = os.getenv("AZURE_STORAGE_CONTAINER", "modelos")
        return _AzureBlobBackend(account, container, os.getenv("AZURE_CLIENT_ID"))
    if kind == "local":
        return _LocalBackend(os.getenv("LOCAL_MODEL_DIR", "./data/modelo"))
    raise ValueError(f"STORAGE_BACKEND inválido: {kind!r} (use 'local' ou 'azure')")



#########################################


def save_model(model: Any, meta: dict) -> None:
    """salva o modelo (pipeline do scikit-learn) e seus metadados"""
    buffer = io.BytesIO()
    # o meta vai junto dentro do .joblib: assim o load_model lê um arquivo só
    # e nunca mistura modelo de um treino com meta de outro
    joblib.dump({"model": model, "meta": meta}, buffer)
    backend = _backend()
    # o meta.json separado continua existindo só para o /status (load_meta),
    # que não precisa desserializar o modelo
    # metadados primeiro, modelo por último: has_model() olha o modelo,
    # então ele só aparece quando os dois já estão gravados
    backend.write(META_NAME, json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"))
    backend.write(MODEL_NAME, buffer.getvalue())


def load_model() -> tuple[Any, dict]:
    """devolve (modelo, metadados) e levanta ModelNotFound se não houver modelo"""
    # uma leitura só: modelo e meta vêm sempre do mesmo treino
    model_bytes = _backend().read(MODEL_NAME)
    # joblib usa pickle: só carregue arquivos gravados pelo próprio servidor
    bundle = joblib.load(io.BytesIO(model_bytes))
    return bundle["model"], bundle["meta"]


def load_meta() -> dict:
    """só os metadados (para o /status), sem carregar o modelo"""
    if not has_model():
        raise ModelNotFound(META_NAME)
    return json.loads(_backend().read(META_NAME).decode("utf-8"))


def has_model() -> bool:
    return _backend().exists(MODEL_NAME)


def delete_model() -> None:
    """apaga modelo e metadados (usado pelo /reset)"""
    backend = _backend()
    backend.delete(MODEL_NAME)
    backend.delete(META_NAME)