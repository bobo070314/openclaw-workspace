import subprocess, sys, json, os
os.environ['PYTHONIOENCODING'] = 'utf-8'
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(r'D:\bobo\openclaw-foreign\workspace\v1.1-self-evo-factory')

def run(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except Exception as e:
        return 1, '', str(e)

# Run self_coder eval
rc1, out1, err1 = run([sys.executable, str(PROJECT_ROOT/'eval-suite'/'test_self_coder.py')])
p1 = out1.count('PASS:')
f1 = out1.count('FAIL:')
g1 = 'ALL GREEN' in out1

# Run extended eval
rc2, out2, err2 = run([sys.executable, str(PROJECT_ROOT/'eval-suite'/'test_extended.py')])
p2 = out2.count('PASS:')
f2 = out2.count('FAIL:')
g2 = 'ALL GREEN' in out2

# Git
rc3, out3, _ = run(['git', '-C', str(PROJECT_ROOT.parent.parent), 'status', '--porcelain'])
dirty = len(out3.strip()) > 0

# Skills count
skills_dir = PROJECT_ROOT.parent.parent / 'skills'
skill_count = len([d for d in skills_dir.iterdir() if d.is_dir()])

status1 = 'GREEN' if g1 else 'RED'
status2 = 'GREEN' if g2 else 'RED'
print(f"Self-coder eval: {p1}P/{f1}F {status1}")
print(f"Extended eval:   {p2}P/{f2}F {status2}")
print(f"Git dirty: {dirty}")
print(f"Skills: {skill_count}")

report = {
    'version': '1.9',
    'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    'date': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
    'summary': {
        'total_tests': p1+f1+p2+f2,
        'passed': p1+p2,
        'failed': f1+f2,
        'all_green': g1 and g2,
        'status': 'PASS' if (g1 and g2) else 'FAIL'
    },
    'health': {
        'docker_running': False,
        'git_dirty': dirty,
        'skill_count': skill_count,
    }
}
report_path = PROJECT_ROOT / 'states' / f"eval_report_{report['date']}.json"
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print(f"Report saved: {report_path}")
print(f"Status: {report['summary']['status']}")
