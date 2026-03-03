import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas.daily_reading import ReadingCreate, ReadingOut
from services import daily_reading as reading_service

router = APIRouter(prefix="/readings", tags=["readings"])


@router.post("", response_model=ReadingOut, status_code=201)
def submit_reading(data: ReadingCreate, db: Session = Depends(get_db)):
    return reading_service.create(db, data)


@router.get("", response_model=list[ReadingOut])
def list_readings(
    patient_id: uuid.UUID,
    limit: int = 30,
    db: Session = Depends(get_db),
):
    return reading_service.get_by_patient(db, patient_id, limit)


@router.get("/{reading_id}", response_model=ReadingOut)
def get_reading(reading_id: uuid.UUID, db: Session = Depends(get_db)):
    reading = reading_service.get_by_id(db, reading_id)
    if not reading:
        raise HTTPException(status_code=404, detail="Reading not found")
    return reading


@router.patch("/{reading_id}/review", response_model=ReadingOut)
def review_reading(reading_id: uuid.UUID, db: Session = Depends(get_db)):
    reading = reading_service.mark_reviewed(db, reading_id)
    if not reading:
        raise HTTPException(status_code=404, detail="Reading not found")
    return reading
