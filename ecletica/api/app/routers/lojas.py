from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..core.db import get_session
from ..core.deps import verify_internal_token
from ..models import Loja
from ..schemas import LojaOut

router = APIRouter(prefix="/lojas", tags=["lojas"])


@router.get("", response_model=list[LojaOut], dependencies=[Depends(verify_internal_token)])
def listar_lojas(session: Session = Depends(get_session)) -> list[Loja]:
    """Registro de lojas da ecletica-api — fonte da verdade (RN06). Endpoint
    de uso interno (serviço-a-serviço), sem filtro por id_loja porque é
    justamente o cadastro de lojas em si."""
    return list(session.exec(select(Loja).where(Loja.ativa == True)).all())  # noqa: E712
