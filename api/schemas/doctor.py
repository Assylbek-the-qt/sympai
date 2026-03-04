import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DoctorCreate(BaseModel):
    full_name: str = Field(max_length=200)
    email: str = Field(max_length=255)
    password: str
    telegram_id: int | None = None


class DoctorOut(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    telegram_id: int | None
    created_at: datetime

    class Config:
        from_attributes = True
