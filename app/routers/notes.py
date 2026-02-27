from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import get_db
from ..models import Case, Note
from ..schemas import NoteCreate, NoteCreated, NotesList

router = APIRouter()


@router.post("/cases/{case_id}/notes", response_model=NoteCreated, status_code=201)
async def add_note(
    case_id: int,
    payload: NoteCreate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Case).where(Case.id == case_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Case not found")

    note = Note(case_id=case_id, author=payload.author, body=payload.body)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return NoteCreated(note_id=note.id, case_id=case_id)


@router.get("/cases/{case_id}/notes", response_model=NotesList)
async def list_notes(case_id: int, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(select(Case.id).where(Case.id == case_id))
    if not exists.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Case not found")

    result = await db.execute(
        select(Note)
        .where(Note.case_id == case_id)
        .order_by(Note.created_at.desc())
    )
    return NotesList(items=result.scalars().all())