"""generates tests from specs"""

import json
import os
import re
import time
from pathlib import Path

import requests

MODEL_NAME = "meta-llama/llama-4-scout-17b-16e-instruct"
SPEC_INPUT = "spec/spec_auto.md"
TESTS_OUTPUT = "tests/tests_auto.json"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


def load_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def extract_requirement_ids(spec_text):
    return re.findall(r"Requirement ID:\s*(FR\d+)", spec_text)


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
            {"role": "system", "content": "You produce strict JSON only."},
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


def parse_model_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    return json.loads(text)


def build_tests_prompt(spec_text):
    prompt = f"""
You are helping with requirements engineering for a mental health app called Wysa.

Task:
Read the following requirements specification and generate at least one validation test scenario for each requirement.

Return ONLY valid JSON in this exact structure:
{{
  "tests": [
    {{
      "test_id": "T_auto_1",
      "requirement_id": "FR1",
      "scenario": "short scenario description",
      "steps": [
        "step 1",
        "step 2",
        "step 3"
      ],
      "expected_result": "expected result text"
    }}
  ]
}}

Rules:
- Generate exactly one test per requirement
- Use test IDs T_auto_1 to T_auto_10
- Every test must reference a requirement_id that appears in the specification
- Every test must include scenario, steps, and expected_result
- steps must be a list with at least 3 clear steps
- expected_result must clearly reflect the requirement being validated
- Return JSON only
- Do not include markdown fences

Specification:
{spec_text}
""".strip()
    return prompt


def validate_tests(result, valid_requirement_ids):
    if "tests" not in result or not isinstance(result["tests"], list):
        raise ValueError("Output JSON must contain a 'tests' list.")

    tests = result["tests"]
    if len(tests) != len(valid_requirement_ids):
        raise ValueError(
            f"Expected {len(valid_requirement_ids)} tests, found {len(tests)}."
        )

    seen_test_ids = set()
    seen_req_ids = set()

    for t in tests:
        required_fields = ["test_id", "requirement_id", "scenario", "steps", "expected_result"]
        for field in required_fields:
            if field not in t:
                raise ValueError(f"Test missing required field: {field}")

        if t["test_id"] in seen_test_ids:
            raise ValueError(f"Duplicate test_id: {t['test_id']}")
        seen_test_ids.add(t["test_id"])

        req_id = t["requirement_id"]
        if req_id not in valid_requirement_ids:
            raise ValueError(f"Invalid requirement_id in tests: {req_id}")
        seen_req_ids.add(req_id)

        if not isinstance(t["steps"], list) or len(t["steps"]) < 3:
            raise ValueError(f"Test {t['test_id']} must have at least 3 steps.")

        if not isinstance(t["scenario"], str) or not t["scenario"].strip():
            raise ValueError(f"Test {t['test_id']} must have a non-empty scenario.")

        if not isinstance(t["expected_result"], str) or not t["expected_result"].strip():
            raise ValueError(f"Test {t['test_id']} must have a non-empty expected_result.")

    missing = set(valid_requirement_ids) - seen_req_ids
    if missing:
        raise ValueError(f"Missing tests for requirement IDs: {sorted(missing)}")


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    spec_text = load_text(SPEC_INPUT)
    requirement_ids = extract_requirement_ids(spec_text)

    if not requirement_ids:
        raise RuntimeError("No requirement IDs found in spec/spec_auto.md")

    prompt = build_tests_prompt(spec_text)

    print(f"Using model: {MODEL_NAME}")
    print(f"Found {len(requirement_ids)} requirements in spec")

    last_error = None
    for attempt in range(1, 6):
        print(f"Generating tests... attempt {attempt}/5")
        raw_output = call_groq(prompt)

        try:
            result = parse_model_json(raw_output)
            validate_tests(result, requirement_ids)
            save_json(TESTS_OUTPUT, result)
            print(f"Saved tests to {TESTS_OUTPUT}")
            return
        except Exception as e:
            last_error = e
            with open("tests/tests_auto_raw_output.txt", "w", encoding="utf-8") as f:
                f.write(raw_output)

            print(f"Test validation failed: {e}")
            prompt += f"""

Previous output failed validation with this error:
{str(e)}

Try again.
Return JSON only.
Generate exactly one test per requirement.
Use only valid requirement IDs from the specification.
"""
            time.sleep(2)

    raise RuntimeError(f"Test generation failed after 5 attempts. Last error: {last_error}")


if __name__ == "__main__":
    main()