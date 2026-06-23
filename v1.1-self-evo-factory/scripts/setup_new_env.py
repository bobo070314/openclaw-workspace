"""
V2.11 — setup_new_env.py
=========================
One-click environment setup for v1.1-self-evo-factory.
Handles Python deps, pre-commit, and environment validation.
"""

import subprocess
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def run(cmd, description="", timeout=60):
    """Run a command and print status."""
    print(f"  ▶ {description or ' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode == 0:
            print(f"    ✅ OK ({result.returncode})")
            return True, result.stdout
        else:
            print(f"    ⚠️ Exit {result.returncode}: {result.stderr[:200]}")
            return False, result.stderr
    except FileNotFoundError:
        print(f"    ❌ Command not found: {cmd[0]}")
        return False, f"{cmd[0]} not found"
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return False, str(e)


def check_python():
    """Verify Python version."""
    print("\n[1/5] Checking Python version...")
    v = sys.version_info
    if v.major >= 3 and v.minor >= 11:
        print(f"  ✅ Python {v.major}.{v.minor}.{v.micro}")
        return True
    else:
        print(f"  ❌ Python {v.major}.{v.minor} — need 3.11+")
        return False


def check_git():
    """Verify Git."""
    print("\n[2/5] Checking Git...")
    ok, out = run(["git", "--version"], "Git version")
    return ok


def check_docker():
    """Verify Docker (optional)."""
    print("\n[3/5] Checking Docker (optional)...")
    ok, _ = run(["docker", "--version"], "Docker version")
    if not ok:
        print("    ℹ️ Docker not found — sandbox-executor will use native fallback")
    return True  # Optional


def install_ruff():
    """Install/upgrade ruff."""
    print("\n[4/5] Installing Python tools...")
    tools = ["ruff", "pre-commit"]
    for tool in tools:
        ok, _ = run(
            [sys.executable, "-m", "pip", "install", "--upgrade", tool],
            f"pip install {tool}",
        )
        if not ok:
            print(f"    ⚠️ {tool} install failed — manual install may be needed")
    return True


def verify_project():
    """Run basic project validation."""
    print("\n[5/5] Verifying project...")

    required_dirs = ["pipeline", "eval-suite", "scripts", "states", "logs"]
    for d in required_dirs:
        exists = (PROJECT_ROOT / d).exists()
        print(f"  {'✅' if exists else '❌'} {d}/ {'exists' if exists else 'MISSING'}")

    required_files = [
        "pipeline/self_coder.py",
        "pipeline/self_improve.py",
    ]
    optional_files = [
        "pipeline/self_heal.py",  # may be pip-installed
        "eval-suite/run_all.py",   # regeneratable
    ]
    for f in required_files:
        exists = (PROJECT_ROOT / f).exists()
        print(f"  {'✅' if exists else '❌'} {f} {'exists' if exists else 'MISSING'}")
    for f in optional_files:
        exists = (PROJECT_ROOT / f).exists()
        print(f"  {'✅' if exists else '⚠️'} {f} {'exists' if exists else 'NOT FOUND (optional)'}")

    # Try importing self_heal
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from pipeline.self_heal import repair
        print(f"  ✅ self_heal.@repair importable")
    except Exception as e:
        print(f"  ❌ self_heal import failed: {e}")

    # Check OPENAI_API_KEY
    key = os.environ.get("OPENAI_API_KEY", "")
    if key:
        print(f"  ✅ OPENAI_API_KEY set ({len(key)} chars)")
    else:
        print(f"  ⚠️ OPENAI_API_KEY not set — @repair LLM won't work")


def main():
    print("=" * 50)
    print("V2.11 — New Environment Setup")
    print("=" * 50)

    checks = [
        ("Python 3.11+", check_python()),
        ("Git", check_git()),
        ("Docker", check_docker()),
        ("Python tools", install_ruff()),
    ]

    print()
    print("=" * 50)
    print("Verification")
    print("=" * 50)
    verify_project()

    print()
    failed = [name for name, ok in checks if not ok]
    if failed:
        print(f"⚠️ Setup complete with warnings: {', '.join(failed)}")
        return 1
    else:
        print("✅ Setup complete — all checks passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
