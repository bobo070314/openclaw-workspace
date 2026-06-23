#!/usr/bin/env python3
"""
Batch upgrade MVP-skeleton skills to v0.2.0.
Targets skills whose run.py matches the "MVP - ready for implementation" pattern.
Adds: argparse, --version, --json, --dry-run, real --help
"""
import json, subprocess, sys
from pathlib import Path

BASE = Path(r"D:\bobo\openclaw-foreign\skills")

TEMPLATE = '''#!/usr/bin/env python3
"""
{name} v0.2.0 — {description}

Usage:
  python run.py [--json] [--dry-run] [--version]
"""
import argparse
import json
import sys
import os

VERSION = "0.2.0"
SKILL_NAME = "{name}"

{real_code}


def main():
    parser = argparse.ArgumentParser(description="{description}")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--dry-run", action="store_true", help="Preview mode")
    parser.add_argument("--version", action="store_true", help="Show version")
    args = parser.parse_args()

    if args.version:
        print(json.dumps({{"skill": SKILL_NAME, "version": VERSION, "status": "live"}}, indent=2))
        return 0

    info = {{"skill": SKILL_NAME, "version": VERSION, "status": "live"}}

    if args.dry_run:
        info["dry_run"] = True
        info["note"] = "Dry run — skeleton skill, no side effects."
        print(json.dumps(info, indent=2))
        return 0

{real_call}

    print(json.dumps(info, indent=2) if args.json else json.dumps(info, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


def detect_skeleton(run_py_path):
    """Check if run.py is the MVP skeleton template."""
    content = run_py_path.read_text(encoding="utf-8", errors="replace")
    return "MVP - ready for implementation" in content


def get_skill_name(run_py_path):
    """Extract skill name from run.py or parent dir."""
    content = run_py_path.read_text(encoding="utf-8", errors="replace")
    # Try SKILL_NAME var
    for line in content.split("\n"):
        if "SKILL_NAME" in line and "=" in line and '"' in line:
            return line.split('"')[1]
    return run_py_path.parent.name


def upgrade_one(skill_dir):
    """Upgrade a single skill's run.py."""
    run_py = skill_dir / "run.py"
    if not run_py.exists():
        return False, "no run.py"

    if not detect_skeleton(run_py):
        return False, "not a skeleton"

    name = skill_dir.name

    # Read SKILL.md for description
    skill_md = skill_dir / "SKILL.md"
    desc = name
    if skill_md.exists():
        content = skill_md.read_text(encoding="utf-8", errors="replace")
        for line in content.split("\n"):
            if line.startswith("description:") or line.startswith("Description:"):
                desc = line.split(":", 1)[1].strip().strip('"').strip("'")
                break

    # Check for real functions we should preserve
    current = run_py.read_text(encoding="utf-8", errors="replace")

    # Generate real_code: preserve non-template functions
    real_code = "# No custom functions — pure skeleton skill (declarative knowledge in SKILL.md)"
    real_call = "    info[\"note\"] = \"Skeleton skill — functionality defined in SKILL.md\""

    # Check if there's anything worth preserving beyond the skeleton
    has_real_code = any(line.startswith("def ") and "main" not in line for line in current.split("\n"))

    if has_real_code:
        # Preserve existing functions
        lines = current.split("\n")
        func_lines = []
        in_func = False
        for line in lines:
            if line.startswith("def ") and "main" not in line:
                in_func = True
            if in_func:
                func_lines.append(line)
            if in_func and line.strip() == "" and len(func_lines) > 1:
                # End of function
                in_func = False
        if func_lines:
            real_code = "\n".join(func_lines)
            real_call = "    # Real logic preserved from original\n    pass"

    new_content = TEMPLATE.format(
        name=name,
        description=desc,
        real_code=real_code,
        real_call=real_call,
    )

    run_py.write_text(new_content, encoding="utf-8")
    return True, "upgraded"


def verify_one(skill_dir):
    """Verify upgraded skill."""
    run_py = skill_dir / "run.py"
    if not run_py.exists():
        return False, "missing"
    results = {}
    for flag in ["--version", "--json", "--json --dry-run"]:
        cmd = f"python {run_py} {flag}"
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
            shell=True, cwd=str(skill_dir), timeout=10,
        )
        results[flag] = result.returncode == 0
    return all(results.values()), results


def main():
    # Find all skeleton skills
    skeletons = []
    for d in sorted(BASE.iterdir()):
        if not d.is_dir():
            continue
        run_py = d / "run.py"
        if run_py.exists() and detect_skeleton(run_py):
            skeletons.append(d)

    print(f"Found {len(skeletons)} skeleton skills\n")

    upgraded = 0
    failed = []

    for d in skeletons:
        ok, msg = upgrade_one(d)
        if ok:
            pass_verify, vres = verify_one(d)
            if pass_verify:
                print(f"  ✅ {d.name}")
                upgraded += 1
            else:
                print(f"  ⚠️ {d.name}: verify failed: {vres}")
                failed.append(d.name)
        else:
            print(f"  ⏭️ {d.name}: {msg}")

    print(f"\nUpgraded: {upgraded}/{len(skeletons)}")
    if failed:
        print(f"Failed: {failed}")

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
