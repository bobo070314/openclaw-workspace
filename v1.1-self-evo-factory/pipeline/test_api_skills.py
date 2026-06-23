#!/usr/bin/env python3
"""V3.1 API skills real-token integration test.

Tests 11 API-dependent skills. Defaults to dry-run with graceful degradation.

Token Vault: C:\\Users\\asus\\.openclaw\\api_tokens.json
  - auto-discovered on every run
  - never committed to git
  - env vars injected into subprocess only

Usage:
  python test_api_skills.py                 # dry-run all 11 (no tokens needed)
  python test_api_skills.py --live          # real API calls (reads vault)
  python test_api_skills.py --skill notion  # test single skill
  python test_api_skills.py --json          # JSON output
  python test_api_skills.py --vault PATH    # override vault path
  python test_api_skills.py --check-health  # check vault integrity
  python test_api_skills.py --version
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

__version__ = "0.2.0"
UTC = timezone.utc

SKILLS_DIR = Path("D:/bobo/openclaw-foreign/skills")
DEFAULT_VAULT = Path.home() / ".openclaw" / "api_tokens.json"


# ── Vault — single source of truth ──────────────────────
def load_vault(vault_path: Path = None) -> dict:
    """Load api_tokens.json from vault. Returns {} if missing or corrupt."""
    path = vault_path or DEFAULT_VAULT
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def inject_env(tokens: dict) -> dict:
    """Inject vault tokens into a subprocess-ready env dict."""
    env = os.environ.copy()
    env["GITHUB_TOKEN"] = tokens.get("github_token", "")
    env["NOTION_TOKEN"] = tokens.get("notion_token", "")
    env["LINEAR_API_KEY"] = tokens.get("linear_token", "")
    env["TENCENT_DOCS_API_KEY"] = tokens.get("tencent_docs_token", "")
    env["WECOM_CORPID"] = tokens.get("wecom_corpid", "")
    env["WECOM_CORPSECRET"] = tokens.get("wecom_corpsecret", "")
    env["WECOM_AGENTID"] = tokens.get("wecom_agentid", "")
    return env


def check_vault_health(vault_path: Path = None) -> dict:
    """Check vault integrity: file exists, JSON valid, known keys present."""
    path = vault_path or DEFAULT_VAULT
    problems = []

    if not path.exists():
        return {"ok": False, "error": f"Vault not found: {path}"}

    try:
        tokens = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"Vault JSON corrupt: {e}"}

    expected = [
        "github_token",
        "notion_token",
        "linear_token",
        "tencent_docs_token",
        "wecom_corpid",
        "wecom_corpsecret",
        "wecom_agentid",
    ]
    for key in expected:
        if key not in tokens:
            problems.append(f"Missing key: {key}")

    populated = sum(1 for k, v in tokens.items() if v)
    return {
        "ok": len(problems) == 0,
        "path": str(path),
        "keys_total": len(tokens),
        "keys_populated": populated,
        "keys_missing": [k for k in expected if k not in tokens],
        "problems": problems,
    }


# 11 API-dependent skills and their dry-run args
API_SKILLS = [
    ("github-actions-generator", ["--dry-run", "--json", "--template", "ci-node"]),
    ("web-deploy-github", ["--dry-run", "--json", "status", "--repo", "test"]),
    ("notion", ["--dry-run", "--json", "query", "--database", "test-db"]),
    ("linear", ["--dry-run", "--json", "issues", "--team", "test"]),
    ("tencent-docs", ["--dry-run", "--json", "list"]),
    ("wecomcli-msg", ["--dry-run", "--json", "send", "--to", "test", "--text", "hello-v3"]),
    ("wecomcli-contact", ["--dry-run", "--json", "search", "--name", "test"]),
    ("wecomcli-doc", ["--dry-run", "--json", "create", "--title", "test", "--type", "doc"]),
    (
        "wecomcli-meeting",
        [
            "--dry-run",
            "--json",
            "create",
            "--title",
            "test",
            "--start",
            "2026-06-23T22:00",
            "--end",
            "2026-06-23T22:30",
        ],
    ),
    ("wecomcli-schedule", ["--dry-run", "--json", "add", "--title", "test", "--time", "2026-06-23T22:00"]),
    ("wecomcli-todo", ["--dry-run", "--json", "add", "--title", "test"]),
]


def test_skill(skill_name: str, args: list[str], live: bool = False, vault_path: Path = None) -> dict:
    skill_path = SKILLS_DIR / skill_name / "run.py"
    if not skill_path.exists():
        return {"skill": skill_name, "success": False, "error": f"Skill not found: {skill_path}", "mode": "dry-run"}

    actual_args = [a for a in args if a != "--dry-run"] if live else args

    env = inject_env(load_vault(vault_path))
    mode = "live" if live else "dry-run"

    cmd = [sys.executable, str(skill_path)] + actual_args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace", env=env
        )
        stdout = result.stdout[:500]
        stderr = result.stderr[:500]
        success = result.returncode == 0
        return {
            "skill": skill_name,
            "success": success,
            "mode": mode,
            "exit_code": result.returncode,
            "stdout": stdout if success else None,
            "stderr": stderr if not success else None,
            "time": datetime.now(UTC).isoformat(),
        }
    except subprocess.TimeoutExpired:
        return {"skill": skill_name, "success": False, "error": "Timeout (30s)", "mode": mode}
    except Exception as e:
        return {"skill": skill_name, "success": False, "error": str(e)[:200], "mode": mode}


def run_all(live: bool = False, vault_path: Path = None) -> dict:
    results = []
    for skill, args in API_SKILLS:
        r = test_skill(skill, args, live, vault_path)
        results.append(r)
        status = "✅" if r["success"] else "❌"
        print(f"  {status} {skill}: {(r.get('stdout') or r.get('error') or '?')[:80]}")

    passed = sum(1 for r in results if r["success"])
    summary = {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "mode": "live" if live else "dry-run",
        "timestamp": datetime.now(UTC).isoformat(),
        "results": results,
    }
    return summary


def main():
    parser = argparse.ArgumentParser(description="V3.1 API Skills Integration Test")
    parser.add_argument("--live", action="store_true", help="Run with real API calls (reads vault)")
    parser.add_argument("--skill", help="Test a single skill")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--vault", help="Override vault path (default: ~/.openclaw/api_tokens.json)")
    parser.add_argument("--check-health", action="store_true", help="Check vault integrity only")
    parser.add_argument("--version", action="store_true")

    args = parser.parse_args()

    if args.version:
        print(__version__)
        return

    vault_path = Path(args.vault) if args.vault else DEFAULT_VAULT

    if args.check_health:
        health = check_vault_health(vault_path)
        if args.json:
            print(json.dumps(health, indent=2))
        else:
            print(f"🔐 Vault: {health['path']}")
            print(f"   Status: {'OK' if health['ok'] else 'DEGRADED'}")
            print(f"   Keys: {health['keys_populated']}/{health['keys_total']} populated")
            if health.get("problems"):
                for p in health["problems"]:
                    print(f"   ⚠️  {p}")
            if health.get("error"):
                print(f"   ❌ {health['error']}")
        sys.exit(0 if health["ok"] else 1)

    print("\n🧪 V3.1 API Skills Integration Test")
    print(f"   Mode: {'LIVE (real API)' if args.live else 'dry-run'}")
    print(f"   Vault: {vault_path}")
    if args.live:
        vault = load_vault(vault_path)
        populated = sum(1 for v in vault.values() if v)
        print(f"   Tokens: {populated}/{len(vault)} populated")
    print(f"   Skills: {len(API_SKILLS)}\n")

    if args.skill:
        for skill_name, skill_args in API_SKILLS:
            if skill_name == args.skill:
                result = test_skill(skill_name, skill_args, args.live, vault_path)
                summary = {
                    "total": 1,
                    "passed": 1 if result["success"] else 0,
                    "failed": 0 if result["success"] else 1,
                    "mode": "live" if args.live else "dry-run",
                    "results": [result],
                }
                break
        else:
            print(f"❌ Unknown skill: {args.skill}")
            sys.exit(1)
    else:
        summary = run_all(args.live, vault_path)

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(f"\n📊 Summary: {summary['passed']}/{summary['total']} passed ({summary['mode']})")

    sys.exit(0 if summary["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
