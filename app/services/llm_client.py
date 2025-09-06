import os, json, httpx

OPENAI_API_KEY = os.getenv("LLM_API_KEY")
MODEL = os.getenv("LLM_MODEL","gpt-4o-mini")  # choose yours

def _chat(prompt: str, system: str = "") -> str:
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    messages=[{"role":"system","content":system},{"role":"user","content":prompt}]
    r = httpx.post("https://api.openai.com/v1/chat/completions",
                   headers=headers, timeout=60,
                   json={"model": MODEL, "messages": messages, "response_format": {"type": "json_object"}})
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def ideate(criteria):
    sys = "You are a product ideator for AU finance micro-SaaS. Output JSON list."
    prompt = f"Propose 5 ideas that match: {criteria.model_dump_json()}. Include scores."
    return json.loads(_chat(prompt, sys))  # ensure it returns a list

def spec_writer(criteria, idea):
    sys = "You output ONLY valid JSON for an App spec object."
    prompt = f"Turn this into a minimal spec with data-test selectors and acceptance tests: {criteria.model_dump_json()} | idea={json.dumps(idea)}"
    return json.loads(_chat(prompt, sys))

def critic(spec, qa_report):
    sys = "You output ONLY valid JSON for a ChangeRequest."
    prompt = f"Spec: {json.dumps(spec)}\nQA: {json.dumps(qa_report)}\nReturn smallest ChangeRequest."
    return json.loads(_chat(prompt, sys))
