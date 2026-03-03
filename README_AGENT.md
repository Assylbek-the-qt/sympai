# SympAI — Agent Context

This file exists so an LLM can understand the full project without being walked through it.
Read this before touching any code. Keep it updated when things change.

---

## What the project is

**SympAI Hypertension** — a Telegram-based clinical early warning system for hypertension patients in Kazakhstan. Patients register via a Telegram bot, submit daily blood pressure readings, get risk-scored, and doctors monitor them via a web dashboard.

**Stack:**
- `api/` — FastAPI + SQLAlchemy + PostgreSQL (backend)
- `tlg/` — python-telegram-bot v22 (patient-facing bot)
- `web/` — doctor dashboard (React Router v7 + JavaScript — bootstrapped with `npm create react-router@latest`, not scaffolded yet)
- `db/` — schema.sql + mock_data.sql + ERD
- `compose.yaml` — Docker Compose (api + db + db-seed running; tlg and web commented out)

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
│   │   ├── patient.py           # PatientCreate, PatientUpdate, PatientOut
│   │   └── daily_reading.py     # ReadingCreate, ReadingOut
│   ├── services/
│   │   ├── patient.py           # get_all, get_by_id, get_by_telegram_id, create, update, delete
│   │   ├── daily_reading.py     # get_by_id, get_by_patient, get_recent, create, mark_reviewed
│   │   └── risk.py              # calculate_risk(recent_readings, current) -> (level, score)
│   ├── routers/
│   │   ├── patients.py          # CRUD /patients
│   │   ├── daily_readings.py    # /readings endpoints
│   │   └── items.py             # PLACEHOLDER — delete this
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env                     # DATABASE_URL
├── tlg/
│   ├── bot.py                   # Main bot — state machine, handlers, cron
│   ├── texts.py                 # All bilingual strings (kz/ru)
│   ├── risk.py                  # LOCAL risk scoring — will be deleted when bot uses API
│   ├── .env                     # TOKEN, (API_URL not yet added)
│   └── venv/
├── db/
│   ├── schema.sql               # Canonical DB schema
│   ├── mock_data.sql            # Seed: 2 doctors, 5 patients, 5 readings
│   └── sympai_erd.mermaid
├── compose.yaml
├── TODO.md                      # Checkbox task list — keep updated
├── PLAN.md                      # High-level architecture plan
└── README_AGENT.md              # This file
```

---

## Running locally

```bash
docker compose up --build        # starts api + db + db-seed
# api available at http://localhost:3069
# docs at http://localhost:3069/docs

cd tlg
source venv/bin/activate
python bot.py                    # run bot separately for now
```

`tlg` and `web` services are commented out in `compose.yaml` — they don't have Dockerfiles yet.

---

## Database schema

Three tables. All PKs are UUIDs (`uuid-ossp`).

### `doctors`
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| full_name | VARCHAR(200) | |
| email | VARCHAR(255) UNIQUE | |
| password | VARCHAR(255) | plain text — **needs hashing** |
| created_at | TIMESTAMPTZ | |

**Missing (not in schema yet):** `telegram_id BIGINT` — needed for high-risk alert push.

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
| created_at | TIMESTAMPTZ | |

**Missing (not in schema yet):**
- `state VARCHAR(30)` — bot conversation state for persistence
- `comorbidities TEXT` — bot collects this but no column exists

### `daily_readings`
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| patient_id | UUID FK → patients | |
| reading_date | DATE | UNIQUE per patient per day |
| sbp | SMALLINT | systolic |
| dbp | SMALLINT | diastolic |
| pulse | SMALLINT | nullable |
| glucose | NUMERIC(4,1) | nullable, for diabetes patients |
| medication_taken | BOOLEAN | |
| symptoms | TEXT[] | e.g. `{headache, chest_pain}` |
| notes | TEXT | nullable |
| risk_score | SMALLINT | set by API on insert |
| risk_level | ENUM | `low \| medium \| high`, set by API |
| doctor_reviewed_at | TIMESTAMPTZ | null until doctor reviews |
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

Routers never touch the DB directly. Services never import routers. `risk.py` is a pure function with no SQLAlchemy dependency.

### Adding a new resource — checklist

1. **Model** (`models/foo.py`) — SQLAlchemy ORM class, inherits `Base` from `models/doctor.py`
2. **Schema** (`schemas/foo.py`) — Pydantic v2: `FooCreate`, `FooUpdate`, `FooOut`
3. **Service** (`services/foo.py`) — plain functions `(db: Session, ...) -> ORM object`
4. **Router** (`routers/foo.py`) — `APIRouter(prefix="/foo", tags=["foo"])`, import service
5. **Register** in `main.py` — `app.include_router(foo.router)`

### Model pattern

```python
# models/foo.py
import uuid
from models.doctor import Base  # always import Base from here
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID

class Foo(Base):
    __tablename__ = "foos"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
```

### Schema pattern

```python
# schemas/foo.py
from pydantic import BaseModel, Field

class FooCreate(BaseModel):
    name: str = Field(max_length=200)

