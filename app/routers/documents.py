from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import get_db
from ..models import Case, Document, DocumentStatus
from ..schemas import DocumentCreate, DocumentCreated, DocumentOut
from ..enqueue import enqueue_document_processing

router = APIRouter()


@router.post("/cases/{case_id}/documents", response_model=DocumentCreated, status_code=201)
async def add_document(
    case_id: int,
    payload: DocumentCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Case).where(Case.id == case_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Case not found")

    doc = Document(
        case_id=case_id,
        filename=payload.filename,
        content_type=payload.content_type,
        status=DocumentStatus.UPLOADED.value,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    background_tasks.add_task(enqueue_document_processing, doc.id)
    return DocumentCreated(document_id=doc.id, case_id=case_id, status=doc.status)


@router.get("/cases/{case_id}/documents", response_model=List[DocumentOut])
async def list_documents(case_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Case).where(Case.id == case_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Case not found")

    docs = await db.execute(
        select(Document)
        .where(Document.case_id == case_id)
        .order_by(Document.id.desc())
    )
    return docs.scalars().all()