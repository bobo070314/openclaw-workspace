#!/usr/bin/env python3
"""cn_channels/wecom_sender.py - OpenClaw-CN v5.1
WeCom (企业微信) messaging: text, markdown, news cards, images.
Supports internal notifications + customer contact (客户联系).
All operations silent, logs to file, no popups.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import requests

UTC = timezone.utc
LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

log = logging.getLogger("cn.wecom")
handler = logging.FileHandler(LOG_DIR / "cn_channels.log", encoding="utf-8")
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
log.addHandler(handler)
log.setLevel(logging.INFO)


class WeComSender:
    """企业微信自建应用消息发送器。

    支持消息类型: text, markdown, news (图文卡片), image.
    """

    def __init__(
        self,
        corpid: str = "",
        corpsecret: str = "",
        agentid: int = 1000002,
    ):
        self.corpid = corpid or os.getenv("WECOM_CORPID", "")
        self.corpsecret = corpsecret or os.getenv("WECOM_CORPSECRET", "")
        self.agentid = agentid or int(os.getenv("WECOM_AGENTID", "1000002"))
        self._token_cache = {"value": None, "exp": 0}
        self._dry_run = os.getenv("OPENCLAW_DRY_RUN", "") == "1"
        self._enabled = bool(self.corpid and self.corpsecret)
        if not self._enabled:
            log.warning("WeComSender disabled -- corpid or corpsecret missing")

    def _access_token(self) -> str:
        now = time.time()
        if self._token_cache["value"] and self._token_cache["exp"] > now + 60:
            return self._token_cache["value"]

        if not self._enabled:
            return "dry-token"

        try:
            r = requests.get(
                "https://qyapi.weixin.qq.com/cgi-bin/gettoken",
                params={"corpid": self.corpid, "corpsecret": self.corpsecret},
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()
            if data.get("errcode") == 0:
                self._token_cache = {"value": data["access_token"], "exp": now + 7200}
                log.info("wecom token refreshed")
                return data["access_token"]
            log.error("wecom token fail: %s", data)
            raise RuntimeError(f"WeCom token error: {data}")
        except requests.RequestException as e:
            log.error("wecom token network error: %s", e)
            raise

    def _call(self, body: dict) -> dict:
        if self._dry_run:
            return {"errcode": 0, "errmsg": "dry-run", "dry": True}
        if not self._enabled:
            return {"errcode": 0, "errmsg": "disabled", "disabled": True}
        tok = self._access_token()
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={tok}"
        try:
            r = requests.post(url, json=body, timeout=10)
            r.raise_for_status()
            result = r.json()
            log.info("wecom send: %s", result.get("errmsg", "unknown"))
            return result
        except requests.RequestException as e:
            log.error("wecom send error: %s", e)
            return {"errcode": -1, "errmsg": str(e)}

    # ---- message types ----

    def send_text(self, touser: str, content: str) -> dict:
        """发送纯文本消息。touser: @all 或 UserID，支持 | 分隔多人."""
        body = {
            "touser": touser,
            "msgtype": "text",
            "agentid": self.agentid,
            "text": {"content": content},
            "safe": 0,
        }
        return self._call(body)

    def send_markdown(self, touser: str, content: str) -> dict:
        """发送 Markdown 消息（企微有限 markdown 子集）."""
        body = {
            "touser": touser,
            "msgtype": "markdown",
            "agentid": self.agentid,
            "markdown": {"content": content},
        }
        return self._call(body)

    def send_news(self, touser: str, articles: List[dict]) -> dict:
        """发送图文卡片。articles: [{"title":"...","description":"...","url":"...","picurl":"..."}]"""
        body = {
            "touser": touser,
            "msgtype": "news",
            "agentid": self.agentid,
            "news": {"articles": articles},
        }
        return self._call(body)

    def send_image(self, touser: str, media_id: str) -> dict:
        """发送图片（需要先 upload 获取 media_id）."""
        body = {
            "touser": touser,
            "msgtype": "image",
            "agentid": self.agentid,
            "image": {"media_id": media_id},
        }
        return self._call(body)

    def upload_media(self, filepath: str, media_type: str = "image") -> Optional[str]:
        """上传临时素材，返回 media_id."""
        if not self._enabled or self._dry_run:
            return "dry-media-id"
        tok = self._access_token()
        url = f"https://qyapi.weixin.qq.com/cgi-bin/media/upload?access_token={tok}&type={media_type}"
        try:
            with open(filepath, "rb") as f:
                r = requests.post(url, files={"media": (Path(filepath).name, f)}, timeout=30)
            data = r.json()
            if data.get("errcode") == 0:
                return data["media_id"]
            log.error("wecom upload failed: %s", data)
            return None
        except Exception as e:
            log.error("wecom upload error: %s", e)
            return None

    # ---- convenience helpers ----

    def notify_boss(self, title: str, body: str, url: str = "") -> dict:
        """快速通知老板（发到 notify_users 列表）."""
        from pathlib import Path as _P

        import yaml

        cfg_path = _P("config/cn_channels.yaml")
        touser = "@all"
        if cfg_path.exists():
            try:
                cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
                users = cfg.get("channels", {}).get("wecom", {}).get("notify_users", ["@all"])
                touser = "|".join(users)
            except Exception:
                pass

        if url:
            return self.send_news(touser, [{"title": title, "description": body, "url": url}])
        return self.send_text(touser, f"{title}\n\n{body}")

    def send_valuation_report(self, touser: str, plate: str, value: float, discount_info: str = "") -> dict:
        """发送估值报告卡片."""
        ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        articles = [
            {
                "title": f"车牌 {plate} 估值报告",
                "description": f"估值: ¥{value:,.0f}\n"
                + (f"损伤折扣: {discount_info}\n" if discount_info else "")
                + f"时间: {ts}",
                "url": "",
            }
        ]
        return self.send_news(touser, articles)

    def send_alert(self, alert_type: str, details: str, level: str = "WARN") -> dict:
        """发送系统告警."""
        emoji = {"INFO": "[i]", "WARN": "⚠️", "ERROR": "🚨", "CRITICAL": "💀"}
        e = emoji.get(level, "[!]")
        text = f"{e} OpenClaw 告警 [{level}]\n\n类型: {alert_type}\n\n{details}\n\n时间: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}"
        cfg_path = Path("config/cn_channels.yaml")
        touser = "@all"
        if cfg_path.exists():
            try:
                import yaml

                cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
                users = cfg.get("channels", {}).get("wecom", {}).get("notify_users", ["@all"])
                touser = "|".join(users)
            except Exception:
                pass
        return self.send_text(touser, text)


# ---- Singleton ----

_wecom: Optional[WeComSender] = None


def get_wecom() -> WeComSender:
    global _wecom
    if _wecom is None:
        _wecom = WeComSender()
    return _wecom


# ---- CLI ----

if __name__ == "__main__":
    import argparse
    import sys

    p = argparse.ArgumentParser(description="WeCom Sender - OpenClaw-CN v5.1")
    p.add_argument("--text", type=str, help="Send text: TOUSER|MESSAGE")
    p.add_argument("--markdown", type=str, help="Send markdown: TOUSER|MESSAGE")
    p.add_argument("--alert", type=str, help="Send alert: TYPE|DETAILS")
    p.add_argument("--test", action="store_true", help="Send test message to configured users")
    p.add_argument("--json", action="store_true", help="JSON output")
    p.add_argument("--dry-run", action="store_true", help="Dry run only")

    args = p.parse_args()

    if args.dry_run:
        os.environ["OPENCLAW_DRY_RUN"] = "1"

    wecom = get_wecom()

    if args.test:
        result = wecom.send_text("@all", "OpenClaw 企微通道测试消息，收到请忽略。🤫🦞")
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Test: {result.get('errmsg', 'ok')}")
        sys.exit(0)

    if args.text:
        parts = args.text.split("|", 1)
        if len(parts) < 2:
            print("Usage: --text 'TOUSER|MESSAGE'")
            sys.exit(1)
        result = wecom.send_text(parts[0], parts[1])
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Send: {result.get('errmsg', 'ok')}")

    if args.markdown:
        parts = args.markdown.split("|", 1)
        if len(parts) < 2:
            print("Usage: --markdown 'TOUSER|MARKDOWN'")
            sys.exit(1)
        result = wecom.send_markdown(parts[0], parts[1])
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Send: {result.get('errmsg', 'ok')}")

    if args.alert:
        parts = args.alert.split("|", 1)
        alert_type = parts[0] if parts else "system"
        details = parts[1] if len(parts) > 1 else "No details"
        result = wecom.send_alert(alert_type, details)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Alert: {result.get('errmsg', 'ok')}")
