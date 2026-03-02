import logging

logger = logging.getLogger(__name__)


def calculate_risk(user: dict, log: dict) -> str:
    sbp = log["sbp"]
    symptoms = log.get("symptoms", [])

    recent_logs = user.get("daily_logs", [])[-3:]
    missed_days = sum(1 for l in recent_logs if not l.get("med_taken", True))

    if sbp >= 170 or "chest_pain" in symptoms:
        risk = "high"
    elif sbp >= 150 or missed_days >= 2:
        risk = "medium"
    else:
        risk = "low"

    logger.info(
        f"Risk | name={user.get('name')} | SBP={sbp} | "
        f"symptoms={symptoms} | missed_days={missed_days} | -> {risk.upper()}"
    )
    return risk
