import uuid

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..core.db import get_session
from ..core.deps import get_current_loja_id, require_roles
from ..models import Insumo, PapelUsuario
from ..schemas import InsumoCreate, InsumoOut

router = APIRouter(prefix="/insumos", tags=["insumos"])


@router.get("", response_model=list[InsumoOut])
def listar_insumos(
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
) -> list[Insumo]:
    return list(session.exec(select(Insumo).where(Insumo.id_loja == id_loja)).all())


@router.post("", response_model=InsumoOut, status_code=201)
def criar_insumo(
    payload: InsumoCreate,
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
    _usuario=Depends(require_roles(PapelUsuario.ADMIN, PapelUsuario.GERENTE)),
) -> Insumo:
    insumo = Insumo(id_loja=id_loja, **payload.model_dump())
    session.add(insumo)
    session.commit()
    session.refresh(insumo)
    return insumo
