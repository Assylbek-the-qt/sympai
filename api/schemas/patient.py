import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from models.patient import DiagnosisType


class PatientBase(BaseModel):
    full_name: str = Field(max_length=200)
    age: int = Field(gt=0, lt=150)
    diagnosis: DiagnosisType
    current_medication: str | None = Field(default=None, max_length=200)
    language: str = Field(default="ru", max_length=5)


class PatientCreate(PatientBase):
    telegram_id: int
    doctor_id: uuid.UUID


class PatientUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=200)
    age: int | None = Field(default=None, gt=0, lt=150)
    diagnosis: DiagnosisType | None = None
    current_medication: str | None = Field(default=None, max_length=200)
    language: str | None = Field(default=None, max_length=5)


class PatientOut(PatientBase):
    id: uuid.UUID
    telegram_id: int
    doctor_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
