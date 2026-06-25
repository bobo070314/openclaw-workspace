import json
import sys

sys.path.insert(0, r"D:\bobo\projects\v1.1-self-evo-factory")
from core.core_orchestrator import CoreOrchestrator

orch = CoreOrchestrator()
r = orch.handle(
    "给iron-lobster-car.com加一个个人车源筛选页，"
    "要求筛选条件：品牌、价格区间、年份、里程，"
    "结果用卡片展示，配色保持黑白灰主色调"
)
print(json.dumps(r, indent=2, ensure_ascii=False, default=str))
