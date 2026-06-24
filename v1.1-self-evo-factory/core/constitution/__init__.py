"""宪法即代码 — 代码生成时的实时宪法拦截器

对标 Claude Code 的宪法系统：
1. 每条宪法规则是代码，不是文档
2. 代码生成时（不是事后）实时检查
3. 违规后给出修正指引，不只是拒绝
4. 支持项目自定义宪法

核心流程：
代码片段 → 宪法检查器(24条规则) → 违规列表 → 自动修复(可选) → OK代码
"""

from .constitutional_checker import ConstitutionalChecker, ConstitutionalRule, RuleCategory, RuleViolation, Severity

__all__ = [
    "ConstitutionalChecker",
    "ConstitutionalRule",
    "RuleViolation",
    "Severity",
    "RuleCategory",
]
