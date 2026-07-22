import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.base import created_field, pk_field
from app.models.enums import UserRole


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = pk_field()
    name: str
    email: str = Field(index=True, unique=True)
    password_hash: str
    role: UserRole = Field(default=UserRole.BUYER)
    created_at: datetime = created_field()


class SellerProfile(SQLModel, table=True):
    __tablename__ = "seller_profiles"

    id: uuid.UUID = pk_field()
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, unique=True)
    store_name: str
    # Reputation is the running average of the seller's product reviews (default 5
    # so a brand-new store isn't penalized before it has any reviews).
    reputation_score: float = Field(default=5.0)
    sales_count: int = Field(default=0)
