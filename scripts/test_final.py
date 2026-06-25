import json
import sys

sys.path.insert(0, r"D:\bobo\projects\v1.1-self-evo-factory")
from core.core_orchestrator import CoreOrchestrator

orch = CoreOrchestrator()
health = orch.health()
print("HEALTH:", json.dumps({k: v for k, v in health["modules"].items()}, ensure_ascii=False))

print("\n--- TEST: React计数器 ---")
r = orch.handle("帮我写一个React计数器组件，用useState hook")
print(f"ok={r['ok']}, blocked={r['blocked']}, cached={r['cached']}")
print(f"steps: {r['pipeline_steps']}")
print(f"result ({len(r['result'])} chars):")
print(r["result"][:600])
print("---")
