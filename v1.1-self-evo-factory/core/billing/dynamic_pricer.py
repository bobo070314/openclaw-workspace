"""
实时报价 + 动态变价 + 用途发毒誓

对标 Claude Code 的做法：
1. 每次 API 调用之前先在本地算出 "这次要花多少钱"
2. 成本到阈值自动触发模型降级（不是事后报警）
3. 用途审计 — 每条 API 调用都带 "这笔钱花来干什么"
"""

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone, timedelta
from typing import Optional
import json

UTC = timezone.utc


class Tier(str, Enum):
    """模型等级"""

    CHEAP = "cheap"  # 便宜模型（7B级）
    STANDARD = "standard"  # 标准模型（DeepSeek V3级）
    PREMIUM = "premium"  # 高级模型（Claude Sonnet级）
    ULTRA = "ultra"  # 顶级模型（Claude Opus级）


# 实时报价表（USD / 1M tokens）
PRICING_TABLE = {
    "deepseek-chat": {"input": 0.27, "output": 1.10, "tier": Tier.CHEAP},
    "deepseek-v3": {"input": 0.50, "output": 2.00, "tier": Tier.STANDARD},
    "deepseek-v4-pro": {"input": 1.00, "output": 4.00, "tier": Tier.PREMIUM},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00, "tier": Tier.PREMIUM},
    "claude-3-5-haiku": {"input": 0.80, "output": 4.00, "tier": Tier.CHEAP},
    "claude-opus": {"input": 15.00, "output": 75.00, "tier": Tier.ULTRA},
    "gpt-4o": {"input": 2.50, "output": 10.00, "tier": Tier.PREMIUM},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60, "tier": Tier.CHEAP},
}

# 降级链：预算超出时自动降级
DOWNGRADE_CHAIN = {
    Tier.ULTRA: Tier.PREMIUM,
    Tier.PREMIUM: Tier.STANDARD,
    Tier.STANDARD: Tier.CHEAP,
    Tier.CHEAP: None,  # 不能再降了
}


class Purpose(str, Enum):
    """用途发毒誓 — 每笔钱花来干什么"""

    TASK_DECOMPOSITION = "task_decomposition"  # 任务拆解
    CODE_GENERATION = "code_generation"  # 代码生成
    CODE_REVIEW = "code_review"  # 代码审查
    SECURITY_AUDIT = "security_audit"  # 安全审计
    MEMORY_RETRIEVAL = "memory_retrieval"  # 记忆检索
    ERROR_REPAIR = "error_repair"  # 错误修复
    SUMMARIZATION = "summarization"  # 摘要生成
    PLANNING = "planning"  # 规划推理
    OTHER = "other"  # 其他


@dataclass
class Quote:
    """实时报价单 — 调用前估算"""

    model: str
    purpose: str
    estimated_input_tokens: int
    estimated_output_tokens: int
    input_cost: float = 0.0
    output_cost: float = 0.0
    total_cost: float = 0.0
    tier: str = ""

    def __post_init__(self):
        self._calculate()

    def _calculate(self):
        """从报价表实时计算成本"""
        pricing = PRICING_TABLE.get(self.model)
        if not pricing:
            self.input_cost = self.estimated_input_tokens / 1_000_000 * 1.0  # 默认 $1/M
            self.output_cost = self.estimated_output_tokens / 1_000_000 * 4.0
        else:
            self.input_cost = self.estimated_input_tokens / 1_000_000 * pricing["input"]
            self.output_cost = self.estimated_output_tokens / 1_000_000 * pricing["output"]
            self.tier = pricing["tier"].value

        self.total_cost = self.input_cost + self.output_cost

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "purpose": self.purpose,
            "estimated_input_tokens": self.estimated_input_tokens,
            "estimated_output_tokens": self.estimated_output_tokens,
            "input_cost": round(self.input_cost, 6),
            "output_cost": round(self.output_cost, 6),
            "total_cost": round(self.total_cost, 6),
            "tier": self.tier,
        }


