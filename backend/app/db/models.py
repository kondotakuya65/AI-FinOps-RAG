"""ORM models — Document registry, query history, ledger line items (next commits)."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
