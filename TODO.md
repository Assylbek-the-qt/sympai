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
- [ ] `api/schemas/doctor.py` — `DoctorCreate`, `DoctorOut`
- [ ] `api/services/doctor.py` — get_all, get_by_id, get_by_email, create
- [ ] `api/routers/doctors.py`
  - `POST /doctors` — create (no auth needed for MVP)
  - `GET /doctors` — list all (bot uses this for registration keyboard)
  - `GET /doctors/{id}/patients` — patients assigned to doctor
  - `GET /doctors/{id}/alerts` — patients with `risk_level = high` in latest reading
- [ ] Register doctors router in `api/main.py`

### Patients — extend existing router
- [ ] `GET /patients/by-telegram/{telegram_id}` — bot lookup by chat_id
- [ ] `GET /patients?state=idle` — query param filter so cron job can fetch idle patients
- [ ] `GET /patients/{id}/compliance` — % of days with a reading in the last 30 days
- [ ] Add `state: str | None` to `PatientUpdate` schema so bot can persist conversation state
- [ ] Add `state` to `PatientOut` schema

### Risk scoring
- [x] `api/services/risk.py` — `calculate_risk(recent_readings: list, current: dict) -> str`
  - Low: SBP < 150, no symptoms
  - Medium: SBP 150–169, or missed meds 2+ of last 3 days
  - High: SBP ≥ 170, or chest pain, or missed 3 days straight
- [x] Call `calculate_risk` inside `daily_reading.create()` before DB insert
- [x] Store result in `risk_level` + `risk_score` columns on `daily_readings`

### Cleanup
- [ ] Delete `api/routers/items.py`
- [ ] Delete `api/services/item.py`
- [ ] Delete `api/schemas/item.py`
- [ ] Delete `api/models/item.py`
- [ ] Remove items import from `api/main.py`

---

## Database schema fixes

- [ ] Add `state VARCHAR(30)` column to `patients` table in `db/schema.sql`
  ```sql
  ALTER TABLE patients ADD COLUMN state VARCHAR(30);
  ```
- [ ] Add `telegram_id BIGINT UNIQUE` to `doctors` table (for high-risk alert push)
  ```sql
  ALTER TABLE doctors ADD COLUMN telegram_id BIGINT UNIQUE;
  ```
