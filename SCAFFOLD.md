# Fase 0 — Fundação (scaffold)

Implementa a base descrita em `docs/plano-implementacao-python.md`: monorepo
Python, `docker-compose.yml`, modelos SQLAlchemy/SQLModel, Alembic e auth
JWT + RBAC para os dois serviços (`ecletica-api` e `anotaai-api` + worker).

## Rodando localmente

```bash
cp .env.example .env
docker compose up --build
```

| Serviço              | URL                          |
| --------------------- | ----------------------------- |
| Eclética API (ERP)    | http://localhost:8000/docs   |
| AnotaAi-like API      | http://localhost:8001/docs   |

No primeiro boot, cada serviço cria o schema (`create_all`) e semeia um
usuário de demonstração:

| Serviço      | Email                  | Senha      |
| ------------ | ----------------------- | ---------- |
| Eclética     | admin@ecletica.local    | admin123   |
| AnotaAi-like | admin@anotaai.local     | admin123   |

## Estrutura

```
.
├── ecletica/api/          # ERP/retaguarda: produtos, insumos, ficha técnica, clientes
├── anotaai/api/           # Atendimento: comandas, itens, KDS
├── anotaai/worker/        # Celery: stubs de webhook WhatsApp/iFood (Fase 3)
├── infra/postgres/        # script de criação do segundo banco
└── docker-compose.yml
```

## Gerando a primeira migração Alembic

Com o Postgres no ar (`docker compose up postgres -d`):

```bash
cd ecletica/api
alembic revision --autogenerate -m "schema inicial"
alembic upgrade head
```

Repita o mesmo em `anotaai/api`.
