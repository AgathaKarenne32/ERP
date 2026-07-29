import time
import uuid

import httpx
from sqlmodel import Session, select

from .core.config import settings
from .core.db import engine
from .core.security import hash_password
from .models import Operador, PapelOperador


def _buscar_id_loja() -> uuid.UUID:
    """RN06: a ecletica-api é a fonte da verdade de Loja. Consulta o registro
    real em vez de usar um id fixo, com algumas tentativas porque os dois
    serviços sobem em paralelo no docker compose e a ecletica pode ainda não
    ter semeado a loja dela no primeiro instante."""
    headers = {"X-Internal-Token": settings.internal_api_token}
    for _tentativa in range(10):
        try:
            resposta = httpx.get(
                f"{settings.ecletica_api_url}/lojas", headers=headers, timeout=5.0
            )
            resposta.raise_for_status()
            lojas = resposta.json()
            if lojas:
                return uuid.UUID(lojas[0]["id"])
        except httpx.HTTPError:
            pass
        time.sleep(2)

    raise RuntimeError(
        "Não foi possível obter o id_loja da ecletica-api após várias tentativas."
    )


def seed_demo_data() -> None:
    """Idempotente: só semeia se ainda não houver nenhum operador cadastrado."""
    with Session(engine) as session:
        if session.exec(select(Operador)).first():
            return

        id_loja = _buscar_id_loja()

        admin = Operador(
            id_loja=id_loja,
            nome="Administrador",
            email="admin@anotaai.app",
            senha_hash=hash_password("admin123"),
            papel=PapelOperador.ADMIN,
        )
        session.add(admin)
        session.commit()
