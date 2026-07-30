import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlmodel import Field, SQLModel, UniqueConstraint


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PapelUsuario(str, Enum):
    ADMIN = "ADMIN"
    GERENTE = "GERENTE"
    CAIXA = "CAIXA"
    COZINHA = "COZINHA"
    GARCOM = "GARCOM"


class Loja(SQLModel, table=True):
    __tablename__ = "loja"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    nome: str
    cnpj: str = Field(unique=True)
    ativa: bool = Field(default=True)
    criado_em: datetime = Field(default_factory=_now)


class Usuario(SQLModel, table=True):
    __tablename__ = "usuario"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    id_loja: uuid.UUID = Field(foreign_key="loja.id", index=True)
    nome: str
    email: str = Field(unique=True, index=True)
    senha_hash: str
    papel: PapelUsuario = Field(default=PapelUsuario.CAIXA)
    ativo: bool = Field(default=True)
    criado_em: datetime = Field(default_factory=_now)


class Insumo(SQLModel, table=True):
    __tablename__ = "insumo"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    id_loja: uuid.UUID = Field(foreign_key="loja.id", index=True)
    nome: str
    unidade_medida: str  # Ex: 'L', 'KG', 'UN'
    custo_unitario: float
    qtd_estoque: float = Field(default=0)


class Produto(SQLModel, table=True):
    __tablename__ = "produto"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    id_loja: uuid.UUID = Field(foreign_key="loja.id", index=True)
    nome: str
    preco_venda: float
    categoria: str | None = None
    ativo_venda: bool = Field(default=True)


class FichaTecnica(SQLModel, table=True):
    """Relacionamento N:N entre Produto e Insumo (RN01 - baixa automática de estoque)."""

    __tablename__ = "ficha_tecnica"

    id_produto: uuid.UUID = Field(foreign_key="produto.id", primary_key=True)
    id_insumo: uuid.UUID = Field(foreign_key="insumo.id", primary_key=True)
    qtd_utilizada: float


class Cliente(SQLModel, table=True):
    __tablename__ = "cliente"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    id_loja: uuid.UUID = Field(foreign_key="loja.id", index=True)
    nome: str
    cpf: str = Field(index=True)
    pontos_fidelidade: int = Field(default=0)


class TipoMovimentoEstoque(str, Enum):
    ENTRADA = "ENTRADA"
    SAIDA_VENDA = "SAIDA_VENDA"
    AJUSTE = "AJUSTE"


class MovimentoEstoque(SQLModel, table=True):
    __tablename__ = "movimento_estoque"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    id_loja: uuid.UUID = Field(foreign_key="loja.id", index=True)
    id_insumo: uuid.UUID = Field(foreign_key="insumo.id", index=True)
    tipo: TipoMovimentoEstoque
    quantidade: float
    referencia: str | None = None
    criado_em: datetime = Field(default_factory=_now)


class FechamentoCaixa(SQLModel, table=True):
    __tablename__ = "fechamento_caixa"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    id_loja: uuid.UUID = Field(foreign_key="loja.id", index=True)
    aberto_em: datetime
    fechado_em: datetime | None = None
    valor_total: float = Field(default=0)


class VendaProcessada(SQLModel, table=True):
    """Marca de idempotência pra POST /vendas/baixa-estoque. A chamada
    anotaai->ecletica é síncrona e ganhou retry de rede — sem isso, um
    retry depois que o processamento já tinha concluído (timeout só na
    volta da resposta) duplicaria a baixa de estoque e a soma no caixa."""

    __tablename__ = "venda_processada"
    __table_args__ = (
        UniqueConstraint("id_loja", "referencia", name="uq_venda_processada_loja_referencia"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    id_loja: uuid.UUID = Field(foreign_key="loja.id", index=True)
    referencia: str | None = Field(default=None, index=True)
    criado_em: datetime = Field(default_factory=_now)


class RefreshToken(SQLModel, table=True):
    """Token opaco (não-JWT) usado para renovar o access token. Só o hash é
    persistido — o valor bruto existe apenas na resposta do login/refresh —
    e a revogação é feita marcando o registro, já que JWT puro não permite
    invalidar um token já emitido antes do seu vencimento."""

    __tablename__ = "refresh_token"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    id_usuario: uuid.UUID = Field(foreign_key="usuario.id", index=True)
    token_hash: str = Field(unique=True, index=True)
    criado_em: datetime = Field(default_factory=_now)
    expira_em: datetime
    revogado: bool = Field(default=False)
    revogado_em: datetime | None = None
