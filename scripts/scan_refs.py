#!/usr/bin/env python3
from pathlib import Path

code = Path(r"D:\bobo\projects\v1.1-self-evo-factory\core\evolution_engine.py").read_text(encoding="utf-8")
targets = [
    "memory_types",
    "extractor",
    "retriever_agent",
    "coordinator_rules",
    "coordinator_agent",
    "acceptance",
    "yolo_classifier",
    "cache_manager",
    "kairos_scheduler",
    "anti_distillation",
]

for t in targets:
    print(f"  {t}: {'FOUND' if t in code else 'NOT REFERENCED'}")

print("\n--- Natural extension points ---")
hooks = [
    "pre_action",
    "post_response",
    "agent_dispatch",
    "before_api_call",
    "after_api_call",
    "on_agent_start",
    "on_agent_complete",
    "validate_output",
    "pre_commit",
    "post_cycle",
]
for h in hooks:
    print(f"  {h}: {'FOUND' if h in code else 'NOT PRESENT'}")
