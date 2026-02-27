from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class PriorAuthCreate(BaseModel):
    case_id: int
    condition: str = Field(min_length=1, max_length=500)
    drug: str = Field(min_length=1, max_length=500)
    questions: list[str] = Field(min_length=1)


class PriorAuthAccepted(BaseModel):
    request_id: int
    case_id: int
    status: str
    message: str = "Request accepted. Processing asynchronously."


class PriorAuthAnswerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question: str
    answer: str
    supporting_record_ids: list
    confidence: float | None = None


class PriorAuthOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    condition: str
    drug: str
    status: str
    error_message: str | None = None
    total_records_fetched: int | None = None
    relevant_records_count: int | None = None
    patient_summary: str | None = None
    created_at: datetime
    updated_at: datetime
    answers: list[PriorAuthAnswerOut] = []