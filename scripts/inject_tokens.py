"""一键注入 API Token，不走交互式输入（避免 PowerShell 吞输入）。
编辑下面的 REAL_TOKENS 字典，填入真实值，然后运行：
  python scripts/inject_tokens.py
"""

import json
from pathlib import Path

# ====== 填入你的真实 Token ======
REAL_TOKENS = {
    "github_token": "",  # ghp_xxx
    "notion_token": "",  # secret_xxx
    "linear_token": "",  # lin_api_xxx
    "tencent_docs_token": "",  # (optional)
    "wecom_corpid": "",  # ww_xxx
    "wecom_corpsecret": "",  # secret
    "wecom_agentid": "",  # 纯数字, 如 1000002
}
# ================================

path = Path.home() / ".openclaw" / "api_tokens.json"
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(REAL_TOKENS, indent=2, ensure_ascii=False), encoding="utf-8")

filled = sum(1 for v in REAL_TOKENS.values() if v)
print(f"[OK] {filled}/{len(REAL_TOKENS)} tokens injected -> {path}")
if filled == 0:
    print("⚠️  No tokens set. Edit the REAL_TOKENS dict above and re-run.")
