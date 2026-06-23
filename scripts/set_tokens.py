"""写入真实 API Token，避免 PowerShell 吞输入。

修改下面的 TOKENS 字典填入真实值，然后：
  python scripts/set_tokens.py
"""

import json
from pathlib import Path

# ====== 改为你的真实 Token ======
TOKENS = {
    "github_token": "ghp_YOUR_REAL_GITHUB_TOKEN",
    "notion_token": "secret_YOUR_REAL_NOTION_TOKEN",
    "linear_token": "lin_api_YOUR_REAL_LINEAR_TOKEN",
    "wecom_corpid": "ww_YOUR_CORP_ID",
    "wecom_corpsecret": "YOUR_CORP_SECRET",
    "wecom_agentid": "1000002",
    "tencent_docs_token": "",
}
# ================================

path = Path.home() / ".openclaw" / "api_tokens.json"
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(TOKENS, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"✅ Tokens written to {path}")
