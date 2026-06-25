"""全链路缺口审计 —— 只测 Orchestrator 健康 + 不走 LLM 的纯链路测试"""

import os
import sys

sys.path.insert(0, r"D:\bobo\projects\v1.1-self-evo-factory")

# 先看各模块能不能单独导入
print("=== 1. IMPORT CHECKS ===")
checks = {
    "memory_types": "core.memory_types",
    "yolo_classifier": "core.yolo_classifier",
    "coordinator_agent": "core.coordinator_agent",
    "cache_manager": "core.cache_manager",
    "acceptance": "core.acceptance",
    "anti_distillation": "core.anti_distillation",
    "kairos_scheduler": "core.kairos_scheduler",
    "local_llm": "core.local_llm",
    "extractor": "core.extractor",
}

for name, mod in checks.items():
    try:
        __import__(mod)
        print(f"  {name}: OK")
    except Exception as e:
        print(f"  {name}: FAIL ({e})")

# 然后测 Orchestrator 初始化（但跳过容易卡住的步骤）
print("\n=== 2. ORCHESTRATOR INIT (fast) ===")
os.environ["DEEPSEEK_API_KEY"] = ""  # 确保不走 cloud

# 劫持进化引擎导入，避免卡 Defender
import core as core_pkg

core_pkg.evolution_engine = type("FakeEvo", (), {"on_event": lambda *a: None, "_apply_safe_patches": lambda *a: False})

# 劫持 Kairos（不需要网络）
core_pkg.kairos_scheduler = type("KairosScheduler", (), {})()

from core.core_orchestrator import CoreOrchestrator

try:
    orch = CoreOrchestrator()
    h = orch.health()
    print(f"  initialized: {h['initialized']}")
    for k, v in h["modules"].items():
        print(f"  {k}: {'OK' if v else 'FAIL'}")
    print(f"  init_log: {h['init_log']}")
except Exception as e:
    print(f"  INIT FAIL: {e}")
    import traceback

    traceback.print_exc()

print("\n=== 3. PIPELINE TEST (simple text) ===")
try:
    r = orch.handle("你好世界")
    print(f"  ok={r['ok']}, blocked={r['blocked']}")
    print(f"  steps: {r['pipeline_steps']}")
    print(f"  result: {r['result'][:200]}")
except Exception as e:
    print(f"  FAIL: {e}")
    import traceback

    traceback.print_exc()

print("\n=== 4. GAPS SUMMARY ===")
print("  DeepSeek KEY: NOT SET (cloud dead)")
print("  qwen: depends on ollama alive")
print("  evolution_engine: DISABLED (Defender seal)")
print("  kairos: needs config")
