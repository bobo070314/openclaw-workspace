"""Check git config and push to GitHub"""

import subprocess

# Check actual origin URL
r = subprocess.run(
    "git -C D:\\bobo\\openclaw-foreign remote get-url origin",
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    shell=True,
)
print(f"Origin URL: [{r.stdout.strip()}]")
if r.stderr:
    print(f"Err: {r.stderr[:200]}")

# Git config remote
r2 = subprocess.run(
    "git -C D:\\bobo\\openclaw-foreign config --list",
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    shell=True,
)
for line in r2.stdout.splitlines():
    if "remote" in line or "url" in line:
        print(f"  {line}")
