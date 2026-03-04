-- ============================================================
-- SympAi MVP — Mock Data Seed
-- Adds 5 patients + required doctors
-- ============================================================

INSERT INTO doctors (id, full_name, email, password)
VALUES
    ('11111111-1111-1111-1111-111111111111', 'Dr. Alice Morgan', 'alice.morgan@sympai.local', '$2b$12$uS3h0uRLXl3hE1hNsSsoJOFpNY8sOedTjEKC1FHoaA1FLnDzMUktC'),
    ('22222222-2222-2222-2222-222222222222', 'Dr. Bekzat Nurgali', 'bekzat.nurgali@sympai.local', '$2b$12$SSrYXXgig/7HPCyhhiZJoeEWKj.2.5a7XAnZzWD16zb1RVBQmYh8m')
ON CONFLICT (email) DO NOTHING;

INSERT INTO patients (
    id,
    telegram_id,
    full_name,
    age,
    diagnosis,
    current_medication,
    doctor_id,
    language
)
VALUES
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1', 700000001, 'Aruzhan Sadykova', 52, 'hypertension', 'Lisinopril 10mg', '11111111-1111-1111-1111-111111111111', 'ru'),
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2', 700000002, 'Timur Askarov', 61, 'diabetes', 'Metformin 500mg', '11111111-1111-1111-1111-111111111111', 'ru'),
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3', 700000003, 'Nargiza Tolegen', 45, 'both', 'Amlodipine 5mg', '22222222-2222-2222-2222-222222222222', 'kz'),
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4', 700000004, 'Daniyar Kozhabek', 58, 'hypertension', 'Losartan 50mg', '22222222-2222-2222-2222-222222222222', 'ru'),
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa5', 700000005, 'Madina Iskakova', 49, 'diabetes', 'Insulin glargine', '11111111-1111-1111-1111-111111111111', 'ru')
ON CONFLICT (telegram_id) DO NOTHING;

INSERT INTO daily_readings (
    patient_id,
    reading_date,
    sbp,
    dbp,
    pulse,
    glucose,
    medication_taken,
    symptoms,
    notes,
    risk_score,
    risk_level
)
VALUES
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1', CURRENT_DATE - INTERVAL '4 days', 148, 94, 82, NULL, TRUE, ARRAY['headache'], 'Mild morning headache', 7, 'high'),
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2', CURRENT_DATE - INTERVAL '3 days', 132, 84, 76, 8.6, TRUE, ARRAY['fatigue'], 'Post-lunch tiredness', 5, 'medium'),
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3', CURRENT_DATE - INTERVAL '2 days', 156, 98, 88, 10.4, FALSE, ARRAY['dizziness', 'thirst'], 'Missed medication', 9, 'high'),
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4', CURRENT_DATE - INTERVAL '1 day', 138, 86, 79, NULL, TRUE, ARRAY[]::TEXT[], 'Stable overall', 4, 'medium'),
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa5', CURRENT_DATE, 128, 80, 74, 7.2, TRUE, ARRAY['none'], 'No complaints', 2, 'low')
ON CONFLICT (patient_id, reading_date) DO NOTHING;
