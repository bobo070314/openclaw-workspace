import json
from pathlib import Path

skills = ['typescript','react','zustand','how-to-write-component','conventions','spa-routes','store-data-structures','i18n','testing','frontend-testing','e2e-cucumber-playwright','data-fetching-architecture','design-system','ux','microcopy']
base = Path(r"D:\bobo\openclaw-foreign\skills")
for s in skills:
    m = base / s / "_meta.json"
    if m.exists():
        d = json.load(open(m, encoding="utf-8"))
        lc = d.get("lifecycle", {})
        print(f"{s}: stub={lc.get('stub','?')}, status={lc.get('status','?')}")
