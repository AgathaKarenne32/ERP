import uuid
from datetime import UTC, datetime

from sqlmodel import Field


def utcnow() -> datetime:
    return datetime.now(UTC)


def uuid_pk() -> uuid.UUID:
    return uuid.uuid4()


# Reusable field factories. We keep timestamps on every table (created_at always;
# updated_at where the row mutates) as required by the data model spec.
def pk_field():
    return Field(default_factory=uuid.uuid4, primary_key=True)


def created_field():
    return Field(default_factory=utcnow, nullable=False)
