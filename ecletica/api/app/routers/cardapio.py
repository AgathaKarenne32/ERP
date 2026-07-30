import uuid

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..core.db import get_session
from ..models import Produto
from ..schemas import CardapioItemOut

router = APIRouter(prefix="/cardapio", tags=["cardapio"])


@router.get("", response_model=list[CardapioItemOut])
def listar_cardapio(id_loja: uuid.UUID, session: Session = Depends(get_session)) -> list[Produto]:
    """Cardápio digital público (ex: acesso via QR code na mesa) — sem
    autenticação, só os produtos ativos para venda daquela loja."""
    return list(
        session.exec(
            select(Produto).where(Produto.id_loja == id_loja).where(Produto.ativo_venda.is_(True))
        ).all()
    )
