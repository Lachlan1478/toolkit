from fastapi import FastAPI
from app.api.routes import router as api_router
from app.api.webhooks import router as webhook_router
from app.models.db import init_db

app = FastAPI(title="Toolkit Orchestrator", version="0.1.0")

@app.on_event("startup")
async def startup():
    init_db()

app.include_router(api_router, prefix="/api")
app.include_router(webhook_router, prefix="/webhooks")

@app.get("/")
def root():
    return {"ok": True, "service": "toolkit"}
