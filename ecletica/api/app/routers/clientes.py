import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..core.db import get_session
from ..core.deps import get_current_loja_id, verify_internal_token
from ..models import Cliente
from ..schemas import ClienteCreate, ClienteOut, CreditarPontosRequest

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


@router.post(
    "/{cliente_id}/creditar-pontos",
    response_model=ClienteOut,
    dependencies=[Depends(verify_internal_token)],
)
def creditar_pontos(
    cliente_id: uuid.UUID,
    payload: CreditarPontosRequest,
    session: Session = Depends(get_session),
) -> Cliente:
    """RN05: credita pontos de fidelidade (1 ponto por R$1 gasto) somente
    após pagamento confirmado. Chamado pela anotaai-api ao fechar comanda,
    nunca no momento da venda."""
    cliente = session.get(Cliente, cliente_id)
    if not cliente or cliente.id_loja != payload.id_loja:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    pontos = int(payload.valor_gasto)
    cliente.pontos_fidelidade += pontos
    session.add(cliente)
    session.commit()
    session.refresh(cliente)
    return cliente
