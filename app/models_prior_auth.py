# app/models_prior_auth.py
import enum
from datetime import datetime
from typing import Optional, List

from sqlalchemy import DateTime, ForeignKey, String, Text, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base
from .models import utcnow


class PriorAuthStatus(str, enum.Enum):
    ACCEPTED = "ACCEPTED"
    FETCHING = "FETCHING"
    CLASSIFYING = "CLASSIFYING"
    ANSWERING = "ANSWERING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PriorAuthRequest(Base):
    __tablename__ = "prior_auth_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE")
    )
    condition: Mapped[str] = mapped_column(String(500))
    drug: Mapped[str] = mapped_column(String(500))
    questions: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(
        String(32),
        default=PriorAuthStatus.ACCEPTED.value,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_records_fetched: Mapped[int | None] = mapped_column(nullable=True)
    relevant_records_count: Mapped[int | None] = mapped_column(nullable=True)
    patient_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    answers: Mapped[list["PriorAuthAnswer"]] = relationship(
        back_populates="request",
        cascade="all, delete-orphan",
    )


class PriorAuthAnswer(Base):
    __tablename__ = "prior_auth_answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("prior_auth_requests.id", ondelete="CASCADE")
    )
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    supporting_record_ids: Mapped[dict] = mapped_column(JSON)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    request: Mapped["PriorAuthRequest"] = relationship(back_populates="answers")