# Plano de Implementação — Ecossistema Eclética + Módulo AnotaAi

**Objetivo:** construir, 100% em Python e com hospedagem em Docker/Kubernetes, os dois sistemas que juntos atendem o bar:

1. **Eclética (ERP / retaguarda)** — o sistema já especificado em `docs/requirements.md`: cadastro de produtos/insumos, ficha técnica, baixa de estoque, fidelidade, fechamento de caixa, multi-loja.
2. **Módulo "AnotaAi"-like (atendimento / omnichannel)** — a frente de operação inspirada no AnotaAi: cardápio digital por QR Code, pedidos via WhatsApp, comandas de salão, KDS (tela da cozinha), consolidação de pedidos físicos e virtuais.

Este documento substitui a stack poliglota original (Flutter/Java/Node/Firestore) por uma stack **totalmente Python**, mantendo as mesmas Regras de Negócio (RN01–RN06) e Requisitos (RF01–RF10, RNF01–RNF07) do documento de requisitos.

---

## 1. Como os dois sistemas se relacionam

```
┌─────────────────────────────┐        eventos de venda        ┌─────────────────────────────┐
│   ANOTAAI-LIKE (atendimento) │ ──────────────────────────────►│   ECLÉTICA (ERP/retaguarda)  │
│                               │                                 │                               │
│  - Cardápio digital (QR)     │        catálogo/estoque         │  - Cadastro de Produtos       │
│  - Bot WhatsApp               │◄────────────────────────────── │  - Cadastro de Insumos        │
│  - Comandas (mesa/senha)     │                                 │  - Ficha Técnica              │
│  - KDS (cozinha)             │                                 │  - Baixa de estoque (RN01/02) │
│  - PDV de salão               │                                 │  - Fidelidade (RN05)          │
│  - Integração iFood           │                                 │  - Fechamento de caixa        │
└─────────────────────────────┘                                 │  - Multi-loja (RN06)          │
                                                                  └─────────────────────────────┘
```

- A **Eclética** é a fonte da verdade de catálogo, estoque e financeiro.
- O **AnotaAi-like** é a origem dos pedidos (físicos e virtuais) e consulta a Eclética para saber o que pode vender; ao fechar uma comanda, publica um evento de venda que a Eclética consome para dar baixa em estoque e creditar fidelidade.
- São dois serviços deployáveis **independentes**, que escalam e evoluem separadamente, mas compartilham o mesmo monorepo Python e a mesma infraestrutura de containers.

---

## 2. Stack técnica (100% Python)

| Camada | Tecnologia | Substitui, no doc original |
|---|---|---|
| API / regras de negócio | **FastAPI** (async) + **SQLModel/SQLAlchemy 2** + Pydantic v2 | API Core em Java |
| Migrações de banco | **Alembic** | scripts SQL manuais |
| Banco relacional | **PostgreSQL 16** | Oracle/PostgreSQL (já era opção válida) |
| Regras de consistência de estoque | Transações + `SELECT … FOR UPDATE` / triggers em PL/pgSQL quando necessário | PL/SQL Oracle |
| Workers de integração (WhatsApp/iFood) | **Celery** (ou **Arq**, mais leve) + Redis/RabbitMQ como broker | Workers TypeScript/Node.js |
| Fila de mensageria | **RabbitMQ** (ou Redis Streams para começar mais simples) | AWS SQS/RabbitMQ |
| Tempo real (KDS ↔ Salão) | **WebSockets nativos do FastAPI** + Redis Pub/Sub (latência < 2s) | Firebase Firestore |
| Telas de Totem / Salão / KDS / App do garçom | **Flet** (framework Python que compila para Flutter — mantém a multiplataforma do requisito original, mas em Python puro) | Flutter/Dart |
| Cardápio digital (QR, público, alto tráfego) e painel admin da Eclética | FastAPI + Jinja2 + HTMX + Tailwind (server-rendered, leve, sem build JS) | — |
| Bot WhatsApp | Worker Python consumindo a **Meta Cloud API** (ou Twilio/Z-API como fallback) | — |
| Integração iFood | Client Python (webhook + REST) rodando no mesmo worker de integrações | — |
| Autenticação | JWT (fastapi-users ou implementação própria) + RBAC por papel (operador, gerente, cozinha) | — |
| Observabilidade | Prometheus + Grafana + Loki + OpenTelemetry (auto-instrumentação FastAPI/SQLAlchemy) | — |
| Empacotamento | Docker (imagem por serviço) | — |
| Orquestração | Docker Compose (fase 1, bar único) → **Kubernetes** (fase 2, multi-loja) | VPC + API Gateway |

