"""Query HTTP API."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.query.service import run_query

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3)
    use_llm: bool = True


@router.post("")
def query_documents(body: QueryRequest, db: Session = Depends(get_db)) -> dict:
    return run_query(db, body.question, use_llm=body.use_llm)
