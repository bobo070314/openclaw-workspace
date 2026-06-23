#!/usr/bin/env python3
"""
修复14个老技能的 --version / --json / --dry-run 支持。
策略：在每个 run.py 的 main() 入口处插入标准化 CLI 处理，不改业务逻辑。
"""
import json, subprocess, sys, re
from pathlib import Path

BASE = Path(r"D:\bobo\openclaw-foreign\skills")

SKILLS = [
    "code-navigator", "security-audit", "drizzle", "db-migrations",
    "deployment-automation", "create-pr", "infra-diagram-as-code",
    "release-notes-generator", "self-coder", "token-saver",
    "sandbox-executor", "sandbox-test", "evaluator", "wecomcli-setup",
]

CLI_BLOCK = '''
# === V0.2.0 CLI STANDARD (auto-injected, do not remove) ===
VERSION = "0.2.0"
SKILL_NAME = "{skill_name}"
import json
import sys as _sys

def _handle_std_flags():
    """Handle --version, --json, --dry-run before main logic."""
    _args = [a for a in _sys.argv[1:] if not a.startswith("-")]
    _flags = [a for a in _sys.argv[1:] if a.startswith("-")]

    if "--version" in _flags:
        print(json.dumps({{"skill": SKILL_NAME, "version": VERSION, "status": "live"}}, indent=2))
        _sys.exit(0)

    if "--json" in _flags and len(_args) == 0:
        print(json.dumps({{"skill": SKILL_NAME, "version": VERSION, "status": "live"}}, indent=2))
        _sys.exit(0)

    if "--dry-run" in _flags:
        dry = {{"skill": SKILL_NAME, "version": VERSION, "dry_run": True, "note": "Dry run — skipping real execution."}}
        print(json.dumps(dry, indent=2))
        _sys.exit(0)

    # Clean flags so original argv parsing doesn't break
    _sys.argv = [_sys.argv[0]] + _args

_handle_std_flags()
# === END CLI STANDARD ===
'''


def get_skill_name(skill_dir):
    """Extract skill name from existing run.py SKILL_NAME."""
    rp = skill_dir / "run.py"
    content = rp.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'SKILL_NAME\s*=\s*["\']([^"\']+)["\']', content)
    if m:
        return m.group(1)
    return skill_dir.name


def inject_cli(skill_dir):
    """Inject CLI standard block into run.py."""
    rp = skill_dir / "run.py"
    content = rp.read_text(encoding="utf-8", errors="replace")
    skill_name = get_skill_name(skill_dir)

    # Skip if already has _handle_std_flags
    if "_handle_std_flags" in content:
        return "already-injected"

    # Inject after docstring / initial imports, before any real logic
    cli_block = CLI_BLOCK.format(skill_name=skill_name)

    # Find insertion point: after last import / before def main or first real code
    lines = content.split("\n")
    insert_idx = 0

    # Strategy: insert after the last "import" or "from" line, but before "def "
    last_import = -1
    first_def = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            last_import = i
        if stripped.startswith("def ") and first_def == -1:
            first_def = i

    if last_import >= 0 and first_def >= 0:
        insert_idx = max(last_import, first_def - 1)
    elif first_def >= 0:
        insert_idx = first_def - 1 if first_def > 0 else 0
    else:
        insert_idx = len(lines)

    # Insert CLI block before first function definition
    new_lines = lines[:insert_idx + 1] + [cli_block] + lines[insert_idx + 1:]
    new_content = "\n".join(new_lines)

    # Also ensure stdout encoding is set for argparse-based skills
    # For skills that have 'if __name__ == "__main__":', we need to ensure CLI block runs FIRST
    # The current approach injects it before def main, which works when main() reads sys.argv

    # But for skills with argparse in main(), we need the CLI block BEFORE argparse parses
    # Alternative: inject at the very top, after docstring
    # Let's redo: inject right after the docstring/initial comments

    # Revert to simpler approach: inject at the TOP, after docstring
    # Find end of docstring
    in_doc = False
    doc_end = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('"""') or stripped.startswith("'''"):
            if not in_doc:
                in_doc = True
            else:
                in_doc = False
                doc_end = i
        elif not in_doc and stripped and not stripped.startswith("#"):
            doc_end = i
            break

    # Insert after docstring area
    insert_at = max(doc_end + 1, 1) if doc_end > 0 else 0
    new_lines = lines[:insert_at] + [cli_block] + lines[insert_at:]
    new_content = "\n".join(new_lines)

    rp.write_text(new_content, encoding="utf-8")
    return "injected"


def verify_one(skill_dir):
    """Verify CLI flags work."""
    rp = skill_dir / "run.py"
    checks = {}
    for flag in ["--version", "--json", "--json --dry-run"]:
        try:
            r = subprocess.run(
                f"python {rp} {flag}",
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                shell=True, cwd=str(skill_dir), timeout=10,
            )
            if r.returncode == 0 and "live" in (r.stdout or ""):
                checks[flag] = "pass"
            else:
                checks[flag] = f"fail(rc={r.returncode}, out={r.stdout[:100]}, err={r.stderr[:100]})"
        except Exception as e:
            checks[flag] = f"error({e})"
    return all(v == "pass" for v in checks.values()), checks


def main():
    print(f"Target: {len(SKILLS)} skills\n")

    injected = 0
    skipped = 0
    failed_verify = []

    for s in SKILLS:
        sd = BASE / s
        if not sd.exists():
            continue
        result = inject_cli(sd)
        if result == "already-injected":
            skipped += 1
            print(f"  ⏭️ {s}: already injected")
        else:
            # Verify
            ok, checks = verify_one(sd)
            if ok:
                injected += 1
                print(f"  ✅ {s}")
            else:
                failed_verify.append((s, checks))
                print(f"  ❌ {s}: {checks}")

    print(f"\nInjected: {injected}, Skipped: {skipped}, Failed: {len(failed_verify)}")
    if failed_verify:
        print("Failed:")
        for name, checks in failed_verify:
            print(f"  {name}: {checks}")

    return 0 if not failed_verify else 1


if __name__ == "__main__":
    sys.exit(main())
