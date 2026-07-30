# Plano de Implementações — Próxima Onda

> Baseado em inspeção real do código em `develop`@`4cbe583`.
> Nenhum item aqui é hipotético — parte de gaps confirmados no código
> (`grep`, leitura de router, leitura de `docker-compose.yml`) ou do
> plano original do projeto (`docs/plano-implementacao-python.md`,
> branch `doc`).

---

## Sumário

| # | Item | Bloco | Prioridade |
|---|---|---|---|
| 1 | Cardápio digital / de-para de SKU externo | B1 | **Alta** |
| 2 | Health checks reais (liveness/readiness) | C4 | Alta |
| 3 | Rate limiting distribuído (Redis) | A3 | Média-alta |
| 4 | TLS/HTTPS na borda | A1 | Média (pré-deploy) |
| 5 | Bot WhatsApp conversacional | B2 | Média |
| 6 | Notificações de status externo | B3 | Média |
| 7 | Backup automatizado do Postgres | C1 | Média |
| 8 | LGPD — consentimento e retenção | C2 | Média |
| 9 | Rotação de secrets (JWT `kid`) | A2 | Baixa-média |
| 10 | Observabilidade de segurança (métricas + alertas) | A5 | Baixa-média |
| 11 | Grafana + Loki | C3 | Baixa |
| 12 | Testes de carga/performance | A4 | Baixa |
| 13 | Migração para Kubernetes | C5 | Baixa (destino final) |

---

## 1. Cardápio digital + de-para de SKU externo (B1)

### Por que é prioridade máxima

Não é uma feature nova — é a correção de um bug de integração já
comprovado no código. `anotaai/worker/app/tasks.py`, função
`_normalizar_itens()`, tem um TODO explícito confessando o problema:

```python
def _normalizar_itens(items_originais: list[dict]) -> list[dict]:
    """TODO (fora do escopo desta feature): assume que `id_produto` já
    vem no payload. Num catálogo real, o provedor referencia produtos
    pelo próprio SKU dele, e precisaríamos de uma tabela de-para..."""
    return [{"id_produto": item["id_produto"], ...} for item in items_originais]
```

Um pedido real do iFood referencia produtos pelo SKU do catálogo do
iFood, não pelo UUID interno da `ecletica-api`. Hoje, `item["id_produto"]`
provavelmente lança `KeyError` ou recebe um valor que não existe na
tabela `produto` — o pedido falha silenciosamente (a task do Celery
falha, tenta de novo 3x com backoff, e desiste).

### Escopo técnico

**Novo modelo (ecletica-api, dono do catálogo):**
```python
class MapeamentoSkuExterno(SQLModel, table=True):
    __tablename__ = "mapeamento_sku_externo"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    id_loja: uuid.UUID = Field(foreign_key="loja.id", index=True)
    id_produto: uuid.UUID = Field(foreign_key="produto.id", index=True)
    provedor: str  # "IFOOD" | "WHATSAPP"
    sku_externo: str
    # unique constraint (id_loja, provedor, sku_externo)
```

**Endpoints novos (ecletica-api):**
- `POST /produtos/{id}/mapear-sku` — vincula um SKU externo a um produto (ADMIN/GERENTE)
- `GET /cardapio` — **público, sem autenticação**, retorna produtos ativos por loja (para QR code e para o worker resolver SKU→produto)

**Mudança no worker:**
```python
def _resolver_produto(provedor: str, sku_externo: str, id_loja: str) -> uuid.UUID:
    # GET ecletica-api /produtos/mapeamento?provedor=...&sku=...
    # cache local (Redis, TTL curto) pra não bater na API a cada item
```

**Painel admin mínimo (novo):**
- FastAPI + Jinja2 + HTMX servindo `/admin/produtos` (como o doc original já especifica — sem SPA, sem build JS)
- CRUD de produto + tela de mapeamento de SKU
- Autenticação reaproveitando o JWT existente (ADMIN/GERENTE)

