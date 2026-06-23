#!/usr/bin/env python3
"""cn_channels/publish_hub.py - OpenClaw-CN v5.1
Unified publishing hub: one piece of content -> auto-adapt -> all platforms.
Supports: WeCom (notify), Douyin (video), Xiaohongshu (note), WeChat OA (template).
All operations silent, queue-based, manual review gate.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

UTC = timezone.utc
LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

log = logging.getLogger("cn.hub")
handler = logging.FileHandler(LOG_DIR / "cn_channels.log", encoding="utf-8")
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
log.addHandler(handler)
log.setLevel(logging.INFO)

QUEUE_ROOT = Path("content/publish_queue")


class PublishHub:
    """统一发布中枢。一次创作，多平台适配出稿。"""

    def __init__(self):
        self._dry_run = os.getenv("OPENCLAW_DRY_RUN", "") == "1"

    def dispatch(
        self,
        title: str,
        body: str,
        image_paths: List[str] = None,
        video_path: str = "",
        topics: List[str] = None,
        platforms: List[str] = None,
    ) -> Dict:
        """一次创作，分发到多平台队列。

        platforms: ["wecom", "douyin", "xhs", "wechat_oa"]
        """
        if platforms is None:
            platforms = ["wecom"]

        result = {
            "title": title,
            "dispatched_at": datetime.now(UTC).isoformat(),
            "platforms": {},
        }

        for platform in platforms:
            try:
                if platform == "wecom":
                    result["platforms"]["wecom"] = self._to_wecom(title, body)
                elif platform == "douyin":
                    result["platforms"]["douyin"] = self._to_douyin(title, body, video_path, topics)
                elif platform == "xhs":
                    result["platforms"]["xhs"] = self._to_xhs(title, body, image_paths, topics)
                elif platform == "wechat_oa":
                    result["platforms"]["wechat_oa"] = self._to_wechat_oa(title, body)
                else:
                    result["platforms"][platform] = {"error": f"Unknown platform: {platform}"}
            except Exception as e:
                result["platforms"][platform] = {"error": str(e)}
                log.error("dispatch %s failed: %s", platform, e)

        # Save dispatch record
        dispatch_file = QUEUE_ROOT / f"dispatch_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
        dispatch_file.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

        log.info(
            "dispatched to %d platforms: %s -> %s",
            len([v for v in result["platforms"].values() if "error" not in v]),
            title,
            list(result["platforms"].keys()),
        )
        return result

    def _to_wecom(self, title: str, body: str) -> Dict:
        """适配企微格式：text + card."""
        if self._dry_run:
            return {"status": "queued", "dry": True}
        try:
            from cn_channels.wecom_sender import get_wecom

            wecom = get_wecom()
        except ImportError:
            import sys

            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from cn_channels.wecom_sender import get_wecom

            wecom = get_wecom()
        # Queue as a pending notification
        note_file = QUEUE_ROOT / f"wecom_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}.json"
        note = {"title": title, "body": body, "status": "pending"}
        note_file.write_text(json.dumps(note, indent=2, ensure_ascii=False), encoding="utf-8")
        return {"status": "queued", "file": str(note_file)}

    def _to_douyin(self, title: str, body: str, video_path: str, topics: List[str]) -> Dict:
        """适配抖音格式：短视频."""
        try:
            from cn_channels.douyin_publisher import DouyinPublisher
        except ImportError:
            import sys

            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from cn_channels.douyin_publisher import DouyinPublisher
        pub = DouyinPublisher()
        return pub.queue_video(title, video_path, topics)

    def _to_xhs(self, title: str, body: str, image_paths: List[str], topics: List[str]) -> Dict:
        """适配小红书格式：图文笔记."""
        try:
            from cn_channels.xiaohongshu_publisher import XhsPublisher
        except ImportError:
            import sys

            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from cn_channels.xiaohongshu_publisher import XhsPublisher
        pub = XhsPublisher()
        return pub.queue_note(title, body, image_paths or [], topics)

    def _to_wechat_oa(self, title: str, body: str) -> Dict:
        """适配公众号格式：模板消息/图文."""
        note_file = QUEUE_ROOT / f"wechat_oa_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}.json"
        note = {"title": title, "body": body, "status": "pending", "type": "template_message"}
        note_file.write_text(json.dumps(note, indent=2, ensure_ascii=False), encoding="utf-8")
        return {"status": "queued", "file": str(note_file)}


# ---- CLI ----

if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Publish Hub - OpenClaw-CN v5.1")
    p.add_argument("--dispatch", type=str, help="Dispatch: 'TITLE|BODY'")
    p.add_argument("--video", type=str, default="", help="Video path for douyin")
    p.add_argument("--images", type=str, default="", help="Comma-separated image paths for xhs")
    p.add_argument("--topics", type=str, default="", help="Comma-separated topics")
    p.add_argument("--platforms", type=str, default="wecom", help="Comma-separated: wecom,douyin,xhs,wechat_oa")
    p.add_argument("--json", action="store_true", help="JSON output")

    args = p.parse_args()

    hub = PublishHub()

    if args.dispatch:
        parts = args.dispatch.split("|", 1)
        title = parts[0]
        body = parts[1] if len(parts) > 1 else ""
        images = [i.strip() for i in args.images.split(",") if i.strip()]
        topics = [t.strip() for t in args.topics.split(",") if t.strip()]
        platforms = [p.strip() for p in args.platforms.split(",") if p.strip()]

        result = hub.dispatch(title, body, images, args.video, topics, platforms)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            for plat, res in result["platforms"].items():
                err = res.get("error", "")
                status = res.get("status", "dispatched")
                print(f"  {plat}: {status}{' ERROR: ' + err if err else ''}")
