# Roadmap — Backend (Eclética + AnotaAi-like)

Este documento organiza a ordem de implementação do backend dos dois
serviços, priorizando valor de negócio e menor dívida técnica primeiro.
Cada linha vira uma branch `feature/nome-da-feature` criada a partir de
`develop`.

## Estado atual

- ✅ Fase 0 (scaffold): monorepo, Docker Compose, modelos, Alembic, auth JWT + RBAC.
- ✅ RN01/RN02: baixa automática de estoque ao fechar comanda, com bloqueio
  se faltar insumo (`feature/baixa-estoque-vendas`).

## P0 — Núcleo financeiro/operacional

| # | Feature branch | Escopo | RN/RF |
|---|---|---|---|
| 1 | `feature/fechamento-caixa` | Abrir/fechar caixa, somar vendas do período, usar o model `FechamentoCaixa` já existente | RF10 |
| 2 | `feature/movimentacao-estoque-manual` | Endpoints de ENTRADA (compra de insumo) e AJUSTE (perda/quebra), usando `MovimentoEstoque` | RN01 (complemento) |
| 3 | `feature/cancelamento-comanda` | Permitir cancelar comanda (status `CANCELADA`) sem baixar estoque, com motivo | RN03 (extensão) |

## P1 — Diferenciais do produto

| # | Feature branch | Escopo | RN/RF |
|---|---|---|---|
| 4 | `feature/vinculo-cliente-comanda` | Adicionar `id_cliente` na `Comanda` (hoje não existe vínculo) — pré-requisito da fidelidade | RN05 (pré-requisito) |
| 5 | `feature/fidelidade-pos-pagamento` | Ao fechar comanda com cliente vinculado, creditar pontos automaticamente | RN05 |
| 6 | `feature/relatorios-vendas` | Endpoints de relatório: vendas por período, produtos mais vendidos, ticket médio | RF10 |
| 7 | `feature/transferencia-comanda` | Mover itens entre comandas/mesas | RF05 |

## P2 — Dívida técnica prioritária

| # | Feature branch | Escopo | RN/RF |
|---|---|---|---|
| 8 | `feature/sincronizacao-loja` | Resolver de vez o problema encontrado no teste manual da RN01: hoje o `id_loja` do `anotaai-api` é alinhado à mão via variável de ambiente. Criar endpoint/evento pra `ecletica-api` ser a fonte da verdade de `Loja`, e `anotaai-api` consultar/cachear isso | RN06 |

## P2 — Ciclo omnichannel (backend, sem frontend ainda)

| # | Feature branch | Escopo | RN/RF |
|---|---|---|---|
| 9 | `feature/webhook-ingestao-pedidos` | Endpoint público que recebe o payload real do iFood/WhatsApp, valida assinatura, publica no Celery e injeta o pedido na comanda (hoje o worker só normaliza e loga) | RF01/RF06 |
| 10 | `feature/kds-websocket` | Trocar o polling do `/kds/fila` por WebSocket + Redis Pub/Sub | RF07 |

## P2 — Qualidade (pode rodar em paralelo, não bloqueia)

| # | Feature branch | Escopo |
|---|---|---|
| 11 | `feature/testes-automatizados` | pytest cobrindo RN01–RN06, a começar pelo fluxo de baixa de estoque validado manualmente |
| 12 | `feature/observabilidade-basica` | Endpoint `/metrics` (Prometheus) + logs estruturados |

## Justificativa da ordem

- **1–3** fecham o ciclo financeiro básico do dia a dia (caixa, estoque,
  cancelamento) — sem isso o backend não sustenta a operação real de um bar.
- **4–7** são o que diferencia o produto (fidelidade, relatório,
  transferência de comanda).
- **8** foi promovida de prioridade: é o problema real que tivemos que
  contornar manualmente durante o teste da RN01/RN02 (alinhar `id_loja` via
  `ANOTAAI_DEMO_LOJA_ID` + reseed manual). Vale resolver antes de acumular
  mais gambiarra em cima disso.
- **9–10** fecham a promessa "omnichannel" do plano original, mas dependem
  menos de pressa — hoje o fluxo manual (`SALAO`) já sustenta a operação.
- **11–12** não bloqueiam entregas, mas quanto mais cedo os testes
  automatizados começarem, menor o risco de regressão conforme o ritmo
  acelerar.