**Migração:** nova tabela via Alembic, mesma convenção das anteriores
(`op.create_table`, revision encadeada no head atual do ecletica).

**Testes:**
- `test_cardapio_publico_nao_exige_auth` (sem header, espera 200)
- `test_mapear_sku_exige_admin` (403 pra GARCOM)
- `test_worker_resolve_sku_ifood_para_produto_interno` (mock da chamada HTTP)
- Regressão: `test_ingestao_externa_e_idempotente` (já existe) precisa continuar passando com o novo fluxo de resolução

**Ordem de entrega sugerida:** modelo + migração → endpoint de mapeamento → endpoint público `/cardapio` → ajuste do worker → painel admin (pode ser a última fatia, é a que menos bloqueia o resto).

---

## 2. Health checks reais (C4)

### Gap

```python
@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "ecletica-api"}
```

Não toca o banco. Um Postgres fora do ar não aparece aqui — o processo
Python continua "vivo" mesmo que toda requisição real esteja falhando
com 500.

### Escopo técnico

Separar liveness de readiness (semântica padrão Kubernetes, mas útil
mesmo em Compose puro):

```python
@app.get("/health/live")
def live() -> dict:
    """Processo está de pé. Nunca toca dependência externa."""
    return {"status": "ok"}

@app.get("/health/ready")
def ready(session: Session = Depends(get_session)) -> Response:
    """Pronto pra receber tráfego real: banco responde."""
    try:
        session.exec(select(1))
        return {"status": "ok"}
    except Exception:
        raise HTTPException(status_code=503, detail="Banco indisponível")
```

Manter `/health` como alias de `/health/live` por compatibilidade (não
quebrar nada que já aponte pra ele — ex: `depends_on: condition:
service_healthy` no `docker-compose.yml`, se algum dia for adicionado).

**`docker-compose.yml`:** adicionar `healthcheck` nos serviços `ecletica-api`/`anotaai-api` apontando pra `/health/ready`, igual já existe pro `postgres`.

**Testes:** `test_health_ready_falha_com_banco_indisponivel` — precisa de um jeito de simular sessão quebrada (override do `get_session` pra levantar exceção). `test_health_live_nao_depende_de_nada` (sem override de dependência, sempre 200).

**Esforço:** pequeno, ~1-2h de implementação + testes. Bom primeiro item pra manter o ritmo depois de itens maiores.

---

## 3. Rate limiting distribuído — Redis-backed (A3)

### Gap

`slowapi` com storage padrão guarda contadores **na memória do
processo Python**. Funciona bem com uma réplica. Com N réplicas atrás
de um load balancer, cada réplica tem sua própria contagem — um
atacante distribuindo requisições entre elas efetivamente multiplica o
rate limit por N.

### Escopo técnico

`ecletica-api` e `anotaai-api` — mudança isolada em `core/rate_limit.py`:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address
from .config import settings

limiter = Limiter(key_func=get_remote_address, storage_uri=settings.rate_limit_storage_uri)
```

**Config novo:** `rate_limit_storage_uri: str = "redis://redis:6379/2"` (DB 2 do Redis — DB 0 é broker do Celery, DB 1 é result backend, ambos já em uso pelo `anotaai-worker`).

**`docker-compose.yml`:** `ecletica-api` hoje **não depende do Redis** —
precisa adicionar `depends_on: redis` e passar a variável de ambiente.
`anotaai-api` já está na mesma rede, só precisa da env var.

**Dependência nova:** `slowapi` já suporta Redis via `limits` (dependência transitiva) — confirmar se precisa adicionar `redis` explícito no `requirements.txt` do `ecletica-api` (hoje só o `anotaai-api` tem `redis==5.0.8`).

**Testes:** o desafio é não exigir Redis real rodando no CI (que hoje só usa SQLite in-memory, zero infra externa). Duas opções:
1. `fakeredis` como dependência de teste — simula Redis em memória, `slowapi` conversa com ele transparentemente
2. Manter storage in-memory nos testes (via override de config no `conftest.py`, `RATE_LIMIT_STORAGE_URI=memory://`) e só usar Redis em produção/staging

