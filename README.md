# SympAi

Chronic disease monitoring platform. Patients submit daily readings via Telegram, doctors monitor them through a web dashboard.

## What it does

- **Telegram bot** collects daily BP, pulse, glucose, medication adherence, and symptoms from patients
- **Risk engine** scores each reading (0–10) based on clinical rules and flags high-risk cases
- **Doctor dashboard** shows patient list, risk levels, compliance stats, and unreviewed alerts

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Telegram    │     │   FastAPI    │     │  PostgreSQL  │
│  Bot (tlg/)  │────▶│  API (api/)  │────▶│  (db/)       │
└──────────────┘     └──────┬───────┘     └──────────────┘
                            │
                     ┌──────▼───────┐
                     │  React App   │
                     │  (web/)      │
                     └──────────────┘
```

## Project structure

```
SympAi/
├── api/                  # FastAPI backend
│   ├── models/           # SQLModel ORM models
│   ├── routers/          # API route handlers
│   ├── schemas/          # Pydantic request/response schemas
│   ├── services/         # Business logic (risk scoring, etc.)
│   ├── utils/            # Helpers
│   ├── main.py           # App entrypoint
│   ├── Dockerfile
│   └── requirements.txt
├── db/                   # Database
│   ├── db_data/          # PG data volume (gitignored)
│   └── schema.sql        # DDL
├── tlg/                  # Telegram bot
├── web/                  # React doctor dashboard
└── compose.yaml          # Docker Compose (all services)
```

## Prerequisites

- Docker & Docker Compose
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))

## Getting started

```bash
# 1. Clone
git clone <repo-url> && cd SympAi

# 2. Environment
cp .env.example .env
# Fill in: POSTGRES_PASSWORD, TELEGRAM_BOT_TOKEN, JWT_SECRET

# 3. Run
docker compose up -d

# 4. Initialize DB
docker compose exec db psql -U sympai -d sympai -f /docker-entrypoint-initdb.d/schema.sql
```

| Service   | URL                        |
|-----------|----------------------------|
| API       | http://localhost:8000      |
| API Docs  | http://localhost:8000/docs |
| Dashboard | http://localhost:3000      |
| Database  | localhost:5432             |

## Environment variables

```env
# Database
POSTGRES_USER=sympai
POSTGRES_PASSWORD=
POSTGRES_DB=sympai
DATABASE_URL=postgresql://sympai:<password>@db:5432/sympai

# Telegram
TELEGRAM_BOT_TOKEN=

# API
JWT_SECRET=
API_PORT=8000
```

## Deployment (VPS)

```bash
# On your VPS
git pull origin main
docker compose -f compose.yaml up -d --build
```


## License

Proprietary. Internal use only.