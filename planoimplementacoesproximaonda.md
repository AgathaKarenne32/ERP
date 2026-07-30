# Plano de Implementações — Próxima Onda

> Baseado em inspeção real do código em `develop`@`4cbe583`.
> Nenhum item aqui é hipotético — parte de gaps confirmados no código
> (`grep`, leitura de router, leitura de `docker-compose.yml`) ou do
> plano original do projeto (`docs/plano-implementacao-python.md`,
> branch `doc`).
>
> Reorganizado em 4 tiers de prioridade: **Tier 0** são bugs de
> correção que vão quebrar assim que o sistema tiver dado real
> (não é "hardening", é conserto); **Tier 1** vai incomodar operação
> real em breve; **Tier 2** é hardening/infra de médio prazo;
> **Tier 3** é operacional/futuro, só relevante com produção real rodando.

---

## Sumário

| # | Item | Tier | Bloco |
|---|---|---|---|
| 1 | Multi-loja quebrado na ingestão externa | **0 — Crítico** | Bug de correção |
| 2 | Chamada interna ecletica↔anotaai sem retry/idempotência | **0 — Crítico** | Bug de correção |
| 3 | Cardápio digital / de-para de SKU externo | **0 — Crítico** | B1 |
| 4 | Forma de pagamento | 1 — Alta | Regra de negócio |
| 5 | Cancelamento de item individual | 1 — Alta | Regra de negócio |
| 6 | Health checks reais (liveness/readiness) | 1 — Alta | C4 |
| 7 | Paginação em listagens | 1 — Alta | API |
| 8 | Rate limiting distribuído (Redis) | 2 — Média | A3 |
| 9 | Alerta de estoque mínimo | 2 — Média | Regra de negócio |
| 10 | Desconto/cupom | 2 — Média | Regra de negócio |
| 11 | TLS/HTTPS na borda | 2 — Média | A1 |
| 12 | Bot WhatsApp conversacional | 2 — Média | B2 |
| 13 | Notificações de status externo | 2 — Média | B3 |
| 14 | Backup automatizado do Postgres | 2 — Média | C1 |
| 15 | LGPD — consentimento e retenção | 2 — Média | C2 |
| 16 | `/docs` e `/openapi.json` públicos sem restrição | 3 — Baixa | Higiene |
| 17 | Scan de dependência vulnerável no CI | 3 — Baixa | Higiene |
| 18 | Rotação de secrets (JWT `kid`) | 3 — Baixa | A2 |
| 19 | Observabilidade de segurança (métricas + alertas) | 3 — Baixa | A5 |
| 20 | Grafana + Loki | 3 — Baixa | C3 |
| 21 | Testes de carga/performance | 3 — Baixa | A4 |
| 22 | Migração para Kubernetes | 3 — Baixa | C5 |

---

# Tier 0 — Crítico (bugs de correção, não hardening)

## 1. Multi-loja quebrado na ingestão externa

### Gap confirmado

```python
# anotaai/api/app/routers/comandas.py, ingestao_externa()
operador_referencia = session.exec(select(Operador)).first()  # ← "o primeiro que existir"
if not operador_referencia:
    raise HTTPException(status_code=503, detail="Loja ainda não inicializada")
id_loja = operador_referencia.id_loja
```

