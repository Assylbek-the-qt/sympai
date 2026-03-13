import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from models.daily_reading import DailyReading, RiskLevel
from schemas.daily_reading import ReadingCreate
from services.risk import calculate_risk


def get_by_id(db: Session, reading_id: uuid.UUID) -> DailyReading | None:
    return db.query(DailyReading).filter(DailyReading.id == reading_id).first()


def get_by_patient(db: Session, patient_id: uuid.UUID, limit: int = 30) -> list[DailyReading]:
    return (
        db.query(DailyReading)
        .filter(DailyReading.patient_id == patient_id)
        .order_by(DailyReading.reading_date.desc())
        .limit(limit)
        .all()
    )


def get_recent(db: Session, patient_id: uuid.UUID, n: int = 3) -> list[DailyReading]:
    return (
        db.query(DailyReading)
        .filter(DailyReading.patient_id == patient_id)
        .order_by(DailyReading.reading_date.desc())
        .limit(n)
        .all()
    )


def create(db: Session, data: ReadingCreate) -> DailyReading:
    recent = get_recent(db, data.patient_id, n=3)
    risk_level, risk_score = calculate_risk(recent, data.model_dump())

    reading = DailyReading(
        **data.model_dump(),
        risk_level=RiskLevel(risk_level),
        risk_score=risk_score,
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading


def mark_reviewed(db: Session, reading_id: uuid.UUID) -> DailyReading | None:
    reading = get_by_id(db, reading_id)
    if not reading:
        return None
    reading.doctor_reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(reading)
    return reading


def set_skip_reason(db: Session, reading_id: uuid.UUID, reason: str) -> DailyReading | None:
    reading = get_by_id(db, reading_id)
    if not reading:
        return None
    reading.medication_skip_reason = reason
    db.commit()
    db.refresh(reading)
    return reading
