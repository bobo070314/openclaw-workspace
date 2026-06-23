#!/usr/bin/env python3
"""cn_channels/xiaohongshu_publisher.py - OpenClaw-CN v5.1
Xiaohongshu (小红书) professional account grass-planting pipeline.
Note creation, queue management, bio link management.
Compliance: professional account only, no private account automation."""

import json
import os
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass, field

UTC = timezone.utc
LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

log = logging.getLogger("cn.xhs")
handler = logging.FileHandler(LOG_DIR / "cn_channels.log", encoding="utf-8")
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
log.addHandler(handler)
log.setLevel(logging.INFO)

QUEUE_DIR = Path("content/publish_queue/xhs")
QUEUE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class XhsNote:
    id: str
    title: str
    content: str
    images: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    status: str = "pending"
    created_at: str = ""
    published_at: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "images": self.images,
            "topics": self.topics,
            "status": self.status,
            "created_at": self.created_at or datetime.now(UTC).isoformat(),
            "published_at": self.published_at,
        }


class XhsPublisher:
    """小红书专业号种草发布器。

    合规:
    - 仅专业号/品牌合作 (蒲公英)
    - 笔记内容符合社区规范
    - 简介可挂官网链接/小程序跳转
    """

    def __init__(self):
        self._dry_run = os.getenv("OPENCLAW_DRY_RUN", "") == "1"

    def queue_note(self, title: str, content: str, images: List[str] = None, topics: List[str] = None) -> Dict:
        """将笔记加入发布队列."""
        note = XhsNote(
            id=f"xhs_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            title=title,
            content=content,
            images=images or [],
            topics=topics or [],
            status="pending",
        )

        queue_file = QUEUE_DIR / f"{note.id}.json"
        queue_file.write_text(json.dumps(note.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        log.info("xhs queued: %s -> %s", note.id, title)
        return note.to_dict()

    def list_queue(self, status_filter: str = None) -> List[Dict]:
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

    def approve_note(self, note_id: str) -> Dict:
        queue_file = QUEUE_DIR / f"{note_id}.json"
        if not queue_file.exists():
            return {"error": f"Note {note_id} not found"}
        data = json.loads(queue_file.read_text(encoding="utf-8"))
        data["status"] = "approved"
        queue_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return data

    def generate_bio_links(self, wecom_qr_url: str = "", website_url: str = "", miniapp_path: str = "") -> Dict:
        """生成小红书简介引导文案（合规引流）."""
        links = {
            "bio_template": "合作/咨询请戳 👇",
            "primary": wecom_qr_url or "[企微二维码]",
            "website": website_url or "",
            "miniapp": miniapp_path or "",
            "compliance_note": "简介链接仅限官网/小程序，不可直接放微信号（社区规范）",
        }
        return links


# ---- CLI ----

if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Xiaohongshu Publisher - OpenClaw-CN v5.1")
    p.add_argument("--queue", type=str, help="Queue a note: 'TITLE|CONTENT'")
    p.add_argument("--images", type=str, default="", help="Comma-separated image paths")
    p.add_argument("--topics", type=str, default="", help="Comma-separated topics")
    p.add_argument("--list", action="store_true", help="List queue")
    p.add_argument("--approve", type=str, help="Approve by note ID")
    p.add_argument("--bio", action="store_true", help="Generate bio link template")
    p.add_argument("--json", action="store_true", help="JSON output")

    args = p.parse_args()

    pub = XhsPublisher()

    if args.queue:
        parts = args.queue.split("|", 1)
        title = parts[0]
        content = parts[1] if len(parts) > 1 else ""
        images = [i.strip() for i in args.images.split(",") if i.strip()]
        topics = [t.strip() for t in args.topics.split(",") if t.strip()]
        result = pub.queue_note(title, content, images, topics)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Queued: {result['id']} - {title}")

    if args.list:
        posts = pub.list_queue()
        if args.json:
            print(json.dumps(posts, indent=2, ensure_ascii=False))
        else:
            for p in posts:
                print(f"  {p['id']} [{p['status']}] {p['title']}")

    if args.approve:
        result = pub.approve_note(args.approve)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Approved: {args.approve}")

    if args.bio:
        result = pub.generate_bio_links()
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Bio: {result['bio_template']}")
            print(f"  Primary: {result['primary']}")
            print(f"  Website: {result['website']}")
            print(f"  Compliance: {result['compliance_note']}")
