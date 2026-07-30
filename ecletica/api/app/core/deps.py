import uuid

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlmodel import Session

from ..models import PapelUsuario, Usuario
from .config import settings
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


def get_usuario_painel_admin(
    request: Request,
    session: Session = Depends(get_session),
) -> Usuario | None:
    """Autenticação do painel HTML (Jinja2+HTMX): lê o mesmo JWT emitido pelo
    /auth/login, mas transportado num cookie httponly em vez do header
    Authorization — a API JSON continua exclusivamente Bearer-header, esse
    caminho existe só para as rotas /admin/* que um navegador acessa direto."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None

    usuario = session.get(Usuario, uuid.UUID(user_id))
    if usuario is None or not usuario.ativo:
        return None
    return usuario


def exigir_usuario_painel_admin(usuario: Usuario | None = Depends(get_usuario_painel_admin)) -> Usuario:
    if usuario is None or usuario.papel not in (PapelUsuario.ADMIN, PapelUsuario.GERENTE):
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/admin/login"},
        )
    return usuario


def verify_internal_token(x_internal_token: str = Header(...)) -> None:
    """Autentica chamadas serviço-a-serviço (ex: anotaai-api -> ecletica-api),
    que não têm um usuário logado para usar o fluxo de JWT normal."""
    if x_internal_token != settings.internal_api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de serviço interno inválido",
        )
