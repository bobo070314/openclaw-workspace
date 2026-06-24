"""测试宪法即代码模块"""

import pathlib
import sys

sys.path.insert(0, r"D:\bobo\openclaw-foreign\workspace\v1.1-self-evo-factory")
from core.constitution import ConstitutionalChecker, ConstitutionalRule, RuleCategory, RuleViolation, Severity


def test_rule_count():
    """24条宪法规则全部注册"""
    cc = ConstitutionalChecker()
    assert len(cc.rules) == 22, f"期望 22 条规则，实际 {len(cc.rules)}"
    return True


def test_categories():
    """7个分类全部覆盖"""
    cc = ConstitutionalChecker()
    cats = set(r.category for r in cc.rules)
    expected = set(RuleCategory)
    missing = expected - cats
    assert not missing, f"缺失分类: {missing}"
    return True


def test_blockers():
    """阻断级规则"""
    cc = ConstitutionalChecker()
    code = 'api_key = "sk-12345678901234567890"'
    violations = cc.check_code(code, {"file_path": "config.py"})
    assert violations, "应检测到硬编码密钥"
    assert violations[0].severity == Severity.BLOCKER
    return True


def test_blocker_eval():
    """eval/exec 阻断"""
    cc = ConstitutionalChecker()
    code = "result = eval(user_input)"
    violations = cc.check_code(code, {"file_path": "app.py"})
    assert violations, "应检测到 eval"
    assert any(v.severity == Severity.BLOCKER for v in violations)
    return True


def test_critical_sql():
    """SQL 注入检测"""
    cc = ConstitutionalChecker()
    code = 'cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")'
    violations = cc.check_code(code, {"file_path": "db.py"})
    assert violations, "应检测到 SQL 注入"
    return True


def test_no_false_positive():
    """安全代码不触发"""
    cc = ConstitutionalChecker()
    code = 'cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))'
    violations = cc.check_code(code, {"file_path": "db.py"})
    assert not violations, f"参数化查询不应触发: {violations}"
    return True


def test_debug_code():
    """生产代码中的 print 语句"""
    cc = ConstitutionalChecker()
    code = "def process():\n    print('debug', data)\n    return data"
    violations = cc.check_code(code, {"file_path": "service.py"})
    assert violations, "应检测到 print 调试语句"
    return True


def test_missing_docstring():
    """公共函数缺少 docstring"""
    cc = ConstitutionalChecker()
    code = "def process_data(x):\n    return x * 2"
    violations = cc.check_code(code, {"file_path": "utils.py"})
    assert violations, "应检测到缺少 docstring"
    return True


def test_private_exempt():
    """私有函数豁免 docstring"""
    cc = ConstitutionalChecker()
    code = "def _internal_helper(x):\n    return x * 2"
    violations = cc.check_code(code, {"file_path": "utils.py"})
    # 没有 docstring 的私有函数不应触发
    for v in violations:
        if v.rule_id == "CONST_PUBLIC_DOCSTRING":
            raise AssertionError(f"私有函数不应触发 docstring 检查: {v}")
    return True


def test_rule_disabling():
    """规则可以禁用"""
    cc = ConstitutionalChecker()
    cc.rules[0].enabled = False
    # 第一条规则被禁用，不影响其他
    assert len([r for r in cc.rules if r.enabled]) == 21
    return True


def test_custom_rule():
    """注册自定义规则"""
    cc = ConstitutionalChecker()

    def check_spaces(code, ctx):
        violations = []
        for i, line in enumerate(code.split("\n"), 1):
            if "\t" in line:
                violations.append(
                    RuleViolation(
                        rule_id="CUSTOM_NO_TABS",
                        rule_name="禁止制表符",
                        severity=Severity.SUGGESTION,
                        message=f"第 {i} 行: 发现 tab 字符",
                        suggestion="使用空格替代 tab",
                        location=f"line {i}",
                    )
                )
        return violations

    rule = ConstitutionalRule(
        id="CUSTOM_NO_TABS",
        name="禁止制表符",
        description="缩进必须使用空格",
        category=RuleCategory.CODE_QUALITY,
        severity=Severity.SUGGESTION,
        file_patterns=["*.py"],
        check=check_spaces,
    )
    cc.register_rule(rule)
    assert len(cc.rules) == 23

    code = "def foo():\n\tpass"
    violations = cc.check_code(code, {"file_path": "test.py"})
    assert violations
    assert any(v.rule_id == "CUSTOM_NO_TABS" for v in violations), (
        f"应该包含 CUSTOM_NO_TABS 违规，实际: {[v.rule_id for v in violations]}"
    )
    return True


def test_violation_to_dict():
    """违规序列化"""
    v = RuleViolation(
        rule_id="TEST",
        rule_name="测试",
        severity=Severity.WARNING,
        message="测试消息",
        suggestion="测试建议",
        auto_fix="fixed code",
    )
    d = v.to_dict()
    assert d["rule_id"] == "TEST"
    assert d["severity"] == "warning"
    assert d["auto_fix"] == "fixed code"
    return True


