import uuid

from pydantic import BaseModel, ConfigDict, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


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