@dataclass
class BillingStatement:
    """计费声明 — 实际调用后"""

    model: str
    purpose: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    timestamp: str
    duration_ms: int = 0
    cached: bool = False

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "purpose": self.purpose,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "cached": self.cached,
        }


class DynamicPricer:
    """动态变价 — 实时"这次要花多少钱" + 自动降级"""

    def __init__(self, budget_daily: float = 5.0, budget_monthly: float = 50.0):
        self.budget_daily = budget_daily
        self.budget_monthly = budget_monthly
        self._daily_spending: dict[str, float] = {}  # date -> usd
        self._monthly_spending: dict[str, float] = {}  # yyyy-mm -> usd
        self._forced_tier: Optional[str] = None  # 手动锁死等级

    def quote(self, model: str, purpose: str, estimated_input: int, estimated_output: int) -> Quote:
        """调用前估算 — 打印报价单"""
        return Quote(
            model=model,
            purpose=purpose,
            estimated_input_tokens=estimated_input,
            estimated_output_tokens=estimated_output,
        )

    def should_downgrade(self, model: str) -> tuple[bool, Optional[str]]:
        """判断是否该降级

        Returns:
            (需要降级?, 降级到哪个模型)
        """
        if self._forced_tier:
            return True, self._get_model_in_tier(self._forced_tier)

        pricing = PRICING_TABLE.get(model, {})
        current_tier = pricing.get("tier")

        # 检查日预算
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        daily_spent = self._daily_spending.get(today, 0.0)

        if daily_spent >= self.budget_daily * 0.9:  # 用了90%预算
            # 降级
            next_tier = DOWNGRADE_CHAIN.get(current_tier)
            if next_tier:
                return True, self._get_model_in_tier(next_tier)

        # 检查月预算
        this_month = datetime.now(UTC).strftime("%Y-%m")
        monthly_spent = self._monthly_spending.get(this_month, 0.0)
        if monthly_spent >= self.budget_monthly * 0.95:
            next_tier = DOWNGRADE_CHAIN.get(current_tier)
            if next_tier:
                return True, self._get_model_in_tier(next_tier)

        return False, None

    def record_spend(self, cost_usd: float):
        """记录实际支出"""
        now = datetime.now(UTC)
        today = now.strftime("%Y-%m-%d")
        this_month = now.strftime("%Y-%m")

        self._daily_spending[today] = self._daily_spending.get(today, 0) + cost_usd
        self._monthly_spending[this_month] = self._monthly_spending.get(this_month, 0) + cost_usd

    def get_daily_spent(self) -> float:
        """今日已花费"""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        return self._daily_spending.get(today, 0.0)

    def get_monthly_spent(self) -> float:
        """本月已花费"""
        this_month = datetime.now(UTC).strftime("%Y-%m")
        return self._monthly_spending.get(this_month, 0.0)

    def force_tier(self, tier: str):
        """手动锁死等级"""
        self._forced_tier = tier

    def release_tier(self):
        """解除锁死"""
        self._forced_tier = None

    @staticmethod
    def _get_model_in_tier(tier: Tier) -> Optional[str]:
        """获取指定等级的最优模型"""
        tier_models = [(m, p["input"]) for m, p in PRICING_TABLE.items() if p["tier"] == tier]
        if not tier_models:
            return None
        # 取同等级最便宜的
        return sorted(tier_models, key=lambda x: x[1])[0][0]

    def status(self) -> dict:
        """预算状态"""
        return {
            "daily_budget": self.budget_daily,
            "daily_spent": self.get_daily_spent(),
            "daily_remaining": self.budget_daily - self.get_daily_spent(),
            "monthly_budget": self.budget_monthly,
            "monthly_spent": self.get_monthly_spent(),
            "monthly_remaining": self.budget_monthly - self.get_monthly_spent(),
            "forced_tier": self._forced_tier,
        }
