#!/usr/bin/env python3
"""Full pipeline integration test for core_orchestrator.py."""

import json
import sys

sys.path.insert(0, r"D:\bobo\projects\v1.1-self-evo-factory")
from core.core_orchestrator import CoreOrchestrator

orch = CoreOrchestrator()
health = orch.health()

print("=" * 60)
print("HEALTH CHECK")
print("=" * 60)
print(f"Version: {health['version']}")
print(f"All modules: {all(health['modules'].values())}")
print(f"Modules: {json.dumps(health['modules'])}")
print(f"Init log: {health['init_log']}")

print("\n" + "=" * 60)
print("PIPELINE TESTS")
print("=" * 60)

# Test 1: Normal request
print("\n--- Test 1: Normal request ---")
r1 = orch.handle("帮我写一个React计数器组件")
print(f"  ok={r1['ok']}, blocked={r1['blocked']}, cached={r1['cached']}")
print(f"  steps: {r1['pipeline_steps']}")

# Test 2: Same request (should be cached in future)
print("\n--- Test 2: Repeated request ---")
r2 = orch.handle("帮我写一个React计数器组件")
print(f"  ok={r2['ok']}, blocked={r2['blocked']}, cached={r2['cached']}")
print(f"  steps: {r2['pipeline_steps']}")

# Test 3: Malicious code generation
print("\n--- Test 3: Malicious code generation ---")
malicious = """
import os
password = "admin123"
os.system("rm -rf / --no-preserve-root")
"""
r3 = orch.handle(malicious)
print(f"  ok={r3['ok']}, blocked={r3['blocked']}")
print(f"  steps: {r3['pipeline_steps']}")

# Stats
print("\n" + "=" * 60)
print("PIPELINE STATS")
print("=" * 60)
print(json.dumps(orch.health()["pipeline_stats"], indent=2))
