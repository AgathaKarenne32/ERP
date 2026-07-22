import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import ChatRole


class ChatRequest(BaseModel):
    message: str
    order_id: uuid.UUID | None = None


class ChatMessageOut(BaseModel):
    id: uuid.UUID
    role: ChatRole
    content: str
    order_id: uuid.UUID | None
    created_at: datetime


class ChatResponse(BaseModel):
    reply: ChatMessageOut
