import logging
import time
import uuid

import httpx
from fastapi import HTTPException, status

from .config import settings

logger = logging.getLogger(__name__)

_MAX_TENTATIVAS = 3
_BACKOFF_BASE_SEGUNDOS = 0.5


def solicitar_baixa_estoque(
    id_loja: uuid.UUID,
    itens: list[dict],
    referencia: str,
    valor_total: float,
) -> None:
    """Chama a ecletica-api para abater o estoque (RN01/RN02) e somar o valor
    da venda no caixa aberto, ao fechar uma comanda.

    Fase 1: chamada HTTP síncrona. Fase 3: substituída por publicação em fila,
    mantendo a mesma responsabilidade e contrato de dados.

    Retry só em falha de rede (timeout, conexão recusada) — nunca em resposta
    HTTP de erro, que é sempre erro de negócio legítimo (409 de estoque
    insuficiente, por exemplo) e retry não muda o resultado. Seguro reter
    mesmo quando o processamento já tinha concluído do outro lado (só a
    resposta que se perdeu), porque /vendas/baixa-estoque é idempotente por
    (id_loja, referencia)."""
    payload = {
        "id_loja": str(id_loja),
        "referencia": referencia,
        "valor_total": valor_total,
        "itens": itens,
    }
    headers = {"X-Internal-Token": settings.internal_api_token}

    resposta: httpx.Response | None = None
    ultimo_erro: httpx.RequestError | None = None
    for tentativa in range(_MAX_TENTATIVAS):
        try:
            resposta = httpx.post(
                f"{settings.ecletica_api_url}/vendas/baixa-estoque",
                json=payload,
                headers=headers,
                timeout=5.0,
            )
            break
        except httpx.RequestError as exc:
            ultimo_erro = exc
            logger.warning(
                "Falha de rede ao chamar baixa-estoque (tentativa %d/%d): %s",
                tentativa + 1,
                _MAX_TENTATIVAS,
                exc,
            )
            if tentativa < _MAX_TENTATIVAS - 1:
                time.sleep(_BACKOFF_BASE_SEGUNDOS * (2**tentativa))

    if resposta is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível contatar o serviço de estoque (ecletica-api).",
        ) from ultimo_erro

    if resposta.status_code == status.HTTP_409_CONFLICT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=resposta.json().get("detail", "Estoque insuficiente."),
        )
    resposta.raise_for_status()


def solicitar_credito_fidelidade(
    id_loja: uuid.UUID,
    id_cliente: uuid.UUID,
    valor_gasto: float,
    referencia: str,
) -> None:
    """RN05: credita pontos de fidelidade na ecletica-api após pagamento
    confirmado. Diferente da baixa de estoque, uma falha aqui NÃO deve
    impedir o fechamento da comanda — a venda já está confirmada; só
    registramos o aviso e seguimos."""
    payload = {
        "id_loja": str(id_loja),
        "valor_gasto": valor_gasto,
        "referencia": referencia,
    }
    headers = {"X-Internal-Token": settings.internal_api_token}

    try:
        resposta = httpx.post(
            f"{settings.ecletica_api_url}/clientes/{id_cliente}/creditar-pontos",
            json=payload,
            headers=headers,
            timeout=5.0,
        )
        resposta.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Falha ao creditar pontos de fidelidade para %s: %s", id_cliente, exc)
