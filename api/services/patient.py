import uuid
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.daily_reading import DailyReading, RiskLevel
from models.patient import Patient
from schemas.patient import PatientCreate, PatientUpdate


def get_all(db: Session, state: str | None = None) -> list[Patient]:
    q = db.query(Patient)
    if state is not None:
        q = q.filter(Patient.state == state)
    return q.all()


def get_by_id(db: Session, patient_id: uuid.UUID) -> Patient | None:
    return db.query(Patient).filter(Patient.id == patient_id).first()


def get_by_telegram_id(db: Session, telegram_id: int) -> Patient | None:
    return db.query(Patient).filter(Patient.telegram_id == telegram_id).first()


def create(db: Session, data: PatientCreate) -> Patient:
    patient = Patient(**data.model_dump())
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def update(db: Session, patient_id: uuid.UUID, data: PatientUpdate) -> Patient | None:
    patient = get_by_id(db, patient_id)
    if not patient:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(patient, field, value)
    db.commit()
    db.refresh(patient)
    return patient


def delete(db: Session, patient_id: uuid.UUID) -> bool:
    patient = get_by_id(db, patient_id)
    if not patient:
        return False
    db.delete(patient)
    db.commit()
    return True


def get_compliance(db: Session, patient_id: uuid.UUID, days: int = 30) -> dict:
    since = date.today() - timedelta(days=days)
    count = (
        db.query(func.count(DailyReading.id))
        .filter(DailyReading.patient_id == patient_id, DailyReading.reading_date >= since)
        .scalar()
    )
    return {
        "compliance_pct": round((count / days) * 100, 1),
        "readings_in_period": count,
        "total_days": days,
    }


def get_stats(db: Session) -> dict:
    today = date.today()
    since = today - timedelta(days=30)
    patients = db.query(Patient).all()
    total = len(patients)

    if total == 0:
        return {
            "total_patients": 0,
            "high_risk_count": 0,
            "avg_compliance_pct": 0.0,
            "missed_today": 0,
            "missed_today_pct": 0.0,
        }

    high_risk = 0
    total_compliance = 0
    missed_today = 0

    for p in patients:
        latest = (
            db.query(DailyReading)
            .filter(DailyReading.patient_id == p.id)
            .order_by(DailyReading.reading_date.desc())
            .first()
        )
        if latest and latest.risk_level in (RiskLevel.high, RiskLevel.critical):
            high_risk += 1

        count = (
            db.query(func.count(DailyReading.id))
            .filter(DailyReading.patient_id == p.id, DailyReading.reading_date >= since)
            .scalar()
        )
        total_compliance += (count / 30) * 100

        has_today = (
            db.query(DailyReading)
            .filter(DailyReading.patient_id == p.id, DailyReading.reading_date == today)
            .first()
        )
        if not has_today:
            missed_today += 1

    return {
        "total_patients": total,
        "high_risk_count": high_risk,
        "avg_compliance_pct": round(total_compliance / total, 1),
        "missed_today": missed_today,
        "missed_today_pct": round((missed_today / total) * 100, 1),
    }
