from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session, select

from ..core.config import settings
from ..core.db import get_session
from ..core.rate_limit import limiter
from ..core.security import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
    refresh_token_expirado,
    verify_password,
)
from ..models import Operador, RefreshToken
from ..schemas import LoginRequest, LogoutRequest, RefreshRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _emitir_tokens(session: Session, operador: Operador) -> TokenResponse:
    access_token = create_access_token(
        subject=str(operador.id),
        extra_claims={"papel": operador.papel.value, "id_loja": str(operador.id_loja)},
    )
    token_bruto, token_hash = create_refresh_token()
    session.add(
        RefreshToken(
            id_operador=operador.id,
            token_hash=token_hash,
            expira_em=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    session.commit()
    return TokenResponse(access_token=access_token, refresh_token=token_bruto)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, payload: LoginRequest, session: Session = Depends(get_session)) -> TokenResponse:
    operador = session.exec(select(Operador).where(Operador.email == payload.email)).first()
    if not operador or not verify_password(payload.senha, operador.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos",
        )
    return _emitir_tokens(session, operador)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
def refresh(request: Request, payload: RefreshRequest, session: Session = Depends(get_session)) -> TokenResponse:
    """Rotaciona o refresh token: o token usado é revogado e um novo par
    access/refresh é emitido. Rotação detecta reuso indevido — se um token
    já revogado for reapresentado, a requisição é rejeitada."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token inválido ou expirado",
    )

    token_hash = hash_refresh_token(payload.refresh_token)
    registro = session.exec(select(RefreshToken).where(RefreshToken.token_hash == token_hash)).first()
    if registro is None or registro.revogado or refresh_token_expirado(registro.expira_em):
        raise credentials_exception

    operador = session.get(Operador, registro.id_operador)
    if operador is None or not operador.ativo:
        raise credentials_exception

    registro.revogado = True
    registro.revogado_em = datetime.now(timezone.utc)
    session.add(registro)

    return _emitir_tokens(session, operador)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: LogoutRequest, session: Session = Depends(get_session)) -> None:
    token_hash = hash_refresh_token(payload.refresh_token)
    registro = session.exec(select(RefreshToken).where(RefreshToken.token_hash == token_hash)).first()
    if registro is not None and not registro.revogado:
        registro.revogado = True
        registro.revogado_em = datetime.now(timezone.utc)
        session.add(registro)
        session.commit()
