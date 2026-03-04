import uuid

from sqlalchemy.orm import Session

from models.doctor import Doctor
from models.daily_reading import DailyReading, RiskLevel
from models.patient import Patient
from schemas.doctor import DoctorCreate
from services.auth import hash_password


def get_all(db: Session) -> list[Doctor]:
    return db.query(Doctor).all()


def get_by_id(db: Session, doctor_id: uuid.UUID) -> Doctor | None:
    return db.query(Doctor).filter(Doctor.id == doctor_id).first()


def get_by_email(db: Session, email: str) -> Doctor | None:
    return db.query(Doctor).filter(Doctor.email == email).first()


def create(db: Session, data: DoctorCreate) -> Doctor:
    doctor = Doctor(
        full_name=data.full_name,
        email=data.email,
        password=hash_password(data.password),
        telegram_id=data.telegram_id,
    )
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor


def get_high_risk_patients(db: Session, doctor_id: uuid.UUID) -> list[Patient]:
    """Return patients assigned to doctor whose latest reading is high risk."""
    # Subquery: latest reading date per patient
    from sqlalchemy import func
    latest = (
        db.query(
            DailyReading.patient_id,
            func.max(DailyReading.reading_date).label("max_date"),
        )
        .group_by(DailyReading.patient_id)
        .subquery()
    )

    high_risk_patient_ids = (
        db.query(DailyReading.patient_id)
        .join(latest, (DailyReading.patient_id == latest.c.patient_id) &
                      (DailyReading.reading_date == latest.c.max_date))
        .filter(DailyReading.risk_level == RiskLevel.high)
        .subquery()
    )

    return (
        db.query(Patient)
        .filter(Patient.doctor_id == doctor_id)
        .filter(Patient.id.in_(db.query(high_risk_patient_ids.c.patient_id)))
        .all()
    )