class FooOut(FooCreate):
    id: uuid.UUID
    class Config:
        from_attributes = True   # required for ORM → Pydantic conversion
```

### Service pattern

```python
# services/foo.py
from sqlalchemy.orm import Session
from models.foo import Foo
from schemas.foo import FooCreate

def get_by_id(db: Session, foo_id: uuid.UUID) -> Foo | None:
    return db.query(Foo).filter(Foo.id == foo_id).first()

def create(db: Session, data: FooCreate) -> Foo:
    foo = Foo(**data.model_dump())
    db.add(foo)
    db.commit()
    db.refresh(foo)
    return foo
```

### Router pattern

```python
# routers/foo.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from schemas.foo import FooCreate, FooOut
from services import foo as foo_service

router = APIRouter(prefix="/foos", tags=["foos"])

@router.post("", response_model=FooOut, status_code=201)
def create_foo(data: FooCreate, db: Session = Depends(get_db)):
    return foo_service.create(db, data)

@router.get("/{foo_id}", response_model=FooOut)
def get_foo(foo_id: uuid.UUID, db: Session = Depends(get_db)):
    foo = foo_service.get_by_id(db, foo_id)
    if not foo:
        raise HTTPException(status_code=404, detail="Foo not found")
    return foo
```

### DB session

`database.py` provides `get_db()` as a FastAPI dependency. Always use `Depends(get_db)` in router functions. Never create a session manually inside a service — receive it as a parameter.

### Risk scoring

`services/risk.py` — `calculate_risk(recent_readings, current_dict) -> (level: str, score: int)`

- `recent_readings` — list of ORM `DailyReading` objects (last N, not including current)
- `current_dict` — plain dict with at minimum `sbp` and `symptoms` keys
- Returns `("low"|"medium"|"high", int)`
- Called inside `services/daily_reading.create()` before the DB insert
- Accepts both ORM objects and dicts for `medication_taken` (checks with `isinstance`)

Risk rules:
- **High** → SBP ≥ 170 OR `chest_pain` in symptoms → score 9
- **Medium** → SBP 150–169 OR missed meds ≥ 2 of last 3 days → score 5
- **Low** → everything else → score 2

---

## Telegram bot patterns (tlg/)

### Architecture

Manual state machine — no ConversationHandler. State is stored per `chat_id` in a global dict.

```python
users: dict[int, dict] = {}   # chat_id -> user data + state
```

**IMPORTANT:** This is in-memory only right now. A bot restart wipes all data. The plan is to persist `state` to the DB via the API (see TODO.md).

### State constants

Defined as plain strings at the top of `bot.py`:

```
LANG → NAME → AGE → DOCTOR → DIAGNOSIS
  → INIT_BP1 → INIT_BP2 → INIT_BP3 → INIT_MED → INIT_COMORBID → None (idle)

None (idle) → DAILY_SBP → DAILY_DBP → DAILY_PULSE → DAILY_MED → DAILY_SYMPTOMS → None
```

`state = None` means the patient is registered and idle (waiting for the daily cron).

### ROUTES dict

All handlers have the same signature: `async def _foo(update, user, text)`.
The main `handle_message` function looks up the handler by state:

```python
ROUTES = {
    LANG: _lang,
    NAME: _name,
    ...
}

async def handle_message(update, context):
    user = users[chat_id]
    handler = ROUTES.get(user["state"])
    if handler:
        await handler(update, user, text)
```

### Adding a new state

1. Add a string constant at the top: `MY_STATE = "my_state"`
2. Write handler: `async def _my_state(update: Update, user: dict, text: str):`
3. Add to `ROUTES`: `MY_STATE: _my_state`
4. Set `user["state"] = MY_STATE` in the preceding handler

### texts.py pattern

All user-facing strings live in `texts.py` as a nested dict:

```python
TEXTS = {
    "kz": { "key": "Қазақша мәтін" },
    "ru": { "key": "Русский текст" },
}
```

Access via helper `t(chat_id, "key")` which reads `user["lang"]` automatically.
Never hardcode bot messages inline — always add to `texts.py` first.

### Keyboard helper

```python
mkb(["Yes", "No"])              # one row
mkb(["A", "B"], ["C", "D"])     # two rows
```

Returns `ReplyKeyboardMarkup` with `resize_keyboard=True, one_time_keyboard=True`.

### Cron job (daily check at 08:00 Almaty / UTC+5)

```python
app.job_queue.run_daily(daily_check_job, time=dtime(hour=8, minute=0, tzinfo=TZ_ALMATY))
```

`daily_check_job` iterates all users with `state == None` and sends the first daily question.
Currently reads from in-memory `users` dict — will change to `GET /patients?state=idle`.

`/check` command manually triggers the daily flow for testing without waiting for 8am.

### Logging convention

```python
logger.info(f"STATE_NAME | chat_id={chat_id} | field={value}")
```

Every state handler logs on entry. `print()` is used for structured console output of completed
registrations and daily logs (separate from the logger output).

---

## Frontend patterns (web/)

### Stack
- **React Router v7** (framework mode) + **plain JavaScript** — no TypeScript
- Bootstrapped with `npm create react-router@latest` — select JS variant + React Router v7
- Talks to the FastAPI backend via `fetch()` — no additional HTTP client library

### File structure (React Router v7 convention)
```
web/
├── app/
│   ├── root.jsx             # root layout, global error boundary
│   ├── routes.js            # route manifest
│   └── routes/
│       ├── _index.jsx       # / → redirect based on auth
│       ├── login.jsx        # /login
│       ├── dashboard.jsx    # /dashboard (auth required)
│       └── patients.$id.jsx # /patients/:id (auth required)
├── public/
├── package.json
└── Dockerfile
```

### Auth pattern
JWT stored in `localStorage`. Each route loader checks for token before fetching data:

```js
// in any protected loader
export async function loader({ request }) {
  const token = localStorage.getItem("token");
  if (!token) throw redirect("/login");
  // fetch data...
}
```

`POST /auth/login` returns `{ access_token }` — store it, redirect to `/dashboard`.

### API calls pattern
Use a thin wrapper so `API_URL` is set once:

```js
// app/api.js
const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:3069";

