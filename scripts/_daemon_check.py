import json
import os
import subprocess
import sys

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("OPENCLAW_DRY_RUN", "1")

r = subprocess.run(
    [sys.executable, r"D:\bobo\openclaw-foreign\skills\subconscious-daemon\run.py", "--json"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=30,
)

d = json.loads(r.stdout)
print(f"Status: {d['status']} | Checks: {len(d['checks'])} | Alerts: {d['alerts']}")
for c in d["checks"]:
    flag = "ALERT" if c.get("alert") else "OK"
    print(f"  {c['type']}: {flag}")
