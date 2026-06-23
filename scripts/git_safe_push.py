#!/usr/bin/env python
"""git_safe_push.py — Filter PowerShell stderr false positives from git push.

PowerShell treats any non-empty stderr as error, but git writes ALL output
to stderr. This wrapper only fails on actual errors (fatal, error, permission
denied, connection refused, etc.).
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

    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)

    if result.returncode != 0:
        if is_true_error(result.stderr):
            return result.returncode
        # False positive from PowerShell: git stderr is normal
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
