from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime

class NoteCreate(BaseModel):
    author: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1)

class NoteCreated(BaseModel):
    note_id: int
    case_id: int

class CaseUpdate(BaseModel):
    # all optional so you can patch one thing at a time
    status: Optional[str] = Field(default=None, description="New case status")
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
    narrative: str = Field(min_length=1)


class IntakeCreated(BaseModel):
    case_id: int
    status: str

class ApplicantOut(BaseModel):
    id: int
    full_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    created_at: datetime

    class Config:
        model_config = ConfigDict(from_attributes=True)



class StatusEventOut(BaseModel):
    id: int
    from_status: Optional[str] = None
    to_status: str
    actor: Optional[str] = None
    reason: Optional[str] = None
    created_at: datetime

    class Config:
        model_config = ConfigDict(from_attributes=True)



class NoteOut(BaseModel):
    id: int
    author: str
    body: str
    created_at: datetime

    class Config:
        model_config = ConfigDict(from_attributes=True)


class CaseDetail(BaseModel):
    id: int
    narrative: str
    current_status: str
    assignee: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    applicant: ApplicantOut
    status_events: List[StatusEventOut] = []
    notes: List[NoteOut] = []

    class Config:
        model_config = ConfigDict(from_attributes=True)


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
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    filename: str
    content_type: Optional[str] = None
    gcs_uri: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

