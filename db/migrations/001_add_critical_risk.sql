-- Migration 001: Add critical risk level and medication_skip_reason
-- Run this on existing databases (fresh containers use schema.sql which already has these)

ALTER TYPE risk_level ADD VALUE IF NOT EXISTS 'critical';

ALTER TABLE daily_readings
    ADD COLUMN IF NOT EXISTS medication_skip_reason VARCHAR(50);
