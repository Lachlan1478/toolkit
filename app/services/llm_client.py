import os, json, httpx

OPENAI_API_KEY = os.getenv("LLM_API_KEY")
MODEL = os.getenv("LLM_MODEL")  # choose yours


# app/services/llm_client.py  (keep stubs at top)

class LLMAuthError(RuntimeError): pass
class LLMFormatError(RuntimeError): pass

class LLMAuthError(RuntimeError): pass
class LLMHTTPError(RuntimeError): pass
class LLMFormatError(RuntimeError): pass

def _openai_chat_json(system: str, user: str, fallback_model: str = "gpt-4.1-mini") -> str:
    key = os.getenv("LLM_API_KEY", "").strip()
    if not key:
        raise LLMAuthError("LLM_API_KEY not set in environment")

    model = os.getenv("LLM_MODEL", fallback_model)

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system or "You output ONLY valid JSON."},
            {"role": "user", "content": user}
        ],
        # json_object mode is supported on 4.1/4.1-mini/4o/4o-mini
        "response_format": {"type": "json_object"},
        "temperature": 0
    }

    try:
        r = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
    except httpx.RequestError as e:
        # network/DNS timeout etc.
        raise LLMHTTPError(f"Network error calling OpenAI: {e!s}")

    # Give helpful errors instead of a bare 500
    if r.status_code == 401:
        raise LLMAuthError("Unauthorized (401): check LLM_API_KEY")
    if r.status_code == 404:
        raise LLMHTTPError(f"Model not found (404). model={model}")
    if r.status_code == 400:
        # Often carries details like “response_format not supported on this model”
        try:
            detail = r.json().get("error", {}).get("message", r.text)
        except Exception:
            detail = r.text
        raise LLMHTTPError(f"Bad request (400): {detail}")
    if r.status_code >= 300:
        # Surface server message to you
        try:
            detail = r.json().get("error", {}).get("message", r.text)
        except Exception:
            detail = r.text
        raise LLMHTTPError(f"OpenAI error {r.status_code}: {detail}")

    data = r.json()
    # Defensive parsing
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise LLMFormatError(f"Unexpected OpenAI response shape: {e}. Body={data}")

    if not isinstance(content, str) or not content.strip():
        raise LLMFormatError("Empty content from model")

    return content



def ideate(criteria):
    # Hard requirement: bare JSON ARRAY with items having {idea: str, score: number}
    system = "You are a product ideator. Output ONLY a JSON ARRAY (no object). Each item must be {\"idea\": string, \"score\": number}."
    user = f"Propose 5 app ideas matching this criteria: {criteria.model_dump_json()}"
    raw = _openai_chat_json(system, user)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise LLMFormatError(f"Ideate returned non-JSON: {e}")

    if not isinstance(data, list) or len(data) == 0:
        raise LLMFormatError("Ideate must return a non-empty JSON array")

    for i, item in enumerate(data):
        if not isinstance(item, dict) or "idea" not in item or "score" not in item:
            raise LLMFormatError(f"Ideate item {i} missing required keys")
    return data

def spec_writer(criteria, idea):
    system = "You output ONLY valid JSON for an App spec object with acceptance_tests using data-test selectors."
    user = f"Turn this idea and criteria into a minimal spec: criteria={criteria.model_dump_json()} idea={json.dumps(idea)}"
    return json.loads(_openai_chat_json(system, user, "gpt-4o-mini"))

def critic(spec, qa_report):
    system = "You output ONLY valid JSON for a minimal ChangeRequest to pass next QA iteration."
    user = f"Spec={json.dumps(spec)} QA={json.dumps(qa_report)}"
    return json.loads(_openai_chat_json(system, user, "gpt-4o-mini"))

