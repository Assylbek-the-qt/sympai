import os
import logging
import httpx

logger = logging.getLogger(__name__)

API_URL = os.getenv("API_URL", "http://localhost:3069")


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=API_URL, timeout=10.0)


async def get_patient(telegram_id: int) -> dict | None:
    """Returns patient dict or None if not found."""
    async with _client() as c:
        r = await c.get(f"/patients/by-telegram/{telegram_id}")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()


async def create_patient(data: dict) -> dict:
    """POST /patients — returns created patient dict."""
    async with _client() as c:
        r = await c.post("/patients", json=data)
        r.raise_for_status()
        return r.json()


async def list_doctors() -> list[dict]:
    """GET /doctors — returns list of doctor dicts."""
    async with _client() as c:
        r = await c.get("/doctors")
        r.raise_for_status()
        return r.json()


async def submit_reading(data: dict) -> dict:
    """POST /readings — returns created reading dict (includes risk_level)."""
    async with _client() as c:
        r = await c.post("/readings", json=data)
        r.raise_for_status()
        return r.json()


async def get_all_patients() -> list[dict]:
    """GET /patients — returns all patients (used for startup reload)."""
    async with _client() as c:
        r = await c.get("/patients")
        r.raise_for_status()
        return r.json()


async def get_idle_patients() -> list[dict]:
    """GET /patients?state=idle — returns patients awaiting daily check."""
    async with _client() as c:
        r = await c.get("/patients", params={"state": "idle"})
        r.raise_for_status()
        return r.json()


async def set_patient_state(patient_id: str, state: str | None) -> dict:
    """PATCH /patients/{id} — updates patient state. Pass state=None to clear."""
    async with _client() as c:
        r = await c.patch(f"/patients/{patient_id}", json={"state": state})
        r.raise_for_status()
        return r.json()


async def get_report(patient_id: str) -> bytes:
    """GET /patients/{id}/report — returns raw PDF bytes."""
    async with httpx.AsyncClient(base_url=API_URL, timeout=30.0) as c:
        r = await c.get(f"/patients/{patient_id}/report")
        r.raise_for_status()
        return r.content


async def get_chart(patient_id: str, limit: int = 7) -> bytes:
    """GET /patients/{id}/chart — returns raw PNG bytes of BP trend chart."""
    async with httpx.AsyncClient(base_url=API_URL, timeout=20.0) as c:
        r = await c.get(f"/patients/{patient_id}/chart", params={"limit": limit})
        r.raise_for_status()
        return r.content


async def set_skip_reason(reading_id: str, reason: str) -> dict:
    """PATCH /readings/{id}/skip-reason — records why medication was skipped."""
    async with _client() as c:
        r = await c.patch(f"/readings/{reading_id}/skip-reason", json={"reason": reason})
        r.raise_for_status()
        return r.json()
