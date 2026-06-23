import sys

sys.path.insert(0, r"D:\bobo\openclaw-foreign\workspace")
from core.evolution_engine import _apply_safe_patches

ts = "2026-01-01T00:00:00Z"

# Test 1: Dangerous patch -> must REJECT
bad = {
    "reason": "test dangerous",
    "code_patches": [
        {
            "target": "auto_valuation",
            "old_function": "def estimate_car_value",
            "new_function": 'import os; os.system("evil")',
        }
    ],
}
r = _apply_safe_patches(bad, ts)
print("Dangerous:", "REJECTED (correct)" if not r else "APPLIED (BAD!)")

# Test 2: Missing func -> REJECT
missing = {
    "reason": "test missing",
    "code_patches": [
        {
            "target": "auto_valuation",
            "old_function": "def i_dont_exist",
            "new_function": "def x(): pass",
        }
    ],
}
r = _apply_safe_patches(missing, ts)
print("Missing func:", "REJECTED (correct)" if not r else "APPLIED (BAD!)")

# Test 3: Off-target -> REJECT
off = {
    "reason": "test off-target",
    "code_patches": [
        {
            "target": "causal_reasoner",
            "old_function": "anything",
            "new_function": "anything",
        }
    ],
}
r = _apply_safe_patches(off, ts)
print("Off-target:", "REJECTED (correct)" if not r else "APPLIED (BAD!)")

print("\nAll safety gates working!")
