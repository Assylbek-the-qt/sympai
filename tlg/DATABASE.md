# Connecting the Bot to a Database

The bot currently stores everything in the `users` dict in memory (`bot.py:41`).
Restarting the bot wipes all data. This doc covers how to swap that out for a real DB.

Two options are covered: **Supabase** (easiest) and **raw PostgreSQL** with asyncpg.

---

## Schema

Two tables are needed, directly mirroring what's in the `users` dict.

```sql
-- One row per registered patient
CREATE TABLE patients (
    chat_id            BIGINT PRIMARY KEY,
    lang               VARCHAR(2)   NOT NULL DEFAULT 'ru',
    name               TEXT         NOT NULL,
    age                INT          NOT NULL,
    doctor             TEXT         NOT NULL,
    diagnosis_confirmed BOOLEAN     NOT NULL DEFAULT FALSE,
    medicines          TEXT,
    comorbidities      TEXT,
    state              TEXT,                        -- current conversation state, NULL = idle
    bp_history         JSONB        DEFAULT '[]',   -- [{sbp, dbp}, ...]
    created_at         TIMESTAMPTZ  DEFAULT NOW()
);

-- One row per daily check submission
CREATE TABLE daily_logs (
    id         BIGSERIAL    PRIMARY KEY,
    chat_id    BIGINT       NOT NULL REFERENCES patients(chat_id),
    date       DATE         NOT NULL,
    sbp        INT          NOT NULL,
    dbp        INT          NOT NULL,
    pulse      INT          NOT NULL,
    med_taken  BOOLEAN      NOT NULL,
    symptoms   TEXT[]       DEFAULT '{}',   -- e.g. {headache, chest_pain}
    risk       TEXT         NOT NULL,       -- low | medium | high
    created_at TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX ON daily_logs(chat_id, date DESC);
```

---

## Option A — Supabase

### 1. Install

```bash
pip install supabase
```

Add to `.env`:
```
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=your-service-role-key
```

### 2. Create `db.py`

```python
import os
from supabase import create_client, Client

_client: Client = None

def get_db() -> Client:
    global _client
    if _client is None:
        _client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    return _client


# ── patients ──────────────────────────────────────────────────────────────────

def get_patient(chat_id: int) -> dict | None:
    res = get_db().table("patients").select("*").eq("chat_id", chat_id).execute()
    return res.data[0] if res.data else None

def upsert_patient(chat_id: int, fields: dict):
    get_db().table("patients").upsert({"chat_id": chat_id, **fields}).execute()

def set_state(chat_id: int, state: str | None):
    get_db().table("patients").update({"state": state}).eq("chat_id", chat_id).execute()


# ── daily_logs ────────────────────────────────────────────────────────────────

def insert_log(chat_id: int, log: dict):
    get_db().table("daily_logs").insert({"chat_id": chat_id, **log}).execute()

def get_recent_logs(chat_id: int, n: int = 3) -> list[dict]:
    res = (
        get_db().table("daily_logs")
        .select("*")
        .eq("chat_id", chat_id)
        .order("date", desc=True)
        .limit(n)
        .execute()
    )
    return res.data


# ── cron helper ───────────────────────────────────────────────────────────────

def get_idle_patients() -> list[dict]:
    """Returns all registered patients currently in idle state (state IS NULL)."""
    res = (
        get_db().table("patients")
        .select("chat_id, lang")
        .is_("state", None)
        .not_.is_("name", None)   # exclude half-registered users
        .execute()
    )
    return res.data
```

---

## Option B — Raw PostgreSQL (asyncpg)

Use this if you're running your own Postgres (Docker, VPS, etc.).

### 1. Install

```bash
pip install asyncpg
```

Add to `.env`:
```
DATABASE_URL=postgresql://user:password@localhost:5432/sympai
```

### 2. Create `db.py`