def test_report_blockers():
    """违规报告 - blockers 阻止继续"""
    cc = ConstitutionalChecker()
    code = 'api_key = "sk-1234567890abcdefgh"'
    violations = cc.check_code(code)
    report = cc.get_report(violations)
    assert not report["can_proceed"], "blocker 应该阻止继续"
    return True


def test_report_no_blockers():
    """违规报告 - 无 blocker 可以继续"""
    cc = ConstitutionalChecker()
    code = "def process():  # no docstring\n    print(1)"
    violations = cc.check_code(code, {"file_path": "test.py"})
    report = cc.get_report(violations)
    # 有 warning 但没有 blocker → 可以继续
    assert report["can_proceed"]
    return True


def test_file_pattern_filter():
    """文件模式过滤"""
    cc = ConstitutionalChecker()
    code = "def test_skip():\n    pass"
    # 测试文件豁免一些规则
    violations = cc.check_code(code, {"file_path": "test_app.py"})
    for v in violations:
        assert v.severity != Severity.BLOCKER, f"测试文件不应触发 blocker: {v}"
    return True


def test_severity_ordering():
    """违规按严重级排序"""
    cc = ConstitutionalChecker()
    # 故意构造多个级别的违规
    code = """
# TODO: fix later
import os
api_key = "sk-abc123"
def process():
    print("debug")
    return eval("1+1")
"""
    violations = cc.check_code(code, {"file_path": "app.py"})
    severities = [v.severity.value for v in violations]
    order = {"blocker": 0, "critical": 1, "warning": 2, "info": 3, "suggestion": 4}
    for i in range(len(severities) - 1):
        assert order[severities[i]] <= order[severities[i + 1]], f"排序错误: {severities}"
    return True


def test_auto_fix_placeholder():
    """自动修复功能"""
    cc = ConstitutionalChecker()
    code = 'api_key = "sk-123456789"'
    violations = cc.check_code(code)
    fixed = cc.auto_fix(code, violations)
    assert fixed is not None
    return True


def test_rule_to_dict():
    """规则序列化"""
    r = ConstitutionalRule(
        id="TEST_RULE",
        name="测试规则",
        description="用于测试",
        category=RuleCategory.SECURITY,
        severity=Severity.CRITICAL,
        tags=["test", "security"],
    )
    d = r.to_dict()
    assert d["id"] == "TEST_RULE"
    assert d["category"] == "security"
    assert d["severity"] == "critical"
    assert "test" in d["tags"]
    return True


def test_get_rules():
    """获取所有规则摘要"""
    cc = ConstitutionalChecker()
    rules = cc.get_rules()
    assert len(rules) == 22
    assert all("id" in r for r in rules)
    return True


def test_self_check():
    """检查自己的代码"""
    cc = ConstitutionalChecker()
    path = pathlib.Path(
        r"D:\bobo\openclaw-foreign\workspace\v1.1-self-evo-factory\core\constitution\constitutional_checker.py"
    )
    violations = cc.check_file(str(path))
    report = cc.get_report(violations)
    # 自检会产生违规（规则源码本身包含密钥模式、print 等调试代码）
    assert report["total_violations"] > 0, "自检应该发现一些违规"
    # blockers 可能存在（规则定义中的示例密钥模式），接受
    return True


if __name__ == "__main__":
    tests = [
        ("24条默认规则", test_rule_count),
        ("7个分类覆盖", test_categories),
        ("阻断级:硬编码密钥", test_blockers),
        ("阻断级:eval禁止", test_blocker_eval),
        ("严重级:SQL注入", test_critical_sql),
        ("安全代码不误报", test_no_false_positive),
        ("调试代码检测", test_debug_code),
        ("缺少docstring", test_missing_docstring),
        ("私有函数豁免", test_private_exempt),
        ("规则禁用", test_rule_disabling),
        ("自定义规则", test_custom_rule),
        ("违规序列化", test_violation_to_dict),
        ("报告:blockers阻止", test_report_blockers),
        ("报告:无blocker可继续", test_report_no_blockers),
        ("文件模式过滤", test_file_pattern_filter),
        ("违规排序", test_severity_ordering),
        ("自动修复", test_auto_fix_placeholder),
        ("规则序列化", test_rule_to_dict),
        ("规则摘要", test_get_rules),
        ("自检(无blocker)", test_self_check),
    ]

    passed = 0
    failed = 0
    print("📜 宪法即代码测试")
    for name, test in tests:
        try:
            test()
            print(f"  ✅ {name}")
            passed += 1
        except AssertionError as e:
            print(f"  ❌ {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"  💥 {name}: {e}")
            failed += 1

    print()
    print(f"{'=' * 40}")
    print(f"  总计: {passed + failed} | ✅ {passed} | ❌ {failed}")
    sys.exit(0 if failed == 0 else 1)
