import os, json, httpx

OPENAI_API_KEY = os.getenv("LLM_API_KEY")
MODEL = os.getenv("LLM_MODEL","gpt-4o-mini")  # choose yours


# app/services/llm_client.py  (keep stubs at top)

def _openai_chat_json(system: str, user: str, model: str):
    key = os.getenv("LLM_API_KEY")
    headers = {"Authorization": f"Bearer {key}"}
    payload = {
        "model": os.getenv("LLM_MODEL", model),
        "messages": [{"role":"system","content":system},{"role":"user","content":user}],
        "response_format": {"type": "json_object"}
    }
    r = httpx.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def ideate(criteria):
    system = "You are a product ideator for AU finance micro-SaaS. Output ONLY valid JSON list."
    user = f"Propose 5 ideas matching this criteria. Include scores for pain, speed, monetization, AU diff. Criteria={criteria.model_dump_json()}"
    return json.loads(_openai_chat_json(system, user, "gpt-4o-mini"))

def spec_writer(criteria, idea):
    system = "You output ONLY valid JSON for an App spec object with acceptance_tests using data-test selectors."
    user = f"Turn this idea and criteria into a minimal spec: criteria={criteria.model_dump_json()} idea={json.dumps(idea)}"
    return json.loads(_openai_chat_json(system, user, "gpt-4o-mini"))

def critic(spec, qa_report):
    system = "You output ONLY valid JSON for a minimal ChangeRequest to pass next QA iteration."
    user = f"Spec={json.dumps(spec)} QA={json.dumps(qa_report)}"
    return json.loads(_openai_chat_json(system, user, "gpt-4o-mini"))

