from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..db import get_db
from ..models import Case
from ..models_prior_auth import PriorAuthRequest, PriorAuthStatus
from ..schemas_prior_auth import PriorAuthCreate, PriorAuthAccepted, PriorAuthOut
from ..pubsub import get_pubsub

router = APIRouter()


@router.post("/prior-auth", response_model=PriorAuthAccepted, status_code=202)
async def create_prior_auth(
    payload: PriorAuthCreate,
    db: AsyncSession = Depends(get_db),
):
    # Verify the case exists
    result = await db.execute(select(Case).where(Case.id == payload.case_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Case not found")

    # Save to database
    pa_request = PriorAuthRequest(
        case_id=payload.case_id,
        condition=payload.condition,
        drug=payload.drug,
        questions=payload.questions,
        status=PriorAuthStatus.ACCEPTED.value,
    )
    db.add(pa_request)
    await db.commit()
    await db.refresh(pa_request)

    # Publish to pub/sub — this is the ONLY async action
    pubsub = get_pubsub()
    await pubsub.publish("prior-auth-requested", {
        "request_id": pa_request.id,
        "case_id": payload.case_id,
        "condition": payload.condition,
        "drug": payload.drug,
        "questions": payload.questions,
    })

    return PriorAuthAccepted(
        request_id=pa_request.id,
        case_id=payload.case_id,
        status=pa_request.status,
    )


@router.get("/prior-auth/{request_id}", response_model=PriorAuthOut)
async def get_prior_auth(
    request_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PriorAuthRequest)
        .where(PriorAuthRequest.id == request_id)
        .options(selectinload(PriorAuthRequest.answers))
    )
    pa_request = result.scalar_one_or_none()

    if not pa_request:
        raise HTTPException(status_code=404, detail="Prior auth request not found")

    return pa_request