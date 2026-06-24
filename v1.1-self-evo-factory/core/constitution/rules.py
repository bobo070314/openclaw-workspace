"""宪法规则定义 — 每条宪法规则 = 可执行函数 + 触发条件 + 违规动作

Claude Code 的宪法不是"文档"，而是"代码"：
1. 每条规则都是一个可执行函数
2. 规则在代码生成时自动触发
3. 违规后自动给出修正指引，不只是"拒绝"

数据模型：
- Rule: 单条宪法规则
- RuleCategory: 规则分类（编码/安全/架构/文档/依赖）
- Severity: 违规严重级别
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional


class RuleCategory(str, Enum):
    """规则分类"""

    CODE_QUALITY = "code_quality"  # 代码质量（命名/结构/注释）
    SECURITY = "security"  # 安全（注入/泄漏/权限）
    ARCHITECTURE = "architecture"  # 架构（依赖/分层/接口）
    DOCUMENTATION = "documentation"  # 文档（注释/README/API文档）
    DEPENDENCY = "dependency"  # 依赖管理（版本/许可证/安全）
    TESTING = "testing"  # 测试（覆盖率/边界/性能）
    DATA = "data"  # 数据处理（隐私/加密/备份）


class Severity(str, Enum):
    """违规严重级别"""

    BLOCKER = "blocker"  # 阻断：必须修复才能继续
    CRITICAL = "critical"  # 严重：自动修复或人工确认
    WARNING = "warning"  # 警告：记录但不阻断
    INFO = "info"  # 信息：仅记录
    SUGGESTION = "suggestion"  # 建议：优化建议


@dataclass
class RuleViolation:
    """规则违规记录"""

    rule_id: str
    rule_name: str
    severity: Severity
    message: str  # 人类可读的违规描述
    suggestion: str  # 修正建议
    location: str = ""  # 违规位置（文件/行号）
    context: str = ""  # 违规上下文
    auto_fix: Optional[str] = None  # 自动修复代码（如果可以）

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "message": self.message,
            "suggestion": self.suggestion,
            "location": self.location,
            "context": self.context,
            "auto_fix": self.auto_fix,
        }


@dataclass
class ConstitutionalRule:
    """单条宪法规则

    每条规则包含：
    - 元数据（名称/分类/严重级/版本）
    - 触发条件（什么情况下激活这条规则）
    - 检测函数（如何检测违规）
    - 修复函数（如何自动修复，可选）
    """

    id: str
    name: str
    description: str
    category: RuleCategory
    severity: Severity
    version: str = "1.0.0"
    enabled: bool = True

    # 触发条件：接收代码/文件信息，返回是否激活
    trigger: Optional[Callable] = None  # (context: dict) -> bool

    # 检测函数：接收代码/文件信息，返回违规列表
    check: Optional[Callable] = None  # (code: str, context: dict) -> list[RuleViolation]

    # 自动修复函数：接收违规和代码，返回修复后代码
    fix: Optional[Callable] = None  # (violation: RuleViolation, code: str) -> str

    # 适用范围
    file_patterns: list[str] = field(default_factory=list)  # 适用文件模式 ["*.py", "*.ts"]
    exclude_patterns: list[str] = field(default_factory=list)  # 排除文件模式 ["test_*", "*.test.*"]
    tags: list[str] = field(default_factory=list)  # 标签

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "severity": self.severity.value,
            "version": self.version,
            "enabled": self.enabled,
            "file_patterns": self.file_patterns,
            "exclude_patterns": self.exclude_patterns,
            "tags": self.tags,
        }
