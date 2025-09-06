# app/services/base44_client.py
import os, httpx, uuid
from loguru import logger

# ---------- STUBS (current behavior) ----------
def base44_create_stub(spec):
    app_id = "app_" + uuid.uuid4().hex[:8]
    preview_url = f"https://preview.base44.local/{app_id}"
    logger.info(f"[Base44] CREATE {app_id} from spec '{spec['name']}'")
    return app_id, preview_url

def base44_update_stub(app_id, change_request):
    logger.info(f"[Base44] UPDATE {app_id} with CR: {change_request['reason']}")

# ---------- REAL CLIENT (switch to these when Base44 is ready) ----------
BASE44_API_URL = os.getenv("BASE44_API_URL", "").rstrip("/")
BASE44_API_KEY = os.getenv("BASE44_API_KEY", "")

def _hdrs():
    return {"api_key": BASE44_API_KEY, "Content-Type": "application/json"}

def make_build_prompt(spec: dict) -> str:
    return (
        "Build a minimal-dark mobile UI with three swipeable screens.\n"
        "Selectors: data-test='overview|movers|news|gainer|loser|news-item'.\n"
        "Follow constraints exactly. If a datasource is unavailable, stub clearly.\n"
        f"SPEC JSON:\n{spec}\n"
    )

def base44_create(spec: dict):
    prompt_text = make_build_prompt(spec)
    r = httpx.post(f"{BASE44_API_URL}/apps.create", headers=_hdrs(), json={"prompt": prompt_text}, timeout=60)
    r.raise_for_status()
    data = r.json()
    app_id = data["app_id"]
    preview_url = data["preview_url"]
    logger.info(f"[Base44] CREATE {app_id} from spec '{spec['name']}'")
    return app_id, preview_url

def base44_update(app_id: str, change_request: dict):
    r = httpx.post(
        f"{BASE44_API_URL}/apps.update",
        headers=_hdrs(),
        json={"app_id": app_id, "change_request": change_request},
        timeout=60,
    )
    r.raise_for_status()
    logger.info(f"[Base44] UPDATE {app_id} with CR: {change_request.get('reason','no-reason')}")
