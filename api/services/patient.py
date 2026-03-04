import uuid

from sqlalchemy.orm import Session

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
