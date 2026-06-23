"""Batch 1: Full skill audit — check all extraDirs skills for run.py presence."""
from pathlib import Path

SKILLS_DIR = Path(r"D:\bobo\openclaw-foreign\skills")

live = []
stub = []
bare = []

for d in sorted(SKILLS_DIR.iterdir()):
    if not d.is_dir():
        continue
    if d.name.startswith("__"):
        continue
    if d.name.startswith("."):
        continue
    if d.name == "openclaw-skills":
        continue  # upstream template, not a skill
    
    has_runpy = (d / "run.py").exists()
    has_skillmd = (d / "SKILL.md").exists()
    has_meta = (d / "_meta.json").exists()
    
    entry = {
        "name": d.name,
        "path": str(d),
        "has_runpy": has_runpy,
        "has_skillmd": has_skillmd,
        "has_meta": has_meta,
    }
    
    if has_runpy:
        live.append(entry)
    elif has_skillmd:
        stub.append(entry)
    else:
        bare.append(entry)

print(f"=== FULL AUDIT RESULTS ===")
print(f"Live (run.py): {len(live)}")
print(f"Stub (SKILL.md only): {len(stub)}")
print(f"Bare (empty/no docs): {len(bare)}")
print(f"TOTAL: {len(live) + len(stub) + len(bare)}")

print(f"\n=== LIVE ({len(live)}) ===")
for s in live:
    print(f"  ✅ {s['name']}")

print(f"\n=== STUB ({len(stub)}) ===")
for s in stub:
    print(f"  ⏳ {s['name']}")

print(f"\n=== BARE ({len(bare)}) ===")
for s in bare:
    print(f"  ❌ {s['name']}")

print(f"\n=== TARGET SKILLS (Batch 1) ===")
targets = [
    "notion", "linear", "wecomcli-msg", "wecomcli-contact",
    "github-actions-generator", "web-deploy-github",
    "typescript", "react", "zustand", "design-system"
]
for t in targets:
    for s in live + stub + bare:
        if s["name"] == t:
            if s["has_runpy"]:
                print(f"  ✅ {t} — ALREADY LIVE (no action needed)")
            elif s["has_skillmd"]:
                print(f"  ⏳ {t} — STUB (needs run.py)")
            else:
                print(f"  ❌ {t} — BARE/MISSING (needs full scaffold)")
            break
    else:
        print(f"  ❓ {t} — NOT FOUND in skills dir")

# Write to JSON for later use
import json
out = {"live": live, "stub": stub, "bare": bare}
out_path = SKILLS_DIR / "__audit_batch1.json"
out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\nSaved audit to {out_path}")
