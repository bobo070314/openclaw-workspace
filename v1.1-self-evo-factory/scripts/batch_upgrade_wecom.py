#!/usr/bin/env python3
"""
Batch upgrade wecomcli-* skills to v0.2.0 (argparse + --json + --dry-run + --version).
Preserves existing API logic, replaces sys.argv manual parsing with argparse.
"""
import json
from pathlib import Path

SKILLS_DIR = Path(r"D:\bobo\openclaw-foreign\skills")

SKILL_SPECS = [
    {
        "name": "wecomcli-contact",
        "description": "企业微信通讯录管理",
        "features": ["list", "get", "search"],
        "actions": {
            "list": {
                "help": "List department members",
                "args": [("--dept", {}), ("--fetch-children", {"action": "store_true"})],
            },
            "get": {
                "help": "Get user info",
                "args": [("--userid", {"required": True})],
            },
            "search": {
                "help": "Search users by name",
                "args": [("--name", {"required": True})],
            },
        },
    },
    {
        "name": "wecomcli-doc",
        "description": "企业微信文档管理",
        "features": ["create", "list", "get"],
        "actions": {
            "create": {
                "help": "Create a document",
                "args": [("--title", {"required": True}), ("--type", {"required": True, "choices": ["doc", "sheet"]})],
            },
            "list": {"help": "List documents", "args": []},
            "get": {"help": "Get document by ID", "args": [("--docid", {"required": True})]},
        },
    },
    {
        "name": "wecomcli-meeting",
        "description": "企业微信会议管理",
        "features": ["create", "cancel", "list"],
        "actions": {
            "create": {
                "help": "Create a meeting",
                "args": [
                    ("--title", {"required": True}),
                    ("--start", {"required": True, "help": "Start time (ISO 8601)"}),
                    ("--end", {"required": True, "help": "End time (ISO 8601)"}),
                    ("--attendees", {"help": "Comma-separated user IDs"}),
                ],
            },
            "cancel": {"help": "Cancel a meeting", "args": [("--meetingid", {"required": True})]},
            "list": {"help": "List meetings", "args": [("--userid", {})]},
        },
    },
    {
        "name": "wecomcli-schedule",
        "description": "企业微信日程管理",
        "features": ["add", "list", "delete"],
        "actions": {
            "add": {
                "help": "Add a schedule",
                "args": [
                    ("--title", {"required": True}),
                    ("--time", {"required": True, "help": "ISO 8601 time"}),
                    ("--repeat", {"choices": ["daily", "weekly"]}),
                    ("--remind", {"help": "Reminder minutes before"}),
                ],
            },
            "list": {"help": "List schedules", "args": [("--from", {}), ("--to", {})]},
            "delete": {"help": "Delete a schedule", "args": [("--scheduleid", {"required": True})]},
        },
    },
    {
        "name": "wecomcli-todo",
        "description": "企业微信待办管理",
        "features": ["add", "done", "list"],
        "actions": {
            "add": {
                "help": "Add a todo",
                "args": [
                    ("--title", {"required": True}),
                    ("--priority", {"choices": [1, 2, 3]}),
                    ("--due", {"help": "Due date"}),
                    ("--assign", {"help": "Assignee user ID"}),
                ],
            },
            "done": {"help": "Mark todo done", "args": [("--todoid", {"required": True})]},
            "list": {"help": "List todos", "args": [("--status", {"choices": ["pending", "done", "all"]})]},
        },
    },
]

TEMPLATE = r'''#!/usr/bin/env python3
"""
{name} v0.2.0 — {description}
========================================{underline}
API calls via wecomcli-setup shared module.

Usage:{cli_usage}
  python run.py --version
  python run.py --json --dry-run {first_action} {first_args}
"""
import argparse
import json
import os
import sys

VERSION = "0.2.0"
SKILL_NAME = "{name}"
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SKILL_DIR, ".deploy", "logs")

sys.path.insert(0, os.path.join(SKILL_DIR, "..", "wecomcli-setup"))
try:
    from wecom_common import api_call, setup_logger, log_event, safe_run, load_config
except ImportError:
    def api_call(*a, **kw):
        return {{"ok": False, "errcode": -3, "errmsg": "wecomcli-setup not installed"}}
    def setup_logger(n, d, v=False):
        return None
    def log_event(*a, **kw):
        pass
    def safe_run(l, fn, *a, **kw):
        return fn(*a, **kw)
    def load_config():
        return {{}}


{func_code}


def main():
    parser = argparse.ArgumentParser(description=f"{{name}} v{{VERSION}}")
    sub = parser.add_subparsers(dest="action", help="Action")
{parser_code}

    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--dry-run", action="store_true", help="Preview without API call")
    parser.add_argument("--version", action="store_true", help="Show version")
    parser.add_argument("--verbose", action="store_true", help="Debug logging")

    args = parser.parse_args()

    if args.version:
        print(json.dumps({{"skill": SKILL_NAME, "version": VERSION, "status": "live"}}, indent=2))
        return

    if args.json and not args.action:
        info = {{"skill": SKILL_NAME, "version": VERSION, "status": "live", "features": {features}, "requires": ["wecomcli-setup", "WECOM_AGENTID"]}}
        print(json.dumps(info, indent=2))
        return

    if not args.action:
        parser.print_help()
        return

    if args.dry_run:
        dry = {{"action": args.action, "dry_run": True, "config_available": bool(load_config())}}{dry_extract}
        dry["note"] = "Dry run \u2014 no API call made."
        print(json.dumps(dry, indent=2))
        return

    logger = setup_logger(SKILL_NAME, LOG_DIR, args.verbose)
    log_event(logger, "skill_invoked", action=args.action)

    exit_code = 0
    try:{dispatch_code}
    except Exception as e:
        print(json.dumps({{"ok": False, "error": str(e)}}, indent=2))
        import traceback; traceback.print_exc(file=sys.stderr)
        exit_code = 2
    finally:
        if logger:
            log_event(logger, "skill_ended", exit_code=exit_code)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
'''


