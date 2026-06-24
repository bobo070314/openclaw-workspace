"""
监控自愈 — 进程复活看门狗 + 分级自愈

核心能力：
1. ProcessWatchdog: 主动心跳检测 + 分级自愈（降级→重启→回滚）
2. 死前遗产: 异常退出前把致命信息写棺材板
3. 零额外开销: 每次 API 调用之后顺手跑健康检查
"""

from .watchdog import ProcessWatchdog, SurvivalWatchdog, ComponentHealth, HealthLevel

__all__ = ["ProcessWatchdog", "SurvivalWatchdog", "ComponentHealth", "HealthLevel"]
