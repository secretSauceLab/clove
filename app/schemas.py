from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime
from .models import CaseStatus

class NoteCreate(BaseModel):
    author: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=10_000)

class NoteCreated(BaseModel):
    note_id: int
    case_id: int


class CaseUpdate(BaseModel):
    # all optional so you can patch one thing at a time
    status: Optional[CaseStatus] = Field(default=None, description="New case status")
    assignee: Optional[str] = Field(default=None, max_length=120)
    actor: Optional[str] = Field(default="system", max_length=120)
    reason: Optional[str] = Field(default=None, max_length=500)


class CaseUpdated(BaseModel):
    case_id: int
    previous_status: str
    status: str
    assignee: Optional[str] = None


class IntakeCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=50)
    narrative: str = Field(min_length=1, max_length=20_000)


class IntakeCreated(BaseModel):
    case_id: int
    status: str


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    note_id: int = Field(validation_alias="id")
    case_id: int
    author: str
    body: str
    created_at: datetime

class NotesList(BaseModel):
    items: List[NoteOut]


class CaseListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    case_id: int
    applicant_name: str
    current_status: str
    assignee: Optional[str] = None
    created_at: datetime


class CaseListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: List[CaseListItem]
    next_cursor: Optional[int] = None

class DocumentCreate(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: Optional[str] = Field(default=None, max_length=100)


class DocumentCreated(BaseModel):
    document_id: int
    case_id: int
    status: str

class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    document_id: int = Field(validation_alias="id")
    case_id: int
    filename: str
    content_type: str | None = None
    gcs_uri: str | None = None
    status: str
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

class ApplicantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    email: EmailStr | None = None
    phone: str | None = None
    created_at: datetime

class StatusEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    case_id: int
    from_status: str | None = None
    to_status: str
    actor: str | None = None
    reason: str | None = None
    created_at: datetime

class CaseDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    narrative: str
    current_status: str
    assignee: str | None = None
    created_at: datetime
    updated_at: datetime
    applicant: ApplicantOut
    status_events: list[StatusEventOut] = []
    notes: list[NoteOut] = []

