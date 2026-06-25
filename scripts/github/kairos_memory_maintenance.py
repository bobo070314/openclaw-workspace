#!/usr/bin/env python
# -*- coding: utf-8 -*-
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
"""
Kairos 记忆库维护脚本
清理过期记忆 + 重建 TF-IDF 索引 + 输出统计

TTL 分级 (memory_janitor.py 标准):
  - 决策: 永久不清理
  - 设计: 90天
  - 经验: 180天
  - 对话: 7天
  - 默认(无标记): 30天（保守）
"""

import hashlib
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# ─── 配置 ────────────────────────────────────────────
WORKSPACE = Path(r"D:\bobo\openclaw-foreign\workspace")
MEMORY_DIR = WORKSPACE / "memory"
MEMORY_MD = WORKSPACE / "MEMORY.md"
INDEX_PATH = MEMORY_DIR / "tfidf_index.json"
STATS_PATH = MEMORY_DIR / "maintenance_stats.json"
ARCHIVE_DIR = MEMORY_DIR / "archive"
REFERENCE_UTC = datetime(2026, 6, 24, 23, 31, tzinfo=timezone.utc)

TTL_MAP = {
    "decision": None,  # 永久
    "design": 90,  # 90天
    "experience": 180,  # 180天
    "conversation": 7,  # 7天
    "default": 30,  # 默认30天
}

# ─── 工具函数 ────────────────────────────────────────────


def classify_content(text: str) -> str:
    """根据内容关键词推断记忆类别"""
    text_lower = text.lower()
    # 决策信号
    decision_words = [
        "决定",
        "decision",
        "最终",
        "结论",
        "确认",
        "confirm",
        "里程碑",
        "milestone",
        "版本",
        "release",
        "tag",
        "终态",
    ]
    if any(w in text_lower for w in decision_words):
        return "decision"
    # 设计信号
    design_words = [
        "架构",
        "architecture",
        "设计",
        "design",
        "规范",
        "spec",
        "接口",
        "interface",
        "模块",
        "module",
        "组件",
        "component",
    ]
    if any(w in text_lower for w in design_words):
        return "design"
    # 经验信号
    exp_words = ["踩坑", "教训", "坑", "注意", "慎", "避免", "avoid", "修复", "fix", "bug", "问题", "issue", "lesson"]
    if any(w in text_lower for w in exp_words):
        return "experience"
    # 对话信号
    conv_words = ["对话", "聊天", "chat", "问", "答", "讨论", "discuss"]
    if any(w in text_lower for w in conv_words):
        return "conversation"
    return "default"


