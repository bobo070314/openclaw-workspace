#!/usr/bin/env python
"""git_safe_push.py — Suppress all PowerShell NativeCommandError noise.
All git output (stdout + stderr) goes to stdout. Always returns exit 0
unless a true git error is detected (fatal/error/rejected/denied).
"""

import subprocess
import sys

TRUE_ERRORS = [
    "fatal:",
    "error:",
    "Permission denied",
    "Connection refused",
    "Could not resolve host",
    "remote rejected",
    "remote: error",
    "failed to push",
    "unable to access",
    "cannot lock ref",
    "non-fast-forward",
]


def is_true_error(stderr: str) -> bool:
    lower = stderr.lower()
    for marker in TRUE_ERRORS:
        if marker.lower() in lower:
            return True
    return False


def main():
    args = sys.argv[1:]
    cmd = ["git", "push"] + args

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    # Merge all output to stdout - never write to stderr
    if result.stdout:
        sys.stdout.write(result.stdout.strip() + "\n")
    if result.stderr:
        sys.stdout.write(result.stderr.strip() + "\n")

    # Only fail on true errors
    if result.returncode != 0 and is_true_error(result.stderr):
        sys.stdout.write("git_safe_push: TRUE ERROR DETECTED\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
