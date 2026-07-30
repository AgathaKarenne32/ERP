import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from .models import FormaPagamento, OrigemPedido, StatusComanda, StatusProducao


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class IntegracaoLojaCreate(BaseModel):
    provedor: OrigemPedido
    identificador_externo: str


class IntegracaoLojaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    id_loja: uuid.UUID
    provedor: OrigemPedido
    identificador_externo: str


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
    forma_pagamento: FormaPagamento | None = None


class ComandaFecharRequest(BaseModel):
    forma_pagamento: FormaPagamento


class ComandaCancelarRequest(BaseModel):
    motivo: str


class ComandaVincularClienteRequest(BaseModel):
    id_cliente: uuid.UUID


class TransferirItensRequest(BaseModel):
    id_comanda_destino: uuid.UUID
    id_itens: list[uuid.UUID]


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


class ValorPorFormaPagamentoOut(BaseModel):
    forma_pagamento: FormaPagamento
    valor_total: float
    quantidade_comandas: int


class RelatorioVendasOut(BaseModel):
    periodo_inicio: datetime | None
    periodo_fim: datetime | None
    total_vendas: float
    quantidade_comandas: int
    ticket_medio: float
    por_forma_pagamento: list[ValorPorFormaPagamentoOut]


class ProdutoMaisVendidoOut(BaseModel):
    nome_produto: str
    quantidade_total: float
    valor_total: float


class ItemIngestaoExterna(BaseModel):
    id_produto: uuid.UUID
    nome_produto: str
    quantidade: float
    preco_aplicado: float
    observacoes: str | None = None


class IngestaoExternaRequest(BaseModel):
    origem: OrigemPedido
    identificador_loja_externa: str
    id_referencia_externa: str
    itens: list[ItemIngestaoExterna]
