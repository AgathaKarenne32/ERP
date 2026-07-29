import logging
import uuid

import httpx
from fastapi import HTTPException, status

from .config import settings

logger = logging.getLogger(__name__)


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
    """
    payload = {
        "id_loja": str(id_loja),
        "referencia": referencia,
        "valor_total": valor_total,
        "itens": itens,
    }
    headers = {"X-Internal-Token": settings.internal_api_token}

    try:
        resposta = httpx.post(
            f"{settings.ecletica_api_url}/vendas/baixa-estoque",
            json=payload,
            headers=headers,
            timeout=5.0,
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível contatar o serviço de estoque (ecletica-api).",
        ) from exc

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
