import json
from pathlib import Path

# load audit
audit_path = Path(r"D:\bobo\openclaw-foreign\workspace\v1.1-self-evo-factory\states\full_skill_audit.json")
data = json.loads(audit_path.read_text(encoding="utf-8"))

# separate categories
live = [s for s in data["skills"] if s.get("category") == "live"]
stub = [s for s in data["skills"] if s.get("category") == "stub"]
bare = [s for s in data["skills"] if s.get("category") == "bare"]

print(f"=== SUMMARY ===")
print(f"Live: {len(live)}")
print(f"Stub: {len(stub)}")
print(f"Bare: {len(bare)}")

# target priority list
targets = [
    "notion", "linear", "wecomcli-msg", "wecomcli-contact",
    "github-actions-generator", "web-deploy-github",
    "typescript", "react", "zustand", "design-system"
]

print(f"\n=== TARGET SKILLS LOCATIONS ===")
for t in targets:
    found = [s for s in stub + live if s["name"] == t]
    if found:
        f = found[0]
        print(f"  {t}: path={f['path']}, has_runpy={f.get('run_py')}, has_skillmd={f.get('skill_md')}")
    else:
        print(f"  {t}: NOT IN AUDIT (check bare/extraDirs)")
