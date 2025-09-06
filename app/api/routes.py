from fastapi import APIRouter
from pydantic import BaseModel
from app.models.schemas import MVPCriteria
from app.services.orchestrator import start_campaign
from fastapi.responses import HTMLResponse

router = APIRouter()

class CampaignIn(BaseModel):
    criteria: MVPCriteria

@router.post("/campaigns")
def create_campaign(payload: CampaignIn):
    run_id = start_campaign(payload.criteria)
    return {"status": "started", "run_id": run_id}

@router.get("/mock_preview", response_class=HTMLResponse)
def mock_preview():
    return """
<!doctype html>
<html>
  <body style="background:#0b0b0b;color:#eee;font-family:system-ui;margin:0;padding:24px">
    <div data-test="overview">
      <h1>Overview</h1>
      <div>ASX200: 7,500</div>
      <div>S&P500: 5,300</div>
      <div>A-VIX: 12.3</div>
      <div>PUT_CALL: 0.83</div>
    </div>

    <hr style="margin:24px 0;border-color:#333">

    <div data-test="movers" style="display:flex;gap:24px">
      <div>
        <h2>Gainers</h2>
        <div data-test="gainer">AAA +5.2%</div>
        <div data-test="gainer">BBB +3.9%</div>
        <div data-test="gainer">CCC +3.1%</div>
      </div>
      <div>
        <h2>Losers</h2>
        <div data-test="loser">DDD -4.8%</div>
        <div data-test="loser">EEE -3.6%</div>
        <div data-test="loser">FFF -2.7%</div>
      </div>
    </div>

    <hr style="margin:24px 0;border-color:#333">

    <div data-test="news">
      <div data-test="news-item">AU equities headline 1</div>
      <div data-test="news-item">AU equities headline 2</div>
      <div data-test="news-item">AU equities headline 3</div>
    </div>
  </body>
</html>
"""