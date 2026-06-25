import os
import sys

sys.path.insert(0, r"D:\bobo\projects\v1.1-self-evo-factory")

# 清缓存
cache_dir = r"D:\bobo\projects\v1.1-self-evo-factory\data\cache"
for f in os.listdir(cache_dir):
    os.remove(os.path.join(cache_dir, f))

from core.core_orchestrator import CoreOrchestrator

orch = CoreOrchestrator()

# Monkey-patch _step_execute to log raw LLM output
_orig_execute = orch._step_execute


def _logged_execute(plan, steps):
    result = _orig_execute(plan, steps)
    if result and "Generated code blocked" not in str(result) and "WATERMARK" not in str(result):
        with open(r"D:\bobo\openclaw-foreign\workspace\scripts\last_llm_output.txt", "w", encoding="utf-8") as f:
            f.write(result)
    return result


orch._step_execute = _logged_execute

r1 = orch.handle("帮我写一个React计数器组件，用useState hook")
print(f"ok={r1['ok']}, blocked={r1['blocked']}, cached={r1['cached']}")
print(f"steps: {r1['pipeline_steps']}")
print(f"result ({len(r1['result'])} chars):")
print(r1["result"][:500])