Opção 2 é mais simples e não adiciona dependência nova — recomendo essa. `limiter.reset()` (já usado nos testes existentes) continua funcionando igual.

**Risco a observar:** o padrão hoje usado nos testes (`limiter.reset()` no início de `test_login_rate_limiting`) depende do storage ser resetável de forma síncrona — confirmar que isso não muda de comportamento com storage diferente entre teste e produção.

---

## 4. TLS/HTTPS na borda (A1)

### Gap

`docker-compose.yml` expõe as APIs direto em HTTP nas portas 8000/8001.
O header `Strict-Transport-Security` (PR#25) é enviado mas inócuo — só
tem efeito depois que o navegador já visitou o site via HTTPS pelo
menos uma vez (é uma política de "não aceite downgrade", não uma
imposição de upgrade).

### Escopo técnico

Novo serviço no compose:

```yaml
nginx:
  image: nginx:alpine
  ports:
    - "443:443"
    - "80:80"  # só pra redirect
  volumes:
    - ./infra/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    - ./infra/nginx/certs:/etc/nginx/certs:ro
  depends_on:
    - ecletica-api
    - anotaai-api
```

`ecletica-api`/`anotaai-api` deixam de expor porta pro host (`ports:`
some do compose, viram só acessíveis dentro da rede docker).

**Config do nginx:** dois `server_name` (ou paths `/ecletica/`,
`/anotaai/` — decisão de produto, não técnica) com `proxy_pass` pros
serviços internos, redirect 301 de HTTP pra HTTPS.

**Certificados:**
- Dev local: `mkcert` (gera CA local confiável pelo SO, sem warning no navegador)
- Produção: `certbot` com renovação automática (cron dentro do próprio container nginx ou um serviço `certbot` dedicado, padrão comum de compose)

**Ajustes de config necessários:**
- `CORS_ALLOWED_ORIGINS` — se o domínio de produção mudar de esquema (http→https), precisa refletir isso
- `ANOTAAI_ECLETICA_API_URL` — comunicação interna serviço-a-serviço pode continuar em HTTP puro (é rede interna do compose, não sai pra internet) — **não** precisa passar pelo nginx

**Não bloqueante para dev:** esse item só importa de verdade quando houver deploy real acessível pela internet. Localmente, HTTP simples continua sendo produtivo — não vale a pena forçar TLS em dev se atrapalhar o fluxo do dia a dia.

---

## 5. Bot WhatsApp conversacional (B2)

### Gap

Hoje existe só a metade passiva: `POST /webhooks/whatsapp` recebe um
pedido **já pronto e estruturado**, valida assinatura, enfileira. Não
existe fluxo de conversa — cliente mandar "oi" no WhatsApp não aciona
nada porque não há como responder (`anotaai-worker` nunca envia
mensagem, só recebe).

### Pré-requisito

**Depende do item 1 (cardápio)** — não dá pra montar um fluxo "escolha
um item do cardápio via WhatsApp" sem o cardápio existir como dado
consultável.

### Escopo técnico

**Cliente de envio (novo, `anotaai/worker/app/whatsapp_client.py`):**
```python
def enviar_mensagem_whatsapp(numero_destino: str, texto: str) -> None:
    # POST https://graph.facebook.com/v.../messages (Meta Cloud API)
    # usa META_APP_SECRET / token de acesso já configurado
```

**Máquina de estados por conversa (Redis, TTL curto — ex 30min de inatividade expira a sessão):**
```
AGUARDANDO_INICIO
  → recebe "oi"/"menu" → envia cardápio (lista numerada) → AGUARDANDO_ITEM
AGUARDANDO_ITEM
  → recebe número → adiciona ao carrinho → AGUARDANDO_ITEM ou AGUARDANDO_CONFIRMACAO
AGUARDANDO_CONFIRMACAO
  → recebe "confirmar" → injeta comanda via /comandas/ingestao-externa → CONCLUIDO
```

Chave Redis: `whatsapp:conversa:{numero}` → JSON com estado + carrinho parcial.

**Mudança no `webhook_whatsapp` (anotaai-api):** hoje assume que todo
payload é um pedido completo. Precisa diferenciar "mensagem de texto
livre" (dispara a máquina de estados) de "pedido estruturado" (fluxo
atual, mantido pra compatibilidade com outros formatos de payload).

