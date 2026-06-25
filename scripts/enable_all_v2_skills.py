import json

# 加载 openclaw.json
with open(r"D:\bobo\openclaw-foreign\openclaw.json", "r", encoding="utf-8-sig") as f:
    d = json.load(f)
ents = d["skills"]["entries"]

# 补上 24 个 v0.2.0 达标的 extraDirs 技能
v2_add = [
    "api-doc-generator",
    "auto-valuation",
    "auto_valuation",
    "causal-reasoner",
    "code-navigator",
    "config-diff",
    "docker-compose-gen",
    "evaluator",
    "infra-diagram-as-code",
    "lobe-agent-testing",
    "lobe-data-fetching",
    "log-analyzer",
    "mtunion-product-ai-guide",
    "n8n-code-review",
    "n8n-db-migrations",
    "owl-vision",
    "sandbox-executor",
    "sandbox-test",
    "security-audit",
    "self-coder",
    "site-doctor",
    "sql-optimizer",
    "subconscious-daemon",
    "token-saver",
]
# 4 个之前已加过的不要重复
already_in_workspace = [
    "github-actions-generator",
    "web-deploy-github",
    "release-notes-generator",
    "deployment-automation",
]
v2_add = [n for n in v2_add if n not in already_in_workspace]

added = []
for name in v2_add:
    if name not in ents:
        ents[name] = {"enabled": True}
        added.append(name)
        print(f"+ {name}")
    else:
        print(f"= {name} already in entries")

# 更新 openclaw.json
with open(r"D:\bobo\openclaw-foreign\openclaw.json", "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=2)

print(f"\nAdded {len(added)} skills to openclaw.json entries")
