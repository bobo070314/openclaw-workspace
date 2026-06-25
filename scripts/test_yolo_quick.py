import sys

sys.path.insert(0, r"D:\bobo\projects\v1.1-self-evo-factory")
from core.yolo_classifier import classify

tests = [
    "做一个律所官网，要求专业严谨，不要花哨",
    "rm -rf /",
    "SELECT * FROM users WHERE id = 1",
    "帮我写一段React组件",
]
for t in tests:
    result = classify(t)
    print(f"Input: {t[:60]}")
    if result["passed"]:
        print("  PASS")
    else:
        for f in result["failures"]:
            print(f"  BLOCKED: {f['id']} L{f['line']}: {f['message']}")
    print()
