import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, func, select

from ..core.db import get_session
from ..core.deps import get_current_loja_id, require_roles
from ..models import FechamentoCaixa, PapelUsuario
from ..schemas import CaixaOut, PaginatedResponse

router = APIRouter(prefix="/caixa", tags=["caixa"])
router_v1 = APIRouter(prefix="/v1/caixa", tags=["caixa"])


def _buscar_caixa_aberto(session: Session, id_loja: uuid.UUID) -> FechamentoCaixa | None:
    return session.exec(
        select(FechamentoCaixa)
        .where(FechamentoCaixa.id_loja == id_loja)
        .where(FechamentoCaixa.fechado_em.is_(None))
    ).first()


@router.post("/abrir", response_model=CaixaOut, status_code=201)
def abrir_caixa(
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
    _usuario=Depends(require_roles(PapelUsuario.ADMIN, PapelUsuario.GERENTE, PapelUsuario.CAIXA)),
) -> FechamentoCaixa:
    if _buscar_caixa_aberto(session, id_loja):
        raise HTTPException(status_code=409, detail="Já existe um caixa aberto para esta loja")

    caixa = FechamentoCaixa(id_loja=id_loja, aberto_em=datetime.now(timezone.utc))
    session.add(caixa)
    session.commit()
    session.refresh(caixa)
    return caixa


@router.patch("/fechar", response_model=CaixaOut)
def fechar_caixa(
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
    _usuario=Depends(require_roles(PapelUsuario.ADMIN, PapelUsuario.GERENTE, PapelUsuario.CAIXA)),
) -> FechamentoCaixa:
    caixa = _buscar_caixa_aberto(session, id_loja)
    if not caixa:
        raise HTTPException(status_code=409, detail="Não há caixa aberto para esta loja")

    caixa.fechado_em = datetime.now(timezone.utc)
    session.add(caixa)
    session.commit()
    session.refresh(caixa)
    return caixa


@router.get("", response_model=list[CaixaOut])
def listar_caixas(
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
    _usuario=Depends(require_roles(PapelUsuario.ADMIN, PapelUsuario.GERENTE, PapelUsuario.CAIXA)),
) -> list[FechamentoCaixa]:
    return list(
        session.exec(
            select(FechamentoCaixa)
            .where(FechamentoCaixa.id_loja == id_loja)
            .order_by(FechamentoCaixa.aberto_em.desc())
        ).all()
    )


@router_v1.get("", response_model=PaginatedResponse[CaixaOut])
def listar_caixas_v1(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
    id_loja: uuid.UUID = Depends(get_current_loja_id),
    _usuario=Depends(require_roles(PapelUsuario.ADMIN, PapelUsuario.GERENTE, PapelUsuario.CAIXA)),
) -> PaginatedResponse[CaixaOut]:
    """Item 7 do plano de próxima onda: versão paginada de GET /caixa.
    Vive em /v1 porque o envelope {items, total, limit, offset} é
    incompatível com o array puro que GET /caixa devolve hoje —
    manter a rota antiga intacta evita quebrar quem já a consome."""
    filtro = FechamentoCaixa.id_loja == id_loja
    total = session.exec(select(func.count()).select_from(FechamentoCaixa).where(filtro)).one()
    itens = session.exec(
        select(FechamentoCaixa)
        .where(filtro)
        .order_by(FechamentoCaixa.aberto_em.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return PaginatedResponse[CaixaOut](
        items=[CaixaOut.model_validate(c) for c in itens],
        total=total,
        limit=limit,
        offset=offset,
    )
