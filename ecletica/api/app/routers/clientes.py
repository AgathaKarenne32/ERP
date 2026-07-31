import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, func, select

from ..core.db import get_session
from ..core.deps import get_current_loja_id, require_roles, verify_internal_token
from ..models import Cliente, PapelUsuario
from ..schemas import ClienteCreate, ClienteOut, CreditarPontosRequest, PaginatedResponse

router = APIRouter(prefix="/clientes", tags=["clientes"])
router_v1 = APIRouter(prefix="/v1/clientes", tags=["clientes"])


@router.get("", response_model=list[ClienteOut])
def listar_clientes(
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
) -> list[Cliente]:
    return list(session.exec(select(Cliente).where(Cliente.id_loja == id_loja)).all())


@router_v1.get("", response_model=PaginatedResponse[ClienteOut])
def listar_clientes_v1(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
) -> PaginatedResponse[ClienteOut]:
    """Item 7 do plano de próxima onda: versão paginada de GET /clientes.
    Vive em /v1 porque o envelope {items, total, limit, offset} é
    incompatível com o array puro que GET /clientes devolve hoje —
    manter a rota antiga intacta evita quebrar quem já a consome."""
    filtro = Cliente.id_loja == id_loja
    total = session.exec(select(func.count()).select_from(Cliente).where(filtro)).one()
    itens = session.exec(
        select(Cliente).where(filtro).order_by(Cliente.nome).limit(limit).offset(offset)
    ).all()
    return PaginatedResponse[ClienteOut](
        items=[ClienteOut.model_validate(c) for c in itens],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=ClienteOut, status_code=201)
def cadastrar_cliente(
    payload: ClienteCreate,
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
    _usuario=Depends(require_roles(PapelUsuario.ADMIN, PapelUsuario.GERENTE, PapelUsuario.CAIXA)),
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
