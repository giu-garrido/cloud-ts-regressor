from fastapi import FastAPI

app = FastAPI(title="cloud-ts-regressor")


@app.get("/")
def root():
    return {"status": "ok", "mensagem": "cloud-ts-regressor no ar"}


@app.get("/health")
def health():
    return {"status": "healthy"}