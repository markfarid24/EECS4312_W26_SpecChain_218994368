"""automated persona generation pipeline"""

import json
import os
import random
import time
from pathlib import Path

import requests

MODEL_NAME = "meta-llama/llama-4-scout-17b-16e-instruct"
INPUT_FILE = "data/reviews_clean.jsonl"
OUTPUT_FILE = "data/review_groups_auto.json"
PROMPT_FILE = "prompts/prompt_auto.json"
PERSONAS_OUTPUT_FILE = "personas/personas_auto.json"
MAX_REVIEWS_FOR_GROUPING = 150
TARGET_GROUPS = 5
REVIEWS_PER_GROUP_MIN = 5
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def load_reviews(path):
    reviews = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                reviews.append(json.loads(line))
    return reviews

def build_prompt(review_items):
    review_lines = []
    for r in review_items:
        review_id = r.get("review_id", "")
        text = r.get("review_text", "")
        score = r.get("score", "")
        review_lines.append(f'- review_id: "{review_id}" | score: {score} | text: "{text}"')
    prompt = f"""
You are helping with requirements engineering analysis for a mental health app called Wysa.

Task:
Group the following app reviews into exactly {TARGET_GROUPS} meaningful review groups.
Each group must:
- represent a clear common theme or user situation
- contain at least {REVIEWS_PER_GROUP_MIN} review_ids
- contain no fewer than the minimum under any circumstance
Mandatory constraint:
- every group must have at least {REVIEWS_PER_GROUP_MIN} review_ids
- if a possible theme has too few reviews, merge it into the most similar larger theme
Return ONLY valid JSON in this exact structure:
{{
  "groups": [
    {{
      "group_id": "A1",
      "theme": "short theme here",
      "review_ids": ["id1", "id2"],
      "example_reviews": [
        "example text 1",
        "example text 2"
      ]
    }}
  ]
}}

Important rules:
- Output exactly {TARGET_GROUPS} groups
- Do not include markdown fences
- Do not invent review_ids
- Each review_id should appear in only one group if possible
- Prefer themes like anxiety support, depression recovery, companion-like conversation, pricing/paywall concerns, repetition/quality issues, sleep help, emotional support, etc., when justified by the data

Reviews:
{chr(10).join(review_lines)}
""".strip()
    return prompt

