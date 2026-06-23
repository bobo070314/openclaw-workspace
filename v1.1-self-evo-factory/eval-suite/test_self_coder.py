#!/usr/bin/env python3
"""
V1.1 Eval Suite — Self-Coder Test Runner
=========================================
Tests that the self-coder rule engine:
1. Can scan itself without crashing (no false SyntaxError)
2. Reports 0 errors on clean code
3. Correctly detects real issues on intentionally buggy code
4. Handles directory scanning
"""

import subprocess
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SELF_CODER = PROJECT_ROOT / 'pipeline' / 'self_coder.py'

# Ensure UTF-8 on Windows
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

def run_self_coder(target, extra_args=None):
    """Run self_coder.py and return (returncode, stdout, stderr)."""
    cmd = [sys.executable, str(SELF_CODER), '--rules', str(target)]
    if extra_args:
        cmd.extend(extra_args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=30,
    )
    return result.returncode, result.stdout, result.stderr


def test_01_self_scan():
    """Self-coder scans itself — should have 0 errors."""
    print("TEST 01: Self-scan (self_coder.py -> self_coder.py)")
    rc, stdout, stderr = run_self_coder(str(SELF_CODER))
    has_errors = '[ERR]' in stdout
    if has_errors:
        print(f"  FAIL: Found errors in self-scan")
        print(f"  stdout: {stdout[:300]}")
        return False
    print(f"  PASS: 0 errors (warnings OK)")
    return True


def test_02_buggy_code_detection():
    """Intentionally buggy code should be caught."""
    print("TEST 02: Buggy code detection")
    buggy_code = '''
import os
import subprocess

def danger():
    # BUG: hardcoded token
    password = "my-secret-password-12345"
    api_key = "sk-abc123def456"
    
    # BUG: os.system
    os.system("rm -rf /")
    
    # BUG: bare except
    try:
        something()
    except:
        pass
    
    # BUG: python3 on Windows
    subprocess.run(["python3", "-c", "print(1)"])
    
    # BUG: datetime.UTC
    from datetime import datetime
    t = datetime.UTC
'''
    # Write to temp file
    tmpfile = PROJECT_ROOT / 'logs' / '_test_buggy.py'
    tmpfile.parent.mkdir(parents=True, exist_ok=True)
    tmpfile.write_text(buggy_code, encoding='utf-8')

    rc, stdout, stderr = run_self_coder(str(tmpfile))
    
    # Should have errors
    has_errors = '[ERR]' in stdout
    error_count = stdout.count('[ERR]')
    
    if not has_errors:
        print("  FAIL: No errors detected in buggy code")
        print(f"  stdout: {stdout[:500]}")
        return False
    
    print(f"  PASS: {error_count} errors detected in buggy code")
    # Cleanup
    tmpfile.unlink()
    return True


def test_03_json_output():
    """JSON output mode should produce valid JSON."""
    print("TEST 03: JSON output mode")
    rc, stdout, stderr = run_self_coder(str(SELF_CODER), ['--json'])
    
    try:
        import json
        data = json.loads(stdout)
        assert isinstance(data, list), "Expected list"
        assert len(data) > 0, "Expected at least 1 file"
        assert 'file' in data[0], "Expected 'file' key"
        assert 'issues' in data[0], "Expected 'issues' key"
        print(f"  PASS: Valid JSON, {len(data)} file(s)")
        return True
    except (json.JSONDecodeError, AssertionError) as e:
        print(f"  FAIL: {e}")
        print(f"  stdout: {stdout[:300]}")
        return False


def test_04_directory_scan():
    """Directory scanning should work."""
    print("TEST 04: Directory scan")
    # Scan the pipeline directory
    pipeline_dir = PROJECT_ROOT / 'pipeline'
    rc, stdout, stderr = run_self_coder(str(pipeline_dir))
    
    # Should find at least self_coder.py
    if 'SUMMARY' not in stdout:
        print(f"  FAIL: No summary in output")
        print(f"  stdout: {stdout[:300]}")
        return False
    
    print(f"  PASS: Directory scan completed")
    return True


def test_05_nonexistent_file():
    """Non-existent file should report error gracefully."""
    print("TEST 05: Non-existent file handling")
    rc, stdout, stderr = run_self_coder(str(PROJECT_ROOT / 'logs' / '__nonexistent__.py'))
    
    if 'not found' in stdout.lower() or 'File not found' in stdout:
        print(f"  PASS: Graceful error for missing file")
        return True
    
    # Also acceptable: just an error exit code
    if rc != 0:
        print(f"  PASS: Non-zero exit code ({rc})")
        return True
    
    print(f"  FAIL: Should report error for missing file")
    print(f"  stdout: {stdout[:200]}")
    return False


# ─── Main ───────────────────────────────────────────────────────

def main():
    tests = [
        ('Self-scan', test_01_self_scan),
        ('Buggy detection', test_02_buggy_code_detection),
        ('JSON output', test_03_json_output),
        ('Directory scan', test_04_directory_scan),
        ('Missing file', test_05_nonexistent_file),
    ]

    print("=" * 50)
    print("V1.1 Eval Suite — Self-Coder Tests")
    print("=" * 50)
    print()

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            if test_fn():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  CRASH: {e}")
            failed += 1
        print()

    print("=" * 50)
    print(f"RESULTS: {passed}/{passed + failed} passed")
    if failed == 0:
        print("ALL GREEN!")
    else:
        print(f"{failed} test(s) FAILED")
    print("=" * 50)

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
