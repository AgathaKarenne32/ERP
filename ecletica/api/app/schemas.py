import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from .models import TipoMovimentoEstoque


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LojaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    cnpj: str
    ativa: bool


class ProdutoCreate(BaseModel):
    nome: str
    preco_venda: float
    categoria: str | None = None


class ProdutoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    preco_venda: float
    categoria: str | None
    ativo_venda: bool


class InsumoCreate(BaseModel):
    nome: str
    unidade_medida: str
    custo_unitario: float
    qtd_estoque: float = 0


class InsumoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    unidade_medida: str
    custo_unitario: float
    qtd_estoque: float


class FichaTecnicaItemCreate(BaseModel):
    id_insumo: uuid.UUID
    qtd_utilizada: float


class ClienteCreate(BaseModel):
    nome: str
    cpf: str


class ClienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    cpf: str
    pontos_fidelidade: int


class CreditarPontosRequest(BaseModel):
    id_loja: uuid.UUID
    valor_gasto: float
    referencia: str | None = None


class ItemVendaBaixa(BaseModel):
    id_produto: uuid.UUID
    quantidade: float


class BaixaEstoqueRequest(BaseModel):
    id_loja: uuid.UUID
    referencia: str | None = None
    valor_total: float = 0
    itens: list[ItemVendaBaixa]


class CaixaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    aberto_em: datetime
    fechado_em: datetime | None
    valor_total: float


class MovimentoEstoqueCreate(BaseModel):
    tipo: TipoMovimentoEstoque
    quantidade: float
    referencia: str | None = None


class MovimentoEstoqueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    id_insumo: uuid.UUID
    tipo: TipoMovimentoEstoque
    quantidade: float
    referencia: str | None
    criado_em: datetime
