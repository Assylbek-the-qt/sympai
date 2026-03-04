# SympAI — Agent Context

This file exists so an LLM can understand the full project without being walked through it.
Read this before touching any code. Keep it updated when things change.

---

## What the project is

**SympAI Hypertension** — a Telegram-based clinical early warning system for hypertension/diabetes patients in Kazakhstan. Patients register via a Telegram bot, submit daily blood pressure readings, get risk-scored automatically, and doctors monitor them via a web dashboard.

**Goal:** Reduce doctor workload by 25%, improve patient medication compliance by 40%.

**Stack:**
- `api/` — FastAPI + SQLAlchemy + PostgreSQL (backend)
- `tlg/` — python-telegram-bot v22 (patient-facing bot)
- `web/` — React Router v7 + TypeScript (doctor dashboard)
- `db/` — schema.sql + mock_data.sql + ERD
- `dev-compose.yaml` — Docker Compose for local dev (api + db + db-seed + tlg + web)
- `.dev.env` — single env file for all services (gitignored)

---

## Project file tree

```
sympai/
├── api/
│   ├── main.py                  # FastAPI app, router registration
│   ├── database.py              # SQLAlchemy engine, SessionLocal, get_db()
│   ├── models/
│   │   ├── doctor.py            # Doctor ORM model + Base (DeclarativeBase)
│   │   ├── patient.py           # Patient ORM model, DiagnosisType enum
│   │   └── daily_reading.py     # DailyReading ORM model, RiskLevel enum
│   ├── schemas/
│   │   ├── doctor.py            # DoctorCreate, DoctorOut
│   │   ├── patient.py           # PatientCreate, PatientUpdate, PatientOut
│   │   └── daily_reading.py     # ReadingCreate, ReadingOut
│   ├── services/
│   │   ├── auth.py              # bcrypt verify/hash, JWT encode/decode, authenticate_doctor
│   │   ├── doctor.py            # get_all, get_by_id, get_by_email, create, get_high_risk_patients
│   │   ├── patient.py           # get_all(state?), get_by_id, get_by_telegram_id, create, update, delete
│   │   ├── daily_reading.py     # get_by_id, get_by_patient, get_recent, create, mark_reviewed
│   │   └── risk.py              # calculate_risk(recent_readings, current) -> (level, score)
│   ├── routers/
│   │   ├── auth.py              # POST /auth/login → JWT
│   │   ├── doctors.py           # GET/POST /doctors, GET /doctors/{id}, GET /doctors/{id}/alerts
│   │   ├── patients.py          # CRUD /patients, GET /patients/by-telegram/{id}, GET /patients?state=
│   │   └── daily_readings.py    # /readings endpoints
│   ├── Dockerfile
│   ├── requirements.txt         # includes bcrypt, python-jose
│   └── .env                     # DATABASE_URL (overridden by dev-compose)
├── tlg/
│   ├── bot.py                   # Main bot — state machine, handlers, cron
│   ├── texts.py                 # All bilingual strings (kz/ru)
│   ├── risk.py                  # LOCAL risk scoring — DELETE after bot uses API
│   ├── Dockerfile
│   └── requirements.txt
├── web/
│   ├── app/
│   │   ├── root.jsx             # root layout
│   │   ├── routes.ts            # route manifest
│   │   └── routes/
│   │       ├── login.tsx        # /login — form, POST /auth/login, stores JWT
│   │       ├── dashboard.tsx    # / — stat cards + patient table, auth guard
│   │       └── patients.$id.tsx # /patients/:id — detail + readings table, auth guard
│   ├── lib/
│   │   └── api.ts               # apiFetch wrapper with Authorization header
│   ├── Dockerfile
│   └── package.json
├── db/
│   ├── schema.sql               # Canonical DB schema
│   ├── mock_data.sql            # Seed: 2 doctors (bcrypt pw), 5 patients, 5 readings
│   └── sympai_erd.mermaid
├── dev-compose.yaml             # Local dev compose — uses .dev.env
├── compose.yaml                 # Production compose skeleton
├── .dev.env                     # All env vars (gitignored) — TOKEN, DATABASE_URL, SECRET_KEY
├── TODO.md                      # Checkbox task list — keep updated
└── README_AGENT.md              # This file
```

---

## Running locally

