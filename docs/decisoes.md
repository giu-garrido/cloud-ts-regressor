# Registro de decisões — cloud-ts-regressor

Este documento registra as escolhas de arquitetura, ferramentas e infraestrutura do projeto, com o motivo de cada uma e as alternativas descartadas. Serve de referência para o grupo e de apoio para a arguição.

**Última atualização:** 21/11/2026
**Entrega:** 23/11/2026, 23:30 (arguição no mesmo dia, com as bases de teste e aplicação entregues na hora)

---

## Contexto

O Projeto Integrador pede um algoritmo de **regressão linear** treinado e executado **remotamente**, com:

- upload de CSV para treino (com rótulos) e retorno de uma **expectativa de desempenho**;
- upload de CSV para teste/aplicação:
  - **com rótulos** → CSV de previsões para download + desempenho real;
  - **sem rótulos** → só o CSV de previsões;
- tratamento de dados necessário ao algoritmo (o enunciado cita normalização min-max como *exemplo*);
- arquivos tratados **ponta a ponta** (compactação e/ou criptografia implementadas pelo grupo);
- possibilidade de **resetar** o modelo para treinar com outra base.

A base é uma série temporal: o valor da coluna `time` é previsto a partir das observações dos **5 momentos anteriores** (`time-5` … `time-1`).

### Critérios de avaliação

| Critério | Pontos | Como o projeto atende |
|---|---|---|
| Treino do modelo em nuvem | 2 | `/train` no Azure Container Apps; modelo salvo no Blob Storage |
| Execução do modelo em nuvem (aplicação e teste) | 4 | `/predict` aceita CSV com `time` (teste) e sem `time` (aplicação) |
| Tratamento de dados ponta a ponta | 2 | CSV cifrado no cliente, decifrado na API, resposta cifrada de volta (D09) |
| Comparação de desempenho real e esperado | 2 | métricas esperadas no `/train`; esperadas + reais no `/predict` com rótulos (D12) |

---

## Visão geral da arquitetura

```
Cliente Streamlit (local ou Docker)
   │  cifra o CSV (crypto.py + tabela alpha)
   ▼
API FastAPI (container no Azure Container Apps)
   │  decifra → valida colunas
   │  StandardScaler (ajustado só no treino) → Regressor (SGD próprio)
   │  modelo + scaler + metadados persistidos no Blob Storage
   │  cifra o CSV de previsões; métricas vão em cabeçalhos HTTP (JSON)
   ▼
Cliente decifra, mostra métricas e gráficos, oferece download
```

Endpoints:

| Endpoint | Função |
|---|---|
| `POST /train` | decifra, treina, calcula o desempenho esperado e salva modelo + scaler |
| `POST /predict` | gera previsões cifradas; se o CSV tiver `time`, devolve também as métricas reais |
| `POST /reset` | apaga modelo e metadados do storage |
| `GET /status` | informa se há modelo treinado e as métricas esperadas |
| `GET /health` | verificação de saúde do container |

URL pública: ver no portal da Azure (Container App `cloud-ts-api` → Visão geral → URL do aplicativo). Documentação interativa em `/docs`.

---

## Decisões

Status possíveis: ✅ adotada · 🔄 em andamento · 📋 planejada · ❌ descartada

### D01 — Sem licença ✅

- **Decisão:** o repositório fica **sem licença** (todos os direitos reservados aos autores).
- **Alternativa descartada:** MIT, que chegou a ser proposta. O grupo preferiu não liberar reuso de um trabalho acadêmico avaliado.

### D02 — Nuvem: Azure for Students ✅

- **Motivo:** sem custo (US$ 100 em créditos, sem cartão, válidos por 12 meses).
- **Alternativas consideradas:** containers locais com Docker Compose (permitido pelo enunciado), Google Cloud Run, Render.
- **Plano B:** o projeto também roda com `docker compose up` local (D13).

### D03 — Controle de custos: alerta de orçamento ✅

- **Decisão:** budget mensal de **US$ 10** com dois alertas por e-mail:
  - *Actual* em 50% (US$ 5 gastos);
  - *Forecasted* em 100% (projeção de passar de US$ 10 no mês).
- **Observação:** o alerta só avisa, não desliga nada. Quando o crédito de estudante acaba, a Microsoft desativa a assinatura em vez de cobrar.

### D04 — Computação: Azure Container Apps (ambiente *express*) ✅

- **Decisão:** a API roda como container no Azure Container Apps, região `brazilsouth`, num ambiente do tipo *express* (`env-cloud-ts`).
- **Motivo:** roda o container direto, escala a zero sem uso (custo quase nulo) e tem URL pública imediata.
- **Limitações do ambiente express que afetam o projeto:**
  - não suporta identidade gerenciada *system-assigned* (ver D07);
  - volumes só do tipo `EmptyDir`, apagados quando o container reinicia (ver D08);
  - sem ACR Tasks (ver D05).
