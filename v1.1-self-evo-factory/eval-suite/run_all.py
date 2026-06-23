#!/usr/bin/env python3
"""
V2.12 — eval-suite/run_all.py
==============================
Master test runner — runs all eval test files in eval-suite/.
"""
import subprocess
import sys
from pathlib import Path
import os

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

EVAL_DIR = Path(__file__).resolve().parent

def main():
    test_files = sorted(
        f for f in EVAL_DIR.glob("test_*.py")
        if f.name != "test_self_coder.py" or True  # include all
    )

    if not test_files:
        print("No test files found in", EVAL_DIR)
        return 1

    total_passed = 0
    total_failed = 0
    errors = []

    for tf in test_files:
        print(f"\n{'='*50}")
        print(f"Running: {tf.name}")
        print(f"{'='*50}")

        result = subprocess.run(
            [sys.executable, str(tf)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )

        stdout = result.stdout
        passed = stdout.count("PASS:") + stdout.count("PASS")
        failed = stdout.count("FAIL:") + stdout.count("FAIL")

        print(stdout[-500:] if len(stdout) > 500 else stdout)

        if result.returncode != 0:
            errors.append(f"{tf.name} (exit {result.returncode})")

        total_passed += passed
        total_failed += failed

    print(f"\n{'='*50}")
    print(f"FINAL: {total_passed}/{total_passed + total_failed} PASSED")
    if errors:
        print(f"ERRORS: {len(errors)}")
        for e in errors:
            print(f"  ❌ {e}")
    else:
        print("ALL GREEN ✅")
    print(f"{'='*50}")

    return 0 if not errors and total_failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
