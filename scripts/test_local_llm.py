import json
import sys

sys.path.insert(0, r"D:\bobo\projects\v1.1-self-evo-factory")
from core.local_llm import chat, health

print(json.dumps(health(), ensure_ascii=False, indent=2))

# 测试有意义的查询
for q in ["你好", "写一个Python函数计算斐波那契数列"]:
    resp, src = chat(q)
    print(f"\n[{src}] Q: {q}")
    print(f"  A: {resp[:200]}")
