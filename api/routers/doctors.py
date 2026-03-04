import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas.doctor import DoctorCreate, DoctorOut
from schemas.patient import PatientOut
from services import doctor as doctor_service

router = APIRouter(prefix="/doctors", tags=["doctors"])


@router.get("", response_model=list[DoctorOut])
def list_doctors(db: Session = Depends(get_db)):
    return doctor_service.get_all(db)


@router.post("", response_model=DoctorOut, status_code=201)
def create_doctor(data: DoctorCreate, db: Session = Depends(get_db)):
    if doctor_service.get_by_email(db, data.email):
        raise HTTPException(status_code=409, detail="Email already registered")
    return doctor_service.create(db, data)


@router.get("/{doctor_id}", response_model=DoctorOut)
def get_doctor(doctor_id: uuid.UUID, db: Session = Depends(get_db)):
    doctor = doctor_service.get_by_id(db, doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor


@router.get("/{doctor_id}/alerts", response_model=list[PatientOut])
def get_alerts(doctor_id: uuid.UUID, db: Session = Depends(get_db)):
    if not doctor_service.get_by_id(db, doctor_id):
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor_service.get_high_risk_patients(db, doctor_id)
