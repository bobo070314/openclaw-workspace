#!/usr/bin/env python3
"""记忆库冷启动 — 把 MEMORY.md 的 2000+ 行历史记忆灌入4类记忆库

原理：
1. 按 Markdown 标题拆 MEMORY.md 为段落
2. 根据内容特征自动分类（IDENTITY/CORRECTIONS/PROJECT/ROUTING）
3. 用 MemoryStore + MemoryIndex 入库
4. 打印统计确认灌入结果
"""

import pathlib
import sys
from datetime import timezone

# 确保能导入 core 模块
CORE = pathlib.Path(__file__).resolve().parents[1] / "v1.1-self-evo-factory"
sys.path.insert(0, str(CORE))

from core.memory.memory_index import MemoryIndex
from core.memory.memory_types import MemoryEntry, MemoryStore, MemoryType

UTC = timezone.utc

MEMORY_FILE = pathlib.Path("D:/bobo/openclaw-foreign/workspace/MEMORY.md")
STORE_PATH = pathlib.Path("D:/bobo/openclaw-foreign/workspace/states/memory_store.json")


# ── 分类规则：根据段落内容特征自动归类 ──


def classify_paragraph(paragraph: str) -> MemoryType:
    """根据内容特征推断4类归属"""
    text = paragraph.lower()

    # CORRECTIONS: 包含纠正/教训/踩坑/不要/别再等关键词
    correction_keywords = [
        "踩过的坑",
        "别再犯",
        "教训",
        "修复方案",
        "坑点",
        "不要用",
        "不能",
        "禁止",
        "修复:",
        "替代方案",
        "注意事项",
        "⚠️",
        "🚨",
    ]
    for kw in correction_keywords:
        if kw in text:
            return MemoryType.CORRECTIONS

    # ROUTING: 包含路径/命令/配置/工具/端口等
    routing_keywords = [
        "路径",
        "命令",
        "CLI",
        "配置",
        "端口",
        "D:\\",
        "package.json",
        "git clone",
        "pip install",
        "npm install",
        "python ",
        "node ",
    ]
    routing_score = sum(1 for kw in routing_keywords if kw in text)
    if routing_score >= 2 and len(text) < 500:
        return MemoryType.ROUTING

    # PROJECT: 包含项目状态/进度/提交/版本等
    project_keywords = [
        "项目",
        "提交",
        "commit",
        "tag",
        "版本",
        "v1.",
        "v2.",
        "v3.",
        "v4.",
        "v5.",
        "✅",
        "🔥",
        "issue",
        "PR",
        "merge",
        "deploy",
        "部署",
        "build",
    ]
    for kw in project_keywords:
        if kw in text:
            return MemoryType.PROJECT

    # IDENTITY: 默认归类为用户身份/偏好
    return MemoryType.IDENTITY


def parse_memory_md(filepath: pathlib.Path) -> list[dict]:
    """解析 MEMORY.md，按 Markdown 结构拆分为段落"""
    content = filepath.read_text(encoding="utf-8")
    lines = content.split("\n")

    paragraphs = []
    current_title = "根"
    current_lines = []

    for line in lines:
        stripped = line.strip()

        # H2 标题 = 新段落开始
        if stripped.startswith("## "):
            # 保存上一个段落
            if current_lines:
                text = "\n".join(current_lines).strip()
                if len(text) > 30:  # 跳过太短的
                    # 如果段落很长（>800字），按空行再拆
                    if len(text) > 800:
                        sub_paras = text.split("\n\n")
                        for sp in sub_paras:
                            sp = sp.strip()
                            if len(sp) > 30:
                                paragraphs.append(
                                    {
                                        "title": current_title,
                                        "content": sp,
                                    }
                                )
                    else:
                        paragraphs.append(
                            {
                                "title": current_title,
                                "content": text,
                            }
                        )
            current_title = stripped.replace("## ", "").strip()
            current_lines = []
        elif stripped.startswith("### "):
            # H3 作为子标题，不另起段落
            current_lines.append(line)
        elif stripped.startswith("# "):
            current_title = stripped.replace("# ", "").strip()
        else:
            current_lines.append(line)

    # 最后一个段落
    if current_lines:
        text = "\n".join(current_lines).strip()
        if len(text) > 30:
            if len(text) > 800:
                sub_paras = text.split("\n\n")
                for sp in sub_paras:
                    sp = sp.strip()
                    if len(sp) > 30:
                        paragraphs.append(
                            {
                                "title": current_title,
                                "content": sp,
                            }
                        )
            else:
                paragraphs.append(
                    {
                        "title": current_title,
                        "content": text,
                    }
                )

    return paragraphs


