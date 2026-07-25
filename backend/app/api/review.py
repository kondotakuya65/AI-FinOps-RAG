"""Invoice review HTTP API (PO + contract price drift)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.reconcile.review import review_invoice

router = APIRouter(prefix="/review", tags=["review"])


class ReviewRequest(BaseModel):
    invoice_id: str = Field(..., min_length=3, examples=["INV-104"])
    include_qty: bool = False


@router.post("")
def review_invoice_endpoint(body: ReviewRequest, db: Session = Depends(get_db)) -> dict:
    result = review_invoice(db, body.invoice_id.upper(), include_qty=body.include_qty)
    if not result.get("found"):
        raise HTTPException(status_code=404, detail=result.get("reason") or "Not found")
    return result


@router.get("/{invoice_id}")
def review_invoice_get(invoice_id: str, db: Session = Depends(get_db)) -> dict:
    result = review_invoice(db, invoice_id.upper(), include_qty=False)
    if not result.get("found"):
        raise HTTPException(status_code=404, detail=result.get("reason") or "Not found")
    return result
