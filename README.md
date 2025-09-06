# Toolkit (Autonomous LLM → Base44 → QA Loop)

## Quick start
1) `cp .env.example .env`
2) `docker-compose up --build`
3) Open the API docs at http://localhost:8000/docs

## Flow
POST /campaigns  -> creates MVP criteria & starts the loop
Base44 callback  -> POST /webhooks/builds/complete
Worker runs QA   -> passes? archive; fails? generate Change Request and iterate

## Notes
- All external calls (LLM, Base44) are stubbed so you can run locally out-of-the-box.
- Replace stubs in `services/llm_client.py` and `services/base44_client.py` to go live.