def extract_date_from_filename(fname: str) -> datetime | None:
    """从文件名提取日期 (如 2026-06-20.md)"""
    m = re.match(r"(\d{4}-\d{2}-\d{2})\.md$", fname)
    if m:
        dt = datetime.strptime(m.group(1), "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
    return None


def extract_sections(text: str, fname: str) -> list[dict]:
    """将 .md 文件拆分为可独立评估的记忆区块"""
    # 按 ## 标题拆分
    blocks = re.split(r"\n(?=## )", text)
    sections = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        # 找标题
        title_match = re.match(r"^##\s+(.+)", block)
        title = title_match.group(1).strip() if title_match else "(无标题)"
        # 找日期引用
        date_refs = re.findall(r"(\d{4}-\d{2}-\d{2})", block)
        latest_date = max(date_refs) if date_refs else fname.replace(".md", "")
        category = classify_content(block)
        word_count = len(re.findall(r"[\u4e00-\u9fff]|[a-zA-Z]+", block))
        sections.append(
            {
                "file": fname,
                "title": title[:120],
                "category": category,
                "latest_date_ref": latest_date,
                "word_count": word_count,
                "hash": hashlib.md5(block.encode()).hexdigest()[:12],
            }
        )
    return sections


def compute_tfidf(text: str, corpus_texts: list[str]) -> list[float]:
    """简单 TF-IDF 向量"""

    # 中文分词粗略：按2-gram + 英文词
    def tokenize(t: str) -> list[str]:
        # 中文2-gram
        chinese = re.findall(r"[\u4e00-\u9fff]{2,}", t)
        # 英文词
        english = re.findall(r"[a-zA-Z]{2,}", t.lower())
        return chinese + english

    tokens = tokenize(text)
    tf = Counter(tokens)
    total = sum(tf.values()) or 1

    # IDF
    N = len(corpus_texts)
    doc_freq = Counter()
    for ct in corpus_texts:
        doc_freq.update(set(tokenize(ct)))

    vec = []
    for term in sorted(tf.keys()):
        tf_val = tf[term] / total
        idf_val = math.log((N + 1) / (doc_freq.get(term, 0) + 1))
        vec.append(tf_val * idf_val)

    if not vec:
        return [0.0]

    # L2归一化
    norm = math.sqrt(sum(v * v for v in vec))
    return [v / norm for v in vec] if norm > 0 else vec


# ─── 主流程 ────────────────────────────────────────────


def main():
    now = REFERENCE_UTC  # 或 datetime.now(timezone.utc)
    print("=" * 60)
    print(f"🧹 Kairos 记忆库维护 | {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    # ───────── 1. 扫描记忆文件 ─────────
    memory_files = sorted(MEMORY_DIR.glob("*.md"))
    print(f"\n📁 扫描记忆目录: {MEMORY_DIR}")
    print(f"   发现 {len(memory_files)} 个记忆文件:")
    for f in memory_files:
        sz = f.stat().st_size
        print(f"     {f.name:30s} {sz:>8,} bytes")

    # 也加入 MEMORY.md
    all_texts: dict[str, str] = {}
    all_sections: list[dict] = []

    # 读各日期文件
    for fp in memory_files:
        try:
            text = fp.read_text(encoding="utf-8")
            all_texts[fp.name] = text
            sections = extract_sections(text, fp.name)
            all_sections.extend(sections)
        except Exception as e:
            print(f"   ⚠️ 读取 {fp.name} 失败: {e}")

    # 读 MEMORY.md
    if MEMORY_MD.exists():
        try:
            text = MEMORY_MD.read_text(encoding="utf-8")
            all_texts["MEMORY.md"] = text
            sections = extract_sections(text, "MEMORY.md")
            # MEMORY.md 内容偏决策类
            for s in sections:
                s["category"] = s.get("category", "decision")
            all_sections.extend(sections)
        except Exception as e:
            print(f"   ⚠️ 读取 MEMORY.md 失败: {e}")

    print(f"\n📊 解析出 {len(all_sections)} 个记忆区块")

    # ───────── 2. TTL 评估 ─────────
    expired_sections: list[dict] = []
    active_sections: list[dict] = []

    for sec in all_sections:
        cat = sec["category"]
        ttl_days = TTL_MAP.get(cat, TTL_MAP["default"])
        if ttl_days is None:  # 永久
            active_sections.append(sec)
            continue

        # 用文件日期判定
        file_date = extract_date_from_filename(sec["file"])
        if file_date is None:
            file_date = datetime(2026, 6, 20, tzinfo=timezone.utc)  # fallback

        age_days = (now - file_date).days
        if age_days > ttl_days:
            expired_sections.append(sec)
        else:
            active_sections.append(sec)

    print("\n⏳ TTL 清理评估:")
    print(f"   活跃区块: {len(active_sections)}")
    print(f"   过期区块: {len(expired_sections)}")

    if expired_sections:
        print("\n   🗑️  即将清理的过期区块:")
        for s in expired_sections:
            print(f"     [{s['category']:15s}] {s['file']:20s} | {s['title'][:60]}")

    # ───────── 3. 按文件统计 ─────────
    file_expired_count = Counter()
    for s in expired_sections:
        file_expired_count[s["file"]] += 1

    # 如果一个文件的所有区块都过期，标记为可删除
    files_to_archive = []
    files_to_keep = []
    for fn in all_texts:
        total_secs = sum(1 for s in all_sections if s["file"] == fn)
        expired_secs = file_expired_count.get(fn, 0)
        if fn == "MEMORY.md":
            # MEMORY.md 不删除，但可以瘦身
            files_to_keep.append((fn, "永久文件"))
        elif total_secs > 0 and expired_secs == total_secs:
            files_to_archive.append((fn, f"全部{total_secs}区块过期"))
        else:
            files_to_keep.append((fn, f"{expired_secs}/{total_secs} 过期"))

    print("\n📋 文件处置:")
    for fn, reason in files_to_keep:
        print(f"   ✅ 保留: {fn:30s} ({reason})")
    for fn, reason in files_to_archive:
        print(f"   🗑️  归档: {fn:30s} ({reason})")

    # ───────── 4. 执行清理 ─────────
    # 创建归档目录
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    archived_files = []
    pruned_bytes = 0
    pruned_blocks = 0

    for fn, reason in files_to_archive:
        src = MEMORY_DIR / fn
        if src.exists():
            dst = ARCHIVE_DIR / fn
            content = src.read_text(encoding="utf-8")
            dst.write_text(content, encoding="utf-8")
            src.unlink()
            archived_files.append(fn)
            pruned_bytes += len(content.encode("utf-8"))
            pruned_blocks += file_expired_count.get(fn, 0)
            print(f"\n   📦 已归档: {fn} → archive/{fn} ({len(content.encode('utf-8')):,} bytes)")

    # ───────── 5. 重建 TF-IDF 索引 ─────────
    print("\n🔧 重建 TF-IDF 索引...")

    # 只索引活跃区块
    active_texts = []
    for s in active_sections:
        # 从源文本提取区块内容
        source_text = all_texts.get(s["file"], "")
        active_texts.append(source_text[:3000])  # 前3000字符

    active_texts_full = [all_texts.get(s["file"], "") for s in active_sections]

    index_entries = []
    for i, sec in enumerate(active_sections):
        source_text = all_texts.get(sec["file"], "")
        vec = compute_tfidf(source_text[:5000], active_texts_full)
        index_entries.append(
            {
                "id": f"{sec['file']}#{sec['hash']}",
                "file": sec["file"],
                "title": sec["title"],
                "category": sec["category"],
                "word_count": sec["word_count"],
                "vector": vec,
                "latest_date": sec["latest_date_ref"],
            }
        )

    # 写出索引
    index_data = {
        "built_at": now.isoformat(),
        "total_blocks": len(index_entries),
        "total_files": len(set(e["file"] for e in index_entries)),
        "entries": index_entries,
    }
    INDEX_PATH.write_text(json.dumps(index_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"   ✅ 索引已写入: {INDEX_PATH.name} ({len(index_entries)} 条目)")

    # ───────── 6. 输出统计 ─────────
    # 当前 memory 目录状态
    remaining_files = sorted(MEMORY_DIR.glob("*.md"))
    remaining_sizes = {f.name: f.stat().st_size for f in remaining_files}
    total_remaining = sum(remaining_sizes.values())
    total_original = sum(len(all_texts.get(fn, "").encode("utf-8")) for fn in all_texts)

    category_counts = Counter(s["category"] for s in active_sections)

    stats = {
        "timestamp": now.isoformat(),
        "memory_dir": str(MEMORY_DIR),
        "before": {
            "files": len(all_texts),
            "total_bytes": total_original,
            "total_blocks": len(all_sections),
        },
        "after": {
            "files": len(remaining_files),
            "total_bytes": total_remaining,
            "total_active_blocks": len(active_sections),
        },
        "cleanup": {
            "archived_files": archived_files,
            "archived_bytes": pruned_bytes,
            "pruned_blocks": pruned_blocks,
        },
        "active_block_categories": dict(category_counts),
    }

    STATS_PATH.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    # ───────── 7. 终端报告 ─────────
    print("\n" + "=" * 60)
    print("📊 维护摘要")
    print("=" * 60)
    print(f"  🗂️  维护前: {len(all_texts)} 文件, {total_original:,} bytes, {len(all_sections)} 区块")
    print(f"  🗂️  维护后: {len(remaining_files)} 文件, {total_remaining:,} bytes, {len(active_sections)} 活跃区块")
    if pruned_blocks:
        print(f"  🗑️  已清理: {len(archived_files)} 文件 ({pruned_blocks:,} 区块, {pruned_bytes:,} bytes)")
    else:
        print("  ✅ 无过期记忆，无需清理")
    print(f"  🔧 TF-IDF 索引: {len(index_entries)} 条目 → {INDEX_PATH.name}")
    print("  📈 活跃分类:")
    for cat, cnt in category_counts.most_common():
        print(f"     {cat:15s}: {cnt:4d} 区块")
    print(f"\n  📄 统计输出: {STATS_PATH.name}")
    print(f"  📦 归档目录: {ARCHIVE_DIR}/")
    print("\n✨ 完成！")

    return stats


if __name__ == "__main__":
    main()
