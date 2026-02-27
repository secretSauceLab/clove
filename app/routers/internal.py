from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import get_db
from ..models import Document
from ..jobs import process_document

router = APIRouter(prefix="/internal")


@router.post("/documents/{document_id}/process", status_code=202)
async def process_document_now(
    document_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == document_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Document not found")

    await process_document(document_id)
    return {"status": "accepted", "document_id": document_id}