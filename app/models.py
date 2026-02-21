import enum
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import DateTime, ForeignKey, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class CaseStatus(str, enum.Enum):
    NEW = "NEW"
    IN_REVIEW = "IN_REVIEW"
    NEEDS_INFO = "NEEDS_INFO"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    CLOSED = "CLOSED"


def utcnow() -> datetime:                               
    return datetime.now(timezone.utc)


class Applicant(Base):
    __tablename__ = "applicants"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(200))
    email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,                                 
    )

    cases: Mapped[List["Case"]] = relationship(back_populates="applicant")


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    applicant_id: Mapped[int] = mapped_column(ForeignKey("applicants.id", ondelete="CASCADE"))
    narrative: Mapped[str] = mapped_column(Text)
    current_status: Mapped[str] = mapped_column(
        String(32),
        default=CaseStatus.NEW.value,
        index=True,                                     
    )
    assignee: Mapped[Optional[str]] = mapped_column(
        String(120),
        nullable=True,
        index=True,                                     
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,                                
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,                                 
        onupdate=utcnow,                                
    )

    applicant: Mapped["Applicant"] = relationship(back_populates="cases")
    status_events: Mapped[List["StatusEvent"]] = relationship(back_populates="case")
    notes: Mapped[List["Note"]] = relationship(back_populates="case")
    documents: Mapped[List["Document"]] = relationship(back_populates="case")


class StatusEvent(Base):
    __tablename__ = "status_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    from_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32))
    actor: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,                                 
    )

    case: Mapped["Case"] = relationship(back_populates="status_events")


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    author: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,                                
    )

    case: Mapped["Case"] = relationship(back_populates="notes")


class DocumentStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))

    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    gcs_uri: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    status: Mapped[str] = mapped_column(String(32), default=DocumentStatus.UPLOADED.value)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,                                 
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,                                
        onupdate=utcnow,                                
    )                                                   

    case: Mapped["Case"] = relationship(back_populates="documents")