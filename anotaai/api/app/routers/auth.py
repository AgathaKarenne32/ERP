from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ..core.db import get_session
from ..core.security import create_access_token, verify_password
from ..models import Operador
from ..schemas import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: Session = Depends(get_session)) -> TokenResponse:
    operador = session.exec(select(Operador).where(Operador.email == payload.email)).first()
    if not operador or not verify_password(payload.senha, operador.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos",
        )
    token = create_access_token(
        subject=str(operador.id),
        extra_claims={"papel": operador.papel.value, "id_loja": str(operador.id_loja)},
    )
    return TokenResponse(access_token=token)