```python
import os
import asyncpg

_pool = None

async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(os.getenv("DATABASE_URL"))
    return _pool


async def get_patient(chat_id: int) -> dict | None:
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM patients WHERE chat_id = $1", chat_id)
    return dict(row) if row else None

async def upsert_patient(chat_id: int, fields: dict):
    pool = await get_pool()
    cols = ", ".join(fields.keys())
    placeholders = ", ".join(f"${i+2}" for i in range(len(fields)))
    updates = ", ".join(f"{k} = EXCLUDED.{k}" for k in fields)
    await pool.execute(
        f"INSERT INTO patients (chat_id, {cols}) VALUES ($1, {placeholders}) "
        f"ON CONFLICT (chat_id) DO UPDATE SET {updates}",
        chat_id, *fields.values(),
    )

async def set_state(chat_id: int, state: str | None):
    pool = await get_pool()
    await pool.execute("UPDATE patients SET state = $1 WHERE chat_id = $2", state, chat_id)

async def insert_log(chat_id: int, log: dict):
    pool = await get_pool()
    await pool.execute(
        """INSERT INTO daily_logs (chat_id, date, sbp, dbp, pulse, med_taken, symptoms, risk)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
        chat_id, log["date"], log["sbp"], log["dbp"],
        log["pulse"], log["med_taken"], log["symptoms"], log["risk"],
    )

async def get_recent_logs(chat_id: int, n: int = 3) -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT * FROM daily_logs WHERE chat_id = $1 ORDER BY date DESC LIMIT $2",
        chat_id, n,
    )
    return [dict(r) for r in rows]

async def get_idle_patients() -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT chat_id, lang FROM patients WHERE state IS NULL AND name IS NOT NULL"
    )
    return [dict(r) for r in rows]
```

---

## What to change in bot.py

Only four areas need to be touched:

### 1. Remove the in-memory dict (line 41)

```python
# DELETE this line:
users: dict[int, dict] = {}
```

### 2. `cmd_start` — create patient row instead of dict entry

```python
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await upsert_patient(chat_id, {"state": LANG})
    ...
```

### 3. Every handler that reads/writes `user[...]`

Replace `user["field"] = value` with `await upsert_patient(chat_id, {"field": value})`.

Replace `user.get("state")` with `(await get_patient(chat_id))["state"]`.

The cleanest way: load the patient once at the top of `handle_message` and pass it down, then persist only at the end of each handler — same pattern as today, just with DB calls at the boundaries.

```python
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    user = await get_patient(chat_id)   # <-- load from DB
    if not user:
        await update.message.reply_text("...")
        return
    ...
    # handlers mutate `user` dict in memory during the conversation step,
    # then call upsert_patient() to persist at the end of each handler
```

### 4. `_daily_symptoms` — save log to DB

```python
# Replace:
user["daily_logs"].append(log)

# With:
await insert_log(chat_id, log)
```

### 5. `daily_check_job` — load idle patients from DB

```python
async def daily_check_job(context: CallbackContext):
    patients = await get_idle_patients()   # <-- from DB
    for row in patients:
        chat_id = row["chat_id"]
        user = await get_patient(chat_id)
        await _start_daily_check_for(context.bot, chat_id, user)
```

### 6. `risk.py` — load recent logs from DB

`calculate_risk` currently reads `user["daily_logs"][-3:]`. Pass recent logs explicitly:

```python
# In _daily_symptoms, before calling calculate_risk:
recent_logs = await get_recent_logs(chat_id, n=3)
risk = calculate_risk(recent_logs, log)

# In risk.py, change signature:
def calculate_risk(recent_logs: list, log: dict) -> str:
    missed_days = sum(1 for l in recent_logs if not l.get("med_taken", True))
    ...
```

---

## .env after adding DB

```
TOKEN=your_telegram_token

# Supabase
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=your-service-role-key

# OR raw Postgres
DATABASE_URL=postgresql://user:password@localhost:5432/sympai
```
