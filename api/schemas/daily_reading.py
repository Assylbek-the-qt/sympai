import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from models.daily_reading import RiskLevel


class ReadingCreate(BaseModel):
    patient_id: uuid.UUID
    reading_date: date = Field(default_factory=date.today)
    sbp: int = Field(ge=50, le=300)
    dbp: int = Field(ge=30, le=200)
    pulse: int | None = Field(default=None, ge=30, le=250)
    glucose: Decimal | None = Field(default=None, ge=0, le=50)
    medication_taken: bool = False
    symptoms: list[str] | None = None
    notes: str | None = None


class ReadingOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    reading_date: date
    sbp: int
    dbp: int
    pulse: int | None
    glucose: Decimal | None
    medication_taken: bool
    symptoms: list[str] | None
    notes: str | None
    risk_score: int | None
    risk_level: RiskLevel | None
    doctor_reviewed_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True
