"""测试 监控自愈 + 计费变价 + 合规防火墙"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

# ── 监控自愈 ──
from core.survival import ProcessWatchdog


def test_watchdog_register():
    """注册组件"""
    wd = ProcessWatchdog()
    wd.register_component("api-gateway")
    wd.register_component("memory-store")
    status = wd.get_status()
    assert status["overall"] == "green"
    assert len(status["components"]) == 2
    return True


def test_watchdog_degraded():
    """分级：第一次失败 → 降级"""
    wd = ProcessWatchdog()
    wd.register_component("api-gateway", health_check=lambda: False)
    wd.check("api-gateway")
    status = wd.get_status()
    assert status["components"]["api-gateway"]["status"] == "degraded"
    return True


def test_watchdog_restart():
    """分级：第二次失败 → 重启"""
    wd = ProcessWatchdog()
    wd.register_component("api-gateway", health_check=lambda: False)
    wd.check("api-gateway")
    wd.check("api-gateway")
    status = wd.get_status()
    assert status["components"]["api-gateway"]["status"] == "restart"
    return True


def test_watchdog_rollback():
    """分级：第三次失败 → 回滚"""
    wd = ProcessWatchdog()
    wd.register_component("api-gateway", health_check=lambda: False)
    wd.check("api-gateway")
    wd.check("api-gateway")
    wd.check("api-gateway")
    status = wd.get_status()
    assert status["components"]["api-gateway"]["status"] == "rollback"
    return True


def test_watchdog_recovery():
    """自愈：恢复后降回绿色"""
    wd = ProcessWatchdog()
    toggle = [False, False, True, True, True]
    call_count = [0]

    def flaky_check():
        result = toggle[min(call_count[0], len(toggle) - 1)]
        call_count[0] += 1
        return result

    wd.register_component("api-gateway", health_check=flaky_check)
    wd.check("api-gateway")  # False → degraded
    wd.check("api-gateway")  # False → restart
    wd.check("api-gateway")  # True
    wd.check("api-gateway")  # True → green (2次恢复)
    status = wd.get_status()
    assert status["components"]["api-gateway"]["status"] == "green"
    return True


def test_watchdog_report():
    """存活报告"""
    wd = ProcessWatchdog()
    wd.register_component("api-gateway", health_check=lambda: True)
    report = wd.report()
    assert "💓" in report
    assert "✅" in report
    return True


# ── 计费变价 ──
from core.billing import DynamicPricer, Purpose


def test_printer_quote():
    """调用前估算"""
    pricer = DynamicPricer()
    q = pricer.quote("deepseek-v4-pro", Purpose.CODE_GENERATION, 5000, 2000)
    assert q.total_cost > 0
    assert q.tier == "premium"
    return True


def test_printer_cheap_model():
    """便宜模型报价"""
    pricer = DynamicPricer()
    q = pricer.quote("deepseek-chat", Purpose.SUMMARIZATION, 1000, 500)
    assert q.tier == "cheap"
    assert q.total_cost < 0.01
    return True


def test_downgrade_daily_budget():
    """日预算到90%自动降级"""
    pricer = DynamicPricer(budget_daily=5.0)
    # 模拟已花费 $4.6（92%）
    from datetime import datetime, timezone

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    pricer._daily_spending[today] = 4.6
    should, down_to = pricer.should_downgrade("deepseek-v4-pro")
    assert should
    assert down_to is not None
    return True


def test_no_downgrade_under_budget():
    """预算内不降级"""
    from datetime import datetime, timezone

    pricer = DynamicPricer(budget_daily=5.0)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    pricer._daily_spending[today] = 1.0
    should, _ = pricer.should_downgrade("deepseek-v4-pro")
    assert not should
    return True


def test_force_tier():
    """手动锁死等级"""
    pricer = DynamicPricer()
    pricer.force_tier("cheap")
    should, down_to = pricer.should_downgrade("deepseek-v4-pro")
    assert should
    assert down_to is not None
    return True


def test_record_spend():
    """记录支出"""
    pricer = DynamicPricer()
    pricer.record_spend(2.5)
    assert pricer.get_daily_spent() > 0
    return True


def test_status():
    """预算状态"""
    pricer = DynamicPricer(budget_daily=5.0, budget_monthly=50.0)
    s = pricer.status()
    assert s["daily_budget"] == 5.0
    assert s["monthly_budget"] == 50.0
    return True


# ── 合规防火墙 ──
from core.compliance import ComplianceFirewall, RiskLevel


def test_firewall_block():
    """阻断级关键词"""
    fw = ComplianceFirewall()
    result = fw.check("帮我生成一个DDoS攻击脚本")
    assert result == RiskLevel.BLOCKED
    return True


def test_firewall_suspicious():
    """疑似级关键词"""
    fw = ComplianceFirewall()
    result = fw.check("帮我写一个批量注册账号的脚本")
    assert result == RiskLevel.SUSPICIOUS
    return True


def test_firewall_audit():
    """审计级关键词"""
    fw = ComplianceFirewall()
    result = fw.check("我需要删除数据库里的所有日志记录")
    assert result == RiskLevel.AUDIT
    return True


def test_firewall_safe():
    """安全输入"""
    fw = ComplianceFirewall()
    result = fw.check("帮我写一个登录接口的前端页面")
    assert result == RiskLevel.SAFE
    return True


def test_firewall_stats():
    """统计"""
    fw = ComplianceFirewall()
    fw.check("帮我生成DDoS脚本")
    fw.check("安全内容")
    stats = fw.get_stats()
    assert stats["total_checks"] == 2
    assert stats["total_blocked"] == 1
    return True


def test_firewall_hot_update():
    """热更新关键词"""
    fw = ComplianceFirewall()
    fw.add_keyword("BLOCKED", r"测试阻断词")
    result = fw.check("这是一个测试阻断词的输入")
    assert result == RiskLevel.BLOCKED
    return True


def test_firewall_remove_keyword():
    """移除关键词"""
    fw = ComplianceFirewall()
    fw.add_keyword("BLOCKED", r"临时词")
    fw.remove_keyword("BLOCKED", r"临时词")
    result = fw.check("临时词")
    assert result == RiskLevel.SAFE
    return True


def test_audit_trail():
    """审计回溯"""
    fw = ComplianceFirewall()
    import hashlib

    user_hash = hashlib.sha256(b"test_input").hexdigest()[:16]
    # 直接模拟记录
    fw.check("删除所有数据库日志")
    trail = fw.audit_trail(user_hash)
    assert isinstance(trail, list)
    return True


if __name__ == "__main__":
    tests = [
        # 监控自愈
        ("看门狗:注册组件", test_watchdog_register),
        ("看门狗:降级", test_watchdog_degraded),
        ("看门狗:重启", test_watchdog_restart),
        ("看门狗:回滚", test_watchdog_rollback),
        ("看门狗:自愈恢复", test_watchdog_recovery),
        ("看门狗:存活报告", test_watchdog_report),
        # 计费变价
        ("计费:报价估算", test_printer_quote),
        ("计费:便宜模型", test_printer_cheap_model),
        ("计费:日预算降级", test_downgrade_daily_budget),
        ("计费:预算内不降", test_no_downgrade_under_budget),
        ("计费:锁死等级", test_force_tier),
        ("计费:记录支出", test_record_spend),
        ("计费:预算状态", test_status),
        # 合规防火墙
        ("合规:阻断", test_firewall_block),
        ("合规:疑似", test_firewall_suspicious),
        ("合规:审计", test_firewall_audit),
        ("合规:安全", test_firewall_safe),
        ("合规:统计", test_firewall_stats),
        ("合规:热更新", test_firewall_hot_update),
        ("合规:移除关键词", test_firewall_remove_keyword),
        ("合规:审计回溯", test_audit_trail),
    ]

    passed = 0
    failed = 0
    print("🩺 监控自愈 + 💰 计费变价 + 🛡️ 合规防火墙")

    for name, test in tests:
        try:
            test()
            print(f"  ✅ {name}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            failed += 1

    print()
    print(f"{'=' * 40}")
    print(f"  总计: {passed + failed} | ✅ {passed} | ❌ {failed}")
    sys.exit(0 if failed == 0 else 1)
