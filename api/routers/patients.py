import io
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from schemas.patient import PatientCreate, PatientOut, PatientUpdate
from services import patient as patient_service
from services import daily_reading as reading_service
from services import report as report_service

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    return patient_service.get_stats(db)


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


@router.get("/{patient_id}/compliance")
def get_compliance(patient_id: uuid.UUID, days: int = 30, db: Session = Depends(get_db)):
    patient = patient_service.get_by_id(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient_service.get_compliance(db, patient_id, days)


@router.get("/{patient_id}/report")
def get_patient_report(patient_id: uuid.UUID, db: Session = Depends(get_db)):
    patient = patient_service.get_by_id(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    readings = reading_service.get_by_patient(db, patient_id, limit=30)
    pdf_bytes = report_service.build_pdf(patient, readings)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="sympai_report_{patient_id}.pdf"'},
    )


@router.get("/{patient_id}/chart")
def get_patient_chart(patient_id: uuid.UUID, limit: int = 7, db: Session = Depends(get_db)):
    patient = patient_service.get_by_id(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    readings = reading_service.get_by_patient(db, patient_id, limit=limit)
    png_bytes = report_service.build_chart_png(readings)
    if not png_bytes:
        raise HTTPException(status_code=404, detail="No readings available for chart")
    return StreamingResponse(
        io.BytesIO(png_bytes),
        media_type="image/png",
        headers={"Content-Disposition": f'inline; filename="chart_{patient_id}.png"'},
    )


@router.delete("/{patient_id}", status_code=204)
def delete_patient(patient_id: uuid.UUID, db: Session = Depends(get_db)):
    if not patient_service.delete(db, patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
