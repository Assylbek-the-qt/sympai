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
- [x] `GET /patients/{id}/compliance` — % of days with a reading in the last 30 days
- [x] Add `state: str | None` to `PatientUpdate` + `PatientOut` schemas
- [x] Add `state` + `comorbidities` to ORM model
- [x] Add `comorbidities: str | None` to `PatientCreate` schema

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
- [x] Replace yes/no diagnosis question with type selection keyboard
  - `Гипертония | Диабет | Екеуі де` → maps to `hypertension | diabetes | both`
- [x] Doctor selection: fetch `GET /doctors`, show as keyboard, store `doctor_id` UUID
- [x] Add glucose question after pulse — only for `diagnosis in [diabetes, both]`
- [x] Pass `comorbidities` free-text to `POST /patients`
- [x] Pass `language` (kz/ru) to `POST /patients`

### API client
- [x] `httpx` already in `tlg/requirements.txt`
- [x] Created `tlg/api_client.py` (async)
  - `get_patient(telegram_id)` → `GET /patients/by-telegram/{id}`
  - `create_patient(data)` → `POST /patients`
  - `list_doctors()` → `GET /doctors`
  - `submit_reading(data)` → `POST /readings`
  - `get_idle_patients()` → `GET /patients?state=idle`
  - `get_all_patients()` → `GET /patients`
  - `set_patient_state(patient_id, state)` → `PATCH /patients/{id}`

### Swap in-memory dict for API
- [x] `cmd_start`: calls `get_patient(chat_id)` — skips registration if already exists
- [x] `_init_comorbid`: calls `create_patient(...)` on registration complete
- [x] `_daily_symptoms`: calls `submit_reading(...)`, uses `risk_level` from API response
- [x] `daily_check_job`: calls `get_idle_patients()` from API (fallback to memory)
- [x] Delete `tlg/risk.py` — use `risk_level` from API response (pending file deletion)

### State persistence
- [x] After registration: `set_patient_state(id, "idle")`
- [x] Daily check start: `set_patient_state(id, "in_check")`
- [x] Daily check end: `set_patient_state(id, "idle")`
- [x] On bot startup: `on_startup()` fetches all patients, reloads into `users` dict

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
- [x] High risk count — patients whose latest reading is `risk_level = high`
- [x] Compliance % — avg across all patients (needs compliance endpoint)
- [x] Missed entry % — days without a reading

### Patient detail
- [x] BP trend chart — Recharts `<LineChart>` (SBP + DBP over time)

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
- [x] `GET /patients/{id}/compliance` endpoint
- [ ] High-risk alert push to doctor's Telegram (after reading scores high)
- [ ] End-of-day missed entry background job (23:59 cron)

---

## Known bugs / active mismatches
- [x] Bot diagnosis handler asks yes/no — fixed: type keyboard (Гипертония/Диабет/Екеуі де)
- [x] Bot stores doctor as free-text name — fixed: stores UUID from API
- [x] Bot never asks glucose — fixed: asked for diabetes/both patients
- [x] Bot is fully in-memory — fixed: API-backed with startup reload

## Testing
- [x] `tlg/tests/user_stories.txt` — 12 manual test scenarios
- [x] `tlg/tests/test_bot.py` — 69 pytest unit test cases (run with pytest + pytest-asyncio)
