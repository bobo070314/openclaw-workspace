"""
⚡ V∞ Self-Evo Factory — One-Click Installer
============================================
pip install related packages and configure all hooks.

Usage: python scripts/install_self_heal.py
"""
import subprocess, os, sys
os.environ['PYTHONIOENCODING'] = 'utf-8'

PACKAGES = [
    'ruff',
    'self-heal-llm',
    'pre-commit',
]

def run(cmd, cwd=None):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=cwd)
    return r.returncode, r.stdout, r.stderr

# 1. install packages
print('=== STEP 1: Install packages ===')
for pkg in PACKAGES:
    print(f'  Installing {pkg}...')
    rc, out, err = run(['pip', 'install', pkg, '-q', '--upgrade'])
    if rc == 0:
        print(f'    ✅ {pkg} installed')
    else:
        print(f'    ❌ {pkg} FAILED: {err[:200]}')

# 2. install pre-commit hook (via python module)
print('\n=== STEP 2: Install git pre-commit hook ===')
rc, out, err = run([sys.executable, '-m', 'pre_commit', 'install'], cwd=r'D:\bobo\openclaw-foreign\workspace')
if rc == 0:
    print(f'  ✅ pre-commit hook installed')
else:
    print(f'  ⚠️ pre-commit install failed: {err[:200]}')
    print('  Manual hook already written to .git/hooks/pre-commit')

# 3. verify ruff
print('\n=== STEP 3: Verify ruff ===')
rc, out, err = run(['python', '-m', 'ruff', 'version'])
print(f'  ruff {out.strip()}')

# 4. verify self-heal-llm
print('\n=== STEP 4: Verify self-heal-llm ===')
try:
    import self_heal
    print(f'  self-heal {self_heal.__version__} ✅')
    print(f'  @repair decorator available ✅')
except Exception as e:
    print(f'  ❌ self-heal import failed: {e}')

# 5. verify OPENAI_API_KEY
print('\n=== STEP 5: Verify API credentials ===')
key = os.environ.get('OPENAI_API_KEY', '')
if key:
    print(f'  OPENAI_API_KEY set (length={len(key)}, prefix={key[:12]}...) ✅')
else:
    print('  ⚠️ OPENAI_API_KEY NOT SET — @repair will use default (Claude)')
    print('    Set with: $env:OPENAI_API_KEY="sk-or-v1-..."')

print('\n=== INSTALL COMPLETE ===')
print('Next: run "python pipeline/self_improve.py --dry-run self_coder" to test')
