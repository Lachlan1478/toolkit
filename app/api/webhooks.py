from fastapi import APIRouter, Request
from app.services.orchestrator import on_build_complete

router = APIRouter()

@router.post("/builds/complete")
async def builds_complete(req: Request):
    payload = await req.json()
    on_build_complete(payload)
    return {"ok": True}
