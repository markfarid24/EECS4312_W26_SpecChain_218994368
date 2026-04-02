"""computes metrics: coverage/traceability/ambiguity/testability"""

import json
import re
from pathlib import Path

REVIEWS_CLEAN = "data/reviews_clean.jsonl"
REVIEW_GROUPS = "data/review_groups_hybrid.json"
PERSONAS = "personas/personas_hybrid.json"
SPEC = "spec/spec_hybrid.md"
TESTS = "tests/tests_hybrid.json"
OUTPUT_FILE = "metrics/metrics_hybrid.json"

AMBIGUOUS_TERMS = {
    "easy", "better", "user-friendly", "fast", "quick", "simple",
    "clear", "responsive", "comprehensive", "relevant", "reliable",
    "welcoming", "comforting", "calming", "empathetic", "helpful"
}

def count_jsonl_lines(path):
    count = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def count_requirements(spec_text):
    return len(re.findall(r"Requirement ID:\s*", spec_text, flags=re.IGNORECASE))

def extract_requirements(spec_text):
    chunks = re.split(r"(?=Requirement ID:\s*)", spec_text, flags=re.IGNORECASE)
    extracted = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk.startswith("Requirement ID:"):
            continue
        req_id_match = re.search(r"Requirement ID:\s*([^\n]+)", chunk, flags=re.IGNORECASE)
        desc_match = re.search(r"(?:-|\u2022)\s*Description:\s*\[?(.*?)\]?\s*(?:\n|$)", chunk, flags=re.IGNORECASE)
        source_match = re.search(r"(?:-|\u2022)\s*Source Persona:\s*\[?(.*?)\]?\s*(?:\n|$)", chunk, flags=re.IGNORECASE)
        trace_match = re.search(r"(?:-|\u2022)\s*Traceability:\s*\[?(.*?)\]?\s*(?:\n|$)", chunk, flags=re.IGNORECASE)
        acc_match = re.search(r"(?:-|\u2022)\s*Acceptance Criteria:\s*\[?(.*?)\]?\s*(?:\n|$)", chunk, flags=re.IGNORECASE)
        if req_id_match and desc_match and source_match and trace_match and acc_match:
            extracted.append((
                req_id_match.group(1).strip(),
                desc_match.group(1).strip(),
                source_match.group(1).strip(),
                trace_match.group(1).strip(),
                acc_match.group(1).strip()
            ))

    return extracted

def has_ambiguous_language(text):
    lowered = text.lower()
    return any(term in lowered for term in AMBIGUOUS_TERMS)

def main():
    dataset_size = count_jsonl_lines(REVIEWS_CLEAN)
    groups_data = load_json(REVIEW_GROUPS)
    personas_data = load_json(PERSONAS)
    tests_data = load_json(TESTS)
    spec_text = load_text(SPEC)
    groups = groups_data.get("groups", [])
    personas = personas_data.get("personas", [])
    tests = tests_data.get("tests", [])
    persona_count = len(personas)
    requirements_count = count_requirements(spec_text)
    tests_count = len(tests)
    unique_review_ids = set()
    for g in groups:
        for rid in g.get("review_ids", []):
            unique_review_ids.add(rid)
    review_coverage_ratio = round(len(unique_review_ids) / dataset_size, 4) if dataset_size else 0.0
    group_to_persona_links = len(personas)
    persona_to_requirement_links = len(re.findall(r"Source Persona:", spec_text, flags=re.IGNORECASE))
    requirement_to_test_links = len({t["requirement_id"] for t in tests if "requirement_id" in t})
    traceability_links = group_to_persona_links + persona_to_requirement_links + requirement_to_test_links
    traced_requirements = persona_to_requirement_links
    traceability_ratio = round(traced_requirements / requirements_count, 4) if requirements_count else 0.0
    tested_requirements = len({t["requirement_id"] for t in tests if "requirement_id" in t})
    testability_rate = round(tested_requirements / requirements_count, 4) if requirements_count else 0.0
    extracted = extract_requirements(spec_text)
    ambiguous_count = 0
    for _, description, _, _, acceptance in extracted:
        if has_ambiguous_language(description) or has_ambiguous_language(acceptance):
            ambiguous_count += 1
    ambiguity_ratio = round(ambiguous_count / requirements_count, 4) if requirements_count else 0.0
    result = {
        "pipeline": "automated",
        "dataset_size": dataset_size,
        "persona_count": persona_count,
        "requirements_count": requirements_count,
        "tests_count": tests_count,
        "traceability_links": traceability_links,
        "review_coverage_ratio": review_coverage_ratio,
        "traceability_ratio": traceability_ratio,
        "testability_rate": testability_rate,
        "ambiguity_ratio": ambiguity_ratio
    }

    Path("metrics").mkdir(exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"Saved metrics to {OUTPUT_FILE}")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
