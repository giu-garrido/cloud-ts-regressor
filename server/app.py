from fastapi import FastAPI, UploadFile, File, HTTPException


# IMPORTANTE 
# para o codigo ficar mais entendivel, coloquei um traçado que separa os tipoes de requisições
# coloquei um marcador "<!>" para coisas que enventuamenlte irao mudar durante o desenvolvimento

# Rode isso aqui no terminal

app = FastAPI(

    title="API de integração para model de regressão",
    description = "Nada a declarar ainda", #<!>
    version ="0.0.1" # <!>
)

# Temos que definir isso aqui ainda em qual o formatodo arquivo e como ele vai receber <!>
def validar_arquivo(arquivo: UploadFile):
    if not arquivo.filename.endswith((".csv", ".xlsx")):
        raise HTTPException(
            status_code=400, 
            detail="Formato inválido. Envie apenas .csv ou .xlsx"
        )


# ------------------------- GET -----------------------------#
@app.get("/health")
def health():
    return {"status": "online"}


@app.get("/status")
def status():
    return {"status": "aguardando"}



# ------------------------- GET -----------------------------#

@app.post("/train")
async def train(arquivo: UploadFile = File(...)):
    validar_arquivo(arquivo)
    
    return {"mensagem": f"Arquivo {arquivo.filename} recebido para treino"}


@app.post("/predict")
async def predict(arquivo: UploadFile = File(...)):
    validar_arquivo(arquivo)
    
    return {"mensagem": f"Arquivo {arquivo.filename} recebido para predição"}


@app.post("/reset")
def reset():
    
    return {"mensagem": "Reset realizado"}