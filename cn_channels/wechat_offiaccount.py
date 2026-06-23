#!/usr/bin/env python3
"""cn_channels/wechat_offiaccount.py - OpenClaw-CN v5.1
WeChat Official Account (微信公众号) integration.
Template messages, menu management, H5 authorization, customer service.
Service account (服务号) or subscription account (订阅号).
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import requests

UTC = timezone.utc
LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

log = logging.getLogger("cn.wechat_oa")
handler = logging.FileHandler(LOG_DIR / "cn_channels.log", encoding="utf-8")
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
log.addHandler(handler)
log.setLevel(logging.INFO)


class WeChatOffiAccount:
    """微信公众号操作。

    能力:
    - 模板消息推送 (服务号必备)
    - 自定义菜单管理
    - 网页授权 (OAuth2) -> 获取 openid
    - 客服消息 (48h内)
    """

    def __init__(self, appid: str = "", appsecret: str = ""):
        self.appid = appid or os.getenv("WECHAT_APPID", "")
        self.appsecret = appsecret or os.getenv("WECHAT_APPSECRET", "")
        self._token_cache = {"value": None, "exp": 0}
        self._enabled = bool(self.appid and self.appsecret)
        self._dry_run = os.getenv("OPENCLAW_DRY_RUN", "") == "1"
        if not self._enabled:
            log.warning("WeChatOffiAccount disabled")

    def _access_token(self) -> str:
        now = time.time()
        if self._token_cache["value"] and self._token_cache["exp"] > now + 60:
            return self._token_cache["value"]
        if not self._enabled:
            return "dry-token"
        r = requests.get(
            "https://api.weixin.qq.com/cgi-bin/token",
            params={"grant_type": "client_credential", "appid": self.appid, "secret": self.appsecret},
            timeout=10,
        )
        data = r.json()
        if "access_token" in data:
            self._token_cache = {"value": data["access_token"], "exp": now + 7200}
            return data["access_token"]
        log.error("wechat_oa token fail: %s", data)
        raise RuntimeError(f"WeChat OA token error: {data}")

    def send_template_message(
        self,
        openid: str,
        template_id: str,
        data: Dict[str, Dict[str, str]],
        url: str = "",
        miniprogram: Dict = None,
    ) -> Dict:
        """发送模板消息."""
        if self._dry_run:
            return {"errcode": 0, "errmsg": "dry-run"}
        tok = self._access_token()
        body = {
            "touser": openid,
            "template_id": template_id,
            "data": data,
        }
        if url:
            body["url"] = url
        if miniprogram:
            body["miniprogram"] = miniprogram

        r = requests.post(
            f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={tok}",
            json=body,
            timeout=10,
        )
        return r.json()

    def send_valuation_notification(self, openid: str, plate: str, value: float, template_id: str) -> Dict:
        """发送估值报告模板消息."""
        data = {
            "first": {"value": f"车牌 {plate} 估值报告已生成", "color": "#173177"},
            "keyword1": {"value": f"¥{value:,.0f}", "color": "#e63946"},
            "keyword2": {"value": datetime.now(UTC).strftime("%Y-%m-%d %H:%M"), "color": "#457b9d"},
            "remark": {"value": "点击查看详细报告 →", "color": "#2a9d8f"},
        }
        return self.send_template_message(openid, template_id, data)

    def set_menu(self, buttons: List[Dict]) -> Dict:
        """设置自定义菜单."""
        if self._dry_run:
            return {"errcode": 0, "errmsg": "dry-run"}
        tok = self._access_token()
        r = requests.post(
            f"https://api.weixin.qq.com/cgi-bin/menu/create?access_token={tok}",
            json={"button": buttons},
            timeout=10,
        )
        return r.json()

    def get_menu(self) -> Dict:
        """获取当前菜单."""
        if self._dry_run:
            return {"menu": {"button": []}}
        tok = self._access_token()
        r = requests.get(f"https://api.weixin.qq.com/cgi-bin/menu/get?access_token={tok}", timeout=10)
        return r.json()


# ---- CLI ----

if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="WeChat Official Account - OpenClaw-CN v5.1")
    p.add_argument("--template", type=str, help="Send template: OPENID|TEMPLATE_ID|MESSAGE")
    p.add_argument("--menu-set", type=str, help="Set menu from JSON file")
    p.add_argument("--menu-get", action="store_true", help="Get current menu")
    p.add_argument("--json", action="store_true", help="JSON output")

    args = p.parse_args()

    oa = WeChatOffiAccount()

    if args.template:
        parts = args.template.split("|", 2)
        if len(parts) < 3:
            print("Usage: --template 'OPENID|TEMPLATE_ID|MESSAGE'")
        else:
            openid, tid, msg = parts
            result = oa.send_template_message(
                openid,
                tid,
                {
                    "first": {"value": msg},
                    "keyword1": {"value": datetime.now(UTC).strftime("%Y-%m-%d")},
                    "remark": {"value": "来自 OpenClaw"},
                },
            )
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print(result.get("errmsg", "ok"))

    if args.menu_get:
        result = oa.get_menu()
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Menu: {json.dumps(result.get('menu', {}), ensure_ascii=False)}")

    if args.menu_set:
        try:
            buttons = json.loads(Path(args.menu_set).read_text(encoding="utf-8"))
            result = oa.set_menu(buttons)
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print(result.get("errmsg", "ok"))
        except Exception as e:
            print(f"Error: {e}")
