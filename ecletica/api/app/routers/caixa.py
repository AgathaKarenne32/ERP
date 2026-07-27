import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ..core.db import get_session
from ..core.deps import get_current_loja_id, require_roles
from ..models import FechamentoCaixa, PapelUsuario
from ..schemas import CaixaOut

router = APIRouter(prefix="/caixa", tags=["caixa"])


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
) -> list[FechamentoCaixa]:
    return list(
        session.exec(
            select(FechamentoCaixa)
            .where(FechamentoCaixa.id_loja == id_loja)
            .order_by(FechamentoCaixa.aberto_em.desc())
        ).all()
    )
