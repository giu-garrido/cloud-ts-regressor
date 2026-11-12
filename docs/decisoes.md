# Registro de decisões — cloud-ts-regressor

Este documento registra as escolhas de arquitetura, ferramentas e infraestrutura do projeto, com o motivo de cada uma e as alternativas descartadas. Serve de referência para o grupo e de apoio para a arguição.

**Última atualização:** 29/10/2026
**Entrega:** 23/11/2026, 23:30 (arguição no mesmo dia, com as bases de teste e aplicação entregues na hora)

---

## Contexto

O Projeto Integrador pede um algoritmo de **regressão linear** treinado e executado **remotamente**, com:

- upload de CSV para treino (com rótulos) e retorno de uma **expectativa de desempenho**;
- upload de CSV para teste/aplicação:
  - **com rótulos** → CSV de previsões para download + desempenho real;
  - **sem rótulos** → só o CSV de previsões;
- tratamento de dados necessário ao algoritmo (ex.: normalização min-max);
- arquivos tratados **ponta a ponta** (compactação e/ou criptografia implementadas pelo grupo);
- possibilidade de **resetar** o modelo para treinar com outra base.

A base é uma série temporal: o valor da coluna `time` é previsto a partir das observações dos **5 momentos anteriores**.

### Critérios de avaliação

| Critério | Pontos |
|---|---|
| Treino do modelo em nuvem | 2 |
| Execução do modelo em nuvem (aplicação e teste) | 4 |
| Tratamento de dados ponta a ponta | 2 |
| Comparação de desempenho real e esperado | 2 |

---

## Visão geral da arquitetura

```
Cliente
   │  
   ▼
API FastAPI (container no Azure Container Apps)
   │  decifra → descompacta → valida schema
   │  Pipeline(MinMaxScaler → LinearRegression)
   │  modelo + metadados persistidos (Blob Storage)
   ▼
Resposta  →  Cliente decifra e oferece download
```

Endpoints planejados:

| Endpoint | Função |
|---|---|
| `POST /train` | treina, calcula o desempenho esperado e salva o modelo |
| `POST /predict` | gera previsões; se o CSV tiver `time`, devolve também as métricas reais |
| `POST /reset` | apaga modelo e metadados |
| `GET /status` | informa se há modelo treinado e as métricas esperadas |
| `GET /health` | verificação de saúde do container |

---

## Decisões

Status possíveis: ✅ adotada · 🔄 em andamento · 📋 planejada · ❌ descartada

### D01 — Licença MIT ✅

- **Motivo:** permissiva e curta; permite reuso mantendo o crédito do grupo.
- **Alternativa descartada:** GPL-3.0 (restritiva demais para um projeto acadêmico).
- **Observação:** atualizar o copyright com os nomes do grupo quando ele estiver fechado.

### D02 — Nuvem: Azure for Students ✅

- **Motivo:** Sem custo: US$ 100 em créditos, sem cartão, válidos por 12 meses.
- **Alternativas consideradas:** containers locais com Docker Compose (permitido pelo enunciado), Google Cloud Run, Render.
- **Plano B:** manter o projeto rodando também com `docker compose up` local, caso a internet falhe no dia.

### D03 — Controle de custos: alerta de orçamento ✅

- **Decisão:** budget mensal de **US$ 10** com dois alertas por e-mail:
  - *Actual* em 50% (US$ 5 gastos);
  - *Forecasted* em 100% (projeção de passar de US$ 10 no mês).
- **Observação:** o alerta só avisa, não desliga nada. Quando o crédito de estudante acaba, a Microsoft desativa a assinatura em vez de cobrar.

### D04 — Computação: Azure Container Apps (ambiente *express*) ✅

- **Decisão:** a API roda como container no Azure Container Apps, região `brazilsouth`, criada com `az containerapp up` (que gerou um ambiente do tipo *express*).
- **Motivo:** roda o container direto, escala a zero sem uso (custo quase nulo) e tem URL pública imediata.
- **Limitações do ambiente express que afetam o projeto:**
  - não suporta identidade gerenciada *system-assigned* (ver D15);
  - volumes só do tipo `EmptyDir`, que são apagados quando o container reinicia (ver D16).
- **Para o dia da arguição:** configurar `min replicas = 1` para evitar a demora do *cold start*.

### D13 — Build da imagem: Docker local + push para o registry ✅

- **Problema:** o `az containerapp up --source` usa o **ACR Tasks** (build na nuvem), que o Azure **suspendeu para assinaturas pagas com crédito gratuito**, incluindo o Azure for Students (erro `TasksOperationsNotAllowed`).
- **Decisão:** construir a imagem localmente com Docker e enviar a imagem pronta ao registry (`docker build` → `docker push`).
- **Evolução possível:** build automático no GitHub Actions com push para o ACR, para que ninguém do grupo precise de Docker local.

### D14 — Registry: Azure Container Registry (ACR) ✅

- **Decisão:** usar o ACR (`ca1770811e71acr`, SKU Basic).
- **Motivo:** objetivo de aprender o ACR, que é o padrão em ambientes Azure corporativos.
- **Alternativa considerada:** GitHub Container Registry (`ghcr.io`), gratuito para imagens públicas e com build via GitHub Actions sem token extra. Descartada por enquanto, mas continua sendo a opção para economizar os ~US$ 5/mês do ACR.

