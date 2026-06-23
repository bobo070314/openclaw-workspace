"""
V2.10 Batch Skill Generator
Generates 15 high-frequency stub skills from create-skill template.
"""
import subprocess, sys, os
os.environ['PYTHONIOENCODING'] = 'utf-8'

SKILLS_DIR = r'D:\bobo\openclaw-foreign\workspace\skills'
CREATE_SKILL = os.path.join(SKILLS_DIR, 'create-skill', 'run.py')

HIGH_FREQ_SKILLS = [
    ('notion', 'Notion API integration — read/write pages, databases, and blocks'),
    ('linear', 'Linear project management — issues, cycles, projects'),
    ('wecomcli-msg', 'WeCom message sending — text, markdown, media messages'),
    ('wecomcli-contact', 'WeCom contact queries — users, departments, tags'),
    ('wecomcli-doc', 'WeCom document operations — create/edit wiki docs'),
    ('wecomcli-meeting', 'WeCom meeting management — schedule and list meetings'),
    ('wecomcli-schedule', 'WeCom calendar scheduling — events and reminders'),
    ('wecomcli-todo', 'WeCom todo management — tasks and checklists'),
    ('github-actions-generator', 'GitHub Actions workflow generation'),
    ('web-deploy-github', 'Deploy static sites to GitHub Pages'),
    ('typescript', 'TypeScript coding standards and patterns'),
    ('react', 'React component patterns and best practices'),
    ('zustand', 'Zustand state management patterns'),
    ('i18n', 'Internationalization and localization guide'),
    ('design-system', 'Design system tokens and component specs'),
]

def create_skill(name, desc):
    """Create a skill via create-skill CLI."""
    r = subprocess.run(
        [sys.executable, CREATE_SKILL, '--name', name, '--description', desc,
         '--dir', SKILLS_DIR, '--no-dry-run', '--json'],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        cwd=SKILLS_DIR,
    )
    status = 'OK' if r.returncode == 0 else 'ERR'
    return status, r.stdout.strip()[:200], r.stderr.strip()[:200]

results = []
for name, desc in HIGH_FREQ_SKILLS:
    skill_dir = os.path.join(SKILLS_DIR, name)
    if os.path.exists(skill_dir) and os.listdir(skill_dir):
        print(f'  ⏭ {name} — already exists')
        results.append((name, 'SKIP', '', ''))
        continue
    status, out, err = create_skill(name, desc)
    print(f'  {status} {name}')
    results.append((name, status, out, err))

ok = sum(1 for _, s, _, _ in results if s == 'OK')
skip = sum(1 for _, s, _, _ in results if s == 'SKIP')
fail = sum(1 for _, s, _, _ in results if s == 'ERR')

print(f'\n=== BATCH RESULT ===')
print(f'Created: {ok}, Skipped: {skip}, Failed: {fail}')

# Verify the count
existing = [d for d in os.listdir(SKILLS_DIR) 
            if os.path.isdir(os.path.join(SKILLS_DIR, d)) and 
            os.path.exists(os.path.join(SKILLS_DIR, d, 'SKILL.md'))]
print(f'Total skills with SKILL.md: {len(existing)}')
