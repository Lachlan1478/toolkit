import os, json, httpx

OPENAI_API_KEY = os.getenv("LLM_API_KEY")
MODEL = os.getenv("LLM_MODEL")  # choose yours

class LLMAuthError(RuntimeError): pass
class LLMHTTPError(RuntimeError): pass
class LLMFormatError(RuntimeError): pass


def _strip_fences(s: str) -> str:
    t = s.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        # drop first ```... line and trailing ``` line if present
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t

def _openai_chat_json(
    system: str,
    user: str,
    fallback_model: str = "gpt-4.1-mini",
    *,
    enforce_json_object: bool = False
) -> str:
    key = OPENAI_API_KEY
    model = (os.getenv("LLM_MODEL") or fallback_model).strip() or MODEL

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system or "You output ONLY valid JSON."},
            {"role": "user", "content": user},
        ],
        "temperature": 0,
    }
    if enforce_json_object:
        payload["response_format"] = {"type": "json_object"}  # requires 4.1/4o family

    print("payload:", payload)  # Debug print
    try:
        r = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )
    except httpx.RequestError as e:
        raise LLMHTTPError(f"Network error calling OpenAI: {e!s}")

    # Helpful errors
    if r.status_code == 401:
        raise LLMAuthError("Unauthorized (401): check LLM_API_KEY/OPENAI_API_KEY")
    if r.status_code == 404:
        raise LLMHTTPError(f"Model not found (404). model={model}")
    if r.status_code == 429:
        try:
            detail = r.json().get("error", {}).get("message", r.text)
        except Exception:
            detail = r.text
        raise LLMHTTPError(f"Rate limit (429): {detail}")
    if r.status_code == 400:
        try:
            detail = r.json().get("error", {}).get("message", r.text)
        except Exception:
            detail = r.text
        raise LLMHTTPError(f"Bad request (400): {detail}")
    if r.status_code >= 300:
        try:
            detail = r.json().get("error", {}).get("message", r.text)
        except Exception:
            detail = r.text
        raise LLMHTTPError(f"OpenAI error {r.status_code}: {detail}")

    try:
        data = r.json()
        content = data["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as e:
        raise LLMFormatError(f"Unexpected OpenAI response shape: {e}. Body={r.text}")

    if not isinstance(content, str) or not content.strip():
        raise LLMFormatError("Empty content from model")

    return content

def ideate(criteria):
    # Hard requirement: bare JSON ARRAY with items having {idea: str, score: number}
    system = (
        'You are a product ideator. Output ONLY a JSON ARRAY (no object). '
        'Each item must be {"idea": string, "score": number}.'
    )
    user = f"Propose 5 app ideas matching this criteria: {criteria.model_dump_json()}"
    raw = _openai_chat_json(system, user, enforce_json_object=False)  # ARRAY → no enforcement
    print("idea generation raw:", raw)  # Debug print
    try:
        data = json.loads(_strip_fences(raw))
    except json.JSONDecodeError as e:
        raise LLMFormatError(f"Ideate returned non-JSON: {e}")

    if not isinstance(data, list) or not data:
        raise LLMFormatError("Ideate must return a non-empty JSON array")

    for i, item in enumerate(data):
        if not isinstance(item, dict) or "idea" not in item or "score" not in item:
            raise LLMFormatError(f"Ideate item {i} missing required keys")
    return data

def spec_writer(criteria, idea):
    system = "You output ONLY valid JSON for an App spec object with acceptance_tests using data-test selectors."
    user = f"Turn this idea and criteria into a minimal spec: criteria={criteria.model_dump_json()} idea={json.dumps(idea)}"
    raw = _openai_chat_json(system, user, "gpt-4o-mini", enforce_json_object=True)  # OBJECT → enforce

    print("spec writer raw:", raw)  # Debug print
    return json.loads(_strip_fences(raw))

def critic(spec, qa_report):
    system = "You output ONLY valid JSON for a minimal ChangeRequest to pass next QA iteration."
    user = f"Spec={json.dumps(spec)} QA={json.dumps(qa_report)}"
    raw = _openai_chat_json(system, user, "gpt-4o-mini", enforce_json_object=True)  # OBJECT → enforce
    return json.loads(_strip_fences(raw))

