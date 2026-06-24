#!/usr/bin/env python3
"""Kairos 定时任务注册到 OpenClaw cron

把 kairos_scheduler.py 里的 7 个预置任务转换成 OpenClaw cron job，
让猫抓 7x24 小时真正自己跑起来。

⭐ 注意: 这个脚本不需要自己写 cron 格式，它输出任务清单。
   实际注册通过 OpenClaw 内置的 cron tool 完成。
"""

import json
import pathlib
import sys

CORE = pathlib.Path(__file__).resolve().parents[1] / "v1.1-self-evo-factory"
sys.path.insert(0, str(CORE))

from core.secrets.kairos_scheduler import KairosScheduler


def main():
    print("⏰ Kairos → OpenClaw Cron 注册器")
    print("=" * 55)

    scheduler = KairosScheduler()
    tasks = scheduler.list_tasks()

    print(f"\n  共 {len(tasks)} 个任务:\n")

    # 按触发类型分组
    cron_jobs = []
    interval_jobs = []

    for task in tasks:
        orig = scheduler.tasks[task["id"]]
        name = task["name"]
        tid = task["id"]
        trigger_type = task["trigger"]
        enabled = task["enabled"]

        status_icon = "✅" if enabled else "⛔"
        print(f"  {status_icon} [{tid}] {name}")
        print(f"     触发: {trigger_type}")
        print(f"     动作: {orig.action[:100]}...")

        if trigger_type == "cron":
            cron_expr = orig.trigger.config.get("cron", "0 9 * * *")
            tz = orig.trigger.config.get("tz", "Asia/Shanghai")
            print(f"     Cron: {cron_expr} ({tz})")

            cron_jobs.append(
                {
                    "name": name,
                    "id": tid,
                    "schedule": {"kind": "cron", "expr": cron_expr, "tz": tz},
                    "payload": {
                        "kind": "agentTurn",
                        "message": f"执行 Kairos 任务: {name} — {orig.action}",
                        "lightContext": True,
                    },
                    "sessionTarget": "isolated",
                    "enabled": enabled,
                    "delivery": {"mode": "none"},
                }
            )

        elif trigger_type == "interval":
            interval_sec = orig.trigger.config.get("interval_seconds", 3600)
            interval_ms = interval_sec * 1000
            print(f"    间隔: {interval_sec}s = {interval_sec / 3600:.1f}h")

            interval_jobs.append(
                {
                    "name": name,
                    "id": tid,
                    "schedule": {"kind": "every", "everyMs": interval_ms},
                    "payload": {
                        "kind": "agentTurn",
                        "message": f"执行 Kairos 任务: {name} — {orig.action}",
                        "lightContext": True,
                    },
                    "sessionTarget": "isolated",
                    "enabled": enabled,
                    "delivery": {"mode": "none"},
                }
            )

        print()

    # 输出注册清单
    print("=" * 55)
    print("📋 任务分类:")
    print(f"   Cron 定时任务: {len(cron_jobs)} 个")
    print(f"   间隔任务:       {len(interval_jobs)} 个")
    print(f"   启用/总数:      {sum(1 for t in tasks if t['enabled'])}/{len(tasks)}")

    # 输出部署指南
    print(f"\n{'=' * 55}")
    print("🚀 部署指南")
    print("=" * 55)
    print("""
这些任务需要通过 OpenClaw 的 cron tool 注册。

方法 1: 在当前会话告诉 AI:
  "帮我把 Kairos 的 7 个预置任务注册到 OpenClaw cron"

方法 2: 手动用 cron 命令注册每个任务:
  - daily_report:     每天 9:00 (Asia/Shanghai)
  - github_watchdog:  每小时
  - memory_maintenance: 每天 2:00
  - skill_health_check: 每 4 小时
  - cost_report:      每天 18:00
  - security_scan:    每天 3:00
  - git_auto_commit:  每小时 (默认关闭)

方法 3: 运行下面的 Python 代码在当前会话注册

📊 注册数据结构见下方 JSON:
""")
    print(
        json.dumps(
            {
                "cron_jobs": cron_jobs,
                "interval_jobs": interval_jobs,
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    # 更新 Kairos 状态
    scheduler._save_state()

    return 0


if __name__ == "__main__":
    sys.exit(main())
