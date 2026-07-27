import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlmodel import Session

from ..models import PapelUsuario, Usuario
from .db import get_session
from .security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_usuario(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> Usuario:
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

    usuario = session.get(Usuario, uuid.UUID(user_id))
    if usuario is None or not usuario.ativo:
        raise credentials_exception
    return usuario


def get_current_loja_id(usuario: Usuario = Depends(get_current_usuario)) -> uuid.UUID:
    """RN06: toda consulta/gravação deve ser filtrada pela loja do usuário autenticado."""
    return usuario.id_loja


def require_roles(*papeis: PapelUsuario):
    def _checker(usuario: Usuario = Depends(get_current_usuario)) -> Usuario:
        if usuario.papel not in papeis:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para executar esta ação.",
            )
        return usuario

    return _checker