def main():
    if not MEMORY_FILE.exists():
        print(f"🚨 错误: {MEMORY_FILE} 不存在")
        return 1

    print(f"📖 读取 {MEMORY_FILE} ...")
    print(f"   文件大小: {MEMORY_FILE.stat().st_size / 1024:.1f} KB")

    print("🧠 解析记忆段落...")
    paragraphs = parse_memory_md(MEMORY_FILE)
    print(f"   解析出 {len(paragraphs)} 个段落")

    print("💾 初始化记忆存储...")
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    store = MemoryStore(str(STORE_PATH))
    index = MemoryIndex()

    # 加载已有记忆
    existing_ids = set(store.entries.keys())
    print(f"   现有记忆: {len(existing_ids)} 条")

    print("📥 开始分类灌入...")
    by_type = {t: 0 for t in MemoryType}
    new_count = 0
    dedup_count = 0

    for i, para in enumerate(paragraphs):
        mem_type = classify_paragraph(para["content"])
        by_type[mem_type] += 1

        # 生成摘要：用标题+内容前100字做记忆内容
        summary = f"[{para['title']}] {para['content'][:300]}"

        entry_id = MemoryEntry.generate_id(mem_type, summary)

        if entry_id in existing_ids:
            dedup_count += 1
            continue

        entry = MemoryEntry(
            id=entry_id,
            type=mem_type,
            content=summary,
            source="memory_cold_start",
            tags=[para["title"][:50]],
            importance=0.9,  # 历史记忆权重高
        )
        store.add(entry)
        index.add(entry)
        new_count += 1

        if (i + 1) % 20 == 0:
            print(f"   进度: {i + 1}/{len(paragraphs)}")

    print(f"\n   ✅ 新增 {new_count} 条，去重跳过 {dedup_count} 条")

    # 重新构建索引（确保一致性）
    print("🔍 重建检索索引...")
    index.rebuild(list(store.entries.values()))
    print(f"   索引大小: {index.size()} 条")

    print("\n" + "=" * 50)
    print("📊 记忆库冷启动报告")
    print("=" * 50)
    print(f"  总记忆数: {len(store.entries)}")
    for t in MemoryType:
        count = sum(1 for e in store.entries.values() if e.type == t)
        label = {
            MemoryType.IDENTITY: "身份/偏好",
            MemoryType.CORRECTIONS: "纠正/教训",
            MemoryType.PROJECT: "项目状态",
            MemoryType.ROUTING: "路径/路由",
        }[t]
        bar = "█" * min(count, 50)
        print(f"  [{label:12s}] {count:4d} 条 {bar}")

    print(f"\n  Store 路径: {STORE_PATH}")
    print(f"  索引条目: {index.size()}")

    # 快速验证：检索几个关键词
    print("\n🔍 快速验证检索:")
    test_queries = ["技术栈", "项目路径", "踩坑", "端口", "git push"]
    for q in test_queries:
        results = index.search(q, top_k=2)
        count = len(results)
        print(f"  '{q}' → {count} 条结果")

    print("\n✅ 记忆库冷启动完成！")
    return 0


if __name__ == "__main__":
    sys.exit(main())
