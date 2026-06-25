"""验证 orchestrator 端到端导入"""

import sys

sys.path.insert(0, r"D:\bobo\projects\v1.1-self-evo-factory")

# 验证 acceptance 正确导入方式
print("1. AcceptanceGate: ", end="")
try:
    from core.acceptance import AcceptanceGate

    print(
        f"OK (check_cso={hasattr(AcceptanceGate, 'check_cso')}, check_vis={hasattr(AcceptanceGate, 'check_vis')}, check_code={hasattr(AcceptanceGate, 'check_code')})"
    )
except Exception as e:
    print(f"FAIL: {e}")

# 验证 extractor
print("2. Extractor: ", end="")
try:
    import core.extractor as _ext

    print(f"OK (get_extractor={hasattr(_ext, 'get_extractor')})")
except Exception as e:
    print(f"FAIL: {e}")

# 直接测试 orchestrator 初始化（预先禁用 Kairos 和 legacy 的 Defender 触发）
print("3. Orchestrator init: ", end="")
import core.core_orchestrator as co

# 劫持 Kairos 避免网络初始化
import core.kairos_scheduler as ks

ks.KairosScheduler = type("S", (), {"health": lambda s: {}})()
co.LEGACY_PATCH_ENABLED = False
try:
    orch = co.CoreOrchestrator()
    h = orch.health()
    print(f"OK (initialized={h['initialized']})")
    for k, v in h["modules"].items():
        print(f"   {k}: {'OK' if v else 'FAIL'}")
except Exception as e:
    print(f"FAIL: {e}")
    import traceback

    traceback.print_exc()
