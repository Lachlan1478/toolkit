# app/services/orchestrator.py
from loguru import logger
from app.services.llm_client import ideate, spec_writer, critic
from app.services.base44_client import base44_create, base44_update
from app.services.qa_runner import run as qa_run

_state = {}  # keep in-memory for now

def start_campaign(criteria):
    ideas = ideate(criteria)
    top = ideas[0]
    spec = spec_writer(criteria, top)

    app_id, preview_url = base44_create(spec)

    run_id = len(_state) + 1
    _state[run_id] = {
        "status": "building",
        "iterations": 0,
        "app_id": app_id,
        "preview_url": preview_url,
        "spec": spec,
        "criteria": criteria.model_dump(),
    }
    logger.info(f"Run {run_id} started; app_id={app_id}")

    # NOTE: when Base44 webhook is real, delete the next line and rely on /webhooks/builds/complete
    on_build_complete({"run_id": run_id, "app_id": app_id, "preview_url": preview_url})
    return run_id

def on_build_complete(payload: dict):
    run_id = payload.get("run_id")
    run = _state.get(run_id)
    if not run:
        return

    run["status"] = "built"

    # 🔎 Real QA: visit preview_url and assert data-test selectors from the spec's acceptance_tests
    report = qa_run(run["spec"]["acceptance_tests"], run["preview_url"])

    if report.passed:
        run["status"] = "passed"
        logger.info(f"Run {run_id} PASSED. Archiving.")
        return

    # ❌ Failing → request smallest change; iterate (still using stub critic)
    cr = critic(run["spec"], {"results": [], "passed": False})
    base44_update(run["app_id"], cr)
    run["iterations"] += 1
    logger.info(f"Run {run_id} iter={run['iterations']} updating app…")

    # NOTE: when Base44 webhook is real, remove this self-call. Now we simulate the next completion.
    on_build_complete({"run_id": run_id, "app_id": run["app_id"], "preview_url": run["preview_url"]})
