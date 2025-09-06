from loguru import logger
from app.models.db import SessionLocal
from app.services.llm_client import ideate, spec_writer, critic
from app.services.base44_client import base44_create, base44_update
from app.services.qa_runner import run as qa_run

# in-memory store for simplicity
_state = {}

def start_campaign(criteria):
    # 1) ideate
    ideas = ideate(criteria)
    top = ideas[0]
    # 2) spec
    spec = spec_writer(criteria, top)
    # 3) build
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
    # simulate build completion callback
    on_build_complete({"run_id": run_id, "app_id": app_id, "preview_url": preview_url})
    return run_id

def on_build_complete(payload: dict):
    run_id = payload.get("run_id")
    run = _state.get(run_id)
    if not run:
        return
    run["status"] = "built"

    # Run real QA
    report = qa_run(run["spec"]["acceptance_tests"], run["preview_url"])

    if report.passed:
        run["status"] = "passed"
        logger.info(f"Run {run_id} PASSED. Archiving.")
        return

    cr = critic(run["spec"])  # swap to real LLM later
    base44_update(run["app_id"], cr)
    run["iterations"] += 1
    logger.info(f"Run {run_id} iter={run['iterations']} updating app…")
    # simulate another completion for now:
    on_build_complete({"run_id": run_id, "app_id": run["app_id"], "preview_url": run["preview_url"]})


    # create CR and update (iterate)
    cr = critic(run["spec"])
    base44_update(run["app_id"], cr)
    run["iterations"] += 1
    logger.info(f"Run {run_id} iter={run['iterations']} updating app…")
    # simulate another build completion -> now pass
    on_build_complete({"run_id": run_id, "app_id": run["app_id"], "preview_url": run["preview_url"]})