- **Para o dia da arguição:** abrir a URL uns 5 minutos antes (ou configurar `min replicas = 1`) para evitar a demora do *cold start*, de cerca de 30 s.

### D05 — Build da imagem: Docker local + push para o registry ✅

- **Problema:** o build na nuvem (`az acr build` / `az containerapp up --source`) usa o **ACR Tasks**, suspenso em assinaturas com crédito gratuito (erro `TasksOperationsNotAllowed`).
- **Decisão:** construir a imagem localmente com `docker buildx` para `linux/amd64` e enviar direto ao ACR:
  - `--platform linux/amd64` garante que roda na Azure mesmo se buildada em outra arquitetura;
  - `oci-mediatypes=true` evita erro de manifesto no Container Apps;
  - cada versão tem tag nova (`v2-oci`, `v3-cifra`…), **nunca `latest`**, para que o update crie uma revisão nova e o rollback seja trocar a tag.
- **Descartado:** build automático no GitHub Actions. Com o admin do ACR desligado (D07), exigiria configurar login federado (OIDC), e não compensava no prazo.

### D06 — Registry: Azure Container Registry (ACR) ✅

- **Decisão:** usar o ACR (`ca1770811e71acr`, SKU Basic).
- **Motivo:** o grupo quis aprender o serviço de registry nativo da Azure, que se integra ao Container Apps pela identidade gerenciada (D07).
- **Alternativa considerada:** GitHub Container Registry (`ghcr.io`), gratuito para imagens públicas. Continua sendo a opção para economizar os ~US$ 5/mês do ACR depois da entrega.

### D07 — Autenticação do app no registry e no storage: identidade gerenciada *user-assigned* ✅

- **Decisão:** a identidade `id-cloud-ts` tem `AcrPull` no registry e acesso aos blobs do Storage. O **usuário admin do ACR está desligado**.
- **Motivo:** nenhuma senha na configuração e princípio do menor privilégio.
- **Por que não *system-assigned*:** não é suportada no ambiente express (erro `ExpressEnvironmentFeatureNotSupported`). A *user-assigned* é a recomendada pela Microsoft para puxar imagens.
- **No código:** `storage.py` usa `DefaultAzureCredential` com `AZURE_CLIENT_ID` da identidade.

### D08 — Persistência do modelo: Azure Blob Storage ✅

- **Decisão:** salvar o modelo (`joblib`: regressor + scaler) e os metadados (features, coluna alvo, métricas esperadas) no container `modelos` do Storage `storagecloud001`.
- **Motivo:** o Container Apps pode reiniciar o container a qualquer momento e o ambiente express só oferece `EmptyDir`. Sem persistência externa, o modelo sumiria entre o treino e o teste.
- **Abstração:** `storage.py` tem dois backends, escolhidos por `STORAGE_BACKEND`:
  - `azure` → Blob Storage (produção);
  - `local` → pasta `LOCAL_MODEL_DIR` (plano B e testes).
- **Reset:** o `/reset` apaga os blobs do modelo.

### D09 — Tratamento ponta a ponta: criptografia própria por substituição homofônica ✅

- **Decisão:** cada valor numérico vira centavos (×100), é escrito em hexadecimal e cada dígito hex é trocado por um símbolo sorteado entre vários possíveis da tabela `alpha`. Marcadores: `~` para negativo, `;` separador, `__NaN__` para ausente.
- **Motivo:** o enunciado pede tratamento **implementado pelo grupo**. A substituição homofônica (vários símbolos por dígito, escolhidos ao acaso) faz o mesmo valor gerar textos diferentes a cada envio, o que dificulta análise de frequência.
- **Onde atua:** cliente cifra o CSV → API decifra → API cifra o CSV de previsões → cliente decifra. As métricas vão em cabeçalhos HTTP, não cifradas, porque não são dado do usuário.
- **Segredo da tabela:**
  - local: variável `alpha` no `.env` (fora do git; `.env.example` mostra só o nome);
  - Azure: secret `alpha-tabela` no Container App, exposto como `alpha=secretref:alpha-tabela`;
  - é definido pelo **Cloud Shell**, porque o shell do Windows corrompe as aspas e os caracteres especiais do JSON;
  - a conferência entre cópias é feita só pelo hash SHA-256, nunca imprimindo o valor.
- **Descartado:** compactação (gzip). As bases do Canvas têm entre 3,2 KB (`PI_application-1.csv`) e 8,3 KB (`PI_train.csv`); o ganho de tamanho não apareceria no tempo de resposta.

