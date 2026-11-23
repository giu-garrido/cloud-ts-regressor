# cloud-ts-regressor

Serviço de regressão linear para série temporal, com treino e previsão feitos remotamente por uma API em container. O valor da coluna `time` é previsto a partir dos 5 momentos anteriores (`time-5` … `time-1`). Os CSVs trafegam cifrados de ponta a ponta com uma criptografia implementada pelo grupo.
## Arquitetura

```
Cliente Streamlit
   │  cifra o CSV (substituição homofônica, tabela alpha)
   ▼
API FastAPI (Azure Container Apps)
   │  decifra → valida colunas → StandardScaler → regressor linear (SGD próprio)
   │  modelo + scaler + métricas salvos no Azure Blob Storage
   │  cifra o CSV de previsões; métricas vão em cabeçalhos HTTP
   ▼
Cliente decifra, mostra métricas e gráficos e oferece o download
```

| Pasta | Conteúdo |
|---|---|
| `server/` | API (`app.py`), modelo (`model.py`), persistência (`storage.py`), criptografia (`crypto.py`) |
| `client/` | interface Streamlit (`client.py`) e a mesma criptografia (`crypto.py`) |
| `docs/` | registro de decisões do projeto (`decisoes.md`) |

## Endpoints

| Endpoint | Função |
|---|---|
| `POST /train` | treina com um CSV rotulado e devolve o desempenho esperado (R², MAE, RMSE) |
| `POST /predict` | devolve o CSV de previsões; se o arquivo tiver a coluna `time`, devolve também o desempenho real |
| `POST /reset` | apaga o modelo para treinar com outra base |
| `GET /status` | informa se há modelo treinado e as métricas esperadas |
| `GET /health` | verificação de saúde do container |

A documentação interativa fica em `/docs` na URL da API.

## Como rodar

### Pré-requisito: arquivo `.env`

Copie o `.env.example` para `.env` e preencha a variável `alpha` com a tabela de cifra (pedir ao grupo). O `.env` nunca vai para o repositório.

```bash
cp .env.example .env
```

### Docker Compose (local)

```bash
docker compose up --build
```

- cliente: http://localhost:8501
- API: http://localhost:8001/docs

O modelo fica salvo em `./data`.

### Cliente local apontando para a API na Azure

```bash
cd client
pip install -r requirements.txt
API_URL=<URL da API> streamlit run client.py
```

## Uso

1. **Treinar:** enviar o CSV de treino (com a coluna `time`) e ver o desempenho esperado.
2. **Testar:** enviar um CSV com `time` e comparar o desempenho real com o esperado.
3. **Aplicar:** enviar um CSV sem `time` e baixar as previsões.
4. **Resetar:** apagar o modelo antes de treinar com outra base.

## Variáveis de ambiente

| Variável | Onde | Descrição |
|---|---|---|
| `alpha` | API e cliente | tabela da criptografia (segredo) |
| `API_URL` | cliente | endereço da API |
| `STORAGE_BACKEND` | API | `local` (pasta) ou `azure` (Blob Storage) |
| `LOCAL_MODEL_DIR` | API | pasta do modelo quando `STORAGE_BACKEND=local` |
| `AZURE_STORAGE_ACCOUNT`, `AZURE_STORAGE_CONTAINER`, `AZURE_CLIENT_ID` | API | Blob Storage e identidade gerenciada quando `STORAGE_BACKEND=azure` |

## Documentação

As decisões de arquitetura, os recursos da Azure, os problemas encontrados e os comandos de deploy estão em [docs/decisoes.md](docs/decisoes.md).
