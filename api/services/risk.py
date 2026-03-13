def calculate_risk(recent_readings: list, current: dict) -> tuple[str, int]:
    """
    Returns (risk_level, risk_score).

    Zones:
      critical — SBP ≥ 180 OR DBP ≥ 120 OR chest_pain  → call 103 immediately
      high     — SBP 160–179 OR DBP 100–119 OR dizziness → urgent therapist
      medium   — SBP 140–159 OR 2+ missed med days       → monitor closely
      low      — everything else                          → home monitoring

    recent_readings: list of dicts or ORM objects (last N readings, not current).
    current:         dict with at least 'sbp', 'dbp', 'symptoms' keys.
    """
    sbp      = current["sbp"]
    dbp      = current.get("dbp", 0)
    symptoms = current.get("symptoms") or []

    missed_days = sum(
        1 for r in recent_readings
        if not (r["medication_taken"] if isinstance(r, dict) else r.medication_taken)
    )

    if sbp >= 180 or dbp >= 120 or "chest_pain" in symptoms:
        level, score = "critical", 10
    elif sbp >= 160 or dbp >= 100 or "dizziness" in symptoms:
        level, score = "high", 7
    elif sbp >= 140 or missed_days >= 2:
        level, score = "medium", 5
    else:
        level, score = "low", 2

    return level, score