export async function apiFetch(path, options = {}) {
  const token = localStorage.getItem("token");
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
```

### Route loader pattern (React Router v7)
Data fetching lives in `loader`, not in `useEffect`:

```js
export async function loader({ params }) {
  const patient = await apiFetch(`/patients/${params.id}`);
  const readings = await apiFetch(`/readings?patient_id=${params.id}&limit=30`);
  return { patient, readings };
}

export default function PatientDetail() {
  const { patient, readings } = useLoaderData();
  // render...
}
```

### Charts
Use **Recharts** (React-native, no CDN needed):
```bash
npm install recharts
```
`<LineChart>` for BP trend, `<BarChart>` for compliance.

### Risk badge convention
```js
const RISK_COLOR = { low: "green", medium: "orange", high: "red" };
<span style={{ color: RISK_COLOR[reading.risk_level] }}>{reading.risk_level}</span>
```

---

## What's done vs pending

### Done
- FastAPI + PostgreSQL running in Docker
- `patients` CRUD (`GET`, `POST`, `PATCH`, `DELETE`)
- `daily_readings` full CRUD + auto risk scoring on insert + doctor review endpoint
- `services/risk.py` — pure risk scoring function
- Telegram bot — full registration flow + daily check flow (in-memory)
- Bilingual support (KZ/RU) with `texts.py`
- Daily cron at 08:00 Almaty

### Pending — see TODO.md for full checkbox list

Priority order:
1. **API: doctors** — schemas, service, router (`GET /doctors`, `POST /doctors`, `GET /doctors/{id}/alerts`)
2. **API: extend patients** — `GET /patients/by-telegram/{id}`, `GET /patients?state=idle`, compliance endpoint
3. **DB schema fixes** — add `state`, `comorbidities` to `patients`; add `telegram_id` to `doctors`
4. **Bot: fix mismatches** — diagnosis type selection (not yes/no), glucose for diabetes, doctor_id FK
5. **Bot: API client** — `tlg/api_client.py` with httpx, swap in-memory dict for API calls
6. **API cleanup** — delete placeholder `items` router/service/schema/model
7. **Web dashboard** — not started (React Router v7 + JavaScript, bootstrap with `npm create react-router@latest`)
8. **Auth** — hash doctor passwords, JWT for API
9. **Docker** — Dockerfiles for `tlg` and `web`, uncomment in compose.yaml

---

## Known bugs / active mismatches

| Bug | Location | Fix |
|-----|----------|-----|
| Bot asks "diagnosis confirmed yes/no" | `tlg/bot.py _diagnosis` | Ask type: hypertension/diabetes/both |
| Bot stores doctor name as free text | `tlg/bot.py _doctor` | Must store `doctor_id` UUID FK |
| Bot never asks for glucose | `tlg/bot.py` | Add after pulse for diabetes patients |
| `comorbidities` not in DB schema | `db/schema.sql` | Add `comorbidities TEXT` column |
| `state` not in DB schema | `db/schema.sql` | Add `state VARCHAR(30)` column |
| `PatientUpdate` missing `state` field | `api/schemas/patient.py` | Add `state: str \| None` |
| `PatientOut` missing `state` field | `api/schemas/patient.py` | Add `state: str \| None` |
| `doctors.telegram_id` missing | `db/schema.sql` | Add for alert push |
| Doctor passwords plain text | `db/mock_data.sql` + `models/doctor.py` | Add bcrypt |
| `tlg/risk.py` duplicates API risk logic | `tlg/risk.py` | Delete after bot uses API |
| `items` router is a placeholder | `api/routers/items.py` | Delete everything items-related |

---

## Environment variables

```
# api/.env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/symp_ai

# tlg/.env
TOKEN=<telegram bot token>
API_URL=http://localhost:3069        # not yet read by bot — needs to be added
```

In Docker, `DATABASE_URL` uses `db` as hostname (`@db:5432`) — set in `compose.yaml` directly.
