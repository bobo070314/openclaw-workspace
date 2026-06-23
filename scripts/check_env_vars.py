import re
from pathlib import Path

skills = {
    "notion": "NOTION_API_KEY",
    "linear": "LINEAR_API_KEY",
    "tencent-docs": "TENCENT_DOCS_API_TOKEN",
    "wecomcli-msg": "WECOM_AGENTID",
}
base = Path("D:/bobo/openclaw-foreign/skills")
for name, expected_env in skills.items():
    f = base / name / "run.py"
    if not f.exists():
        print(f"{name}: MISSING")
        continue
    t = f.read_text(encoding="utf-8", errors="replace")
    env_vars = re.findall(r'os\.environ\["([^"]+)"\]', t)
    env_vars += re.findall(r"os\.environ\['([^']+)'\]", t)
    env_vars += re.findall(r'os\.getenv\("([^"]+)"\)', t)
    print(f"{name}: env vars used = {list(set(env_vars))}")