- [ ] Add `comorbidities TEXT` to `patients` table (bot collects this, schema doesn't have it)
  ```sql
  ALTER TABLE patients ADD COLUMN comorbidities TEXT;
  ```
- [ ] Update `mock_data.sql` seed to reflect new columns

---

## Telegram bot

### Fix registration flow — schema mismatches
The bot currently has wrong/missing fields compared to the actual DB schema:

- [ ] Replace yes/no diagnosis question with diagnosis **type** selection
  - Show keyboard: `Гипертония | Диабет | Екеуі де / Оба` (maps to `hypertension | diabetes | both`)
  - Pass as `diagnosis` enum to `POST /patients`
- [ ] Add glucose question to daily check **only for diabetes patients**
  - After pulse, if `patient.diagnosis in [diabetes, both]`: ask glucose level
  - Include `glucose` field in the reading payload
- [ ] `comorbidities` free-text answer → send as `comorbidities` field (after schema column is added)
- [ ] Store `language` (kz/ru) properly — `PatientCreate` already has `language` field, just pass it

### API client
- [ ] `pip install httpx` in tlg venv, add to `tlg/requirements.txt`
- [ ] Create `tlg/api_client.py`
  - `get_patient(telegram_id)` → `GET /patients/by-telegram/{id}`
  - `create_patient(data)` → `POST /patients`
  - `list_doctors()` → `GET /doctors`
  - `submit_reading(data)` → `POST /readings`
  - `get_idle_patients()` → `GET /patients?state=idle`
  - `set_patient_state(telegram_id, state)` → `PATCH /patients/by-telegram/{id}`
- [ ] Read `API_URL` from `.env` (set to `http://localhost:3069` locally, `http://api:3069` in Docker)

### Swap in-memory dict for API
- [ ] `cmd_start`: call `get_patient(chat_id)` first — skip registration if already exists
- [ ] Doctor selection step: fetch `list_doctors()`, show as keyboard, store `doctor_id` UUID in temp
- [ ] `_init_comorbid`: call `create_patient(...)` on registration complete
- [ ] `_daily_symptoms`: call `submit_reading(...)` instead of `user["daily_logs"].append(...)`
- [ ] `daily_check_job`: call `get_idle_patients()` instead of iterating local dict
- [ ] `handle_message`: load patient from API when not in active flow dict
- [ ] Delete `tlg/risk.py` — use `risk_level` from API response instead

### State persistence
- [ ] Each state transition: call `set_patient_state(chat_id, new_state)` to persist to DB
- [ ] On bot startup: fetch all patients with non-null state, reload into in-memory flow dict
- [ ] Keep temp data (mid-flow answers) in memory only — acceptable to lose on restart

### Docker + compose
- [ ] Create `tlg/requirements.txt`
- [ ] Create `tlg/Dockerfile`
- [ ] Uncomment `tlg` service in `compose.yaml`
  - `API_URL=http://api:3069`
  - `depends_on: api`

---

## Doctor dashboard (web/ — React Router v7 + JavaScript)

**Stack decision: React Router v7 (framework mode) + plain JavaScript. No TypeScript.**
Bootstrapped with `npm create react-router@latest`. Talks to the FastAPI backend via REST.

### Setup
- [x] Decide tech: React Router v7 + JavaScript
- [x] Bootstrap project: `npm create react-router@latest web` (select JS + React Router v7)
- [x] Clean out boilerplate, set up `API_URL` env var pointing to FastAPI
- [x] Create `web/Dockerfile` (node:22-alpine, multi-stage)
- [x] Uncomment `web` service in `compose.yaml`

### Routes (`web/app/routes/`)
- [ ] `login.jsx` — login form, POST to `POST /auth/login`, store JWT in localStorage
- [x] `dashboard.tsx` — stat cards (total, by diagnosis) + patient table with View links
- [x] `patients.$id.tsx` — patient info + full readings table (BP, pulse, med, symptoms, risk, reviewed)
- [ ] Add BP trend chart to patient detail (Recharts `<LineChart>`)
- [ ] Auth guard — loader checks JWT, redirects to `/login` if missing/expired

---

## Security / Auth

- [ ] Hash doctor passwords with `bcrypt` or `passlib`
  - Update `mock_data.sql` seed to use hashed values
  - Update login logic to verify hash
- [ ] JWT tokens for API (if web calls API rather than DB directly)
  - `POST /auth/login` → returns JWT
  - Protect doctor-scoped endpoints with `Depends(get_current_doctor)`
- [ ] Move all secrets to env vars — no hardcoded passwords anywhere

---

## Infra / ops

- [ ] Create root `.env.example`
  ```
  # API
  DATABASE_URL=postgresql://postgres:postgres@localhost:5432/symp_ai

  # Bot
  TOKEN=your_telegram_bot_token
  API_URL=http://localhost:3069

  # Web
  SECRET_KEY=change_me
  ```
- [ ] Missed entry tracking — end-of-day background job
  - At 23:59, check if each patient has a reading for today
  - If not, store a zero-entry or flag as missed for compliance calculation
- [ ] High-risk alert push to doctor's Telegram
  - After `submit_reading` scores `high`, send message to `doctor.telegram_id` if set
  - Requires `telegram_id` column on `doctors` (see schema fixes above)
- [ ] Consolidate `api/.env` and `tlg/.env` — single root `.env` mounted into containers

---

## Known bugs / mismatches

- [ ] Bot `_diagnosis` handler asks yes/no but schema expects `hypertension | diabetes | both`
- [ ] Bot doesn't collect `glucose` — needed for diabetes patients
- [ ] Bot `doctor` field is free-text name but schema needs a `doctor_id` UUID FK
- [ ] `comorbidities` has no column in `patients` table yet
- [ ] `PatientUpdate` schema missing `state` field — bot can't persist state to DB yet
- [ ] `mock_data.sql` passwords are plain text — will break when hashing is added
