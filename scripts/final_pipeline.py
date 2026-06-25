import os
import sys

# 手动注入刚 setx 的 key（当前进程还读不到）
os.environ["DEEPSEEK_API_KEY"] = "sk-49f9170dc71648499300e2c193cb983e"
os.environ["DEEPSEEK_BASE_URL"] = "https://api.deepseek.com/v1"

sys.path.insert(0, r"D:\bobo\projects\v1.1-self-evo-factory")
import core.core_orchestrator as co

# 劫持 Kairos
import core.kairos_scheduler as ks

ks.KairosScheduler = type("S", (), {"health": lambda s: {}})()

orch = co.CoreOrchestrator()
h = orch.health()
print(f"Initialized: {h['initialized']}")
print(f"STATS: {h['pipeline_stats']}")

# 真正跑一次：React计数器
print("\n=== RUN: React计数器 ===")
r = orch.handle("帮我写一个React计数器组件，用useState hook，Tailwind CSS样式")
print(f"ok={r['ok']}, blocked={r['blocked']}, cached={r['cached']}")
print(f"pipeline steps: {r['pipeline_steps']}")
print(f"output ({len(r['result'])} chars):")
print(r["result"][:800])