### D10 — Normalização: `StandardScaler` ajustado só no treino ✅

- **Decisão:** o `/train` ajusta um `StandardScaler` **apenas no `X_train`**, aplica em validação e teste, e salva o scaler junto com o modelo. O `/predict` reaplica o mesmo scaler.
- **Motivo:** o gradiente descendente precisa de features na mesma escala para convergir. O enunciado cita min-max só como exemplo; padronização (média 0, desvio 1) atende igual.
- **Correção feita em 21/11:** a normalização estava duplicada (no `prepare_data` do `model.py` e no `/train`) e depois triplicada (no `Regressor.predict`). As previsões saíam entre −29 400 e 23 413 para um alvo entre 0 e 718. Ficou só a do `/train`.

### D11 — Modelo: regressor linear próprio com SGD ✅

- **Decisão:** `model.py` implementa a regressão linear do zero, treinada por gradiente descendente estocástico, com busca do coeficiente de aprendizado (0,0001 a 0,05) pelo melhor R² na validação.
- **Divisão dos dados:** `train_test_split` aleatório (`random_state=42`): 64% treino, 16% validação, 20% teste.
- **Ponto de atenção para a arguição:** a divisão é aleatória, não temporal. Como cada linha já traz as 5 defasagens como colunas, o modelo treina sem depender da ordem das linhas; ainda assim, uma divisão cronológica seria mais rigorosa para série temporal.

### D12 — Desempenho esperado vs real ✅

- **Métricas:** R², RMSE e MAE.
- **Esperado:** calculado no `/train` sobre os 20% de teste separados; salvo nos metadados e devolvido no JSON do treino.
- **Real:** calculado no `/predict` quando o CSV tem a coluna alvo.
- **Transporte:** cabeçalhos `X-Metricas-Esperadas` e `X-Metricas-Reais`, em JSON (`json.dumps`), porque o corpo da resposta é o CSV de previsões.
- **Referência na base `PI_test-1.csv`:** modelo do grupo R² 0,14 / MAE 101,6 / RMSE 122,7; baseline ingênuo (`time-1`) MAE ≈ 102; `sklearn` LinearRegression com min-max R² ≈ 0,20 / MAE ≈ 87.
- **Bases do Canvas:** `PI_application-1.csv` é o `PI_test-1.csv` sem a coluna `time`. A comparação real vs esperado precisa ser feita com o `PI_test-1.csv`.

### D13 — Plano B: Docker Compose local ✅

- **Decisão:** `docker-compose.yml` sobe dois serviços:
  - `api`: porta **8001** do host → 8000 do container (a 8000 costuma estar ocupada), `STORAGE_BACKEND=local`, modelo em `./data`;
  - `client`: Streamlit na porta 8501, com `API_URL=http://api:8000`.
- Ambos leem o `alpha` do `.env` (`env_file`). O `docker compose config` mostra `$` como `$$`; é só escape, o valor chega certo.
- **Uso:** `docker compose up --build` e abrir `http://localhost:8501`.

### D14 — Cliente publicado na Azure ✅

- **Decisão:** o cliente Streamlit roda como segundo Container App (`cloud-ts-client`), no mesmo ambiente e com a mesma identidade, para ter um link pronto na arguição (URL no portal da Azure, em `cloud-ts-client` → Visão geral).
- **Configuração:** porta 8501, 0,5 vCPU e 1 GiB (Streamlit com matplotlib e plotly passa dos 0,5 GiB), `min-replicas 0` e `max-replicas 1` (o Streamlit guarda a sessão em memória; com duas réplicas o usuário perderia o estado).
- **Segredo:** secret `alpha-tabela` copiado do `cloud-ts-api` pelo Cloud Shell, sem colar o JSON; `API_URL` aponta para a API.
- **Ponto de atenção:** com o cliente na nuvem, o CSV sai do navegador em texto (protegido só por HTTPS) e é cifrado no servidor do cliente. Para mostrar a cifra saindo da própria máquina, usar o cliente local (D13).

---

## Recursos no Azure

| Recurso | Nome | Observação |
|---|---|---|
| Assinatura | Azure for Students | US$ 100 em créditos |
| Resource Group | `rg-cloud-ts-regressor` | agrupa todos os recursos do projeto |
| Ambiente do Container Apps | `env-cloud-ts` | tipo *express*, região `brazilsouth` |
| Container App | `cloud-ts-api` | ingress externo, porta 8000, imagem `v3-cifra` |
| Container App | `cloud-ts-client` | ingress externo, porta 8501, imagem `cloud-ts-client:v1` (D14) |
| Container Registry | `ca1770811e71acr` | SKU Basic, admin desligado; único custo fixo (~US$ 5/mês) |
| Identidade gerenciada | `id-cloud-ts` | *user-assigned*; `AcrPull` + acesso ao Storage (D07) |
| Storage Account | `storagecloud001` | Standard_LRS; container `modelos` (D08) |
| Log Analytics | `workspace-rgcloudtsregressor05x8` | criado automaticamente |

