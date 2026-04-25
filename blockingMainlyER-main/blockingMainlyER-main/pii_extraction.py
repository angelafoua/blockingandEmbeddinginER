import os
import requests
import json
import re

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = os.environ.get("OLLAMA_MODEL", "qwen3:4b")

def extract_pii(record_text):

    rec_id = record_text.split()[0]

    prompt = f"""
    Extract structured fields from this record:
    {record_text}

    Return JSON:
    {{
        "record_id": "",
        "first_name": "",
        "middle_name": "
        
        ",
        "last_name": "",
        "address": "",
        "phone": "",
        "ssn": "",
        "email": "",
        "dob": ""
    }}
    """

    response = requests.post(
        OLLAMA_URL,
        json={"model": MODEL_NAME, "prompt": prompt, "stream": False},
    )

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        # Bubble up a clearer error when the model isn’t reachable or errors.
        raise RuntimeError(f"Ollama request failed: {response.status_code} {response.text}") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(f"Ollama returned non-JSON: {response.text}") from exc

    text = payload.get("response")
    if not text:
        raise RuntimeError(f"Ollama response missing 'response' field: {payload}")

    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match:
        raise RuntimeError(f"Could not find JSON in model output: {text}")

    data = json.loads(match.group(0))

    if not data.get("record_id"):
        data["record_id"] = rec_id

    return data