> Por que **Flet** para as telas físicas: ele resolve o requisito original (`RNF01` — base única de código para tablet/mobile/web) sem sair de Python, evitando manter um segundo ecossistema (Node/Dart) só para telas.

---

## 3. Serviços (containers) do ecossistema

| Serviço | Repositório/pasta | Função |
|---|---|---|
| `ecletica-api` | `ecletica/api/` | ERP: produtos, insumos, ficha técnica, estoque, fidelidade, caixa, multi-loja |
| `anotaai-api` | `anotaai/api/` | Comandas, pedidos, consolidação omnichannel, PDV de salão |
| `anotaai-worker` | `anotaai/worker/` | Consome webhooks do WhatsApp e iFood, normaliza (`docs/api-contracts.md`) e publica na fila |
| `realtime-gateway` | `anotaai/realtime/` | WebSocket hub que alimenta KDS e telas de salão a partir dos eventos da fila |
| `frontend-kds` | `anotaai/frontend_kds/` (Flet) | Tela da cozinha |
| `frontend-salao` | `anotaai/frontend_salao/` (Flet) | Tablet do garçom / totem |
| `frontend-cardapio` | `anotaai/frontend_cardapio/` (FastAPI+HTMX) | Cardápio público via QR Code |
| `frontend-admin` | `ecletica/frontend_admin/` (FastAPI+HTMX) | Backoffice da Eclética (cadastros, relatórios) |
| `postgres` | — | Banco relacional (um schema por sistema, ou dois bancos) |
| `redis` | — | Cache, Pub/Sub e broker leve |
| `rabbitmq` | — | Fila de pedidos virtuais (RNF06) — opcional na fase 1, usar Redis Streams para simplificar |
| `traefik`/`nginx` | — | Ingress, TLS, roteamento por subdomínio |

---

## 4. Modelo de dados (herdado de `database/migrations/`, adaptado para Postgres/SQLAlchemy)

Reaproveita as entidades já definidas, distribuídas entre os dois sistemas:

**Eclética:** `Loja`, `Insumo`, `Produto`, `FichaTecnica`, `Cliente` (CPF + saldo de fidelidade), `MovimentoEstoque`, `FechamentoCaixa`.

**AnotaAi-like:** `Comanda`, `ItemComanda` (com `origem`: SALAO/IFOOD/WHATSAPP), `TicketProducao` (espelha a coleção `tickets_producao` do Firestore original, agora como tabela + evento realtime), `Mesa/Senha`.

Todas as tabelas carregam `id_loja` (RN06 — isolamento multi-loja), aplicado via um middleware/dependency do FastAPI que injeta o filtro automaticamente em toda query — evitando repetir a regra em cada endpoint.

---

## 5. Como as Regras de Negócio (RN) mapeiam para código

| Regra | Onde é garantida |
|---|---|
| RN01 — baixa automática de estoque | Service `checkout.py` da `anotaai-api`, dentro da mesma transação que insere o `ItemComanda`; publica evento consumido pela `ecletica-api` para abater `Insumo` conforme `FichaTecnica` |
| RN02 — estoque insuficiente | Validação no service antes do commit; bloqueia salvo `flag permitir_quebra` no perfil gerencial |
| RN03 — comanda só fecha pelo PDV | Endpoint `PATCH /comandas/{id}/fechar` restrito ao papel `CAIXA`; após fechar, novos `POST /itens` retornam 409 |
| RN04 — imutabilidade de preço | `preco_aplicado` gravado no `ItemComanda` no momento da inserção (snapshot), nunca recalculado a partir do catálogo |
| RN05 — fidelidade só após pagamento confirmado | Worker assíncrono dispara ao evento `comanda.paga`, nunca no momento da venda |
| RN06 — isolamento multi-loja | Dependency global do FastAPI (`get_current_loja`) + filtro obrigatório em todas as queries |

