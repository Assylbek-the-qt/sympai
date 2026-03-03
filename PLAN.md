# SympAI — Implementation Plan

## Project structure

```
sympai/
├── api/        FastAPI backend (SQLAlchemy + PostgreSQL) — partially built
├── tlg/        Telegram bot (python-telegram-bot) — in-memory only right now
├── web/        Doctor dashboard — empty
├── db/         schema.sql, mock_data.sql, ERD
└── compose.yaml  api + db + db-seed running; tlg and web commented out
```

---

## 1. API — fill in the gaps

### 1a. Daily readings router
The `DailyReading` model and table exist in schema but there is no router yet.

- [ ] Create `api/routers/daily_readings.py`
  - `POST /readings` — submit a reading (called by bot after daily check)
  - `GET /readings?patient_id=&limit=` — fetch recent readings for risk calc
  - `GET /readings/{id}` — single reading detail
  - `PATCH /readings/{id}/review` — doctor marks as reviewed (`doctor_reviewed_at = now()`)
- [ ] Create `api/services/daily_reading.py` with the actual DB logic
- [ ] Create `api/schemas/daily_reading.py` — Pydantic in/out schemas
- [ ] Register router in `api/main.py`

### 1b. Doctors router
Schema has `doctors` table; no router exists.

- [ ] Create `api/routers/doctors.py`
  - `POST /doctors` — create doctor (admin only for now, no auth needed for MVP)
  - `GET /doctors` — list all (for bot registration: patient picks their doctor)
  - `GET /doctors/{id}/patients` — all patients assigned to a doctor
  - `GET /doctors/{id}/alerts` — patients whose latest reading is `risk_level = high`
- [ ] Create `api/services/doctor.py`
- [ ] Create `api/schemas/doctor.py`

### 1c. Patient router — extend existing
`api/routers/patients.py` exists but is missing:

- [ ] `GET /patients/by-telegram/{telegram_id}` — bot needs to look up patient by Telegram chat_id
- [ ] `GET /patients/{id}/compliance` — % of days with a reading in last 30 days (for dashboard)

### 1d. Risk scoring — move to API
`tlg/risk.py` has the logic but it belongs in the backend.

- [ ] Add `api/services/risk.py` — same `calculate_risk(recent_readings, current)` logic
- [ ] Call it inside `services/daily_reading.py` when inserting a new reading
  - Fetch last 3 readings for the patient
  - Score risk, set `risk_level` and `risk_score` on the new reading before saving
- [ ] Delete `tlg/risk.py` and import risk level from the API response instead

### 1e. Remove placeholder items router
`api/routers/items.py` and `api/services/item.py` are scaffolding, not real features.

- [ ] Delete `api/routers/items.py`, `api/services/item.py`, `api/schemas/item.py`, `api/models/item.py`
- [ ] Remove items import from `api/main.py`

---

## 2. Telegram bot — connect to the DB

The bot currently stores all state in a Python dict (`tlg/bot.py:41`). A restart wipes everything. The API and Postgres are already running via compose.

### 2a. HTTP client in bot
- [ ] Add `httpx` to `tlg/` venv: `pip install httpx`
- [ ] Create `tlg/api_client.py` — thin async wrapper around the API
  - `get_patient_by_telegram_id(chat_id)` → `GET /patients/by-telegram/{chat_id}`
  - `create_patient(data)` → `POST /patients`
  - `submit_reading(data)` → `POST /readings`
  - `get_recent_readings(patient_id, n=3)` → `GET /readings?patient_id=&limit=`
  - `list_doctors()` → `GET /doctors` (for registration flow)

### 2b. Registration — pick a doctor
Currently the patient types a doctor's name freehand. It should link to a real `doctor_id`.

- [ ] In registration flow, after DIAGNOSIS state:
  - Fetch `GET /doctors` and show as a keyboard (doctor full names)
  - Store selected `doctor_id` (UUID) in user temp data
  - Pass `doctor_id` to `POST /patients`

