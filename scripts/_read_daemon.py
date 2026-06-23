import json
import sys
from pathlib import Path

d = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(f"Status: {d['status']} | Checks: {len(d['checks'])} | Alerts: {d['alerts']}")
for c in d["checks"]:
    flag = "ALERT" if c.get("alert") else "OK"
    print(f"  {c['type']}: {flag}")
