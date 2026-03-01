import uuid
from datetime import date, datetime
from enum import Enum

from sqlalchemy import Boolean, Column, Date, DateTime, Enum as SAEnum, ForeignKey, Numeric, SmallInteger, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from models.doctor import Base


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class DailyReading(Base):
    __tablename__ = "daily_readings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    reading_date = Column(Date, nullable=False, default=date.today)
    sbp = Column(SmallInteger, nullable=False)
    dbp = Column(SmallInteger, nullable=False)
    pulse = Column(SmallInteger, nullable=True)
    glucose = Column(Numeric(4, 1), nullable=True)
    medication_taken = Column(Boolean, nullable=False, default=False)
    symptoms = Column(ARRAY(Text), nullable=True)
    notes = Column(Text, nullable=True)
    risk_score = Column(SmallInteger, nullable=True)
    risk_level = Column(SAEnum(RiskLevel), nullable=True)
    doctor_reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    patient = relationship("Patient")