### 2c. Swap in-memory dict for API calls
Replace `users: dict` with API calls at the boundaries. Keep the in-memory dict only for
active conversation temp state (data being collected mid-flow — it's fine to lose that on restart).

- [ ] `cmd_start`: check if patient exists via `get_patient_by_telegram_id` first;
  if yes, skip registration and go idle
- [ ] `_init_comorbid` (registration complete): call `create_patient(...)` instead of printing
- [ ] `_daily_symptoms` (daily check complete): call `submit_reading(...)` instead of `user["daily_logs"].append(...)`
- [ ] `daily_check_job`: fetch idle patients from API (`GET /patients?state=idle` or similar)
  instead of iterating local `users` dict
- [ ] `handle_message`: load patient from API at the top when `chat_id not in active_flows`

### 2d. Conversation state persistence
For active flows (mid-registration or mid-daily-check), keep temp state in memory — it's fine.
Add a `state` column to `patients` so the bot can resume after restart.

- [ ] `set_state(chat_id, state)` → `PATCH /patients/by-telegram/{chat_id}` with `{"state": ...}`
- [ ] On bot startup, re-load any patients with a non-null state and put them back in `users` dict
  so in-progress flows survive a restart

### 2e. Wire bot into compose
`tlg` service is commented out in `compose.yaml`.

- [ ] Create `tlg/Dockerfile`
  ```dockerfile
  FROM python:3.12-slim
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install -r requirements.txt
  COPY . .
  CMD ["python", "bot.py"]
  ```
- [ ] Create `tlg/requirements.txt`
- [ ] Uncomment and fill in `tlg` service in `compose.yaml`
  - Set `API_URL=http://api:3069` env var
  - `depends_on: api`

---

## 3. Doctor dashboard (web/)

Currently `web/` is empty. Dashboard is for doctors to monitor their patients.

### 3a. Tech choice
Use plain **FastAPI + Jinja2 templates** (no separate frontend framework) to keep it simple.
Or a single-page React app if preferred. Pick one and note it here before starting.

> **Recommended for MVP:** FastAPI + Jinja2 (no npm, no build step, runs in the same Docker network)

### 3b. Pages to build

- [ ] `GET /` — Login page (doctor email + password)
- [ ] `GET /dashboard` — After login:
  - Total patients assigned to this doctor
  - Count of high-risk patients today
  - Overall medication compliance % (last 7 days)
  - Table: patient name | latest BP | risk badge | last reading date | missed days
- [ ] `GET /patients/{id}` — Patient detail:
  - BP trend chart (last 30 readings) — use Chart.js via CDN
  - Medication compliance timeline
  - List of all readings with symptoms and risk
  - "Mark as reviewed" button on unreviewed high-risk readings
- [ ] Auth: session cookie, check `doctors` table on login

### 3c. Wire into compose
`web` service is commented out in `compose.yaml`.

- [ ] Create `web/Dockerfile`
- [ ] Uncomment and fill in `web` service in `compose.yaml`
  - `depends_on: api` or `depends_on: db` depending on whether it calls API or DB directly

---

## 4. Cross-cutting / infra

- [ ] **Password hashing** — `doctors.password` is plain text in schema (noted in schema comment).
  Add `bcrypt` or `passlib` before any real users are created.
- [ ] **Doctor auth token** — add JWT or a simple signed session token so the web dashboard
  can authenticate against the API (if web calls API) or directly against DB.
- [ ] **`.env` consolidation** — `api/.env` and `tlg/.env` are separate. Document all required
  env vars in root `.env.example`.
- [ ] **`db/schema.sql` — add `state` column to `patients`** for bot conversation persistence (see 2d):
  ```sql
  ALTER TABLE patients ADD COLUMN state VARCHAR(30);
  ```
- [ ] **Missed entry tracking** — add a background job (APScheduler or pg_cron) that checks at
  end of day whether a reading exists for each patient; if not, increment a `missed_days` counter
  or log a zero-entry. Needed for compliance % on dashboard.
- [ ] **High-risk alert push** — when `submit_reading` scores `risk_level = high`, optionally
  send a message to the doctor's Telegram (if doctor has a `telegram_id` column — add it to schema).

---

## Priority order for next session

1. `1a` + `1b` + `1c` — get the API fully working with all routes
2. `2a` + `2b` + `2c` — wire the bot to the API (biggest impact, removes in-memory limitation)
3. `1d` — move risk scoring to API
4. `3a` + `3b` — build dashboard MVP
5. `2d` + `2e` — state persistence + compose integration
6. `3c` + `4.*` — wire everything into compose, add auth, cleanup
