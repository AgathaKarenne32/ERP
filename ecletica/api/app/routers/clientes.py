import uuid

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..core.db import get_session
from ..core.deps import get_current_loja_id
from ..models import Cliente
from ..schemas import ClienteCreate, ClienteOut

router = APIRouter(prefix="/clientes", tags=["clientes"])


@router.get("", response_model=list[ClienteOut])
def listar_clientes(
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
) -> list[Cliente]:
    return list(session.exec(select(Cliente).where(Cliente.id_loja == id_loja)).all())


@router.post("", response_model=ClienteOut, status_code=201)
def cadastrar_cliente(
    payload: ClienteCreate,
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
) -> Cliente:
    cliente = Cliente(id_loja=id_loja, **payload.model_dump())
    session.add(cliente)
    session.commit()
    session.refresh(cliente)
    return cliente
