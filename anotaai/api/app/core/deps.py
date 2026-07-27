import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlmodel import Session

from ..models import Operador, PapelOperador
from .db import get_session
from .security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_operador(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> Operador:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    operador = session.get(Operador, uuid.UUID(user_id))
    if operador is None or not operador.ativo:
        raise credentials_exception
    return operador


def get_current_loja_id(operador: Operador = Depends(get_current_operador)) -> uuid.UUID:
    """RN06: toda consulta/gravação deve ser filtrada pela loja do operador autenticado."""
    return operador.id_loja


def require_roles(*papeis: PapelOperador):
    def _checker(operador: Operador = Depends(get_current_operador)) -> Operador:
        if operador.papel not in papeis:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para executar esta ação.",
            )
        return operador

    return _checker
