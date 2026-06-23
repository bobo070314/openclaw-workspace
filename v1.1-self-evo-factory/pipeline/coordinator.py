#!/usr/bin/env python3.
"""V3.0 Coordinator — Parallel multi-agent step scheduler.

Couples with Planner output, runs steps via thread pool respecting
DAG dependencies, with @repair-style retry on failure.

Usage:
  python coordinator.py --plan "deploy and audit"
  python coordinator.py --steps '[{"action":"security-audit","params":{},"depends_on":[]}]'
  python coordinator.py --plan "发布版本" --dry-run
"""

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List

SKILLS_DIR = Path(r"D:\bobo\openclaw-foreign\skills")


def _handle_std_flags(cmd: List[str], extra_args: List[str]) -> List[str]:
    """Hack: insert --version/--json/--dry-run before subcommands for v0.2 skills."""
    # Most 0.2.0 skills want flags before subcommand
    flags = []
    remainder = []
    for a in extra_args:
        if a.startswith("--"):
            flags.append(a)
        else:
            remainder.append(a)
    return cmd + flags + remainder


def exec_skill(action: str, params: dict, extra_flags: list[str] | None = None) -> Dict[str, Any]:
    """Execute a skill run.py with retry (max 2)."""
    skill_path = SKILLS_DIR / action / "run.py"
    if not skill_path.exists():
        return {"skill": action, "success": False, "error": f"Skill {action} not found"}

    base_cmd = [sys.executable, str(skill_path)]
    extra_flags = extra_flags or []

    # Add param flags
    for key, value in params.items():
        if isinstance(value, bool):
            if value:
                extra_flags.append(f"--{key}")
        else:
            extra_flags.extend([f"--{key}", str(value)])

    cmd = _handle_std_flags(base_cmd, extra_flags)

    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
                cwd=str(skill_path.parent),
            )

            output = result.stdout.strip() or result.stderr.strip() or ""

            if result.returncode == 0:
                try:
                    data = json.loads(output)
                    return {"skill": action, "success": True, "data": data, "attempts": attempt + 1}
                except json.JSONDecodeError:
                    return {"skill": action, "success": True, "data": output[:500], "attempts": attempt + 1}

            # Non-fatal exit: vulnerability found, etc.
            if any(kw in output.lower() for kw in ["vulnerabilit", "audit report", "found", "warn"]):
                return {
                    "skill": action,
                    "success": True,
                    "data": output[:500],
                    "attempts": attempt + 1,
                    "note": "non-fatal exit",
                }

            if attempt < max_retries:
                print(f"  ⚠️ {action} attempt {attempt + 1} failed, retrying...")
                continue
            return {"skill": action, "success": False, "error": output[:300], "attempts": attempt + 1}

        except subprocess.TimeoutExpired:
            if attempt < max_retries:
                continue
            return {"skill": action, "success": False, "error": "Timeout(60s)", "attempts": attempt + 1}
        except Exception as e:
            if attempt < max_retries:
                continue
            return {"skill": action, "success": False, "error": str(e), "attempts": attempt + 1}

    return {"skill": action, "success": False, "error": "Max retries", "attempts": max_retries + 1}


def topological_sort(steps: List[dict]) -> List[str]:
    """Kahn's algorithm: steps → ordered action names."""
    in_degree: Dict[str, int] = {}
    graph: Dict[str, list] = {}
    all_actions = {s["action"] for s in steps}

    for s in steps:
        a = s["action"]
        if a not in in_degree:
            in_degree[a] = 0
            graph[a] = []
        for dep in s.get("depends_on", []):
            if dep not in graph:
                graph[dep] = []
                in_degree[dep] = 0
            graph[dep].append(a)
            in_degree[a] = in_degree.get(a, 0) + 1

    q = [a for a in in_degree if in_degree[a] == 0]
    order = []
    while q:
        node = q.pop(0)
        if node in all_actions:
            order.append(node)
        for child in graph.get(node, []):
            in_degree[child] -= 1
            if in_degree[child] == 0:
                q.append(child)
    return order