```bash
# All services via Docker
docker compose -f dev-compose.yaml up --build

# API: http://localhost:3069
# API docs: http://localhost:3069/docs
# Web dashboard: http://localhost:3000

# Bot only (outside Docker)
cd tlg && source venv/bin/activate && python bot.py
# Bot reads TOKEN + API_URL from root .dev.env
```

---

## Database schema

Three tables. All PKs are UUIDs (`uuid-ossp`).

### `doctors`
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| full_name | VARCHAR(200) | |
| email | VARCHAR(255) UNIQUE | |
| password | VARCHAR(255) | bcrypt hashed |
| telegram_id | BIGINT UNIQUE | nullable — for high-risk alert push |
| created_at | TIMESTAMPTZ | |

### `patients`
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| telegram_id | BIGINT UNIQUE | Telegram chat_id |
| full_name | VARCHAR(200) | |
| age | SMALLINT | |
| diagnosis | ENUM | `hypertension \| diabetes \| both` |
| current_medication | VARCHAR(200) | nullable |
| doctor_id | UUID FK → doctors | |
| language | VARCHAR(5) | `kz` or `ru` |
| state | VARCHAR(30) | nullable — bot conversation state |
| comorbidities | TEXT | nullable |
| created_at | TIMESTAMPTZ | |

### `daily_readings`
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| patient_id | UUID FK → patients | |
| reading_date | DATE | UNIQUE per patient per day |
| sbp | SMALLINT | systolic |
| dbp | SMALLINT | diastolic |
| pulse | SMALLINT | nullable |
| glucose | NUMERIC(4,1) | nullable, diabetes patients only |
| medication_taken | BOOLEAN | |
| symptoms | TEXT[] | e.g. `{headache, chest_pain}` |
| notes | TEXT | nullable |
| risk_score | SMALLINT | set by API on insert |
| risk_level | ENUM | `low \| medium \| high`, set by API |
| doctor_reviewed_at | TIMESTAMPTZ | null until doctor marks reviewed |
| created_at | TIMESTAMPTZ | |

**Constraint:** `UNIQUE (patient_id, reading_date)` — one reading per patient per day.

---

## Backend patterns (api/)

### Layer order
```
router → service → model
         ↓
       risk.py (pure function, no DB)
```

Routers never touch DB directly. Services never import routers.

### Auth
- `POST /auth/login` body: `{ email, password }` → returns `{ access_token, token_type }`
- JWT signed with `SECRET_KEY` env var (24h expiry), algorithm HS256
- `services/auth.py` — `authenticate_doctor`, `create_access_token`, `decode_token`, `hash_password`, `verify_password`
- Passwords hashed with `bcrypt` directly (not passlib — compat issue with Python 3.13)
- Routes are **not yet protected** — `Depends(get_current_doctor)` is a TODO

### Risk scoring
`services/risk.py` — `calculate_risk(recent_readings, current_dict) -> (level: str, score: int)`
- **High** → SBP ≥ 170 OR `chest_pain` in symptoms → score 9
- **Medium** → SBP 150–169 OR missed meds ≥ 2 of last 3 days → score 5
- **Low** → everything else → score 2
- Called inside `services/daily_reading.create()` before DB insert

### Adding a new resource
1. **Model** (`models/foo.py`) — import `Base` from `models/doctor.py`
2. **Schema** (`schemas/foo.py`) — Pydantic v2, `FooCreate` / `FooOut` with `Config: from_attributes = True`
3. **Service** (`services/foo.py`) — plain functions `(db: Session, ...) -> ORM`
4. **Router** (`routers/foo.py`) — `APIRouter(prefix="/foo", tags=["foo"])`
5. **Register** in `main.py`

---

## Telegram bot patterns (tlg/)

### Architecture
Manual state machine — no ConversationHandler. State stored per `chat_id` in global dict.

```python
users: dict[int, dict] = {}   # chat_id -> user data + state
```

**CRITICAL:** Bot is currently 100% in-memory. Restart wipes everything. The plan is to persist state via the API — `tlg/api_client.py` does not exist yet and must be created.

### State flow
```
LANG → NAME → AGE → DOCTOR → DIAGNOSIS
  → INIT_BP1 → INIT_BP2 → INIT_BP3 → INIT_MED → INIT_COMORBID → None (idle)

None (idle) → DAILY_SBP → DAILY_DBP → DAILY_PULSE → DAILY_MED → DAILY_SYMPTOMS → None
```

`state = None` = registered and idle, waiting for daily cron at 08:00 Almaty.

