"""generates structured specs from personas"""

import json
import os
import re
import time
from pathlib import Path

import requests

MODEL_NAME = "meta-llama/llama-4-scout-17b-16e-instruct"
PERSONAS_INPUT = "personas/personas_auto.json"
SPEC_OUTPUT = "spec/spec_auto.md"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def call_groq(prompt):
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set.")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "You produce strict text output only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }

    last_error = None
    for attempt in range(1, 6):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except requests.exceptions.HTTPError as e:
            last_error = e
            status = e.response.status_code if e.response is not None else None
            print(f"Groq HTTP error on attempt {attempt}/5: {status}")
            if status not in [429, 500, 502, 503, 504]:
                raise
            time.sleep(3)
        except requests.exceptions.RequestException as e:
            last_error = e
            print(f"Groq request error on attempt {attempt}/5: {e}")
            time.sleep(3)

    raise RuntimeError(f"Groq API failed after 5 attempts: {last_error}")


def build_spec_prompt(personas_json):
    prompt = f"""
You are helping with requirements engineering for a mental health app called Wysa.

Task:
Generate exactly 10 functional requirements from the personas below.

Each requirement must follow this exact 4-line format and wording:
Requirement ID: FR1
- Description: [requirement text]
- Source Persona: [exact persona name from input]
- Traceability: [Derived from review group A1]
- Acceptance Criteria: [Given ... When ... Then ...]

You must repeat that exact structure for FR1 through FR10.
Do not rename any field.
Do not omit brackets.
Do not use alternative labels.

Rules:
- Generate exactly 10 requirements
- Use IDs FR1 to FR10
- Each requirement must include one unique requirement ID
- Each requirement must describe observable system behavior
- Each requirement must reference a persona name from the input
- Each requirement must reference the review group of that persona
- Acceptance criteria must be testable
- Avoid vague words like easy, better, user-friendly, fast, intuitive unless measurable
- Return plain text only, no markdown code fences
- Do not use markdown fences.
- Do not add commentary before or after the requirements.

Personas:
{json.dumps(personas_json, ensure_ascii=False, indent=2)}
""".strip()
    return prompt


def validate_spec(text, personas_json):
    ids = re.findall(r"Requirement ID:\s*(FR\d+)", text)
    if len(ids) != 10:
        raise ValueError(f"Expected 10 requirements, found {len(ids)}")
    if ids != [f"FR{i}" for i in range(1, 11)]:
        raise ValueError("Requirements must be FR1 to FR10 in order.")

    persona_names = {p["name"] for p in personas_json["personas"]}
    source_personas = re.findall(r"- Source Persona:\s*(?:\[(.*?)\]|(.*))", text)
    source_personas = [a if a else b.strip() for a, b in source_personas]
    if len(source_personas) != 10:
        raise ValueError("Each requirement must include Source Persona.")
    for sp in source_personas:
        if sp not in persona_names:
            raise ValueError(f"Unknown persona referenced: {sp}")

    trace_lines = re.findall(r"- Traceability:\s*(?:\[(.*?)\]|(.*))", text)
    trace_lines = [a if a else b.strip() for a, b in trace_lines]
    if len(trace_lines) != 10:
        raise ValueError("Each requirement must include Traceability.")

    acceptance = re.findall(r"- Acceptance Criteria:\s*(?:\[(.*?)\]|(.*))", text)
    acceptance = [a if a else b.strip() for a, b in acceptance]
    if len(acceptance) != 10:
        raise ValueError("Each requirement must include Acceptance Criteria.")


def save_text(path, text):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    personas_json = load_json(PERSONAS_INPUT)
    prompt = build_spec_prompt(personas_json)

    print(f"Using model: {MODEL_NAME}")

    last_error = None
    for attempt in range(1, 6):
        print(f"Generating spec... attempt {attempt}/5")
        raw_output = call_groq(prompt)

        try:
            validate_spec(raw_output, personas_json)
            save_text(SPEC_OUTPUT, raw_output)
            print(f"Saved spec to {SPEC_OUTPUT}")
            return
        except Exception as e:
            last_error = e
            with open("spec/spec_auto_raw_output.txt", "w", encoding="utf-8") as f:
                f.write(raw_output)

            print(f"Spec validation failed: {e}")
            prompt += f"""

Previous output failed validation with this error:
{str(e)}

Try again.
Return plain text only.
Generate exactly 10 requirements in the required format.
"""
            time.sleep(2)

    raise RuntimeError(f"Spec generation failed after 5 attempts. Last error: {last_error}")


if __name__ == "__main__":
    main()