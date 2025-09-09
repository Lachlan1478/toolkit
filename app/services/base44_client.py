import os
from loguru import logger
from app.services.base44_bot import Base44Bot

BASE44_MODE = os.getenv("BASE44_MODE", "ui").lower()  # 'ui' or 'stub'

def base44_create(prompt_text: str):
    """
    Build via the UI (Playwright) and return (app_id, preview_url).
    Falls back to stub if BASE44_MODE != 'ui'.
    """
    if BASE44_MODE != "ui":
        logger.warning("[Base44] BASE44_MODE != ui; using stub create()")
        return base44_create_stub({"name": "unknown"})

    with Base44Bot() as bot:
        logger.info("[Base44] Starting UI build…")
        app_id, preview_url = bot.build_from_spec(prompt_text)
        logger.info(f"[Base44] UI build ok: app_id={app_id} preview={preview_url}")
        return app_id, preview_url

def base44_update(app_id: str, change_request: dict):
    """
    (Optional) Implement update via UI:
    - Navigate to app page
    - Paste change request
    - Click 'Update' and wait for completion
    """
    if BASE44_MODE != "ui":
        logger.warning("[Base44] BASE44_MODE != ui; using stub update()")
        return base44_update_stub(app_id, change_request)

    # Example placeholder: you will mirror build_from_spec but on the app page.
    # with Base44Bot() as bot:
    #     bot.ensure_logged_in()
    #     bot.page.goto(f"{BASE44_URL}/apps/{app_id}")
    #     # paste CR, click Update, wait for preview readiness
    #     return {"ok": True}

# ---- existing stubs ----
import uuid
def base44_create_stub(spec):
    app_id = "app_" + uuid.uuid4().hex[:8]
    preview_url = f"https://preview.base44.local/{app_id}"
    logger.info(f"[Base44] CREATE {app_id} (stub)")
    return app_id, preview_url

def base44_update_stub(app_id, change_request):
    logger.info(f"[Base44] UPDATE {app_id} (stub) reason={change_request.get('reason')}")
    return {"ok": True}