def run_pipeline(
    steps: List[dict],
    dry_run: bool = False,
    max_workers: int = 4,
) -> dict:
    """Execute steps in dependency-aware parallel batches."""
    order = topological_sort(steps)
    print(f"Execution order: {' → '.join(order) if order else '(none)'}\n")

    if dry_run:
        for i, action in enumerate(order):
            step = next((s for s in steps if s["action"] == action), {})
            print(f"  [DRY-RUN] {i + 1}. {action}")
        return {"total": len(order), "passed": len(order), "failed": 0, "results": {}, "dry_run": True}

    # Build batches: steps with same in-degree can run in parallel
    results: Dict[str, dict] = {}
    completed: set = set()
    remaining = {s["action"]: s for s in steps}

    while remaining:
        # Collect ready actions (all deps completed)
        ready = [
            (action, step)
            for action, step in remaining.items()
            if all(d in completed for d in step.get("depends_on", []))
        ]

        if not ready:
            # Deadlock: run remaining sequentially
            print("  ⚠️  Possible dependency deadlock, running remaining sequentially")
            for action, step in remaining.items():
                extra = ["--json", "--dry-run"] if dry_run else ["--json"]
                results[action] = exec_skill(action, step.get("params", {}), extra)
                completed.add(action)
            break

        # Parallel batch
        with ThreadPoolExecutor(max_workers=min(max_workers, len(ready))) as pool:
            futures = {}
            for action, step in ready:
                extra = ["--json", "--dry-run"] if dry_run else ["--json"]
                f = pool.submit(exec_skill, action, step.get("params", {}), extra)
                futures[f] = action

            for future in as_completed(futures):
                action = futures[future]
                result = future.result()
                results[action] = result
                completed.add(action)
                del remaining[action]

                status = "✅" if result.get("success") else "❌"
                attempts = f" (attempts: {result.get('attempts', 1)})" if result.get("attempts", 1) > 1 else ""
                err = result.get("error", "")[:80]
                note = result.get("note", "")
                extra_info = f" — {err}" if err else f" {note}" if note else ""
                print(f"  {status} {action}{attempts}{extra_info}")

    passed = sum(1 for r in results.values() if r.get("success"))
    total = len(results)
    return {"total": total, "passed": passed, "failed": total - passed, "results": results}


# ----------------------------------------------------------------
# CLI
# ----------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="V3.0 Coordinator — parallel multi-agent scheduler")
    parser.add_argument("--plan", help="Natural language goal (uses Planner)")
    parser.add_argument("--steps", help="JSON array of steps")
    parser.add_argument("--max-workers", type=int, default=4, help="Parallel workers")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--json", action="store_true", help="JSON output")

    args = parser.parse_args()
    steps = []

    if args.steps:
        steps = json.loads(args.steps)
    elif args.plan:
        # Import planner lazily
        sys.path.insert(0, str(Path(__file__).parent))
        from planner import Planner  # noqa: E402

        p = Planner()
        plan_steps = p.plan(args.plan)
        steps = p.to_dict(plan_steps)
        print(f"Planned {len(steps)} steps: {[s['action'] for s in steps]}\n")
    else:
        # Demo pipeline
        steps = [
            {"action": "security-audit", "params": {"target": "."}, "depends_on": []},
            {"action": "code-navigator", "params": {"type": "function"}, "depends_on": []},
            {"action": "deployment-automation", "params": {"env": "dev"}, "depends_on": ["security-audit"]},
        ]
        print("No --plan/--steps provided. Using demo pipeline.\n")

    result = run_pipeline(steps, dry_run=args.dry_run, max_workers=args.max_workers)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"\n{'=' * 50}")
        print(f"Pipeline: {result['passed']}/{result['total']} passed")
        if result.get("dry_run"):
            print("[DRY RUN — no real execution]")

    return 0 if result["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
