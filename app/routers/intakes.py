from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import get_db
from ..models import Applicant, Case, StatusEvent, CaseStatus
from ..schemas import IntakeCreate, IntakeCreated

router = APIRouter()


@router.post("/intakes", response_model=IntakeCreated, status_code=201)
async def create_intake(payload: IntakeCreate, db: AsyncSession = Depends(get_db)):
    applicant = Applicant(
        full_name=payload.full_name,
        email=str(payload.email) if payload.email else None,
        phone=payload.phone,
    )
    db.add(applicant)
    await db.flush()

    case = Case(
        applicant_id=applicant.id,
        narrative=payload.narrative,
        current_status=CaseStatus.NEW.value,
    )
    db.add(case)
    await db.flush()

    event = StatusEvent(
        case_id=case.id,
        from_status=None,
        to_status=CaseStatus.NEW.value,
        actor="system",
        reason="case created from intake",
    )
    db.add(event)
    await db.commit()
    return IntakeCreated(case_id=case.id, status=case.current_status)