Tags no ACR:
- `cloud-ts-api`: `v1`, `v2`, `v2-oci`, `v3-cifra` (atual: com criptografia na entrada e na saída e normalização corrigida);
- `cloud-ts-client`: `v1` (coluna alvo padrão em `time`).

Resource providers registrados na assinatura: `Microsoft.App`, `Microsoft.OperationalInsights`, `Microsoft.ContainerRegistry`.

---

## Problemas encontrados e soluções

| Erro | Causa | Solução |
|---|---|---|
| `[Errno 98] Address already in use` (local) | outro processo usando a porta 8000 | API local na porta 8001 (D13) |
| `--source ./server` executado de dentro de `server/` | caminho relativo errado | rodar da raiz do repo |
| `MissingSubscriptionRegistration` | provider nunca usado na assinatura | `az provider register --namespace <provider> --wait` |
| `TasksOperationsNotAllowed` | ACR Tasks suspenso em assinaturas de crédito gratuito | build local com `docker buildx` + push (D05) |
| `ExpressEnvironmentFeatureNotSupported` | identidade *system-assigned* não suportada no express | identidade *user-assigned* (D07) |
| JSON do `alpha` corrompido ao criar o secret | `az.cmd`/cmd.exe no Windows mexe em aspas e `& \| ^ % !` | definir o secret pelo Cloud Shell e conferir pelo hash |
| `UnicodeEncodeError` ao imprimir no terminal | console Windows em cp1252 | `PYTHONIOENCODING=utf-8` |
| Previsões entre −29 400 e 23 413 | normalização aplicada 2–3 vezes | só o scaler do `/train` (D10) |
| `SyntaxError` em `app.py`, `crypto.py`, `client.py` | merge commitado com marcadores `<<<<<<<` | conflitos resolvidos em 21/11; conferir com `grep -rn "^<<<<<<<" server client` antes de commitar |
| `CERTIFICATE_VERIFY_FAILED` no Python e no `az` | Norton Antivirus intercepta HTTPS com certificado próprio | exceção no Norton para o domínio, ou `REQUESTS_CA_BUNDLE` com o certificado raiz do Norton |
| Métricas ilegíveis no cliente | cabeçalho enviado como `str(dict)` (aspas simples) | `json.dumps` na API e `json.loads` no cliente |

---

## Comandos de referência

Variáveis usadas abaixo (redefinir a cada terminal novo):

```bash
ACR=ca1770811e71acr
RG=rg-cloud-ts-regressor
TAG=v4   # sempre uma tag nova
```

Build e push de uma nova versão (da raiz do repo):

```bash
az acr login -n $ACR
docker buildx build --platform linux/amd64 \
  -t $ACR.azurecr.io/cloud-ts-api:$TAG \
  --output type=registry,oci-mediatypes=true ./server
```

Atualizar o app e conferir a revisão:

```bash
az containerapp update -n cloud-ts-api -g $RG --image $ACR.azurecr.io/cloud-ts-api:$TAG
az containerapp revision list -n cloud-ts-api -g $RG \
  --query "[].{rev:name, img:properties.template.containers[0].image, ativo:properties.active, saude:properties.healthState}" -o table
```

Voltar para a versão anterior: o mesmo `update` com a tag antiga.

Logs do container:

```bash
az containerapp logs show -n cloud-ts-api -g $RG --tail 50
```

Listar imagens e versões no registry:

```bash
az acr repository show-tags -n $ACR --repository cloud-ts-api -o table
```

Rodar o cliente local apontando para a Azure:

```bash
cd client
API_URL=<URL da cloud-ts-api> streamlit run client.py
```

---

## Próximos passos

- [x] Identidade *user-assigned* e admin do ACR desligado (D07)
- [x] `data/` e `*.joblib` no `.gitignore`
- [x] `model.py` com regressor próprio e métricas (D11, D12)
- [x] `/train`, `/predict`, `/status`, `/reset` e criptografia na entrada e na saída (D09)
- [x] Storage Account e persistência do modelo no Blob (D08)
- [x] Cliente Streamlit com métricas e gráficos
- [x] Docker Compose funcionando localmente como plano B (D13)
- [x] Imagem `v3-cifra` publicada e teste ponta a ponta cifrado na Azure (21/11)
- [x] Seletor de coluna alvo do cliente começando em `time`
- [x] Cliente publicado na Azure (D14)
- [ ] Merge `dev` → `main` via PR
- [ ] Ensaio da arguição simulando uma base nova
