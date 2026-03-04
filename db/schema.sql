-- ============================================================
-- SympAi MVP — Database Schema (PostgreSQL)
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TYPE diagnosis_type AS ENUM ('hypertension', 'diabetes', 'both');
CREATE TYPE risk_level     AS ENUM ('low', 'medium', 'high');

-- ============================================================
-- 1. DOCTORS
-- ============================================================

CREATE TABLE doctors (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    full_name     VARCHAR(200)  NOT NULL,
    email         VARCHAR(255)  NOT NULL UNIQUE,
    password      VARCHAR(255)  NOT NULL,           -- plain text for MVP, hash later
    telegram_id   BIGINT        UNIQUE,
    created_at    TIMESTAMPTZ   NOT NULL DEFAULT now()
);

-- ============================================================
-- 2. PATIENTS
-- ============================================================

CREATE TABLE patients (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    telegram_id         BIGINT         NOT NULL UNIQUE,
    full_name           VARCHAR(200)   NOT NULL,
    age                 SMALLINT       NOT NULL,
    diagnosis           diagnosis_type NOT NULL,
    current_medication  VARCHAR(200),               -- single drug, nullable
    doctor_id           UUID           NOT NULL REFERENCES doctors(id),
    language            VARCHAR(5)     NOT NULL DEFAULT 'ru',
    state               VARCHAR(30),
    comorbidities       TEXT,
    created_at          TIMESTAMPTZ    NOT NULL DEFAULT now()
);

-- ============================================================
-- 3. DAILY_READINGS
-- ============================================================

CREATE TABLE daily_readings (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id          UUID        NOT NULL REFERENCES patients(id),
    reading_date        DATE        NOT NULL DEFAULT CURRENT_DATE,
    sbp                 SMALLINT    NOT NULL,
    dbp                 SMALLINT    NOT NULL,
    pulse               SMALLINT,
    glucose             NUMERIC(4,1),
    medication_taken    BOOLEAN     NOT NULL DEFAULT FALSE,
    symptoms            TEXT[],
    notes               TEXT,
    risk_score          SMALLINT,
    risk_level          risk_level,
    doctor_reviewed_at  TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (patient_id, reading_date)
);