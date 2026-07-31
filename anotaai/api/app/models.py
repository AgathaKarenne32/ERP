import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlmodel import Field, SQLModel, UniqueConstraint


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PapelOperador(str, Enum):
    ADMIN = "ADMIN"
    GERENTE = "GERENTE"
    CAIXA = "CAIXA"
    COZINHA = "COZINHA"
    GARCOM = "GARCOM"


class Operador(SQLModel, table=True):
    """Conta de acesso ao PDV/KDS. Independente do Usuario da ecletica-api
    (cada serviço tem sua própria base de autenticação — fase 0)."""

    __tablename__ = "operador"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    id_loja: uuid.UUID = Field(index=True)
    nome: str
    email: str = Field(unique=True, index=True)
    senha_hash: str
    papel: PapelOperador = Field(default=PapelOperador.GARCOM)
    ativo: bool = Field(default=True)


class RefreshToken(SQLModel, table=True):
    """Token opaco (não-JWT) usado para renovar o access token. Só o hash é
    persistido — o valor bruto existe apenas na resposta do login/refresh —
    e a revogação é feita marcando o registro, já que JWT puro não permite
    invalidar um token já emitido antes do seu vencimento."""

    __tablename__ = "refresh_token"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    id_operador: uuid.UUID = Field(foreign_key="operador.id", index=True)
    token_hash: str = Field(unique=True, index=True)
    criado_em: datetime = Field(default_factory=_now)
    expira_em: datetime
    revogado: bool = Field(default=False)
    revogado_em: datetime | None = None


class StatusComanda(str, Enum):
    ABERTA = "ABERTA"
    PAGA = "PAGA"
    CANCELADA = "CANCELADA"


class OrigemPedido(str, Enum):
    SALAO = "SALAO"
    IFOOD = "IFOOD"
    WHATSAPP = "WHATSAPP"


class IntegracaoLoja(SQLModel, table=True):
    """Roteia um pedido externo (iFood/WhatsApp) para a loja correta.
    Sem isso, a ingestão externa não tem como saber qual loja recebeu
    o pedido — é o de-para entre o identificador do provedor (merchant
    ID do iFood, número de telefone do WhatsApp Business) e id_loja."""

    __tablename__ = "integracao_loja"
    __table_args__ = (
        UniqueConstraint("provedor", "identificador_externo", name="uq_integracao_provedor_identificador"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    id_loja: uuid.UUID = Field(index=True)
    provedor: OrigemPedido
    identificador_externo: str = Field(index=True)
    criado_em: datetime = Field(default_factory=_now)


class FormaPagamento(str, Enum):
    DINHEIRO = "DINHEIRO"
    CARTAO_CREDITO = "CARTAO_CREDITO"
    CARTAO_DEBITO = "CARTAO_DEBITO"
    PIX = "PIX"


class Comanda(SQLModel, table=True):
    __tablename__ = "comanda"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    id_loja: uuid.UUID = Field(index=True)
    id_cliente: uuid.UUID | None = Field(default=None, index=True)  # referência solta ao Cliente da ecletica-api
    identificador: str  # Ex: 'MESA 04', 'SENHA 102'
    status: StatusComanda = Field(default=StatusComanda.ABERTA)
    valor_total: float = Field(default=0)
    desconto_total: float = Field(default=0)
    aberta_em: datetime = Field(default_factory=_now)
    fechada_em: datetime | None = None
    motivo_cancelamento: str | None = None
    origem_externa: OrigemPedido | None = Field(default=None, index=True)
    id_referencia_externa: str | None = Field(default=None, index=True)
    forma_pagamento: FormaPagamento | None = None


class ItemComanda(SQLModel, table=True):
    __tablename__ = "item_comanda"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    id_loja: uuid.UUID = Field(index=True)
    id_comanda: uuid.UUID = Field(foreign_key="comanda.id", index=True)
    id_produto: uuid.UUID  # referência ao Produto da ecletica-api (outro serviço/banco)
    nome_produto: str  # snapshot — RN04: imutabilidade de preço/nome histórico
    quantidade: float
    preco_aplicado: float  # snapshot — RN04
    origem: OrigemPedido = Field(default=OrigemPedido.SALAO)
    observacoes: str | None = None
    criado_em: datetime = Field(default_factory=_now)


class StatusProducao(str, Enum):
    PENDENTE = "PENDENTE"
    EM_PREPARO = "EM_PREPARO"
    PRONTO = "PRONTO"
    ENTREGUE = "ENTREGUE"


class TicketProducao(SQLModel, table=True):
    """Equivalente à coleção `tickets_producao` do desenho original em Firestore,
    agora como tabela + WebSocket (fase 3 do plano) para alimentar o KDS."""

    __tablename__ = "ticket_producao"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    id_loja: uuid.UUID = Field(index=True)
    id_item_comanda: uuid.UUID = Field(foreign_key="item_comanda.id", index=True)
    status_producao: StatusProducao = Field(default=StatusProducao.PENDENTE)
    atualizado_em: datetime = Field(default_factory=_now)
