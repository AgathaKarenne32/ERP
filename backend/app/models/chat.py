import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.base import created_field, pk_field
from app.models.enums import ChatRole


class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_messages"

    id: uuid.UUID = pk_field()
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    order_id: uuid.UUID | None = Field(default=None, foreign_key="orders.id", index=True)
    role: ChatRole
    content: str
    created_at: datetime = created_field()
