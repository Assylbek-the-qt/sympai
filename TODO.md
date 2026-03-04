# SympAI — TODO

> Checkboxes = not done. Checked = done.
> Sections ordered by priority.

---

## API

### Daily readings
- [x] `api/schemas/daily_reading.py` — Pydantic schemas (`ReadingCreate`, `ReadingOut`)
- [x] `api/services/daily_reading.py` — DB logic (insert, fetch by patient, fetch recent N)
- [x] `api/routers/daily_readings.py`
  - `POST /readings` — submit reading, auto-scores risk before saving
  - `GET /readings?patient_id=&limit=` — fetch readings (used by bot + dashboard)
  - `GET /readings/{id}` — single reading
  - `PATCH /readings/{id}/review` — sets `doctor_reviewed_at = now()`
- [x] Register readings router in `api/main.py`

### Doctors
- [x] `api/schemas/doctor.py` — `DoctorCreate`, `DoctorOut`
- [x] `api/services/doctor.py` — get_all, get_by_id, get_by_email, create, get_high_risk_patients
- [x] `api/routers/doctors.py`
  - `POST /doctors` — create (passwords auto-hashed)
  - `GET /doctors` — list all (bot uses this for registration keyboard)
  - `GET /doctors/{id}` — single doctor
  - `GET /doctors/{id}/alerts` — patients with `risk_level = high` in latest reading
- [x] Register doctors router in `api/main.py`

### Patients — extend existing router
- [x] `GET /patients/by-telegram/{telegram_id}` — bot lookup by chat_id
- [x] `GET /patients?state=idle` — query param filter so cron job can fetch idle patients
- [ ] `GET /patients/{id}/compliance` — % of days with a reading in the last 30 days
- [x] Add `state: str | None` to `PatientUpdate` + `PatientOut` schemas
- [x] Add `state` + `comorbidities` to ORM model

### Risk scoring
- [x] `api/services/risk.py` — `calculate_risk(recent_readings, current) -> (level, score)`
- [x] Called inside `daily_reading.create()` before DB insert
- [x] Stored in `risk_level` + `risk_score` columns

### Cleanup
- [x] Deleted all items placeholder files + removed from `main.py`

---

## Database schema fixes
- [x] `state VARCHAR(30)` on `patients`
- [x] `comorbidities TEXT` on `patients`
- [x] `telegram_id BIGINT UNIQUE` on `doctors`
- [x] `mock_data.sql` passwords are bcrypt hashed

---

## Telegram bot

### Fix registration flow — schema mismatches
- [ ] Replace yes/no diagnosis question with type selection keyboard
  - `Гипертония | Диабет | Екеуі де` → maps to `hypertension | diabetes | both`
- [ ] Doctor selection: fetch `GET /doctors`, show as keyboard, store `doctor_id` UUID
- [ ] Add glucose question after pulse — only for `diagnosis in [diabetes, both]`
- [ ] Pass `comorbidities` free-text to `POST /patients`
- [ ] Pass `language` (kz/ru) to `POST /patients`

### API client
- [ ] `pip install httpx`, add to `tlg/requirements.txt`
- [ ] Create `tlg/api_client.py`
  - `get_patient(telegram_id)` → `GET /patients/by-telegram/{id}`
  - `create_patient(data)` → `POST /patients`
  - `list_doctors()` → `GET /doctors`
  - `submit_reading(data)` → `POST /readings`
  - `get_idle_patients()` → `GET /patients?state=idle`
  - `set_patient_state(patient_id, state)` → `PATCH /patients/{id}`

### Swap in-memory dict for API
- [ ] `cmd_start`: call `get_patient(chat_id)` — skip registration if already exists
- [ ] `_init_comorbid`: call `create_patient(...)` on registration complete
- [ ] `_daily_symptoms`: call `submit_reading(...)` instead of appending to local list
- [ ] `daily_check_job`: call `get_idle_patients()` instead of iterating local dict
- [ ] `handle_message`: load patient from API when not in active flow dict
- [ ] Delete `tlg/risk.py` — use `risk_level` from API response

### State persistence
- [ ] Each state transition: call `set_patient_state(...)` to persist to DB
- [ ] On bot startup: fetch all patients with non-null state, reload into in-memory dict

### Docker + compose
- [x] `tlg/requirements.txt` + `tlg/Dockerfile`
- [x] `tlg` service wired in `dev-compose.yaml`

---

## Doctor dashboard (web/ — React Router v7 + TypeScript)

### Setup
- [x] React Router v7 + TypeScript, bootstrapped
- [x] `web/Dockerfile` + wired in `dev-compose.yaml`

### Routes
- [x] `login.tsx` — login form → `POST /auth/login` → stores JWT
- [x] `dashboard.tsx` — stat cards + patient table
- [x] `patients.$id.tsx` — patient detail + readings table
- [x] Auth guard on dashboard + patient detail
- [x] Sign out button

### Dashboard stat cards (from original spec)
- [x] Total patients
- [x] By diagnosis (hypertension / diabetes / both)
- [ ] High risk count — patients whose latest reading is `risk_level = high`
- [ ] Compliance % — avg across all patients (needs compliance endpoint)
- [ ] Missed entry % — days without a reading

### Patient detail
- [ ] BP trend chart — Recharts `<LineChart>` (SBP + DBP over time)

---

## Security / Auth
- [x] bcrypt password hashing on `POST /doctors` + mock seed
- [x] `POST /auth/login` → JWT
- [x] JWT sent with every `apiFetch` call (`Authorization: Bearer`)
- [ ] `Depends(get_current_doctor)` on doctor-scoped endpoints
- [ ] `SECRET_KEY` from env (currently falls back to hardcoded dev string)

---

## Infra / ops
- [x] `.dev.env` at project root (gitignored)
- [x] `dev-compose.yaml` — all services, uses `.dev.env`
- [ ] `GET /patients/{id}/compliance` endpoint
- [ ] High-risk alert push to doctor's Telegram (after reading scores high)
- [ ] End-of-day missed entry background job (23:59 cron)

---

## Known bugs / active mismatches
- [ ] Bot diagnosis handler asks yes/no — needs type keyboard
- [ ] Bot stores doctor as free-text name — needs `doctor_id` UUID from API
- [ ] Bot never asks glucose — needed for diabetes/both patients
- [ ] Bot is fully in-memory — restart wipes all patient data
