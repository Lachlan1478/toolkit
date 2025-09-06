import os, httpx
from loguru import logger

BASE44_API_URL = os.getenv("BASE44_API_URL")
BASE44_API_KEY = os.getenv("BASE44_API_KEY")
HDRS = {"api_key": BASE44_API_KEY, "Content-Type": "application/json"}

def base44_create(spec: dict):
    # Turn your spec into a prompt/text contract as needed
    payload = {"prompt": make_build_prompt(spec)}
    r = httpx.post(f"{BASE44_API_URL}/apps.create", headers=HDRS, json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    app_id = data["app_id"]
    preview_url = data["preview_url"]
    logger.info(f"[Base44] CREATE {app_id} from spec '{spec['name']}'")
    return app_id, preview_url

def base44_update(app_id: str, change_request: dict):
    r = httpx.post(f"{BASE44_API_URL}/apps.update", headers=HDRS,
                   json={"app_id": app_id, "change_request": change_request}, timeout=60)
    r.raise_for_status()
    logger.info(f"[Base44] UPDATE {app_id} with CR: {change_request.get('reason','no-reason')}")

def make_build_prompt(spec: dict) -> str:
    # Minimal mapping; keep your “data-test” selectors
    return (
        "Build a minimal-dark mobile UI with three swipeable screens.\n"
        "Selectors: data-test='overview|movers|news|gainer|loser|news-item'.\n"
        f"Spec JSON:\n{spec}\n"
    )
