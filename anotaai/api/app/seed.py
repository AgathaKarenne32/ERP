import os
import uuid

from sqlmodel import Session, select

from .core.db import engine
from .core.security import hash_password
from .models import Operador, PapelOperador

# Fase 0: id_loja gerado/fixado aqui de forma independente da ecletica-api
# (cada serviço tem seu próprio banco). A sincronização do cadastro de lojas
# entre os dois serviços entra na Fase 4 do plano.
DEMO_LOJA_ID = uuid.UUID(os.getenv("ANOTAAI_DEMO_LOJA_ID", "00000000-0000-0000-0000-000000000001"))


def seed_demo_data() -> None:
    """Idempotente: só semeia se ainda não houver nenhum operador cadastrado."""
    with Session(engine) as session:
        if session.exec(select(Operador)).first():
            return

        admin = Operador(
            id_loja=DEMO_LOJA_ID,
            nome="Administrador",
            email="admin@anotaai.app",
            senha_hash=hash_password("admin123"),
            papel=PapelOperador.ADMIN,
        )
        session.add(admin)
        session.commit()
