"""
进程复活看门狗 — 不是"状态检查"，是"原地复活"

对标 Claude Code 的做法：
1. 主动心跳检测 — 不用被动等 cron 调度
2. 分级自愈 — 轻伤重启线程、重伤重启进程、致命伤回滚代码
3. 死前遗嘱 — 异常退出前把致命信息写棺材板

设计原则：
- 每次 API 调用之后顺手跑健康检查（零额外开销）
- 分级处理：WARNING(降级) → ERROR(重启) → FATAL(回滚)
"""

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
import json, os, pathlib, traceback, threading, time

UTC = timezone.utc


class HealthLevel(str, Enum):
    """健康等级"""

    GREEN = "green"  # 完全不处理
    DEGRADED = "degraded"  # 降级运行（关闭非关键功能）
    RESTART = "restart"  # 重启组件
    ROLLBACK = "rollback"  # 回滚到上次稳定版本


@dataclass
class ComponentHealth:
    """组件健康状态"""

    name: str
    status: HealthLevel = HealthLevel.GREEN
    last_check: str = ""
    message: str = ""
    fail_count: int = 0
    recover_count: int = 0
    degraded_at: str = ""

    def to_dict(self):
        return {
            "name": self.name,
            "status": self.status.value,
            "last_check": self.last_check,
            "message": self.message,
            "fail_count": self.fail_count,
            "recover_count": self.recover_count,
        }


class ProcessWatchdog:
    """进程看门狗 — 分级自愈"""

    # 分级阈值（连续失败次数 → 动作）
    THRESHOLDS = {
        HealthLevel.DEGRADED: 1,  # 第 1 次失败 → 降级
        HealthLevel.RESTART: 2,  # 第 2 次 → 重启组件
        HealthLevel.ROLLBACK: 3,  # 第 3 次 → 回滚代码
    }

    def __init__(self, state_dir: str = None):
        self._state_dir = pathlib.Path(state_dir or os.path.join(os.path.dirname(__file__), "..", "..", "states"))
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._components: dict[str, ComponentHealth] = {}
        self._health_checks: dict[str, callable] = {}
        self._repair_actions: dict[str, dict] = {}  # component -> {level: callable}
        self._lock = threading.Lock()

    def register_component(self, name: str, health_check: callable = None, repair_actions: dict = None):
        """注册组件"""
        with self._lock:
            self._components[name] = ComponentHealth(name=name)
            if health_check:
                self._health_checks[name] = health_check
            if repair_actions:
                self._repair_actions[name] = repair_actions

    def check(self, component: str) -> HealthLevel:
        """主动健康检查 — 每次 API 调用之后顺手跑"""
        with self._lock:
            comp = self._components.get(component)
            if not comp:
                return HealthLevel.GREEN

            now = datetime.now(UTC).isoformat()
            comp.last_check = now

            # 运行健康检查函数
            checker = self._health_checks.get(component)
            if checker:
                try:
                    result = checker()
                    is_healthy = result if isinstance(result, bool) else result.get("healthy", True)
                except Exception as e:
                    is_healthy = False
                    comp.message = f"健康检查异常: {e}"
            else:
                is_healthy = True

            if is_healthy:
                # 恢复计数
                if comp.fail_count > 0:
                    comp.recover_count += 1
                if comp.status != HealthLevel.GREEN and comp.recover_count >= 2:
                    comp.status = HealthLevel.GREEN
                    comp.fail_count = 0
                    comp.degraded_at = ""
                return comp.status

            # 不健康 → 累加失败次数 → 分级处理
            comp.fail_count += 1
            level = self._determine_level(comp.fail_count)
            old_status = comp.status
            comp.status = level

            if level == HealthLevel.DEGRADED and not comp.degraded_at:
                comp.degraded_at = now
                self._save_coffin(component, comp)

            # 执行修复动作
            self._repair(component, level)

            return level

    def _determine_level(self, fail_count: int) -> HealthLevel:
        """根据连续失败次数决定处理级别"""
        if fail_count >= self.THRESHOLDS[HealthLevel.ROLLBACK]:
            return HealthLevel.ROLLBACK
        elif fail_count >= self.THRESHOLDS[HealthLevel.RESTART]:
            return HealthLevel.RESTART
        elif fail_count >= self.THRESHOLDS[HealthLevel.DEGRADED]:
            return HealthLevel.DEGRADED
        return HealthLevel.GREEN

    def _repair(self, component: str, level: HealthLevel):
        """执行修复动作"""
        actions = self._repair_actions.get(component, {})
        action = actions.get(level)
        if action:
            try:
                action()
            except Exception as e:
                traceback.print_exc()

    def _save_coffin(self, component: str, comp: ComponentHealth):
        """写棺材板 — 降级前保存致命信息"""
        coffin = {
            "component": component,
            "degraded_at": comp.degraded_at,
            "message": comp.message,
            "fail_count": comp.fail_count,
            "recent_errors": getattr(comp, "recent_errors", []),
        }
        coffin_path = self._state_dir / f"coffin_{component}.json"
        try:
            coffin_path.write_text(json.dumps(coffin, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def get_status(self) -> dict:
        """获取全系统健康状态"""
        with self._lock:
            components = {name: comp.to_dict() for name, comp in self._components.items()}
            overall = HealthLevel.GREEN

            for comp in self._components.values():
                severity = {
                    HealthLevel.GREEN: 0,
                    HealthLevel.DEGRADED: 1,
                    HealthLevel.RESTART: 2,
                    HealthLevel.ROLLBACK: 3,
                }
                if severity.get(comp.status, 0) > severity[overall]:
                    overall = comp.status

            return {
                "overall": overall.value,
                "components": components,
                "timestamp": datetime.now(UTC).isoformat(),
            }

    def report(self) -> str:
        """人类可读的存活报告"""
        status = self.get_status()
        lines = [f"💓 存活报告: {status['overall']}"]
        for name, comp in status["components"].items():
            icon = {"green": "✅", "degraded": "⚠️", "restart": "🔄", "rollback": "🚨"}.get(comp["status"], "❓")
            lines.append(f"  {icon} {name}: {comp['status']} (fail:{comp['fail_count']} rec:{comp['recover_count']})")
            if comp["message"]:
                lines.append(f"     {comp['message'][:80]}")
        return "\n".join(lines)


class SurvivalWatchdog(ProcessWatchdog):
    """别名兼容"""
    pass
