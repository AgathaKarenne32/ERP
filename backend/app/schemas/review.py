import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = ""


class ReviewOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    buyer_id: uuid.UUID
    rating: int
    comment: str
    created_at: datetime
