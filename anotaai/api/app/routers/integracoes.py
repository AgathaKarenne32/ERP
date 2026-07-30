import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ..core.db import get_session
from ..core.deps import get_current_loja_id, require_roles
from ..models import IntegracaoLoja, PapelOperador
from ..schemas import IntegracaoLojaCreate, IntegracaoLojaOut

router = APIRouter(prefix="/integracoes", tags=["integracoes"])


@router.post("", response_model=IntegracaoLojaOut, status_code=201)
def criar_integracao(
    payload: IntegracaoLojaCreate,
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
    _operador=Depends(require_roles(PapelOperador.ADMIN)),
) -> IntegracaoLoja:
    """Vincula um identificador externo (merchant ID do iFood, número do
    WhatsApp Business) à loja do admin autenticado — é esse vínculo que
    permite a ingestão externa rotear pra loja certa."""
    ja_existe = session.exec(
        select(IntegracaoLoja)
        .where(IntegracaoLoja.provedor == payload.provedor)
        .where(IntegracaoLoja.identificador_externo == payload.identificador_externo)
    ).first()
    if ja_existe:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esse identificador externo já está vinculado a uma loja",
        )

    integracao = IntegracaoLoja(id_loja=id_loja, **payload.model_dump())
    session.add(integracao)
    session.commit()
    session.refresh(integracao)
    return integracao


@router.get("", response_model=list[IntegracaoLojaOut])
def listar_integracoes(
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
    _operador=Depends(require_roles(PapelOperador.ADMIN, PapelOperador.GERENTE)),
) -> list[IntegracaoLoja]:
    return list(session.exec(select(IntegracaoLoja).where(IntegracaoLoja.id_loja == id_loja)).all())
