# v1.1-self-evo-factory — Installation Guide

## Prerequisites

| Tool | Min Version | Verify | Notes |
|------|-------------|--------|-------|
| Python | 3.11+ | `python -V` | Required for all pipelines |
| Git | 2.30+ | `git --version` | For version control |
| Docker Desktop | 24+ | `docker --version` | Optional, for sandbox-executor |

### Optional

| Tool | Purpose |
|------|---------|
| GitHub CLI (`gh`) | For create-pr, clone-project, GitHub releases |
| Node.js 18+ | For frontend/testing skills that use npm |
| WeCom Webhook | For daily report push notifications |
| SMTP credentials | For email delivery of daily reports |

## Quick Start

```powershell
# 1. Clone the repo
git clone git@github.com:bobo070314/v1.1-self-evo-factory.git
cd v1.1-self-evo-factory

# 2. Run the setup script
python scripts/setup_new_env.py

# 3. Verify everything works
python eval-suite/run_all.py
python pipeline/self_improve.py --all --dry-run
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PYTHONIOENCODING` | Yes | `utf-8` | Must be utf-8 on Windows |
| `OPENAI_API_KEY` | Yes | — | OpenRouter API key for @repair LLM |
| `HEAL_MODEL` | No | `deepseek/deepseek-v4-pro` | Model for self-heal |
| `WECOM_WEBHOOK_URL` | No | — | WeCom bot webhook for reports |
| `SMTP_HOST` | No | `smtp.qq.com` | SMTP server |
| `SMTP_PORT` | No | `587` | SMTP port |
| `SMTP_USER` | No | — | SMTP username |
| `SMTP_PASSWORD` | No | — | SMTP password |
| `SMTP_FROM` | No | — | Sender email |
| `SMTP_TO` | No | — | Recipient email |

## Project Structure

```
v1.1-self-evo-factory/
├── pipeline/
│   ├── self_coder.py          # Rule engine (9 rules, pure Python)
│   ├── self_improve.py        # Closed-loop optimizer + @repair
│   ├── self_heal.py           # @repair decorator
│   ├── daily_eval_reporter.py # Daily eval + reporting
│   ├── report_delivery.py     # WeCom/Email delivery
│   └── exec_wrapper.py        # Token-saver proxy
├── eval-suite/
│   ├── run_all.py             # Master test runner
│   └── test_*.py              # Individual skill tests
├── scripts/
│   ├── setup_new_env.py       # One-click environment setup
│   └── batch1_*.py            # Batch operation scripts
├── states/                    # Runtime state files
└── logs/                      # Execution logs
```

## Skills Location

Skills live in `D:\bobo\openclaw-foreign\skills\` (configured via OpenClaw's `extraDirs`).
To migrate to a new machine:

```powershell
# On source machine
robocopy D:\bobo\openclaw-foreign\skills D:\bobo\openclaw-foreign\skills-backup /E /MIR

# On target machine
git clone git@github.com:bobo070314/v1.1-self-evo-factory.git
robocopy D:\bobo\openclaw-foreign\skills-backup D:\bobo\openclaw-foreign\skills /E
```

## Troubleshooting

### Windows GBK encoding errors
```powershell
$env:PYTHONIOENCODING="utf-8"
```
Set permanently: `[Environment]::SetEnvironmentVariable('PYTHONIOENCODING', 'utf-8', 'User')`

### PowerShell eats Python inline quotes
Always use `.py` files instead of `python -c "..."` for multi-line code.

### Git push exit code 1 on Windows
PowerShell treats git stderr as error. Check `git status` before assuming failure.

### Docker not found
Sandbox-executor falls back to native execution. Docker is optional.

### OpenRouter API key
```powershell
$env:OPENAI_API_KEY="sk-or-v1-..."
```
Or add to System Environment Variables permanently.

## Cron Setup (OpenClaw Gateway)

The daily eval reporter runs at 9:00 AM Asia/Shanghai:
```
cron: 0 9 * * * Asia/Shanghai
task: python pipeline/daily_eval_reporter.py
```

## Verification Checklist

- [ ] `python eval-suite/run_all.py` → ALL GREEN
- [ ] `python pipeline/self_improve.py --all --dry-run` → 148 skills scanned
- [ ] `python pipeline/daily_eval_reporter.py` → Report saved to states/
- [ ] `python pipeline/report_delivery.py` → Delivery status printed
- [ ] `ruff check pipeline/` → No errors
