"""裸模块导入测试——确认 Defenders 不杀"""

import sys

sys.path.insert(0, r"D:\bobo\projects\v1.1-self-evo-factory")

print("START")
tests = [
    ("yolo_classifier", "from core.yolo_classifier import classify"),
    ("coordinator_agent", "from core.coordinator_agent import CoordinatorAgent"),
    ("acceptance", "from core.acceptance import check_cso, check_vis, check_code"),
    ("anti_distillation", "from core.anti_distillation import AntiDistillation"),
    ("local_llm", "from core.local_llm import chat"),
    ("extractor", "from core.extractor import get_extractor"),
    ("memory_types", "from core.memory_types import MemoryClass, MemoryFragment"),
    ("cache_manager", "from core.cache_manager import CacheManager"),
]

for name, code in tests:
    try:
        exec(code)
        print(f"  {name}: OK")
    except Exception as e:
        print(f"  {name}: FAIL ({e})")

# 最后：尝试导入 core_orchestrator 但不实例化
print("\nImport core_orchestrator module...")
try:
    import core.core_orchestrator as co

    print(f"  OK (v{co.VERSION})")
    print(f"  LEGACY_PATCH_ENABLED: {co.LEGACY_PATCH_ENABLED}")
except Exception as e:
    print(f"  FAIL: {e}")

print("DONE")
