import json
import os

# ExtraDirs 中未启用的技能，筛选重要类别
extra_dir = r"D:\bobo\openclaw-foreign\skills"
extra = set(os.listdir(extra_dir))
with open(r"D:\bobo\openclaw-foreign\openclaw.json", "r", encoding="utf-8-sig") as f:
    d = json.load(f)
ents = set(d["skills"]["entries"].keys())
missing = extra - ents
# 过滤掉非技能目录（pycache, .json等）
filtered = [
    n for n in sorted(missing) if not n.startswith("_") and not n.startswith(".") and n.endswith(".py") == False
]
print(f"Missing extraDirs skills ({len(filtered)}):")
for n in filtered:
    print(f"  {n}")
print()
# 给这些技能分类
cats = {
    "安全审计": ["adversarial-guard", "security-audit", "causal-reasoner"],
    "推理/编码": ["self-coder", "evaluator", "site-doctor"],
    "API/工具": ["tavily-search", "summarize", "token-saver", "sandbox-executor", "infra-diagram-as-code"],
    "数据库/配置": ["sql-optimizer", "config-diff", "docker-compose-gen", "log-analyzer", "api-doc-generator"],
    "Agent/测试": ["lobe-agent-testing", "lobe-data-fetching", "n8n-code-review", "n8n-db-migrations"],
    "系统守护": ["subconscious-daemon", "system-governor", "self-improvement-agent", "owl-vision"],
    "前端/估值": ["auto-valuation", "auto_valuation", "dashboard.py"],
    "其他": ["code-navigator", "openclaw-skills", "qclaw-shared", "mtunion-product-ai-guide"],
}
for cat, items in cats.items():
    present = [n for n in items if n in filtered]
    if present:
        print(f"  [{cat}] {', '.join(present)}")
