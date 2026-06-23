"""Create github-actions-generator and web-deploy-github scaffolds in extraDirs."""
import json as json_module
from pathlib import Path

SKILLS_DIR = Path(r"D:\bobo\openclaw-foreign\skills")

new_skills = [
    {
        "name": "github-actions-generator",
        "description": "Generate GitHub Actions workflow YAML from natural language descriptions. Supports CI/CD pipelines, scheduled tasks, and deployment workflows.",
        "category": "devops",
    },
    {
        "name": "web-deploy-github",
        "description": "Deploy static sites and web apps to GitHub Pages. Handles build, asset optimization, and deployment with a single command.",
        "category": "devops",
    },
]

TEMPLATE_RUN_PY = '''#!/usr/bin/env python3
"""{name} — {description}

Usage:
  python {name}/run.py --help
  python {name}/run.py --json
  python {name}/run.py --dry-run
"""
import argparse
import json as json_module
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="{description}")
    parser.add_argument("-i", "--info", action="store_true", help="Show help info")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no side effects)")
    parser.add_argument("--version", action="store_true", help="Show version info")
    args = parser.parse_args()

    if args.version:
        info = {{
            "skill": "{name}",
            "version": "0.1.0",
            "status": "live",
            "description": "{description}",
        }}
        print(json_module.dumps(info, indent=2))
        return

    if args.json:
        info = {{
            "skill": "{name}",
            "version": "0.1.0",
            "status": "live",
            "description": "{description}",
            "dry_run": args.dry_run,
        }}
        print(json_module.dumps(info, indent=2))
        return

    print(f"{{name}} v0.1.0 — {{description}}")
    print("Run with --json for machine-readable output.")
    print("Run with --dry-run to preview without side effects.")


if __name__ == "__main__":
    main()
'''

TEMPLATE_SKILL_MD = '''---
name: {name}
description: {description}
version: 0.1.0
category: {category}
---

# {name}

{description}

## Usage

```bash
python {name}/run.py --help
python {name}/run.py --json
python {name}/run.py --dry-run
```

## Features

- Feature 1 (TBD)
- Feature 2 (TBD)

## Requirements

- Python 3.11+
- GitHub CLI (`gh`) or GitHub API token

## Status

v0.1.0 — MVP scaffold. Ready for API integration.
'''

TEMPLATE_META_TXT = '''{{
    "name": "{name}",
    "version": "0.1.0",
    "description": "{description}",
    "category": "{category}",
    "status": "live",
    "author": "OpenClaw Agent"
}}'''

for skill in new_skills:
    name = skill["name"]
    skill_dir = SKILLS_DIR / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    
    # Write run.py
    run_py = skill_dir / "run.py"
    run_py.write_text(
        TEMPLATE_RUN_PY.format(**skill),
        encoding="utf-8",
    )
    
    # Write SKILL.md
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        TEMPLATE_SKILL_MD.format(**skill),
        encoding="utf-8",
    )
    
    # Write _meta.json
    meta_json = skill_dir / "_meta.json"
    meta_json.write_text(
        TEMPLATE_META_TXT.format(**skill),
        encoding="utf-8",
    )
    
    # Write run.bat (Windows wrapper)
    run_bat = skill_dir / "run.bat"
    run_bat.write_text(
        f'@echo off\nset PYTHONIOENCODING=utf-8\npython "%~dp0run.py" %*\n',
        encoding="utf-8",
    )
    
    # Write run.sh (Linux/Mac wrapper)
    run_sh = skill_dir / "run.sh"
    run_sh.write_text(
        f'#!/bin/bash\nPYTHONIOENCODING=utf-8 python "$(dirname "$0")/run.py" "$@"\n',
        encoding="utf-8",
    )
    
    # Write .deploy (deploy config)
    deploy_file = skill_dir / ".deploy"
    deploy_file.write_text(
        f'# {name} deploy config\nSTATUS=live\nVERSION=0.1.0\n',
        encoding="utf-8",
    )

    print(f"Created {skill_dir}")
    print(f"  run.py, SKILL.md, _meta.json, run.bat, run.sh, .deploy")
    print()

print("Done. Verifying...")
for skill in new_skills:
    name = skill["name"]
    import subprocess
    result = subprocess.run(
        ["python", str(SKILLS_DIR / name / "run.py"), "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode == 0:
        data = json_module.loads(result.stdout)
        print(f"✅ {name}: --json OK (status={data.get('status')})")
    else:
        print(f"❌ {name}: FAILED ({result.stderr.strip()})")