---

## 6. Infraestrutura: Docker → Kubernetes

**Fase 1 — MVP para 1 bar (Docker Compose):**
- Um único `docker-compose.yml` sobe: `postgres`, `redis`, `ecletica-api`, `anotaai-api`, `anotaai-worker`, `realtime-gateway`, `frontend-admin`, `frontend-cardapio`, `traefik`.
- Hospedagem recomendada: uma VPS simples (ex.: Hetzner CX22 ou DigitalOcean Droplet 4GB) — custo baixo, suficiente para um bar.
- Telas de salão/totem/KDS: apps Flet compilados, rodando localmente nos tablets/PCs do bar e falando com a API pela rede local ou VPN (Tailscale), sem depender de latência de internet para operação crítica.

**Fase 2 — Multi-loja / franquia (Kubernetes):**
- Migrar para **k3s** (mais barato, ideal para poucas lojas) ou GKE/EKS gerenciado se crescer mais.
- Um `Deployment` por serviço, `HorizontalPodAutoscaler` em `anotaai-api` e `anotaai-worker` (picos de pedido no almoço/happy hour).
- `StatefulSet` ou banco gerenciado (Cloud SQL/RDS) para o Postgres — dado financeiro não deve depender de reagendamento de pod.
- `Ingress` + `cert-manager` para TLS automático por loja/subdomínio.
- `ConfigMap`/`Secret` por ambiente; Helm chart único parametrizado por `loja_id`.
- Repetir o RN06 na infraestrutura: cada loja pode ter seu próprio namespace ou apenas seu `id_loja` isolado no mesmo banco — decisão a tomar quando houver 3+ lojas reais.

---

## 7. Roadmap por fases

| Fase | Duração estimada | Entregas |
|---|---|---|
| **0. Fundação** | 2–3 semanas | Monorepo Python, `docker-compose.yml`, modelos SQLAlchemy, Alembic, auth JWT + RBAC |
| **1. Eclética core** | 3–4 semanas | CRUD de Produto/Insumo/Ficha Técnica, baixa de estoque (RN01/RN02), fechamento de caixa, relatórios (RF10) |
| **2. PDV & Comandas** | 3–4 semanas | Abrir/editar/transferir/fechar comanda (RF05, RN03/RN04), KDS básico (RF07) |
| **3. Omnichannel** | 4 semanas | Cardápio QR (RF02), bot WhatsApp (RF01), integração iFood, fila de eventos, consolidação em comanda única (RF06), notificações de status (RF04) |
| **4. Fidelidade & multi-loja** | 2 semanas | Extrato por CPF (RF09), motor de pontos pós-pagamento (RN05), isolamento multi-loja (RN06) |
| **5. Produção** | 2 semanas | Deploy Kubernetes, observabilidade, backups automáticos do Postgres, testes de carga no checkout/fila |

Total estimado: ~16–19 semanas para o ecossistema completo em produção no seu bar.

---

## 8. Segurança e conformidade

- LGPD: CPF e dados de cliente (fidelidade) exigem consentimento e política de retenção — armazenar apenas o necessário.
- Webhooks públicos (WhatsApp/iFood) validados por assinatura/token, com rate limiting.
- Segredos (chaves de API, JWT secret) via `Secret` do Kubernetes / `.env` não versionado no Compose.
- Backup automático do Postgres (pg_dump agendado ou snapshot do volume) antes de qualquer deploy de produção.

---

## 9. Próximos passos sugeridos

1. Validar esta divisão Eclética/AnotaAi-like e a escolha de Flet para as telas físicas.
2. Iniciar a **Fase 0**: criar o monorepo (`ecletica/`, `anotaai/`), `docker-compose.yml` inicial e os modelos de dados em SQLAlchemy a partir de `database/migrations/`.
3. Definir provedor do bot de WhatsApp (Meta Cloud API oficial vs. Twilio/Z-API) — impacta custo e tempo de aprovação.
