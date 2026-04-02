"""checks required files/folders exist"""

from pathlib import Path

REQUIRED_FILES = [
    "data/reviews_raw.jsonl",
    "data/reviews_clean.jsonl",
    "data/dataset_metadata.json",
    "data/review_groups_manual.json",
    "data/review_groups_auto.json",
    "data/review_groups_hybrid.json",
    "personas/personas_manual.json",
    "personas/personas_auto.json",
    "personas/personas_hybrid.json",
    "spec/spec_manual.md",
    "spec/spec_auto.md",
    "spec/spec_hybrid.md",
    "tests/tests_manual.json",
    "tests/tests_auto.json",
    "tests/tests_hybrid.json",
    "metrics/metrics_manual.json",
    "metrics/metrics_auto.json",
    "metrics/metrics_hybrid.json",
    "metrics/metrics_summary.json",
    "src/00_validate_repo.py",
    "src/01_collect_or_import.py",
    "src/02_clean.py",
    "src/05_personas_auto.py",
    "src/06_spec_generate.py",
    "src/07_tests_generate.py",
    "src/08_metrics.py",
    "src/run_all.py",
    "README.md",
    "reflection/reflection.md",
]

ROOT = Path(__file__).resolve().parent.parent

def main():
    print("Checking repository structure...")
    missing = []
    for rel_path in REQUIRED_FILES:
        path = ROOT / rel_path
        if path.exists():
            print(f"{rel_path} found")
        else:
            print(f"{rel_path} MISSING")
            missing.append(rel_path)
    if missing:
        print("\nRepository validation incomplete")
        print("Missing files:")
        for m in missing:
            print(f"- {m}")
    else:
        print("\nRepository validation complete")

if __name__ == "__main__":
    main()