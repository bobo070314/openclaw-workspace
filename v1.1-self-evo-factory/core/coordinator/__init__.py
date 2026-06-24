# core/coordinator/ — AI项目经理 + 自然语言命令 + 拒绝橡皮图章
# 对标 Claude Code 的 Coordinator 模式

from .acceptance_criteria import AcceptanceCriteria
from .coordinator_agent import CoordinatorAgent, Mission, Task, TaskStatus, VerificationLevel
from .natural_commands import NaturalCommandParser
