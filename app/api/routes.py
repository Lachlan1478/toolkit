from fastapi import APIRouter
from pydantic import BaseModel
from app.models.schemas import MVPCriteria
from app.services.orchestrator import start_campaign

router = APIRouter()

class CampaignIn(BaseModel):
    criteria: MVPCriteria

@router.post("/campaigns")
def create_campaign(payload: CampaignIn):
    run_id = start_campaign(payload.criteria)
    return {"status": "started", "run_id": run_id}