### Known bot bugs (must fix before production)
- `_diagnosis` asks yes/no → must show keyboard: `Гипертония | Диабет | Екеуі де` → maps to `hypertension | diabetes | both`
- `_doctor` stores free-text name → must fetch `GET /doctors`, store UUID as `doctor_id`
- No glucose question → needed for `diagnosis in [diabetes, both]`
- No API calls at all — `tlg/api_client.py` doesn't exist yet
- `tlg/risk.py` duplicates API logic → delete after bot uses API

### texts.py pattern
All user-facing strings in `TEXTS = { "kz": {...}, "ru": {...} }`.
Access via `t(chat_id, "key")`. Never hardcode bot messages inline.

### Keyboard helper
```python
mkb(["Yes", "No"])           # one row
mkb(["A", "B"], ["C", "D"]) # two rows
# Returns ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
```

### ROUTES dict pattern
```python
ROUTES = { STATE_NAME: _handler_fn, ... }

async def handle_message(update, context):
    user = users[chat_id]
    handler = ROUTES.get(user["state"])
    if handler:
        await handler(update, user, text)
```

---

## Frontend patterns (web/)

### Auth flow
1. `/login` — form submits to `POST /auth/login`
2. On success → server action redirects to `/?token=<jwt>`
3. Dashboard mounts → stores token in `localStorage`, navigates to `/` clean
4. All `apiFetch` calls attach `Authorization: Bearer <token>`
5. Sign out → clears token → back to `/login`

### apiFetch (`web/app/lib/api.ts`)
Thin wrapper. Reads `localStorage.getItem("token")` and attaches it.
Base URL: `process.env.API_URL` (SSR) or `import.meta.env.VITE_API_URL` (client).

### Auth guard pattern (client-side)
```ts
useEffect(() => {
  if (!localStorage.getItem("token")) navigate("/login", { replace: true });
}, []);
```

### Route loader pattern
Data fetching in `loader`, not `useEffect`:
```ts
export async function loader({ params }) {
  return { patient: await api.patients.get(params.id) };
}
export default function Page() {
  const { patient } = useLoaderData<typeof loader>();
}
```

---

## Environment variables (.dev.env)

```
# API
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/symp_ai

# Bot
TOKEN=<telegram bot token>
API_URL=http://localhost:3069      # use http://api:3069 inside Docker

# Auth
SECRET_KEY=change_me
```

In `dev-compose.yaml`: api + tlg load via `env_file: .dev.env`. DB hostname inside Docker is `db`.

---

## What's done vs pending

### Done ✅
- FastAPI + PostgreSQL + Docker Compose (dev-compose.yaml)
- Full CRUD: patients, doctors, daily_readings
- Auth: `POST /auth/login` → JWT, bcrypt passwords on all doctor creates
- Risk scoring — auto-calculated on every reading insert
- `GET /patients/by-telegram/{id}`, `GET /patients?state=idle`
- `GET /doctors/{id}/alerts` — high risk patients for a doctor
- Telegram bot — registration + daily check flow (in-memory, not connected to API yet)
- Bilingual bot (KZ/RU), daily cron at 08:00 Almaty, `/check` command for testing
- Web dashboard — login page, dashboard with stat cards, patient detail, auth guard, sign out
- `.dev.env` (gitignored) + `dev-compose.yaml` wiring all services

### Pending — see TODO.md for full list

Priority order:
1. **Bot: `tlg/api_client.py`** — httpx wrapper (`get_patient`, `create_patient`, `list_doctors`, `submit_reading`, `get_idle_patients`, `set_patient_state`)
2. **Bot: fix registration** — diagnosis type keyboard, doctor UUID picker from API, glucose question for diabetes
3. **Bot: swap in-memory → API** — `create_patient`, `submit_reading`, `get_idle_patients`, state persistence
4. **Dashboard: missing stat cards** — high risk count, compliance %, missed entry %
5. **`GET /patients/{id}/compliance`** endpoint — % of days with a reading in last 30 days
6. **BP trend chart** — Recharts `<LineChart>` on patient detail page
7. **JWT route protection** — `Depends(get_current_doctor)` on doctor-scoped endpoints
8. **High-risk Telegram push** — send alert to `doctor.telegram_id` when reading scores high

---

## Mock data credentials

Dashboard login (both password: `password123`):
- `alice.morgan@sympai.local`
- `bekzat.nurgali@sympai.local`
