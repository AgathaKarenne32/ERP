from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session, select

from ..core.db import get_session
from ..core.rate_limit import limiter
from ..core.security import create_access_token, verify_password
from ..models import Usuario
from ..schemas import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, payload: LoginRequest, session: Session = Depends(get_session)) -> TokenResponse:
    usuario = session.exec(select(Usuario).where(Usuario.email == payload.email)).first()
    if not usuario or not verify_password(payload.senha, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos",
        )
    token = create_access_token(
        subject=str(usuario.id),
        extra_claims={"papel": usuario.papel.value, "id_loja": str(usuario.id_loja)},
    )
    return TokenResponse(access_token=token)
