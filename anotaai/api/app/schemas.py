import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from .models import OrigemPedido, StatusComanda, StatusProducao


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ComandaCreate(BaseModel):
    identificador: str
    id_cliente: uuid.UUID | None = None


class ComandaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    identificador: str
    id_cliente: uuid.UUID | None
    status: StatusComanda
    valor_total: float
    aberta_em: datetime
    motivo_cancelamento: str | None = None


class ComandaCancelarRequest(BaseModel):
    motivo: str


class ComandaVincularClienteRequest(BaseModel):
    id_cliente: uuid.UUID


class ItemComandaCreate(BaseModel):
    id_produto: uuid.UUID
    nome_produto: str
    quantidade: float
    preco_aplicado: float
    origem: OrigemPedido = OrigemPedido.SALAO
    observacoes: str | None = None


class ItemComandaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    id_comanda: uuid.UUID
    nome_produto: str
    quantidade: float
    preco_aplicado: float
    origem: OrigemPedido
    observacoes: str | None


class TicketProducaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    id_item_comanda: uuid.UUID
    status_producao: StatusProducao


class RelatorioVendasOut(BaseModel):
    periodo_inicio: datetime | None
    periodo_fim: datetime | None
    total_vendas: float
    quantidade_comandas: int
    ticket_medio: float


class ProdutoMaisVendidoOut(BaseModel):
    nome_produto: str
    quantidade_total: float
    valor_total: float
