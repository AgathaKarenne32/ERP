import uuid

import httpx
from fastapi import HTTPException, status

from .config import settings


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
