#!/usr/bin/env python3
"""cn_channels/douyin_publisher.py - OpenClaw-CN v5.1
Douyin (抖音) enterprise publisher via open platform.
Video upload, publish, comment reply, lead capture -> WeCom.
All operations silent, queue-based, manual review gate.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

UTC = timezone.utc
LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

log = logging.getLogger("cn.douyin")
handler = logging.FileHandler(LOG_DIR / "cn_channels.log", encoding="utf-8")
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
log.addHandler(handler)
log.setLevel(logging.INFO)

QUEUE_DIR = Path("content/publish_queue/douyin")
QUEUE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class DouyinPost:
    """A queued douyin post, reviewed before publish."""

    id: str
    title: str
    video_path: str = ""
    cover_path: str = ""
    topics: List[str] = field(default_factory=list)
    status: str = "pending"  # pending / approved / published / failed
    created_at: str = ""
    published_at: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "video_path": self.video_path,
            "cover_path": self.cover_path,
            "topics": self.topics,
            "status": self.status,
            "created_at": self.created_at or datetime.now(UTC).isoformat(),
            "published_at": self.published_at,
        }


class DouyinPublisher:
    """抖音企业号发布器。

    合规要求:
    - 仅使用抖音开放平台 (open.douyin.com) 官方接口
    - 企业号授权后操作，不碰私人号
    - 所有内容先入队列，人工审核后再发布
    """

    def __init__(self, client_key: str = "", client_secret: str = ""):
        self.ck = client_key or os.getenv("DOUYIN_CLIENT_KEY", "")
        self.cs = client_secret or os.getenv("DOUYIN_CLIENT_SECRET", "")
        self.open_id = os.getenv("DOUYIN_OPEN_ID", "")
        self._access_token: Optional[str] = None
        self._token_exp: float = 0
        self._enabled = bool(self.ck and self.cs)
        self._dry_run = os.getenv("OPENCLAW_DRY_RUN", "") == "1"

        if not self._enabled:
            log.warning("DouyinPublisher disabled -- client_key or client_secret missing")

    def _get_token(self) -> str:
        """获取 client_credential access_token."""
        import time as _time

        now = _time.time()
        if self._access_token and self._token_exp > now + 60:
            return self._access_token

        if self._dry_run or not self._enabled:
            return "dry-token"

        try:
            import requests

            r = requests.post(
                "https://open.douyin.com/oauth/client_token/",
                json={
                    "client_key": self.ck,
                    "client_secret": self.cs,
                    "grant_type": "client_credential",
                },
                timeout=10,
            )
            data = r.json()
            if data.get("data", {}).get("error_code", 0) == 0:
                self._access_token = data["data"]["access_token"]
                self._token_exp = now + data["data"].get("expires_in", 7200)
                return self._access_token
            log.error("douyin token fail: %s", data)
            raise RuntimeError(f"Douyin token error: {data}")
        except Exception as e:
            log.error("douyin token error: %s", e)
            raise

    def queue_video(self, title: str, video_path: str, topics: List[str] = None) -> Dict:
        """将视频加入发布队列（人工审核前一步）."""
        post = DouyinPost(
            id=f"dy_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            title=title,
            video_path=video_path,
            topics=topics or [],
            status="pending",
        )

        queue_file = QUEUE_DIR / f"{post.id}.json"
        queue_file.write_text(json.dumps(post.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        log.info("douyin queued: %s -> %s", post.id, title)
        return post.to_dict()

    def list_queue(self, status_filter: str = None) -> List[Dict]:
        """列出发布队列."""
        posts = []
        for f in sorted(QUEUE_DIR.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if status_filter and data.get("status") != status_filter:
                    continue
                posts.append(data)
            except Exception:
                pass
        return posts

    def approve_post(self, post_id: str) -> Dict:
        """标记为已审核（人工审核通过后调用）."""
        queue_file = QUEUE_DIR / f"{post_id}.json"
        if not queue_file.exists():
            return {"error": f"Post {post_id} not found"}
        data = json.loads(queue_file.read_text(encoding="utf-8"))
        data["status"] = "approved"
        queue_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        log.info("douyin approved: %s", post_id)
        return data

    def publish_video(self, post_id: str) -> Dict:
        """发布已审核的视频到抖音。"""
        queue_file = QUEUE_DIR / f"{post_id}.json"
        if not queue_file.exists():
            return {"error": f"Post {post_id} not found"}

        data = json.loads(queue_file.read_text(encoding="utf-8"))
        if data.get("status") != "approved":
            return {"error": "Not approved yet", "status": data["status"]}

        if self._dry_run:
            data["status"] = "published"
            data["published_at"] = datetime.now(UTC).isoformat()
            queue_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            return {"errcode": 0, "errmsg": "dry-run publish ok", "post": data}

        # 实际发布: POST /video/upload/ + /video/publish/
        try:
            tok = self._get_token()

            # Step 1: upload video
            video_url = "https://open.douyin.com/video/upload/?open_id={open_id}&access_token={tok}"
            # Step 2: publish with title + topics

            # 占位 - 需要实际填 open_id 和完整接口参数
            result = {
                "errcode": -1,
                "errmsg": "Not implemented: fill your enterprise open_id and API params",
                "hint": "Go to open.douyin.com -> 视频管理 -> 发布能力",
            }
            log.warning("douyin publish not fully implemented: need open_id + API params")
            return result
        except Exception as e:
            log.error("douyin publish error: %s", e)
            data["status"] = "failed"
            queue_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            return {"errcode": -1, "errmsg": str(e)}

    def auto_reply_keywords(self, comment_text: str) -> Optional[str]:
        """评论关键词自动回复规则。匹配后返回引导文案."""
        keywords = {
            "价格": "私信我发「报价」获取最新价格表 👇",
            "怎么联系": "点击主页简介加我企微，秒回！",
            "在吗": "在的！有什么可以帮您？也可以加企微聊 👇",
            "怎么买": "主页有联系方式，私信我「下单」获取链接 👇",
        }
        for kw, reply in keywords.items():
            if kw in comment_text:
                return reply
        return None


# ---- CLI ----

if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Douyin Publisher - OpenClaw-CN v5.1")
    p.add_argument("--queue", type=str, help="Queue a video: 'TITLE|VIDEO_PATH'")
    p.add_argument("--topics", type=str, default="", help="Comma-separated topics")
    p.add_argument("--list", action="store_true", help="List pending queue")
    p.add_argument("--approve", type=str, help="Approve by post ID")
    p.add_argument("--publish", type=str, help="Publish by post ID")
    p.add_argument("--json", action="store_true", help="JSON output")

    args = p.parse_args()

    pub = DouyinPublisher()

    if args.queue:
        parts = args.queue.split("|", 1)
        title = parts[0]
        vpath = parts[1] if len(parts) > 1 else ""
        topics = [t.strip() for t in args.topics.split(",") if t.strip()]
        result = pub.queue_video(title, vpath, topics)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Queued: {result['id']} - {title} [{result['status']}]")

    if args.list:
        posts = pub.list_queue()
        if args.json:
            print(json.dumps(posts, indent=2, ensure_ascii=False))
        else:
            for p in posts:
                print(f"  {p['id']} [{p['status']}] {p['title']}")

    if args.approve:
        result = pub.approve_post(args.approve)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Approved: {args.approve}")

    if args.publish:
        result = pub.publish_video(args.publish)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Publish: {result.get('errmsg', 'ok')}")
