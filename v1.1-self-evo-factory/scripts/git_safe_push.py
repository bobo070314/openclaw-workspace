#!/usr/bin/env python3
"""
git-safe-push.py — Safe git push wrapper for Windows PowerShell.
================================================================
Workaround for PowerShell's NativeCommandError: git outputs to stderr,
PowerShell treats any stderr as exit code 1 even on success.

Usage:
  python scripts/git-safe-push.py [remote] [branch]
"""

import subprocess
import sys
import os

os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def main():
    remote = sys.argv[1] if len(sys.argv) > 1 else "origin"
    branch = sys.argv[2] if len(sys.argv) > 2 else "master"

    result = subprocess.run(
        ["git", "push", remote, branch],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    # Combine stdout + stderr for display
    output = result.stdout + result.stderr

    # Real failure: connection refused, authentication, non-fast-forward
    failure_keywords = [
        "fatal:", "error:", "Permission denied",
        "non-fast-forward", "authentication failed",
        "could not read", "connection refused", "cannot lock ref",
    ]

    is_real_failure = any(kw.lower() in output.lower() for kw in failure_keywords)

    if is_real_failure:
        print(output.strip())
        return 1
    else:
        # "Everything up-to-date" or "master -> master" = success
        if "up-to-date" in output or "->" in output:
            print(output.strip())
            return 0
        else:
            # Unknown state — print and treat as warning, not failure
            print(output.strip())
            return 0  # Don't block on unknown state


if __name__ == "__main__":
    sys.exit(main())
