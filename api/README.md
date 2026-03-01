# SympAi API

FastAPI backend. Handles patient data, daily readings, risk scoring, and doctor authentication.

## Stack

- **FastAPI** — async API framework
- **SQLModel** — ORM (SQLAlchemy + Pydantic)
- **Pydantic** — request/response validation
- **PostgreSQL** — database
- **Uvicorn** — ASGI server

## Structure

```
api/
├── models/              # SQLModel tables (map to DB)
│   ├── patient.py       # patients table
│   ├── doctor.py        # doctors table
│   └── daily_reading.py # daily_readings table
├── routers/             # Endpoint definitions
│   └── patients.py      # /api/patients routes
├── schemas/             # Pydantic schemas (request/response DTOs)
│   └── patient.py       # PatientCreate, PatientResponse, etc.
├── services/            # Business logic
│   └── risk_engine.py   # Risk scoring (lives here, NOT in DB)
├── utils/               # Helpers (db session, auth, etc.)
├── main.py              # FastAPI app
├── Dockerfile
└── requirements.txt
```

## Endpoints

### Telegram bot → API (writes)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/patients` | Register new patient |
| `PUT` | `/api/patients/{telegram_id}` | Update patient profile |
| `POST` | `/api/patients/{telegram_id}/readings` | Submit daily reading |

### Doctor dashboard → API (reads)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/login` | Doctor login |
| `GET` | `/api/doctors/{doctor_id}/patients` | List doctor's patients |
| `GET` | `/api/patients/{patient_id}` | Patient detail + readings |
| `PATCH` | `/api/readings/{reading_id}/review` | Mark reading as reviewed |

### Design decisions

**Two identifiers for patients.** The bot uses `telegram_id` (that's what it knows). The dashboard uses the internal UUID `patient_id` (from the patient list). This keeps each interface using its natural key.

**Readings are nested inside patient detail.** `GET /api/patients/{id}` returns the patient object with their readings array. No separate readings list endpoint needed — the dashboard gets everything in one call.

**Risk scoring is in `services/`, not in the database.** The DB stores the computed `risk_score` and `risk_level` on each reading row, but the actual calculation happens in Python when a reading is submitted. This keeps the DB dumb and the logic testable.

## Running locally (without Docker)

```bash
cd api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set env
export DATABASE_URL=postgresql://sympai:password@localhost:5432/sympai

# Run
uvicorn main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs` (Swagger) and `/redoc`.

## Models vs Schemas

| Layer | Purpose | Example |
|-------|---------|---------|
| `models/` | SQLModel classes → DB tables | `Patient(SQLModel, table=True)` |
| `schemas/` | Pydantic classes → API validation | `PatientCreate(BaseModel)` with only the fields the bot sends |

The model is what's in the database. The schema is what crosses the wire. They look similar but serve different purposes — schemas let you control exactly what goes in and out without exposing internal fields like `id` or `created_at` on create requests.