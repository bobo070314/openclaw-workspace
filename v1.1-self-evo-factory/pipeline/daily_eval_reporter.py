#!/usr/bin/env python3
"""
V1.9 — Daily Eval Reporter
==========================
Runs full eval suite and outputs JSON report to states/.
Designed to be called by cron or heartbeat.
"""

import subprocess
import sys
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from pipeline.report_delivery import deliver_report

PROJECT_ROOT = Path(r'D:\bobo\openclaw-foreign\workspace\v1.1-self-evo-factory')
STATES_DIR = PROJECT_ROOT / 'states'
LOGS_DIR = PROJECT_ROOT / 'logs'

os.environ.setdefault('PYTHONIOENCODING', 'utf-8')


def safe_run(cmd, timeout=60):
    r = subprocess.run(
        cmd, capture_output=True, text=True,
        encoding='utf-8', errors='replace', timeout=timeout
    )
    return r.returncode, r.stdout, r.stderr


def run_eval_suite(suite_path: Path) -> dict:
    """Run one eval suite, return parsed stats."""
    rc, stdout, stderr = safe_run([sys.executable, str(suite_path)], timeout=60)
    passed = stdout.count('PASS:') + stdout.count('PASS')
    failed = stdout.count('FAIL:') + stdout.count('FAIL')
    all_green = 'ALL GREEN' in stdout or (failed == 0 and passed > 0)

    # Count individual test results
    tests = []
    for line in stdout.split('\n'):
        line = line.strip()
        if 'PASS:' in line:
            tests.append({'name': line.split('PASS:')[-1].strip(), 'result': 'pass'})
        elif 'FAIL:' in line:
            tests.append({'name': line.split('FAIL:')[-1].strip(), 'result': 'fail'})

    return {
        'exit_code': rc,
        'passed': passed,
        'failed': failed,
        'total': passed + failed,
        'all_green': all_green,
        'tests': tests,
        'suite': suite_path.name,
    }


def collect_system_health() -> dict:
    """Collect basic system health metrics."""
    health = {}

    # Check Docker
    rc, out, _ = safe_run(['docker', 'info'], timeout=10)
    health['docker_running'] = rc == 0

    # Check git status
    rc, out, _ = safe_run(
        ['git', '-C', str(PROJECT_ROOT.parent.parent), 'status', '--porcelain'],
        timeout=10
    )
    health['git_dirty'] = len(out.strip()) > 0

    # Skill count
    skills_dir = PROJECT_ROOT.parent.parent / 'skills'
    health['skill_count'] = len([d for d in skills_dir.iterdir() if d.is_dir()])

    # Pipeline files present
    pipeline_files = [
        'pipeline/self_coder.py',
        'pipeline/self_improve.py',
    ]
    health['pipeline_files'] = {
        f: (PROJECT_ROOT / f).exists() for f in pipeline_files
    }

    return health


def generate_report() -> dict:
    """Generate a full daily eval report."""
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    report = {
        'version': '1.9',
        'timestamp': timestamp,
        'date': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        'evals': [],
        'health': {},
        'summary': {},
    }

    # Run all eval suites
    eval_files = [
        PROJECT_ROOT / 'eval-suite' / 'test_self_coder.py',
        PROJECT_ROOT / 'eval-suite' / 'test_extended.py',
    ]

    for ef in eval_files:
        if ef.exists():
            try:
                result = run_eval_suite(ef)
                report['evals'].append(result)
            except Exception as e:
                report['evals'].append({
                    'suite': ef.name,
                    'error': str(e),
                })

    # Health check
    try:
        report['health'] = collect_system_health()
    except Exception as e:
        report['health'] = {'error': str(e)}

    # Summary
    total_passed = sum(e.get('passed', 0) for e in report['evals'])
    total_failed = sum(e.get('failed', 0) for e in report['evals'])
    all_green = all(e.get('all_green', False) for e in report['evals'])

    report['summary'] = {
        'total_tests': total_passed + total_failed,
        'passed': total_passed,
        'failed': total_failed,
        'all_green': all_green,
        'status': 'PASS' if all_green else 'FAIL',
    }

    return report


def save_report(report: dict):
    """Save report to states/ with date-stamped filename."""
    STATES_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    date_str = report['date']
    report_path = STATES_DIR / f'eval_report_{date_str}.json'
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')

    # Also write a daily log line
    log_path = LOGS_DIR / 'eval_history.jsonl'
    summary_line = {
        'date': date_str,
        'timestamp': report['timestamp'],
        **report['summary'],
    }
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(summary_line, ensure_ascii=False) + '\n')

    return report_path, log_path


def main():
    print("=" * 50)
    print("V1.9 Daily Eval Report")
    print("=" * 50)
    print()

    report = generate_report()

    # Print summary
    s = report['summary']
    print(f"Status: {s['status']}")
    print(f"Tests:  {s['passed']}/{s['total_tests']} passed, {s['failed']} failed")
    print()
    print(f"Docker: {'🟢 running' if report['health'].get('docker_running') else '🔴 stopped'}")
    print(f"Git:    {'dirty' if report['health'].get('git_dirty') else 'clean'}")
    print(f"Skills: {report['health'].get('skill_count', '?')}")
    print()

    # Save
    report_path, log_path = save_report(report)
    print(f"Report saved: {report_path}")
    print(f"Log appended: {log_path}")

    # Deliver to channels
    print()
    print("Delivery:")
    delivery_results = deliver_report(report)
    for channel, status in delivery_results.items():
        print(f"  {channel}: {status}")

    return 0 if report['summary']['all_green'] else 1


if __name__ == '__main__':
    sys.exit(main())
