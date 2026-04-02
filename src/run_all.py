"""runs the full pipeline end-to-end"""

import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent

def run_step(script_path: str):
    full_path = ROOT / script_path
    print(f"\nRunning {script_path} ...")
    result = subprocess.run([sys.executable, str(full_path)], cwd=ROOT)
    if result.returncode != 0:
        raise RuntimeError(f"Step failed: {script_path}")

def main():
    print("Starting the automated pipeline...")
    run_step("src/01_collect_or_import.py")
    run_step("src/02_clean.py")
    run_step("src/05_personas_auto.py")
    run_step("src/06_spec_generate.py")
    run_step("src/07_tests_generate.py")
    print("\ncomputing automated metrics...")
    run_step("src/08_metrics.py")
    print("\nAutomated pipeline complete!")

if __name__ == "__main__":
    main()
