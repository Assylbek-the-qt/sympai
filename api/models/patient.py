import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import BigInteger, Column, DateTime, Enum as SAEnum, ForeignKey, SmallInteger, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from models.doctor import Base


class DiagnosisType(str, Enum):
    hypertension = "hypertension"
    diabetes = "diabetes"
    both = "both"


class Patient(Base):
    __tablename__ = "patients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_id = Column(BigInteger, nullable=False, unique=True)
    full_name = Column(String(200), nullable=False)
    age = Column(SmallInteger, nullable=False)
    diagnosis = Column(SAEnum(DiagnosisType), nullable=False)
    current_medication = Column(String(200), nullable=True)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=False)
    language = Column(String(5), nullable=False, default="ru")
    state = Column(String(30), nullable=True)
    comorbidities = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    doctor = relationship("Doctor")
