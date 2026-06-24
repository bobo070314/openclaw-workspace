"""
计费变价 — 实时报价 + 动态变价 + 用途发毒誓

核心能力：
1. 每次 API 调用前先估算成本（Quote）
2. 预算到阈值自动触发模型降级（90%日预算 → cheap, 95%月预算 → cheap）
3. 每条调用声明用途（purpose）
"""

from .dynamic_pricer import DynamicPricer, Quote, BillingStatement, Purpose, Tier, PRICING_TABLE, DOWNGRADE_CHAIN

__all__ = ["DynamicPricer", "Quote", "BillingStatement", "Purpose", "Tier", "PRICING_TABLE", "DOWNGRADE_CHAIN"]
