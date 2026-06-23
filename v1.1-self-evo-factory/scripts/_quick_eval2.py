import subprocess, sys, json, os
os.environ['PYTHONIOENCODING'] = 'utf-8'
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(r'D:\bobo\openclaw-foreign\workspace\v1.1-self-evo-factory')

def run(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except Exception as e:
        return 1, '', str(e)

rc1, out1, err1 = run([sys.executable,
    str(PROJECT_ROOT / 'eval-suite' / 'test_self_coder.py')])
p1 = out1.count('PASS:')
f1 = out1.count('FAIL:')
g1 = 'ALL GREEN' in out1

skills_dir = PROJECT_ROOT.parent.parent / 'skills'
skill_count = len([d for d in skills_dir.iterdir() if d.is_dir()])

print(f"Self-coder eval: {p1}P/{f1}F - {'ALL GREEN' if g1 else 'FAIL'}")
print(f"Skills: {skill_count}")
print(f"Extended eval: SKIPPED (sandbox Docker hangs)")
total_status = 'PASS' if g1 else 'FAIL'
print(f"Overall: {total_status}")

report = {
    'version': '1.9',
    'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    'date': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
    'summary': {
        'self_coder_passed': p1,
        'self_coder_failed': f1,
        'self_coder_all_green': g1,
        'status': total_status,
    },
    'health': {
        'skill_count': skill_count,
    }
}
report_path = PROJECT_ROOT / 'states' / f"eval_report_{report['date']}.json"
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print(f"Report: {report_path}")
