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

---

## MedTech upgrade — feedback from semifinal (target: final judges + clinics)
> Context: passed ANamed + Digital Kazakhstan semifinal. Clinic visit ~2026-03-23.
> Ordered by impact.

### 1. Triage system — 3 clinical zones (replaces low/medium/high)
- [x] Redefine risk zones in `api/services/risk.py`:
  - **Red** (`critical`): BP ≥ 180/120 or chest pain — immediate 103
  - **Yellow** (`high`): BP 160–179 / 100–119 or dizziness — urgent therapist
  - **Green** (`normal`): below thresholds — home monitoring
- [x] Add `critical` as a new `risk_level` value in DB schema + Pydantic schemas
- [x] Bot response for `critical`: show first aid steps (lie down, sublingual med, breathe deeply) before "call 103"
- [x] Update bot `texts.py` with `risk_critical` key (kz + ru)

### 2. PDF Medical Report — primary differentiator feature
- [x] `pip install reportlab` (or `weasyprint`), add to `api/requirements.txt`
- [x] `GET /patients/{id}/report` endpoint — returns PDF
  - Last 30 days of readings
  - BP + glucose trend chart embedded (matplotlib → PNG → PDF)
  - Medication compliance %
  - Risk level summary
- [x] Bot: add `/report` command — fetches PDF from API, sends as document to patient
- [x] Bot `texts.py`: add `report_generating`, `report_ready`, `report_error` keys (kz + ru)

### 3. Inline buttons for numeric BP entry (UX)
- [x] Replace reply keyboard Yes/No with `InlineKeyboardMarkup` in daily check
- [x] For SBP: show preset inline buttons `[110] [120] [130] [140] [150] [160] [170] [180]` + "Other" (falls back to typed input)
- [x] For DBP: `[70] [80] [90] [100] [110] [120]` + "Other"
- [x] For pulse: `[60] [70] [80] [90] [100]` + "Other"
- [x] Wire `CallbackQueryHandler` in `bot.py` alongside existing `MessageHandler`

### 4. Medication reminder — morning push notification
- [x] Add cron job at **09:00 Almaty** — sends "Time to take your medication" to all idle patients
- [x] Add `last_reminder_sent` timestamp check so it only fires once per day per patient
- [x] Bot `texts.py`: add `med_reminder` key (kz + ru)

### 5. Evening medication compliance follow-up
- [x] Add cron job at **20:00 Almaty** — asks patients who haven't submitted a reading today "Did you take your medication?"
- [x] If "No" → ask reason: `[Forgot] [Ran out] [Side effects] [Other]`
- [x] Store missed reason in new `medication_skip_reason` column on `daily_readings` (nullable)
- [x] Surface missed reasons in doctor dashboard patient detail

### 6. Weekly BP trend chart in Telegram
- [x] After 7th consecutive daily reading, bot sends a chart image:
  - `matplotlib` line chart: SBP + DBP over 7 days
  - Saved as PNG, sent via `bot.send_photo`
- [x] Also available on demand via `/chart` command
- [x] Bot `texts.py`: add `chart_caption` key (kz + ru)

### 7. NLP symptom understanding (free-text triage)
- [ ] In `_daily_symptoms` handler: if user types free text instead of tapping a button, run simple keyword matching:
  - "басым айналады / голова кружится / dizziness" → `dizziness`
  - "бас ауырады / головная боль / head hurts" → `headache`
  - "кеудем ауырады / боль в груди / chest pain" → `chest_pain`
  - "желке / затылок / back of head" → `headache` + flag potential hypertensive crisis
- [ ] If matched → confirm with user before saving: `"Мен дұрыс түсіндім бе: басым айналады?"` (inline Yes/No)
- [ ] Unrecognized free text → show symptom keyboard

### 8. Find nearest clinic button
- [ ] Add `/clinic` command — replies with inline button linking to 2GIS / Google Maps search for "clinics near me"
- [ ] Also surface this button in the `risk_high` and `risk_critical` response messages

### 9. Clinical protocol references
- [ ] Add `PROTOCOLS` dict in `tlg/protocols.py` mapping diagnosis + risk zone to recommended action per Kazakhstan MoH guidelines
- [ ] Replace generic risk messages in `texts.py` with protocol-backed advice
- [ ] Note in bot responses: "Per Kazakhstan MoH Clinical Protocol #X"