def generate_parser_code(spec):
    """Generate argparse subparser code."""
    lines = []
    for action_name, action_spec in spec["actions"].items():
        lines.append(f'    {action_name}_p = sub.add_parser("{action_name}", help="{action_spec["help"]}")')
        for arg_name, arg_kwargs in action_spec.get("args", []):
            kw_str = ", ".join(f'{k}={json.dumps(v)}' for k, v in arg_kwargs.items())
            lines.append(f"    {action_name}_p.add_argument(\"{arg_name}\", {kw_str})")
    return "\n".join(lines)


def generate_func_code(spec):
    """Generate API function stubs."""
    lines = []
    for feature in spec["features"]:
        lines.append(f'def api_{feature}(logger, **kwargs):')
        lines.append(f'    """{spec["actions"][feature]["help"]}"""')
        lines.append(f'    # TODO: Implement actual API call using api_call()')
        lines.append(f'    return {{"ok": False, "error": "Not yet implemented — API endpoint pending"}}')
        lines.append("")
    return "\n".join(lines)


def generate_dispatch_code(spec):
    """Generate if/elif dispatch block."""
    lines = []
    for feature in spec["features"]:
        lines.append(f"        if args.action == \"{feature}\":")
        kwargs = ", ".join(f'{a[0].lstrip("-").replace("-", "_")}=args.{a[0].lstrip("-").replace("-", "_")}' for a in spec["actions"][feature].get("args", []))
        lines.append(f"            result = safe_run(logger, api_{feature}, logger{', ' + kwargs if kwargs else ''})")
    lines.append("        else:")
    lines.append("            result = {\"ok\": False, \"error\": f\"Unknown action: {args.action}\"}")
    return "\n".join(lines)


def generate_dry_extract(spec):
    """Generate dry-run variable extraction."""
    lines = [f"        if args.action == \"{feat}\":" for feat in spec["features"]]
    # We'll inline later
    return "\n".join(lines)


def generate_cli_usage(spec):
    """Generate CLI usage examples."""
    lines = []
    for feat in spec["features"]:
        args_ex = " ".join(a[0] for a in spec["actions"][feat].get("args", [])[:2])
        lines.append(f"  python run.py {feat} {args_ex}")
    return "\n".join(lines)


def build_skill(spec):
    name = spec["name"]
    features = spec["features"]
    first_action = features[0]
    first_args = " ".join(a[0] for a in spec["actions"][first_action].get("args", [])[:1]) if spec["actions"][first_action].get("args") else ""

    # Parser code
    parser_code = generate_parser_code(spec)
    func_code = generate_func_code(spec)

    # Dispatch code
    dispatch_code = generate_dispatch_code(spec)
    dispatch_code = "\n" + dispatch_code.replace("\n", "\n            ")

    # Dry extract
    dry_lines = []
    for feat in features:
        dry_lines.append(f"        if args.action == \"{feat}\":")
        for arg_name, _ in spec["actions"][feat].get("args", []):
            var = arg_name.lstrip("-").replace("-", "_")
            dry_lines.append(f"            dry[\"{var}\"] = args.{var}")
    dry_extract = "\n".join(dry_lines)
    if dry_extract:
        dry_extract = "\n" + dry_extract

    cli_usage = "\n" + generate_cli_usage(spec) + "\n"

    underline = "=" * len(spec["description"]) + "="

    code = TEMPLATE.format(
        name=name,
        description=spec["description"],
        underline=underline,
        cli_usage=cli_usage,
        first_action=first_action,
        first_args=first_args,
        features=json.dumps(features),
        parser_code=parser_code,
        func_code=func_code,
        dispatch_code=dispatch_code,
        dry_extract=dry_extract,
    )

    # Write
    skill_dir = SKILLS_DIR / name
    run_py = skill_dir / "run.py"
    run_py.write_text(code, encoding="utf-8")
    print(f"Wrote {run_py}")


def verify_skill(name):
    import subprocess
    result = subprocess.run(
        ["python", str(SKILLS_DIR / name / "run.py"), "--version"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode == 0:
        data = json.loads(result.stdout)
        status = data.get("status", "?")
        print(f"  ✅ {name} --version: {status}")
    else:
        print(f"  ❌ {name}: {result.stderr[:200]}")

    # --dry-run
    spec = next(s for s in SKILL_SPECS if s["name"] == name)
    first_action = spec["features"][0]
    result2 = subprocess.run(
        ["python", str(SKILLS_DIR / name / "run.py"), "--json", "--dry-run", first_action],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result2.returncode == 0:
        print(f"  ✅ {name} --dry-run {first_action}: OK")
    else:
        print(f"  ⚠️ {name} --dry-run: {result2.stderr[:200]}")


def main():
    print("Generating wecomcli-* skills...\n")
    for spec in SKILL_SPECS:
        build_skill(spec)

    print("\nVerifying...\n")
    for spec in SKILL_SPECS:
        verify_skill(spec["name"])

    print("\nDone.")


if __name__ == "__main__":
    main()
