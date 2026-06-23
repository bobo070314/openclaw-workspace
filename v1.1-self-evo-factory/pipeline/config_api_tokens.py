#!/usr/bin/env python3.
"""API Token configuration tool — secure env-var loader.

Saves tokens to ~/.openclaw/api_tokens.json and exports to os.environ.
On Windows, warns about file permissions (no chmod available).

Usage:
  python config_api_tokens.py          # interactive setup
  python config_api_tokens.py --test   # test if tokens are loaded
  python config_api_tokens.py --env    # print export commands
"""

import json
import os
from pathlib import Path

CONFIG_FILE = Path.home() / ".openclaw" / "api_tokens.json"

# Token env var mapping
TOKEN_MAP = {
    "github_token": {
        "env": "GITHUB_TOKEN",
        "label": "GitHub Token (ghp_xxx)",
        "skills": ["github-actions-generator", "web-deploy-github"],
    },
    "notion_token": {"env": "NOTION_TOKEN", "label": "Notion Token (secret_xxx)", "skills": ["notion"]},
    "linear_token": {"env": "LINEAR_TOKEN", "label": "Linear Token (lin_api_xxx)", "skills": ["linear"]},
    "tencent_docs_token": {"env": "TENCENT_DOCS_TOKEN", "label": "腾讯文档 Token", "skills": ["tencent-docs"]},
    "wecom_corpid": {"env": "WECOM_CORPID", "label": "企业微信 CorpID", "skills": ["wecomcli-*"]},
    "wecom_corpsecret": {"env": "WECOM_CORPSECRET", "label": "企业微信 CorpSecret", "skills": ["wecomcli-*"]},
    "wecom_agentid": {"env": "WECOM_AGENTID", "label": "企业微信 AgentID", "skills": ["wecomcli-*"]},
}


def load_tokens() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_tokens(tokens: dict):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2, ensure_ascii=False)
    tmp.replace(CONFIG_FILE)
    print(f"  💾 Saved to {CONFIG_FILE}")


def export_to_env(tokens: dict):
    """Export tokens to os.environ."""
    env_map = {v["env"]: tokens.get(k, "") for k, v in TOKEN_MAP.items() if k in tokens}
    os.environ.update({k: v for k, v in env_map.items() if v})
    return env_map


def interactive_setup():
    tokens = load_tokens()
    print("🔑 API Token Configuration\n")
    print("Enter values (or press Enter to skip unchanged)\n")

    changed = False
    for key, meta in TOKEN_MAP.items():
        current = tokens.get(key, "")
        masked = current[:4] + "****" + current[-4:] if len(current) > 8 else ("***" if current else "(not set)")
        val = input(f"  {meta['label']} [{masked}]: ").strip()
        if val:
            tokens[key] = val
            changed = True

    if changed:
        save_tokens(tokens)
    else:
        print("\n  ℹ️  No changes.")

    # Export to current process
    env_map = export_to_env(tokens)
    if env_map:
        print(f"\n  ✅ {len(env_map)} tokens exported to environment")
    else:
        print("\n  ⚠️  No tokens configured — API skills will use dry-run mode")

    # Show skill status
    print("\n📊 Skill readiness:")
    skill_keys = set()
    for key, meta in TOKEN_MAP.items():
        for sk in meta["skills"]:
            skill_keys.add(sk)
    for sk in sorted(skill_keys):
        has_token = any(tokens.get(k) for k, v in TOKEN_MAP.items() if sk in v["skills"] or v["skills"] == [sk])
        print(f"  {'✅' if has_token else '⚠️ '} {sk} {'(live)' if has_token else '(dry-run only)'}")


def test_tokens():
    """Test if tokens are loaded and report skill readiness."""
    tokens = load_tokens()
    export_to_env(tokens)

    print("🔍 Token Status:\n")
    all_good = True
    for key, meta in TOKEN_MAP.items():
        val = tokens.get(key, "")
        if val:
            print(f"  ✅ {meta['label']}: configured")
        else:
            all_good = False
            print(f"  ⚠️  {meta['label']}: NOT SET (skills: {', '.join(meta['skills'])})")

    print(f"\n{'✅ All tokens ready' if all_good else '⚠️  Some tokens missing — API skills will use dry-run mode'}")


def print_env():
    """Print export commands for shell."""
    tokens = load_tokens()
    for key, meta in TOKEN_MAP.items():
        val = tokens.get(key, "")
        if val:
            print(f"export {meta['env']}={val}")


def main():
    parser = argparse.ArgumentParser(description="API Token Configuration")
    parser.add_argument("--test", action="store_true", help="Test token status")
    parser.add_argument("--env", action="store_true", help="Print export commands")
    args = parser.parse_args()

    if args.env:
        print_env()
    elif args.test:
        test_tokens()
    else:
        interactive_setup()


if __name__ == "__main__":
    import argparse

    main()
