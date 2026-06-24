"""
合规防火墙 — 关键词触发 + 全量日志 + 事后审计

核心能力：
1. ComplianceFirewall: 关键词实时触发（BLOCKED/SUSPICIOUS/AUDIT）
2. 全量合规日志（JSONL每日文件）
3. 审计链条完整（audit_trail 回溯用户操作）
4. 关键词热更新（add_keyword/remove_keyword）
"""

from .firewall import ComplianceFirewall, ComplianceRecord, RiskLevel, COMPLIANCE_KEYWORDS

__all__ = ["ComplianceFirewall", "ComplianceRecord", "RiskLevel", "COMPLIANCE_KEYWORDS"]
