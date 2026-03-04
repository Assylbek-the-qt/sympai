import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from schemas.patient import PatientCreate, PatientOut, PatientUpdate
from services import patient as patient_service

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=list[PatientOut])
def list_patients(state: Optional[str] = Query(default=None), db: Session = Depends(get_db)):
    return patient_service.get_all(db, state=state)


@router.get("/by-telegram/{telegram_id}", response_model=PatientOut)
def get_by_telegram(telegram_id: int, db: Session = Depends(get_db)):
    patient = patient_service.get_by_telegram_id(db, telegram_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: uuid.UUID, db: Session = Depends(get_db)):
    patient = patient_service.get_by_id(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.post("", response_model=PatientOut, status_code=201)
def create_patient(data: PatientCreate, db: Session = Depends(get_db)):
    return patient_service.create(db, data)


@router.patch("/{patient_id}", response_model=PatientOut)
def update_patient(patient_id: uuid.UUID, data: PatientUpdate, db: Session = Depends(get_db)):
    patient = patient_service.update(db, patient_id, data)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.delete("/{patient_id}", status_code=204)
def delete_patient(patient_id: uuid.UUID, db: Session = Depends(get_db)):
    if not patient_service.delete(db, patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
