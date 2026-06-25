import json

d = json.load(open(r"D:\bobo\openclaw-foreign\openclaw.json", "r", encoding="utf-8"))
m = d.get("models", {})
for k, v in m.items():
    if isinstance(v, dict):
        print(f"{k}: provider={v.get('provider', '?')} model={v.get('model', '?')}")
    else:
        print(f"{k}: {type(v).__name__}")