**Testes:** mockar a chamada de envio (não bater na Meta API de
verdade em teste), testar cada transição de estado isoladamente, testar
timeout/expiração de conversa.

**Risco de escopo:** esse é o item de maior superfície da lista inteira.
Vale quebrar em sub-entregas: (a) enviar mensagem simples primeiro, sem
máquina de estados, só pra validar a credencial/API da Meta funciona; (b)
depois a máquina de estados.

---

## 6. Notificações de status para canal externo (B3)

### Gap

O KDS (`PATCH /kds/tickets/{id}`) já publica atualização em tempo real
via WebSocket+Redis Pub/Sub (PR do RF07) — mas só a tela da cozinha
escuta isso. Um cliente que pediu pelo iFood/WhatsApp não sabe quando o
pedido ficou pronto.

### Pré-requisito

**Depende do item 5** pro canal WhatsApp (precisa do `enviar_mensagem_whatsapp`).

### Escopo técnico

Em `kds.py`, função `atualizar_status`, depois do `publicar_atualizacao_kds` existente:

```python
if novo_status == StatusProducao.PRONTO:
    comanda = _comanda_do_ticket(session, ticket)  # join via item_comanda
    if comanda.origem_externa == OrigemPedido.WHATSAPP:
        enviar_mensagem_whatsapp(comanda.id_referencia_externa, "Seu pedido está pronto!")
    elif comanda.origem_externa == OrigemPedido.IFOOD:
        # chamada à API de status do iFood, se o provedor expuser isso
        # (verificar documentação real da API do iFood — pode não existir endpoint de status)
        pass
```

**Nota importante:** a notificação pro iFood depende de o provedor
expor uma API de atualização de status de pedido — isso precisa ser
verificado na documentação real do parceiro iFood antes de prometer a
entrega (pode ser que só WhatsApp seja viável tecnicamente).

**Testes:** mockar `enviar_mensagem_whatsapp`, verificar que é chamado
só quando `status == PRONTO` e `origem_externa == WHATSAPP` — não
disparar notificação pra comanda de salão (`origem_externa is None`).

---

## 7. Backup automatizado do Postgres (C1)

### Gap