### D15 — Autenticação do app no registry: identidade gerenciada *user-assigned* 🔄

- **Situação atual:** o app puxa a imagem com o **usuário admin** do ACR (senha compartilhada).
- **Decisão:** trocar por uma identidade gerenciada *user-assigned* (`id-cloud-ts`) com permissão `AcrPull` no registry e, depois de validar, desligar o admin.
- **Motivo:** elimina senhas na configuração e aplica o princípio do menor privilégio (a identidade só lê imagens).
- **Por que não *system-assigned*:** não é suportada no ambiente express (erro `ExpressEnvironmentFeatureNotSupported`). A *user-assigned* é, inclusive, a recomendada pela Microsoft para puxar imagens.

### D16 — Persistência do modelo: Azure Blob Storage 📋

- **Decisão:** salvar o pipeline treinado (`joblib`) e os metadados (colunas, métricas esperadas, data, hash da base) em um container do Blob Storage.
- **Motivo:** o Container Apps pode reiniciar o container a qualquer momento, e o ambiente express só oferece volumes `EmptyDir`, que se perdem no restart. Sem persistência externa, o modelo treinado sumiria entre o treino e o teste.
- **Reset:** o `/reset` apaga os blobs do modelo.

---

## Recursos no Azure

| Recurso | Nome | Observação |
|---|---|---|
| Assinatura | Azure for Students | US$ 100 em créditos |
| Resource Group | `rg-cloud-ts-regressor` | agrupa todos os recursos do projeto |
| Ambiente do Container Apps | `env-cloud-ts` | tipo *express*, região `brazilsouth` |
| Container App | `cloud-ts-api` | ingress externo, porta 8000 |
| Container Registry | `ca1770811e71acr` | SKU Basic; único custo fixo (~US$ 5/mês) |
| Log Analytics | `workspace-rgcloudtsregressor05x8` | criado automaticamente |
| Identidade gerenciada | `id-cloud-ts` | 🔄 a criar (D15) |
| Storage Account | — | 📋 a criar (D16) |

Resource providers registrados na assinatura: `Microsoft.App`, `Microsoft.OperationalInsights`, `Microsoft.ContainerRegistry`.

---

## Problemas encontrados e soluções

| Erro | Causa | Solução |
|---|---|---|
| `[Errno 98] Address already in use` (local) | outro processo usando a porta 8000 | rodar com `--port 8001` ou encerrar o processo (`ss -ltnp \| grep :8000`) |
| `--source ./server` executado de dentro de `server/` | caminho relativo errado | rodar da raiz do repo, ou usar `--source .` |
| `MissingSubscriptionRegistration` | provider nunca usado na assinatura | `az provider register --namespace <provider> --wait` |
| `TasksOperationsNotAllowed` | ACR Tasks suspenso em assinaturas de crédito gratuito | build local com Docker + push (D13) |
| `ExpressEnvironmentFeatureNotSupported` | identidade *system-assigned* não suportada no express | usar identidade *user-assigned* (D15) |

---

## Comandos de referência

Variáveis usadas abaixo (redefinir a cada terminal novo):

```bash
ACR=ca1770811e71acr
RG=rg-cloud-ts-regressor
```

Build e push de uma nova versão:

```bash
az acr login -n $ACR
docker build -t $ACR.azurecr.io/cloud-ts-api:v2 ./server
docker push $ACR.azurecr.io/cloud-ts-api:v2
```

Atualizar o app para a nova versão:

```bash
az containerapp update -n cloud-ts-api -g $RG --image $ACR.azurecr.io/cloud-ts-api:v2
```

Listar imagens e versões no registry:

```bash
az acr repository list -n $ACR -o table
az acr repository show-tags -n $ACR --repository cloud-ts-api -o table
```

---

## Próximos passos

- [ ] Configurar a identidade *user-assigned* e desligar o admin do ACR (D15)
- [ ] Adicionar `data/` e `*.joblib` ao `.gitignore`
- [ ] EDA da base de treino e definição do schema
- [ ] Implementar `model.py` com validação temporal e baseline (D04–D06)
- [ ] Implementar `/train`, `/status`, `/reset` e o módulo de criptografia (D08)
- [ ] Criar o Storage Account e persistir o modelo no Blob (D16)
- [ ] Implementar `/predict` com e sem rótulos
- [ ] Cliente Streamlit com gráficos (D09)
- [ ] Docker Compose funcionando localmente como plano B (D10)
- [ ] Adicionar os colegas como *Contributor* no Resource Group quando o grupo fechar
- [ ] Ensaio da arguição simulando uma base nova

### Cronograma

| Período | Foco |
|---|---|
| 29/10 – 04/11 | repo, esqueleto, deploy de teste, EDA, schema |
| 05/11 – 11/11 | modelo com validação temporal; `/train`, `/status`, `/reset`; criptografia |
| 12/11 – 18/11 | `/predict`; cliente Streamlit; persistência no Blob; teste ponta a ponta com as bases do Canvas |
| 19/11 – 23/11 | ensaio da arguição, README, folga para bugs, entrega |
