from sqlmodel import Session, select

from .core.db import engine
from .core.security import hash_password
from .models import Loja, PapelUsuario, Usuario


def seed_demo_data() -> None:
    """Idempotente: só semeia se ainda não houver nenhuma loja cadastrada."""
    with Session(engine) as session:
        if session.exec(select(Loja)).first():
            return

        loja = Loja(nome="Bar Eclética - Matriz", cnpj="00.000.000/0001-00")
        session.add(loja)
        session.commit()
        session.refresh(loja)

        admin = Usuario(
            id_loja=loja.id,
            nome="Administrador",
            email="admin@ecletica.app",
            senha_hash=hash_password("admin123"),
            papel=PapelUsuario.ADMIN,
        )
        session.add(admin)
        session.commit()
