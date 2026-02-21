# app/routers/cases.py
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select
from sqlalchemy.orm import selectinload

from ..db import get_db
from ..models import Applicant, Case, StatusEvent
from ..schemas import CaseDetail, CaseUpdate, CaseUpdated, CaseListResponse, CaseListItem

router = APIRouter()

ALLOWED_TRANSITIONS = {
    "NEW": {"IN_REVIEW", "CLOSED"},
    "IN_REVIEW": {"NEEDS_INFO", "SUBMITTED", "CLOSED"},
    "NEEDS_INFO": {"IN_REVIEW", "CLOSED"},
    "SUBMITTED": {"APPROVED", "DENIED"},
    "APPROVED": {"CLOSED"},
    "DENIED": {"CLOSED"},
    "CLOSED": set(),
}


@router.get("/cases", response_model=CaseListResponse)
async def list_cases(
    status: Optional[str] = None,
    assignee: Optional[str] = None,
    limit: int = 20,
    cursor: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    limit = max(1, min(limit, 100))

    q = (
        select(Case)
        .join(Applicant)
        .options(selectinload(Case.applicant))
    )

    if status:
        q = q.where(Case.current_status == status)
    if assignee:
        q = q.where(Case.assignee == assignee)
    if cursor is not None:
        q = q.where(Case.id < cursor)

    q = q.order_by(desc(Case.id)).limit(limit + 1)

    result = await db.execute(q)
    rows = list(result.scalars().all())

    has_more = len(rows) > limit
    rows = rows[:limit]

    items = [
        CaseListItem(
            case_id=c.id,
            applicant_name=c.applicant.full_name,
            current_status=c.current_status,
            assignee=c.assignee,
            created_at=c.created_at,
        )
        for c in rows
    ]

    next_cursor = rows[-1].id if has_more and rows else None
    return CaseListResponse(items=items, next_cursor=next_cursor)


@router.get("/cases/{case_id}", response_model=CaseDetail)
async def get_case(case_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Case)
        .where(Case.id == case_id)
        .options(
            selectinload(Case.applicant),
            selectinload(Case.status_events),
            selectinload(Case.notes),
        )
    )
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    case.status_events.sort(key=lambda e: e.created_at, reverse=True)
    case.notes.sort(key=lambda n: n.created_at, reverse=True)
    return case


@router.patch("/cases/{case_id}", response_model=CaseUpdated)
async def update_case(
    case_id: int,
    payload: CaseUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    previous_status = case.current_status

    if payload.assignee is not None:
        case.assignee = payload.assignee

    if payload.status is not None:
        new_status = payload.status

        if new_status not in ALLOWED_TRANSITIONS:
            raise HTTPException(status_code=400, detail=f"Unknown status '{new_status}'")

        allowed = ALLOWED_TRANSITIONS.get(previous_status, set())
        if new_status == previous_status:
            pass
        elif new_status not in allowed:
            raise HTTPException(
                status_code=409,
                detail=f"Invalid status transition {previous_status} -> {new_status}",
            )
        else:
            event = StatusEvent(
                case_id=case.id,
                from_status=previous_status,
                to_status=new_status,
                actor=payload.actor or "system",
                reason=payload.reason,
            )
            db.add(event)
            case.current_status = new_status

    await db.commit()
    await db.refresh(case)
    return CaseUpdated(
        case_id=case.id,
        previous_status=previous_status,
        status=case.current_status,
        assignee=case.assignee,
    )