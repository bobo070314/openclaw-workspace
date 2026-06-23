# Vault Guide — Token Management SOP

## Overview

The **Token Vault** is the single source of truth for all API credentials.
It lives at:

```
C:\Users\asus\.openclaw\api_tokens.json
```

**Security guarantees:**
- Never committed to Git (outside workspace, outside repos)
- Injected into subprocess environment only at test/run time
- Read by `test_api_skills.py`, `subconscious-daemon`, and all API skills via env vars
- No plaintext tokens in logs (truncated to first 10 chars)

## Vault Schema

```json
{
  "github_token": "ghp_xxx",
  "notion_token": "secret_xxx",
  "linear_token": "lin_api_xxx",
  "tencent_docs_token": "",
  "wecom_corpid": "",
  "wecom_corpsecret": "",
  "wecom_agentid": ""
}
```

## Adding Tokens — Clean Flow

### Step 1: Edit the vault manually

Open `C:\Users\asus\.openclaw\api_tokens.json` in any text editor.
Paste your token values. Save.

**Do NOT use PowerShell Set-Content or inline scripts** — they eat quotes and newlines on Windows.

### Step 2: Verify vault health

```bash
python pipeline\test_api_skills.py --check-health
```

Expected output:
```
🔐 Vault: C:\Users\asus\.openclaw\api_tokens.json
   Status: OK
   Keys: 1/7 populated
```

### Step 3: Run live tests

```bash
# Test all API skills with real credentials
python pipeline\test_api_skills.py --live

# Test a single skill
python pipeline\test_api_skills.py --live --skill notion

# JSON output for scripting
python pipeline\test_api_skills.py --live --json
```

## Token Sources

| Service | Token Key | Where to Get |
|---------|-----------|-------------|
| GitHub | `github_token` | `gh auth token` or https://github.com/settings/tokens |
| Notion | `notion_token` | https://www.notion.so/my-integrations |
| Linear | `linear_token` | https://linear.app/settings/api |
| Tencent Docs | `tencent_docs_token` | OAuth or env var from Tencent Cloud |
| WeCom | `wecom_corpid` / `wecom_corpsecret` / `wecom_agentid` | WeCom Admin Console |

## Auto-Injection from gh CLI

If you have `gh` CLI authenticated (you do — `gh auth status` returns OK),
run this **once** to seed the GitHub token:

```bash
python scripts\inject_tokens.py
```

This reads `gh auth token` and writes it to the vault.

## Daemon Monitoring

`subconscious-daemon` checks the vault every cycle:

```
[22:00:00] [tokens] Vault OK (1 tokens populated) ← healthy
[22:01:00] [tokens] gh auth status failed ← alert!
```

When a token expires or gh auth breaks, the daemon:
1. Flags the `check_tokens` alert
2. Runs through `arm_response()` 
3. If causal-reasoner cannot explain the failure → triggers adversarial-guard

## Vault Compromise Detection

- `adversarial-guard` scans for unexpected changes to `~/.openclaw/api_tokens.json`
- Any modification outside the expected editor flow → alert
- Daemon's `check_git()` also watches for `.env` or credential files in workspace

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Vault not found` | Create `C:\Users\asus\.openclaw\api_tokens.json` manually |
| `Vault JSON corrupt` | Check for trailing commas, unescaped quotes. Edit manually. |
| `0/7 keys populated` | Fill in token values. Don't leave empty strings. |
| `PS1> Set-Content` mangled JSON | **Stop using Set-Content.** Edit in VSCode/Notepad. |
| gh auth status fails | Run `gh auth login` to re-authenticate. |