def call_groq(prompt):
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set. Please set it in your terminal before running.")
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

    response = requests.post(url, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    return content

def parse_model_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    return json.loads(text)

def validate_output(result, valid_ids):
    if "groups" not in result or not isinstance(result["groups"], list):
        raise ValueError("Output JSON must contain a 'groups' list.")
    if len(result["groups"]) != TARGET_GROUPS:
        raise ValueError(f"Expected exactly {TARGET_GROUPS} groups, got {len(result['groups'])}.")
    seen = set()
    for group in result["groups"]:
        if "group_id" not in group or "theme" not in group or "review_ids" not in group:
            raise ValueError("Each group must contain group_id, theme, and review_ids.")
        if len(group["review_ids"]) < REVIEWS_PER_GROUP_MIN:
            raise ValueError(
                f"Group {group.get('group_id')} has fewer than {REVIEWS_PER_GROUP_MIN} review_ids."
            )
        for rid in group["review_ids"]:
            if rid not in valid_ids:
                raise ValueError(f"Invalid review_id generated: {rid}")
            if rid in seen:
                pass
            seen.add(rid)
        if "example_reviews" not in group or len(group["example_reviews"]) < 2:
            raise ValueError(f"Group {group.get('group_id')} must include 2 example_reviews.")

def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
def build_persona_prompt(groups_json):
    prompt = f"""
You are helping with requirements engineering analysis for a mental health app called Wysa.
Task:
Using the review groups below, generate exactly one persona per review group.
Return ONLY valid JSON in this exact structure:
{{
  "personas": [
    {{
      "id": "AP1",
      "name": "short persona name",
      "description": "persona summary",
      "derived_from_group": "A1",
      "goals": ["goal 1", "goal 2", "goal 3"],
      "pain_points": ["pain point 1", "pain point 2", "pain point 3"],
      "context": ["context 1", "context 2"],
      "constraints": ["constraint 1", "constraint 2"],
      "evidence_reviews": ["review_id_1", "review_id_2"]
    }}
  ]
}}

Rules:
- Output exactly one persona per group
- Use persona IDs AP1, AP2, AP3, AP4, AP5
- derived_from_group must match the review group ID exactly
- evidence_reviews must use review_ids that appear in the corresponding group
- Do not include markdown fences
- Return JSON only
- Make the personas realistic, distinct, and grounded in the review-group themes
Review groups:
{json.dumps(groups_json, ensure_ascii=False, indent=2)}
""".strip()
    return prompt

def validate_personas(result, groups_json):
    if "personas" not in result or not isinstance(result["personas"], list):
        raise ValueError("Output JSON must contain a 'personas' list.")
    groups = groups_json["groups"]
    if len(result["personas"]) != len(groups):
        raise ValueError("Number of personas must equal number of groups.")
    valid_group_ids = {g["group_id"] for g in groups}
    group_to_reviews = {g["group_id"]: set(g["review_ids"]) for g in groups}
    seen_persona_ids = set()
    seen_group_refs = set()
    for p in result["personas"]:
        required = [
            "id", "name", "description", "derived_from_group",
            "goals", "pain_points", "context", "constraints", "evidence_reviews"
        ]
        for field in required:
            if field not in p:
                raise ValueError(f"Persona missing required field: {field}")
        if p["id"] in seen_persona_ids:
            raise ValueError(f"Duplicate persona id: {p['id']}")
        seen_persona_ids.add(p["id"])
        group_id = p["derived_from_group"]
        if group_id not in valid_group_ids:
            raise ValueError(f"Invalid derived_from_group: {group_id}")
        if group_id in seen_group_refs:
            raise ValueError(f"More than one persona derived from group {group_id}")
        seen_group_refs.add(group_id)

        if not isinstance(p["goals"], list) or len(p["goals"]) < 2:
            raise ValueError(f"Persona {p['id']} must have at least 2 goals.")
        if not isinstance(p["pain_points"], list) or len(p["pain_points"]) < 2:
            raise ValueError(f"Persona {p['id']} must have at least 2 pain points.")
        if not isinstance(p["context"], list) or len(p["context"]) < 1:
            raise ValueError(f"Persona {p['id']} must have context.")
        if not isinstance(p["constraints"], list) or len(p["constraints"]) < 1:
            raise ValueError(f"Persona {p['id']} must have constraints.")
        if not isinstance(p["evidence_reviews"], list) or len(p["evidence_reviews"]) < 2:
            raise ValueError(f"Persona {p['id']} must have at least 2 evidence reviews.")

        valid_reviews = group_to_reviews[group_id]
        for rid in p["evidence_reviews"]:
            if rid not in valid_reviews:
                raise ValueError(
                    f"Persona {p['id']} uses evidence review {rid} not found in group {group_id}."
                )
                
def main():
    reviews = load_reviews(INPUT_FILE)

    if len(reviews) < MAX_REVIEWS_FOR_GROUPING:
        sampled = reviews
    else:
        random.seed(4312)
        sampled = random.sample(reviews, MAX_REVIEWS_FOR_GROUPING)
    valid_ids = {r["review_id"] for r in sampled}
    prompt = build_prompt(sampled)
    save_json(PROMPT_FILE, {"model": MODEL_NAME, "prompt": prompt})
    print(f"Loaded {len(reviews)} cleaned reviews")
    print(f"Using {len(sampled)} reviews for automated grouping")
    print(f"Using model: {MODEL_NAME}")
    max_attempts = 5
    last_error = None
    for attempt in range(1, max_attempts + 1):
        print(f"Calling Groq API... attempt {attempt}/{max_attempts}")
        raw_output = call_groq(prompt)
        try:
            result = parse_model_json(raw_output)
            validate_output(result, valid_ids)
            save_json(OUTPUT_FILE, result)
            print(f"Saved grouped reviews to {OUTPUT_FILE}")
            print(f"Saved prompt to {PROMPT_FILE}")
            persona_prompt = build_persona_prompt(result)
            raw_persona_output = ""
            for persona_attempt in range(1, 6):
                print(f"Generating personas... attempt {persona_attempt}/5")
                raw_persona_output = call_groq(persona_prompt)
                try:
                    persona_result = parse_model_json(raw_persona_output)
                    validate_personas(persona_result, result)
                    save_json(PERSONAS_OUTPUT_FILE, persona_result)
                    print(f"Saved personas to {PERSONAS_OUTPUT_FILE}")
                    return
                except Exception as pe:
                    with open("personas/personas_auto_raw_output.txt", "w", encoding="utf-8") as f:
                        f.write(raw_persona_output)
                    print(f"Persona validation failed: {pe}")
                    persona_prompt += f"""

Previous output failed validation with this error:
{str(pe)}

Try again.
Return JSON only.
Generate exactly one persona per review group.
Use only valid group IDs and evidence review IDs from the groups.
"""
                    time.sleep(2)
            raise RuntimeError("Persona generation failed after 5 attempts.")
        except Exception as e:
            last_error = e
            with open("data/review_groups_auto_raw_output.txt", "w", encoding="utf-8") as f:
                f.write(raw_output)
            print(f"Validation failed: {e}")
            prompt += f"""
Your previous output failed validation with this error:
{str(e)}
Try again and fix it.
Rules:
- Return exactly {TARGET_GROUPS} groups
- Every group must contain at least {REVIEWS_PER_GROUP_MIN} review_ids
- Use only review_ids from the provided list
- Do not invent IDs
- Return JSON only
"""
            time.sleep(2)

    raise RuntimeError(
        f"Model output could not be parsed/validated after {max_attempts} attempts. "
        f"Last error: {last_error}"
    )

if __name__ == "__main__":
    main()