O próprio `docs/plano-implementacao-python.md` já lista isso como
requisito de segurança ("Backup automático do Postgres... antes de
qualquer deploy de produção") e não existe nenhuma automação hoje —
`docker-compose.yml` só declara o volume `postgres_data`, sem rotina de
dump.

### Escopo técnico

**Opção simples (recomendada pra começar):** serviço dedicado no compose rodando `pg_dump` agendado:

```yaml
postgres-backup:
  image: postgres:16-alpine
  environment:
    PGPASSWORD: ecletica
  volumes:
    - ./infra/postgres/backup.sh:/backup.sh:ro
    - postgres_backups:/backups
  entrypoint: ["sh", "-c", "while true; do /backup.sh; sleep 86400; done"]
```

`backup.sh`:
```bash
#!/bin/sh
DATA=$(date +%Y%m%d_%H%M%S)
pg_dump -h postgres -U ecletica ecletica > /backups/ecletica_$DATA.sql
pg_dump -h postgres -U ecletica anotaai > /backups/anotaai_$DATA.sql
find /backups -name "*.sql" -mtime +30 -delete  # retenção de 30 dias
```

**Teste de restore (crítico, frequentemente esquecido):** documentar e,
idealmente, automatizar um teste periódico que restaura o backup mais
recente num Postgres descartável e roda uma query de sanidade —
"backup que nunca foi restaurado não é backup, é esperança".

**Produção real:** para ambiente gerenciado (RDS, Cloud SQL), preferir
snapshot nativo do provedor em vez de `pg_dump` manual — esse escopo
aqui é para o cenário atual (Postgres em container próprio).

---

## 8. LGPD — consentimento e retenção de dados de cliente (C2)

### Gap

`Cliente` (ecletica-api) grava CPF sem qualquer campo de consentimento
ou política de expiração. O próprio doc do projeto já cita isso
("CPF e dados de cliente exigem consentimento e política de
retenção") — hoje é letra morta.

### Escopo técnico

**Migração de modelo:**
```python
class Cliente(SQLModel, table=True):
    ...  # campos existentes
    consentimento_em: datetime | None = None
    consentimento_finalidade: str | None = None  # ex: "fidelidade"
```

`cadastrar_cliente` passa a exigir `consentimento_finalidade` no
payload (recusa cadastro sem isso — decisão de produto: bloquear ou só
registrar ausência, precisa validar com quem toma decisão de negócio).

**Job de retenção (novo, Celery task periódica no worker ou script standalone):**
- Cliente sem `consentimento_em` há mais de N dias (configurável) → anonimizar (`nome="Cliente removido"`, `cpf` hasheado ou nulificado, mantendo `pontos_fidelidade` histórico agregado se necessário pra relatório)
- Rodar via Celery Beat (schedule periódico) — hoje o worker só tem tasks reativas (disparadas por evento), precisaria adicionar Beat como novo componente

**Testes:** `test_cadastro_sem_consentimento_bloqueia` (ou só registra —
depende da decisão de produto), `test_job_anonimiza_cliente_expirado`.

**Nota:** este item tem uma componente de decisão de produto/jurídico
maior que técnica — vale confirmar com quem entende de LGPD antes de
implementar a política de retenção específica (prazo, o que conta como
"consentimento válido", etc.) em vez de eu decidir isso unilateralmente
no código.

---

## 9. Rotação de secrets — JWT com `kid` (A2)

### Gap

PR#26 tornou os secrets obrigatórios (fail-fast no boot), mas o
`secret_key` é único e estático. Se vazar, **todo refresh token válido
(até 7 dias) permite gerar access tokens novos indefinidamente** — não
existe forma de invalidar "tokens assinados com a chave antiga" sem
invalidar literalmente todo mundo.

### Escopo técnico

**Formato de config novo:**
```python
# em vez de secret_key: str
jwt_keys: dict[str, str]  # {"2026-07": "chave-atual", "2026-04": "chave-anterior"}
jwt_current_kid: str  # "2026-07"
```

**`create_access_token`:** inclui `kid` no header do JWT (`jose`
suporta isso nativamente via `headers={"kid": ...}`), sempre assina com
`jwt_keys[jwt_current_kid]`.

**`decode_access_token`:** lê o `kid` do header do token recebido
(sem verificar assinatura ainda), busca a chave correspondente em
`jwt_keys`, só então decodifica/verifica com aquela chave específica.
Tokens assinados com chave que não está mais no dicionário (removida
após período de transição) passam a falhar naturalmente.

**Fluxo de rotação operacional:**
1. Adiciona nova chave ao dicionário, mantém `jwt_current_kid` na antiga por enquanto (chave nova existe mas não é usada pra assinar ainda — só pra permitir teste)
2. Muda `jwt_current_kid` pra nova chave — daqui pra frente, tokens novos usam a nova
3. Espera o tempo máximo de vida de um refresh token (7 dias) — todo token antigo já expirou naturalmente
4. Remove a chave antiga do dicionário

**Endpoint adicional:**
`POST /auth/revogar-todos` (ADMIN-only, por usuário-alvo) — marca todos
os `RefreshToken.revogado=True` de um usuário específico. Útil pra
resposta a incidente sem esperar rotação de chave completa (ex:
funcionário demitido, suspeita de token roubado específico).

**Prioridade real:** baixa até existir produção de verdade — em dev,
rotacionar secret nunca vai acontecer organicamente.

---

## 10. Observabilidade de segurança (A5)

### Gap

Prometheus já expõe métricas genéricas (latência, contagem por
endpoint, via `prometheus-fastapi-instrumentator`, PR#18). Não existe
nenhuma métrica dedicada a eventos de segurança — hoje só vira log JSON
estruturado, que ninguém consulta em tempo real sem abrir o log manualmente.

### Escopo técnico

**Métrica nova (Prometheus counter):**
```python
from prometheus_client import Counter

auth_failures = Counter(
    "auth_failures_total", "Falhas de autenticação/autorização",
    ["service", "reason"]  # reason: "credenciais_invalidas" | "rbac_negado" | "token_invalido"
)
```

Incrementar em:
- `auth.py::login` — no branch de `HTTPException(401)`
- `deps.py::require_roles` — no branch de `HTTPException(403)`
- `deps.py::get_current_usuario`/`get_current_operador` — no branch de token inválido

**Alertas (depende de Alertmanager, que não existe no stack ainda —
ver item 11):**
```yaml
- alert: PicoDeFalhasAutenticacao
  expr: rate(auth_failures_total[5m]) > 10
  for: 2m
  annotations:
    summary: "Taxa anormal de falhas de auth em {{ $labels.service }}"
```

**Sem Alertmanager, esse item para na métrica** — ela já fica
consultável manualmente no Prometheus/Grafana, só não dispara
notificação proativa sem o componente de alerta.

---

## 11. Grafana + Loki (C3)

### Gap

O doc original do projeto já definia a stack alvo como "Prometheus +
Grafana + Loki + OpenTelemetry". Só Prometheus básico existe. Logs
estruturados em JSON (PR#18) vão pro stdout do container e morrem
quando o container recicla — ninguém consulta histórico de log hoje.

### Escopo técnico

**`docker-compose.yml`, dois serviços novos:**
```yaml
grafana:
  image: grafana/grafana:latest
  ports: ["3001:3000"]
  volumes: [grafana_data:/var/lib/grafana]

loki:
  image: grafana/loki:latest
  ports: ["3100:3100"]

promtail:  # coleta logs dos containers e envia pro Loki
  image: grafana/promtail:latest
  volumes:
    - /var/lib/docker/containers:/var/lib/docker/containers:ro
    - ./infra/promtail/config.yml:/etc/promtail/config.yml
```

**Grafana:** datasource Prometheus (já existe, só conectar) + datasource
Loki (logs). Dashboard inicial: latência por endpoint, taxa de erro
4xx/5xx, e (se item 10 for feito antes) o painel de `auth_failures_total`.

**Esforço:** majoritariamente configuração de infra, pouco código
Python — bom item pra intercalar com itens de código puro.

---

## 12. Testes de carga/performance (A4)

### Gap

Zero validação de capacidade. Não sabemos se 30/min no rate limit de
webhook é generoso ou apertado pro volume real de pico (ex: sexta à
noite, promoção no iFood gerando rajada de pedidos).

### Escopo técnico

**Ferramenta:** `locust` (Python-native, integra naturalmente com o
resto do stack — não é uma dependência de produção, só de dev/CI opcional).

**Cenários mínimos:**
```python
class UsuarioComanda(HttpUser):
    @task
    def fluxo_completo(self):
        self.client.post("/auth/login", json={...})
        self.client.post("/comandas", json={...}, headers=...)
        self.client.post("/comandas/{id}/itens", json={...}, headers=...)
```

1. **Login concorrente** — validar que o rate limit segura sob carga real simultânea, não só sequencial (teste atual só valida sequencialmente via `TestClient`)
2. **Fluxo de comanda em paralelo** — abrir + lançar item + fechar, simulando múltiplas mesas simultâneas
3. **Rajada de webhook** — validar que a fila do Celery não empaca e que o rate limit de 30/min realmente protege sem descartar pedidos legítimos

**Não roda em CI** (locust é execução manual/agendada, não parte do
pipeline de PR — adicionaria minutos desnecessários a cada commit).
Documentar como rodar localmente e como interpretar resultado.

**SLO informal a definir** (não é decisão técnica pura, envolve
expectativa de negócio): ex. "p95 de `POST /comandas/{id}/itens` abaixo
de 200ms com 50 usuários concorrentes" — só faz sentido definir depois
de ter uma primeira medição real como baseline.

**Prioridade real:** só vale a pena com tráfego real ou meta de
capacidade concreta — fazer isso cedo demais é otimizar sem dado.

---

## 13. Migração para Kubernetes (C5)

### Contexto

Já é item explícito do doc original: "Docker Compose (fase 1, bar
único) → Kubernetes (fase 2, multi-loja)". Não detalho aqui como um
passo isolado porque é grande demais e **depende tecnicamente** de
itens já listados:

- **Item 3 (rate limit distribuído)** é pré-requisito real — sem Redis
  como storage compartilhado, múltiplos pods do mesmo serviço quebram
  o rate limit exatamente como descrito no gap original
- **Item 2 (health checks reais)** é pré-requisito real — Kubernetes
  usa liveness/readiness probes nativamente; sem eles, o orquestrador
  não sabe quando reiniciar um pod com dependência quebrada

Quando esses dois existirem, migrar para Kubernetes vira uma questão de
Helm chart / manifests YAML, não mais de mudança de código Python.
Vale revisitar como projeto próprio quando isso ficar concreto.

---

## Dependências entre itens (visão rápida)

```
1 (Cardápio) ──────► 5 (Bot WhatsApp) ──────► 6 (Notificações)
                                                    ▲
                                    (também pode notificar iFood,
                                     se a API do provedor permitir)

2 (Health checks) ──┐
3 (Rate limit Redis)─┴──► 13 (Kubernetes)

10 (Métricas de segurança) ──► 11 (Grafana/Loki, painel dedicado)
```

Itens sem dependência (podem entrar a qualquer momento, isolados):
4 (TLS), 7 (Backup), 8 (LGPD), 9 (Rotação de secret), 12 (Carga).

---

## Ordem sugerida de execução

| Ordem | Item | Por quê nessa posição |
|---|---|---|
| 1 | **1 — Cardápio digital** | Não é feature nova, é bug de integração real já identificado no código |
| 2 | **2 — Health checks reais** | Barato, rápido, destrava observabilidade de verdade |
| 3 | **3 — Rate limit distribuído** | Barato (Redis já existe no compose), remove um débito técnico antes que vire urgente |
| 4 | **4 — TLS/HTTPS** | Só relevante quando houver deploy real; fazer antes de expor a API publicamente |
| 5 | **5/6 — Bot WhatsApp + notificações** | Maior escopo, depende do item 1 |
| 6 | **7/8 — Backup e LGPD** | Requisito já documentado pelo próprio projeto, sem dependência técnica de nada acima |
| 7 | **9/10/11 — Rotação de secrets, alertas, Grafana/Loki** | Operacional, ganha mais valor com tráfego real em produção |
| 8 | **12 — Testes de carga** | Só faz sentido com meta de capacidade real definida |
| 9 | **13 — Kubernetes** | Destino final, não passo isolado |
