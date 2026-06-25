import os
import sys

sys.path.insert(0, r"D:\bobo\projects\v1.1-self-evo-factory")

# 清缓存文件
cache_dir = r"D:\bobo\projects\v1.1-self-evo-factory\data\state"
if os.path.isdir(cache_dir):
    for f in os.listdir(cache_dir):
        if f.startswith("cache_"):
            os.remove(os.path.join(cache_dir, f))
            print(f"Cleared: {f}")

from core.core_orchestrator import CoreOrchestrator

orch = CoreOrchestrator()

r1 = orch.handle("帮我写一个React计数器组件，用useState hook")
print(f"ok={r1['ok']}, blocked={r1['blocked']}, cached={r1['cached']}")
print(f"steps: {r1['pipeline_steps']}")
print(f"result ({len(r1['result'])} chars):")
print("---BEGIN---")
print(r1["result"][:1200])
print("---END---")
