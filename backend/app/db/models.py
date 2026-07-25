"""ORM models — documents, ledger line items, query history."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_file: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    doc_type: Mapped[str] = mapped_column(String(64), index=True)  # invoice|report|contract
    content_sha256: Mapped[str] = mapped_column(String(64), index=True)
    vendor: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, index=True)
    invoice_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    currency: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    total_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    period: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    invoice_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    payment_terms: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    po_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    extra: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    line_items: Mapped[list[LineItem]] = relationship(
        "LineItem",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class LineItem(Base):
    __tablename__ = "line_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    sku: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    qty: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unit_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    line_total: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sold_qty: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    received_qty: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    return_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    period: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    vendor: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, index=True)
    row_kind: Mapped[str] = mapped_column(String(32), default="line")  # line|report|contract_price

    document: Mapped[Document] = relationship("Document", back_populates="line_items")


class QueryRun(Base):
    __tablename__ = "query_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    markdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
