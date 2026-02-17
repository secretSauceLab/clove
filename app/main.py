from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from typing import Dict, Set, Optional
from sqlalchemy import desc 

from .db import get_db
from .models import Applicant, Case, StatusEvent, Note, CaseStatus
from .schemas import IntakeCreate, IntakeCreated, CaseDetail, CaseUpdate, CaseUpdated, NoteCreate, NoteCreated, CaseListResponse, CaseListItem

app = FastAPI(title="Patient Advocacy Intake API")

ALLOWED_TRANSITIONS: Dict[str, Set[str]] = {
    "NEW": {"IN_REVIEW", "CLOSED"},
    "IN_REVIEW": {"NEEDS_INFO", "SUBMITTED", "CLOSED"},
    "NEEDS_INFO": {"IN_REVIEW", "CLOSED"},
    "SUBMITTED": {"APPROVED", "DENIED"},
    "APPROVED": {"CLOSED"},
    "DENIED": {"CLOSED"},
    "CLOSED": set(),
}

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/intakes", response_model=IntakeCreated, status_code=201)
def create_intake(payload: IntakeCreate, db: Session = Depends(get_db)):
    try:
        applicant = Applicant(
            full_name=payload.full_name,
            email=str(payload.email) if payload.email else None,
            phone=payload.phone,
        )
        db.add(applicant)
        db.flush()  # assigns applicant.id without committing

        case = Case(
            applicant_id=applicant.id,
            narrative=payload.narrative,
            current_status=CaseStatus.NEW.value,
        )
        db.add(case)
        db.flush()  # assigns case.id

        event = StatusEvent(
            case_id=case.id,
            from_status=None,
            to_status=CaseStatus.NEW.value,
            actor="system",
            reason="case created from intake",
        )
        db.add(event)

        db.commit()
        return IntakeCreated(case_id=case.id, status=case.current_status)
    except Exception:
        db.rollback()
        raise

@app.get("/cases/{case_id}", response_model=CaseDetail)
def get_case(case_id: int, db: Session = Depends(get_db)):
    case = (
        db.query(Case)
        .options(
            selectinload(Case.applicant),
            selectinload(Case.status_events),
            selectinload(Case.notes),
        )
        .filter(Case.id == case_id)
        .first()
    )

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Optional: sort status events newest-first for the UI
    case.status_events.sort(key=lambda e: e.created_at, reverse=True)
    case.notes.sort(key=lambda n: n.created_at, reverse=True)

    return case

@app.patch("/cases/{case_id}", response_model=CaseUpdated)
def update_case(case_id: int, payload: CaseUpdate, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    previous_status = case.current_status

    # Update assignee if provided
    if payload.assignee is not None:
        case.assignee = payload.assignee

    # Update status if provided
    if payload.status is not None:
        new_status = payload.status

        if new_status not in ALLOWED_TRANSITIONS:
            raise HTTPException(status_code=400, detail=f"Unknown status '{new_status}'")

        allowed = ALLOWED_TRANSITIONS.get(previous_status, set())
        if new_status == previous_status:
            # no-op status update is allowed but doesn't create an event
            pass
        elif new_status not in allowed:
            raise HTTPException(
                status_code=409,
                detail=f"Invalid status transition {previous_status} -> {new_status}",
            )
        else:
            # record audit event
            event = StatusEvent(
                case_id=case.id,
                from_status=previous_status,
                to_status=new_status,
                actor=payload.actor or "system",
                reason=payload.reason,
            )
            db.add(event)
            case.current_status = new_status

    try:
        db.commit()
        db.refresh(case)
        return CaseUpdated(
            case_id=case.id,
            previous_status=previous_status,
            status=case.current_status,
            assignee=case.assignee,
        )
    except Exception:
        db.rollback()
        raise

@app.post("/cases/{case_id}/notes", response_model=NoteCreated, status_code=201)
def add_note(case_id: int, payload: NoteCreate, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    note = Note(
        case_id=case_id,
        author=payload.author,
        body=payload.body,
    )
    db.add(note)

    try:
        db.commit()
        db.refresh(note)
        return NoteCreated(note_id=note.id, case_id=case_id)
    except Exception:
        db.rollback()
        raise




@app.get("/cases", response_model=CaseListResponse)
def list_cases(
    status: Optional[str] = None,
    assignee: Optional[str] = None,
    limit: int = 20,
    cursor: Optional[int] = None,
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 100))

    q = db.query(Case).join(Applicant)

    if status:
        q = q.filter(Case.current_status == status)
    if assignee:
        q = q.filter(Case.assignee == assignee)
    if cursor is not None:
        # cursor is "the last seen case id" (we return older items next)
        q = q.filter(Case.id < cursor)

    q = q.order_by(desc(Case.id)).limit(limit + 1)

    rows = q.all()
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