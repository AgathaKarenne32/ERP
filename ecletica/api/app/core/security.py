import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str, extra_claims: dict | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode = {"sub": subject, "exp": expire, **(extra_claims or {})}
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_refresh_token() -> tuple[str, str]:
    """Retorna (token_bruto, token_hash). Apenas o hash é persistido no banco;
    o token bruto é devolvido uma única vez, na resposta do login/refresh."""
    token = secrets.token_urlsafe(48)
    return token, hash_refresh_token(token)


def refresh_token_expirado(expira_em: datetime) -> bool:
    """SQLite descarta o tzinfo no round-trip (volta naive); Postgres preserva.
    Normaliza para UTC antes de comparar para funcionar em ambos."""
    if expira_em.tzinfo is None:
        expira_em = expira_em.replace(tzinfo=timezone.utc)
    return expira_em < datetime.now(timezone.utc)
