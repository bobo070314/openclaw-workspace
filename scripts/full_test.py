"""多场景全链路验证"""

import os
import sys

sys.path.insert(0, r"D:\bobo\projects\v1.1-self-evo-factory")
os.environ["DEEPSEEK_API_KEY"] = "sk-49f9170dc71648499300e2c193cb983e"
os.environ["DEEPSEEK_BASE_URL"] = "https://api.deepseek.com/v1"

import core.kairos_scheduler as ks

ks.KairosScheduler = type("S", (), {"health": lambda s: {}})()

from core.core_orchestrator import CoreOrchestrator

orch = CoreOrchestrator()
h = orch.health()
print(f"INIT: {h['initialized']} ({sum(1 for v in h['modules'].values() if v)}/9 modules)")
for k, v in h["modules"].items():
    print(f"  {k}: {'OK' if v else 'FAIL'}")

tests = [
    ("CODE", "写一个React倒计时组件，Tailwind CSS"),
    ("PRD", "写一个在线协作白板的产品需求文档"),
    ("OPS", "写一个Docker部署的nginx配置"),
    ("TEXT", "你好世界"),
]

for label, q in tests:
    r = orch.handle(q)
    ok = r["ok"]
    blocked = r["blocked"]
    steps = r["pipeline_steps"]
    out_len = len(r["result"])
    print(f"\n=== {label} === ok={ok} blocked={blocked} len={out_len}")
    print(f"  steps: {steps}")
    if ok and not blocked:
        print(f"  preview: {r['result'][:150]}...")
    else:
        print(f"  result: {r['result'][:300]}")
