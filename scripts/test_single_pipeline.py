import sys

sys.path.insert(0, r"D:\bobo\projects\v1.1-self-evo-factory")
from core.core_orchestrator import CoreOrchestrator

orch = CoreOrchestrator()
health = orch.health()

print("=" * 60)
print("HEALTH CHECK")
print("=" * 60)
print(f"llm_engine: {health['modules'].get('llm_engine', 'NOT_IN_HEALTH')}")
print(f"Init log: {health['init_log']}")

print("\n" + "=" * 60)
print("SINGLE PIPELINE TEST")
print("=" * 60)

r1 = orch.handle("帮我写一个React计数器组件，用useState hook")
print(f"ok={r1['ok']}, blocked={r1['blocked']}, cached={r1['cached']}")
print(f"steps: {r1['pipeline_steps']}")
print(f"\nresult preview ({len(r1['result'])} chars):")
print(r1["result"][:500])