RN06 (sincronização multi-loja, PR#12) resolveu isolamento de loja pra
tudo que passa por JWT (`get_current_loja_id`), mas a ingestão externa
não tem usuário logado — é o worker chamando via token interno. Com
**mais de uma loja cadastrada**, um webhook do iFood/WhatsApp injeta a
comanda numa loja arbitrária, decidida por ordem de inserção no banco,
não por qual loja realmente recebeu o pedido. Hoje só "funciona" porque
o ambiente de demo tem uma loja só.

### Escopo técnico

**Novo modelo (ecletica-api ou anotaai-api — decisão: como é sobre
roteamento de pedido, faz mais sentido no anotaai-api, que já possui
`Operador.id_loja`):**
```python
class IntegracaoLoja(SQLModel, table=True):
    __tablename__ = "integracao_loja"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    id_loja: uuid.UUID = Field(index=True)
    provedor: str  # "IFOOD" | "WHATSAPP"
    identificador_externo: str  # merchant_id do iFood / número do WhatsApp Business
    # unique constraint (provedor, identificador_externo)
```

**Mudança de contrato:** `IngestaoExternaRequest` ganha
`identificador_loja_externa: str` — o worker já precisa extrair esse
dado do payload bruto do provedor antes de normalizar (merchant ID já
vem no payload de pedido do iFood; número de telefone de destino já
vem no payload da Meta Cloud API — nenhum dos dois exige mudança no
provedor, só no worker).

`ingestao_externa` passa a resolver `id_loja` via
`IntegracaoLoja.identificador_externo == payload.identificador_loja_externa`.
Se não achar mapeamento, retorna erro claro (422/404) em vez de
silenciosamente escolher uma loja errada.

**Dependência:** este item é pré-requisito de fato pro item 12 (bot
WhatsApp) — sem saber pra qual loja rotear, não dá pra montar
conversa alguma.

### Testes
- `test_ingestao_externa_roteia_para_loja_correta_por_identificador`
- `test_ingestao_externa_sem_mapeamento_retorna_erro_claro`
- `test_ingestao_externa_nao_pega_loja_arbitraria_com_duas_lojas_cadastradas` — regressão específica do bug atual, cadastra 2 lojas e garante que não pega a errada

---

## 2. Chamada interna ecletica↔anotaai sem retry nem idempotência

### Gap confirmado

```python
# anotaai/api/app/core/ecletica_client.py
try:
    resposta = httpx.post(f"{settings.ecletica_api_url}/vendas/baixa-estoque", ...)
except httpx.RequestError as exc:
    raise HTTPException(503, "Não foi possível contatar...") from exc  # sem retry
```

Diferente do webhook externo (que ganhou idempotência real no PR#21),
essa chamada **interna síncrona** não tenta de novo em timeout de rede
transitório — o garçom vê "erro 503" fechando uma comanda por
instabilidade de rede momentânea entre os dois containers. E adicionar
retry ingênuo sem mais nada é pior: se o timeout acontecer *depois* do
ecletica-api já ter processado a baixa, um retry duplica o decremento
de estoque — porque `referencia` (o id da comanda) é só um campo de
texto gravado em `MovimentoEstoque.referencia`, nunca usado pra
deduplicar.

### Escopo técnico

**Lado ecletica-api (`routers/vendas.py`):** antes de aplicar a baixa,
checar se já existe `MovimentoEstoque` com aquela `referencia` e
`tipo=SAIDA_VENDA` — se existir, é reenvio, responde sucesso sem
duplicar (mesmo padrão de idempotência já usado em `ingestao_externa`
pro webhook, agora replicado aqui).

**Lado anotaai-api (`ecletica_client.py`):** adicionar retry com
backoff curto (2-3 tentativas, ex: via `tenacity` ou loop manual) —
**só** para `httpx.RequestError` (falha de rede/timeout), nunca para
respostas 4xx (409 de estoque insuficiente é erro de negócio legítimo,
não deve reter).

### Testes
- `test_baixa_estoque_e_idempotente_por_referencia` — chama duas vezes com mesma referência, garante que só decrementa uma vez
- `test_retry_recupera_de_timeout_transitorio` — mock de `httpx` falhando uma vez e sucedendo na segunda tentativa
- `test_retry_nao_repete_em_409` — garante que erro de negócio não aciona retry desnecessário

---

## 3. Cardápio digital + de-para de SKU externo

### Por que é crítico, não só feature nova

`anotaai/worker/app/tasks.py`, função `_normalizar_itens()`, tem TODO
explícito confessando o problema:

```python
def _normalizar_itens(items_originais: list[dict]) -> list[dict]:
    """TODO (fora do escopo desta feature): assume que `id_produto` já
    vem no payload. Num catálogo real, o provedor referencia produtos
    pelo próprio SKU dele, e precisaríamos de uma tabela de-para..."""
    return [{"id_produto": item["id_produto"], ...} for item in items_originais]
```

Um pedido real do iFood referencia produtos pelo SKU do catálogo do
iFood, não pelo UUID interno da `ecletica-api`. `item["id_produto"]`
provavelmente lança `KeyError` ou recebe valor inexistente na tabela
`produto` — o pedido falha, a task do Celery tenta de novo 3x e desiste.

### Escopo técnico

**Novo modelo (ecletica-api, dona do catálogo):**
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
- `POST /produtos/{id}/mapear-sku` — vincula SKU externo a produto (ADMIN/GERENTE)
- `GET /cardapio` — **público, sem autenticação**, produtos ativos por loja (QR code + resolução do worker)

**Mudança no worker:** `_resolver_produto(provedor, sku_externo, id_loja)` — chama o endpoint de mapeamento, cache local em Redis (TTL curto) pra não bater na API a cada item.

**Painel admin mínimo:** FastAPI + Jinja2 + HTMX (`/admin/produtos`), CRUD de produto + tela de mapeamento de SKU, reaproveitando o JWT existente.

### Testes
- `test_cardapio_publico_nao_exige_auth`
- `test_mapear_sku_exige_admin` (403 pra GARCOM)
- `test_worker_resolve_sku_ifood_para_produto_interno` (mock HTTP)
- Regressão: `test_ingestao_externa_e_idempotente` continua passando com o novo fluxo

**Ordem de entrega:** modelo + migração → mapeamento → `/cardapio` público → ajuste do worker → painel admin (última fatia, menos bloqueante).

---

# Tier 1 — Alta prioridade (vai incomodar operação real em breve)

## 4. Forma de pagamento

### Gap confirmado

Nenhum model, nenhum schema, em lugar nenhum, registra se o cliente
pagou em dinheiro, cartão ou PIX. `fechar_comanda` soma `valor_total`
pro caixa mas não sabe compor por método — impossível fazer
conciliação financeira real, algo padrão em qualquer PDV.

### Escopo técnico

```python
class FormaPagamento(str, Enum):
    DINHEIRO = "DINHEIRO"
    CARTAO_CREDITO = "CARTAO_CREDITO"
    CARTAO_DEBITO = "CARTAO_DEBITO"
    PIX = "PIX"

class Comanda(SQLModel, table=True):
    ...
    forma_pagamento: FormaPagamento | None = None
```

`fechar_comanda` passa a exigir `forma_pagamento` no body do `PATCH`.
Relatório de vendas (RF10, `relatorios.py`) ganha quebra por forma de
pagamento — `RelatorioVendasOut` recebe um breakdown adicional.

### Testes
- `test_fechar_comanda_exige_forma_pagamento`
- `test_relatorio_vendas_agrupa_por_forma_pagamento`

---

## 5. Cancelamento de item individual

### Gap confirmado

Existe cancelamento de comanda inteira (RN03 extensão, PR#9) e
lançamento de item (`adicionar_item`), mas **não existe remover um
item já lançado** antes de fechar a comanda. Garçom erra o pedido, só
tem a opção nuclear de cancelar a comanda toda.

### Escopo técnico

```python
@router.delete("/{comanda_id}/itens/{item_id}", status_code=204)
def remover_item(
    comanda_id: uuid.UUID, item_id: uuid.UUID,
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
    _operador=Depends(require_roles(ADMIN, GERENTE, CAIXA, GARCOM)),  # mesma política de adicionar_item
) -> None:
```

**Regra de negócio a confirmar com o time:** bloquear remoção se o
ticket de produção correspondente já estiver `EM_PREPARO` ou além (a
cozinha já começou a fazer, não faz sentido sumir com o pedido sem
aviso) — ou permitir sempre e só notificar a cozinha via
`publicar_atualizacao_kds` que o item foi cancelado. Decisão de
produto, não técnica.

### Testes
- `test_remove_item_de_comanda_aberta_recalcula_total`
- `test_bloqueia_remocao_de_comanda_fechada`
- `test_bloqueia_ou_avisa_remocao_de_item_ja_em_preparo` (depende da decisão acima)

---

## 6. Health checks reais (liveness/readiness)

### Gap

```python
@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "ecletica-api"}
```

Não toca o banco. Postgres fora do ar não aparece aqui — o processo
Python continua "vivo" mesmo com toda requisição real falhando com 500.

### Escopo técnico

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

Manter `/health` como alias de `/health/live` por compatibilidade.
`docker-compose.yml`: adicionar `healthcheck` nos serviços apontando
pra `/health/ready`, igual já existe pro `postgres`.

### Testes
- `test_health_ready_falha_com_banco_indisponivel` (override do `get_session` pra levantar exceção)
- `test_health_live_nao_depende_de_nada`

**Esforço:** pequeno, ~1-2h. Bom item pra manter ritmo entre entregas maiores.

---

## 7. Paginação em listagens

### Gap confirmado

```python
grep -n "limit\|offset\|Query(" clientes.py comandas.py  # zero resultado
```

`listar_clientes`, `listar_comandas`, `listar_caixas` retornam a
tabela inteira sempre. Com meses de histórico acumulado, cresce sem
limite — degrada performance e payload de resposta.

### Escopo técnico

```python
@router.get("", response_model=PaginatedResponse[ComandaOut])
def listar_comandas(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    ...
) -> PaginatedResponse[Comanda]:
```

Envelope de resposta novo: `{items: [...], total: int, limit: int, offset: int}`
— **isso é breaking change de contrato** (hoje é `list[X]` puro). Vale
avaliar junto com a decisão de versionamento de API (`/v1/...`), se
fizer sentido introduzir agora pra não quebrar clientes existentes
silenciosamente.

### Testes
- `test_listar_comandas_respeita_limit`
- `test_listar_comandas_default_nao_estoura_com_muitos_registros`
- `test_listar_comandas_total_reflete_contagem_real_nao_so_pagina_atual`

---

# Tier 2 — Média prioridade (hardening/infra de médio prazo)

## 8. Rate limiting distribuído — Redis-backed

### Gap

`slowapi` com storage padrão guarda contadores **na memória do
processo**. Com N réplicas atrás de load balancer, cada réplica conta
separado — multiplica o rate limit efetivo por N.

### Escopo técnico

```python
limiter = Limiter(key_func=get_remote_address, storage_uri=settings.rate_limit_storage_uri)
```

Config novo: `rate_limit_storage_uri: str = "redis://redis:6379/2"`
(DB 2 — DB 0 é broker Celery, DB 1 é result backend). `ecletica-api`
hoje **não depende do Redis** — precisa `depends_on: redis` no compose.

**Testes:** manter storage in-memory nos testes via override de config
(`RATE_LIMIT_STORAGE_URI=memory://`), só usar Redis em produção —
evita exigir Redis real no CI. `limiter.reset()` (já usado hoje)
continua funcionando igual.

---

## 9. Alerta de estoque mínimo

### Gap confirmado

`Insumo.qtd_estoque` existe e é decrementado corretamente, mas não há
`estoque_minimo` nem qualquer sinalização de "vai faltar gelo sexta à noite".

### Escopo técnico

```python
class Insumo(SQLModel, table=True):
    ...
    estoque_minimo: float = Field(default=0)
```

```python
@router.get("/abaixo-do-minimo", response_model=list[InsumoOut])
def insumos_abaixo_do_minimo(
    _usuario=Depends(require_roles(ADMIN, GERENTE)),
    ...
) -> list[Insumo]:
    return session.exec(select(Insumo).where(Insumo.qtd_estoque < Insumo.estoque_minimo)).all()
```

**Opcional (fase 2 deste item):** hook depois de `MovimentoEstoque`
tipo `SAIDA_VENDA` que loga/notifica quando o decremento cruza o
limiar — mais complexo, começar só pelo endpoint de consulta.

### Testes
- `test_lista_insumos_abaixo_do_minimo`
- `test_insumo_no_minimo_exato_nao_aparece_na_lista` (checar operador `<` vs `<=`)

---

## 10. Desconto/cupom

### Gap confirmado

RN04 garante imutabilidade de `preco_aplicado`/`nome_produto` (correto
e deve continuar assim), mas não existe nenhum campo pra aplicar
desconto pontual (happy hour, cortesia, fidelidade resgatada).

### Escopo técnico

```python
class Comanda(SQLModel, table=True):
    ...
    desconto_total: float = Field(default=0)
```

Desconto fica em campo separado a nível de comanda, **nunca** editando
`ItemComanda.preco_aplicado` diretamente (preservaria RN04). Endpoint
`PATCH /comandas/{id}/desconto` exige papel restrito (CAIXA/GERENTE/
ADMIN — GARCOM não deveria dar desconto livre, risco de fraude interna).

`valor_total` efetivo pro pagamento passa a ser
`comanda.valor_total - comanda.desconto_total` — decidir se isso é
calculado on-the-fly ou persistido (recomendo calculado, evita
inconsistência).

### Testes
- `test_aplicar_desconto_exige_papel_restrito` (403 pra GARCOM)
- `test_desconto_nao_afeta_preco_aplicado_dos_itens` (RN04 preservada)
- `test_fechar_comanda_com_desconto_soma_valor_liquido_no_caixa`

---

## 11. TLS/HTTPS na borda

### Gap

`docker-compose.yml` expõe as APIs direto em HTTP. O header
`Strict-Transport-Security` (PR#25) é enviado mas inócuo sem HTTPS de
verdade na frente.

### Escopo técnico

Novo serviço `nginx` no compose como reverse proxy, `ecletica-api`/
`anotaai-api` deixam de expor porta pro host. Certificado: `mkcert` em
dev, `certbot` com renovação automática em produção. Redirect 301
HTTP→HTTPS obrigatório.

Ajustes: `CORS_ALLOWED_ORIGINS` se o esquema mudar; comunicação
interna serviço-a-serviço continua HTTP puro (rede interna do compose,
não precisa passar pelo nginx).

**Não bloqueante pra dev** — só importa com deploy real acessível pela internet.

---

## 12. Bot WhatsApp conversacional

### Gap

Só existe a metade passiva: recebe pedido **já pronto e estruturado**.
Não existe conversa — cliente mandar "oi" não aciona nada porque não
há como responder.

### Pré-requisito

**Depende do item 1** (multi-loja) pra saber pra qual loja rotear a
conversa, e do **item 3** (cardápio) pra ter o que oferecer.

### Escopo técnico

Cliente de envio novo (`whatsapp_client.py`, Meta Cloud API). Máquina
de estados por conversa em Redis (TTL de inatividade):
`AGUARDANDO_INICIO → AGUARDANDO_ITEM → AGUARDANDO_CONFIRMACAO → CONCLUIDO`.
`webhook_whatsapp` passa a diferenciar mensagem de texto livre
(dispara a máquina de estados) de pedido estruturado (fluxo atual,
mantido).

**Risco de escopo:** maior item da lista. Quebrar em sub-entregas: (a)
enviar mensagem simples primeiro, validar credencial da Meta funciona;
(b) só depois a máquina de estados completa.

---

## 13. Notificações de status externo

### Gap

KDS já publica em tempo real via WebSocket+Redis (RF07), mas só a
cozinha escuta — cliente que pediu por fora não sabe quando ficou pronto.

### Pré-requisito

**Depende do item 12** pro canal WhatsApp.

### Escopo técnico

Em `atualizar_status` (kds.py), branch condicional: se
`comanda.origem_externa == WHATSAPP` e `novo_status == PRONTO`, chama
`enviar_mensagem_whatsapp`. Pra iFood, **verificar antes** se o
provedor expõe API de atualização de status — pode não ser tecnicamente
viável, não prometer sem confirmar na documentação real do parceiro.

---

## 14. Backup automatizado do Postgres

### Gap

O próprio doc do projeto já lista isso como requisito e não existe
nenhuma automação — só o volume `postgres_data`, sem rotina de dump.

### Escopo técnico

Serviço `postgres-backup` no compose rodando `pg_dump` diário +
retenção de 30 dias (`find -mtime +30 -delete`). **Teste de restore
periódico é a parte que mais costuma faltar** — documentar e
idealmente automatizar restaurar o dump mais recente num Postgres
descartável + query de sanidade.

---

## 15. LGPD — consentimento e retenção de dados de cliente

### Gap

`Cliente` grava CPF sem campo de consentimento ou expiração — o
próprio doc do projeto já cita isso como requisito, hoje é letra morta.

### Escopo técnico

```python
class Cliente(SQLModel, table=True):
    ...
    consentimento_em: datetime | None = None
    consentimento_finalidade: str | None = None
```

Job de retenção (Celery Beat, componente novo no worker) anonimiza
cliente sem consentimento válido há N dias. **Componente de decisão de
produto/jurídico maior que técnica** — confirmar política de retenção
específica antes de implementar, não decidir isso unilateralmente no código.

---

# Tier 3 — Baixa prioridade (operacional/futuro)

## 16. `/docs` e `/openapi.json` públicos sem restrição

### Gap confirmado

```python
app = FastAPI(title="Eclética API", version="0.1.0", lifespan=lifespan)
# sem docs_url=None, sem qualquer gate
```

Swagger UI expõe a superfície inteira da API (todo endpoint, todo
schema) pra qualquer um na internet, por padrão do FastAPI.

### Escopo técnico

```python
app = FastAPI(
    ...,
    docs_url="/docs" if settings.expose_api_docs else None,
    redoc_url="/redoc" if settings.expose_api_docs else None,
    openapi_url="/openapi.json" if settings.expose_api_docs else None,
)
```

`expose_api_docs: bool = True` default (mantém DX em dev), `False`
explicitamente configurado em produção.

### Testes
- `test_docs_desabilitado_quando_config_producao`

---

## 17. Scan de dependência vulnerável no CI

### Gap

Nada tipo `pip-audit`/Dependabot roda hoje. Já tropeçamos uma vez num
`cryptography` do sistema quebrado (sandbox de dev) — risco diferente,
mas evidencia que ninguém monitora CVE de dependência.

### Escopo técnico

Novo step em `.github/workflows/tests.yml` (ou job dedicado):
```yaml
- name: Auditoria de dependências
  run: pip install pip-audit && pip-audit -r requirements.txt
```
Falha o CI em CVE de severidade alta/crítica sem exceção documentada.
Sem teste de código — é infra de CI.

---

## 18. Rotação de secrets — JWT com `kid`

### Gap

`secret_key` é único e estático. Se vazar, todo refresh token válido
(até 7 dias) permite gerar access tokens novos indefinidamente — sem
forma de invalidar "tokens da chave antiga" sem invalidar todo mundo.

### Escopo técnico

`jwt_keys: dict[str, str]` + `jwt_current_kid`. `create_access_token`
inclui `kid` no header do JWT; `decode_access_token` lê o `kid`, busca
a chave correspondente, decodifica com ela. Fluxo de rotação: adiciona
chave nova → muda `current_kid` → espera 7 dias (vida do refresh
token) → remove chave antiga.

Endpoint adicional: `POST /auth/revogar-todos` (ADMIN-only,
por usuário-alvo) — resposta a incidente sem esperar rotação completa.

**Prioridade real:** baixa até existir produção de verdade.

---

## 19. Observabilidade de segurança (métricas + alertas)

### Gap

Prometheus expõe métricas genéricas (PR#18). Nenhuma métrica dedicada
a evento de segurança — só vira log JSON, ninguém consulta em tempo real.

### Escopo técnico

```python
auth_failures = Counter("auth_failures_total", "...", ["service", "reason"])
```
Incrementar em `login` (401), `require_roles` (403), validação de
token (token inválido). Alerta Prometheus depende de Alertmanager
(item 20) — sem ele, a métrica fica só consultável manualmente.

---

## 20. Grafana + Loki

### Gap

Doc original já define "Prometheus + Grafana + Loki + OpenTelemetry"
como stack alvo. Só Prometheus básico existe. Logs JSON vão pro stdout
e morrem quando o container recicla.

### Escopo técnico

Três serviços novos no compose: `grafana`, `loki`, `promtail`
(coleta logs dos containers). Datasource Prometheus (já existe) +
Loki. Dashboard inicial: latência, taxa de erro 4xx/5xx, e (se item 19
feito antes) painel de `auth_failures_total`.

**Esforço:** majoritariamente config de infra, pouco código Python.

---

## 21. Testes de carga/performance

### Gap

Zero validação de capacidade. Não sabemos se 30/min no rate limit de
webhook é generoso ou apertado pro volume real de pico.

### Escopo técnico

`locust` (dependência de dev, não produção). Cenários mínimos: login
concorrente, fluxo de comanda em paralelo, rajada de webhook. **Não
roda em CI** — execução manual/agendada.

**Prioridade real:** só vale a pena com tráfego real ou meta de
capacidade concreta — fazer cedo demais é otimizar sem dado.

---

## 22. Migração para Kubernetes

### Contexto

Item explícito do doc original ("Docker Compose fase 1 → Kubernetes
fase 2, multi-loja"). Depende tecnicamente do **item 8** (rate limit
distribuído — sem Redis compartilhado, múltiplos pods quebram o rate
limit) e do **item 6** (health checks — Kubernetes usa liveness/
readiness probes nativamente).

Quando esses dois existirem, migrar vira questão de Helm chart/
manifests YAML, não mais mudança de código Python.

---

## Dependências entre itens (visão rápida)

```
1 (Multi-loja) ──┬──► 12 (Bot WhatsApp) ──► 13 (Notificações)
3 (Cardápio) ─────┘

6 (Health checks) ──┐
8 (Rate limit Redis)─┴──► 22 (Kubernetes)

19 (Métricas segurança) ──► 20 (Grafana/Loki, painel dedicado)

2 (Retry/idempotência interna) — independente, mas mesma "família"
de correção que 1 e 3, todos Tier 0
```

Itens sem dependência (podem entrar a qualquer momento, isolados):
4 (pagamento), 5 (cancelar item), 7 (paginação), 9 (estoque mínimo),
10 (desconto), 11 (TLS), 14 (backup), 15 (LGPD), 16 (docs), 17 (scan
dependência), 18 (rotação secret), 21 (carga).

---

## Ordem sugerida de execução

| Ordem | Item | Por quê nessa posição |
|---|---|---|
| 1 | **1 — Multi-loja na ingestão externa** | Bug de correção mais grave: hoje escolhe loja arbitrária com 2+ lojas |
| 2 | **2 — Retry/idempotência interna** | Mesma família de correção; afeta toda venda que fecha comanda |
| 3 | **3 — Cardápio digital** | Bug de integração já confirmado por TODO no próprio código |
| 4 | **4 — Forma de pagamento** | Gap óbvio de PDV, baixo esforço, alto valor operacional |
| 5 | **6 — Health checks reais** | Barato, rápido, destrava observabilidade de verdade |
| 6 | **5 — Cancelamento de item individual** | Fricção real do dia a dia do garçom |
| 7 | **7 — Paginação** | Cresce em urgência com o tempo; melhor resolver antes de doer |
| 8 | **8 — Rate limit distribuído** | Barato (Redis já existe no compose) |
| 9 | **9/10 — Estoque mínimo + desconto** | Valor de produto, sem dependência técnica |
| 10 | **11 — TLS/HTTPS** | Só relevante quando houver deploy real |
| 11 | **12/13 — Bot WhatsApp + notificações** | Maior escopo, depende dos itens 1 e 3 |
| 12 | **14/15 — Backup e LGPD** | Requisito já documentado pelo próprio projeto |
| 13 | **16/17 — Docs público + scan dependência** | Higiene barata, qualquer momento |
| 14 | **18/19/20 — Rotação secret, alertas, Grafana/Loki** | Ganha mais valor com tráfego real em produção |
| 15 | **21 — Testes de carga** | Só faz sentido com meta de capacidade real definida |
| 16 | **22 — Kubernetes** | Destino final, não passo isolado |
