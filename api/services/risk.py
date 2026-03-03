def calculate_risk(recent_readings: list, current: dict) -> tuple[str, int]:
    """
    Returns (risk_level, risk_score).

    recent_readings: list of dicts or ORM objects representing the last N readings
                     (not including the current one being submitted).
    current:         dict with at least 'sbp' and 'symptoms' keys.
    """
    sbp = current["sbp"]
    symptoms = current.get("symptoms") or []

    missed_days = sum(
        1 for r in recent_readings
        if not (r["medication_taken"] if isinstance(r, dict) else r.medication_taken)
    )

    if sbp >= 170 or "chest_pain" in symptoms:
        level, score = "high", 9
    elif sbp >= 150 or missed_days >= 2:
        level, score = "medium", 5
    else:
        level, score = "low", 2

    return level, score
