# SympAI

Chronic disease monitoring platform for hypertension and diabetes patients in Kazakhstan. Patients submit daily readings via Telegram; doctors monitor them through a web dashboard.

## What it does

| Component | Role |
|---|---|
| **Telegram bot** (`tlg/`) | Bilingual (KZ/RU) patient interface — registration, daily check-ins, inline buttons, medication reminders, evening compliance follow-up, PDF report on demand |
| **Risk engine** (`api/services/risk.py`) | 4-zone clinical triage per reading — Critical / High / Medium / Low — with first-aid instructions for critical BP |
| **FastAPI backend** (`api/`) | REST API, JWT auth, PDF report generation, PostgreSQL persistence |
| **Doctor dashboard** (`web/`) | Login-gated React app — patient list, risk levels, compliance stats, BP trend charts |

## Bot commands

| Command | Description |
|---|---|
| `/start` | Register (new) or resume (returning patient) |
| `/check` | Start daily check manually (runs automatically at 08:00 Almaty) |
| `/report` | Generate and send a PDF medical report to share with your doctor |

## Risk zones

| Zone | Colour | Threshold | Action |
|---|---|---|---|
| Critical | 🆘 Red | SBP ≥ 180 or DBP ≥ 120 or chest pain | First aid steps + call 103 immediately |
| High | 🚨 Yellow | SBP 160–179 or DBP 100–119 or dizziness | Urgent therapist visit |
| Medium | ⚠️ Orange | SBP 140–159 or 2+ missed med days | Monitor closely |
| Low | ✅ Green | Below thresholds | Home monitoring |

## Architecture

```
┌──────────────────┐     ┌─────────────────┐     ┌──────────────┐
│  Telegram Bot    │     │   FastAPI API   │     │  PostgreSQL  │
│  (tlg/)          │────▶│   (api/)        │────▶│  (db/)       │
│                  │     │                 │     └──────────────┘
│  • inline UX     │     │  • risk scoring │
│  • 3 cron jobs   │     │  • PDF reports  │
│  • API-backed    │     │  • JWT auth     │
└──────────────────┘     └────────┬────────┘
                                  │
                         ┌────────▼────────┐
                         │  React Dashboard│
                         │  (web/)         │
                         │  • stat cards   │
                         │  • BP charts    │
                         └─────────────────┘
```

## Daily schedule (Almaty time, UTC+5)

| Time | Event |
|---|---|
| 08:00 | Daily check sent to all idle patients |
| 09:00 | Medication reminder push notification |
| 20:00 | Evening compliance check — asks if medication was taken; records reason if not |

## Project structure

```
sympai/
├── api/
│   ├── models/          # SQLAlchemy ORM (doctor, patient, daily_reading)
│   ├── routers/         # auth, doctors, patients, daily_readings
│   ├── schemas/         # Pydantic schemas
│   ├── services/
│   │   ├── risk.py      # 4-zone triage algorithm
│   │   └── report.py    # PDF generator (reportlab + matplotlib)
│   ├── main.py
│   └── requirements.txt
├── db/
│   ├── schema.sql        # Canonical DB schema
│   ├── mock_data.sql     # Seed data (2 doctors, 5 patients)
│   └── migrations/       # ALTER scripts for existing DBs
├── tlg/
│   ├── bot.py            # State machine + cron jobs + inline keyboards
│   ├── texts.py          # Bilingual strings (kz/ru)
│   ├── api_client.py     # httpx async API client
│   ├── docs/bot_flow.md  # Full UX flow documentation
│   └── tests/            # pytest unit tests + user stories
├── web/
│   └── app/routes/       # login, dashboard, patients.$id
├── dev-compose.yaml      # All services for local dev
└── .dev.env              # Env vars (gitignored)
```

## Prerequisites

- Docker & Docker Compose
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))

## Getting started

```bash
# 1. Clone
git clone git@github.com:Assylbek-the-qt/sympai.git && cd sympai

# 2. Create env file
cp .dev.env.example .dev.env
# Fill in: TOKEN (Telegram), SECRET_KEY

# 3. Start all services
docker compose -f dev-compose.yaml up --build

# Services
# API:       http://localhost:3069
# API docs:  http://localhost:3069/docs
# Dashboard: http://localhost:3000
```

## Environment variables (.dev.env)

```env
# Database (auto-configured by dev-compose)
DATABASE_URL=postgresql://postgres:postgres@db:5432/symp_ai

# Telegram bot
TOKEN=<your_bot_token>

# API (inside Docker)
API_URL=http://api:3069

# Auth
SECRET_KEY=change_me_in_production
```

## Applying DB migrations

For existing running databases (fresh containers auto-apply `schema.sql`):

```bash
docker compose -f dev-compose.yaml exec db \
  psql -U postgres -d symp_ai -f /migrations/001_add_critical_risk.sql
```

## Mock data credentials

Dashboard login (password: `password123` for both):

- `alice.morgan@sympai.local`
- `bekzat.nurgali@sympai.local`

## License

Proprietary. Internal use only.
