"""合规防火墙 — 关键词触发 + 全量日志 + 事后审计

对标 Claude Code：不是"拦截可疑内容"，而是：
1. 关键词实时触发（命中立即拒绝 + 写告警）
2. 全量合规日志（每条输入输出都落盘）
3. 审计链条完整（谁在什么时候干了什么，事后能查）
"""

import hashlib
import json
import os
import pathlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

UTC = timezone.utc


class RiskLevel(str, Enum):
    """风险等级"""

    SAFE = "safe"  # 安全，放行
    SUSPICIOUS = "suspicious"  # 疑似，记录但不拦截
    BLOCKED = "blocked"  # 阻断，绝对不执行
    AUDIT = "audit"  # 审计标记，执行但重点记录


# ================================================
# 合规关键词库（运行时可热更新）
# ================================================
COMPLIANCE_KEYWORDS = {
    # 阻断级（命中立即拒接）
    "BLOCKED": [
        # 金融欺诈
        r"(虚假|伪造|篡改)\s*(交易|账单|凭证|合同)",
        r"(洗钱|套现|刷单|刷量|薅羊毛)",
        r"(破解|绕过|crack|bypass)\s*(支付|付费|会员|license|licence)",
        # 非法内容
        r"(生成|制作|制造)\s*(假身份证|假护照|假证件|假文凭)",
        r"(盗版|cracked|pirated)\s*(软件|电影|音乐|游戏|课程)",
        # 隐私侵犯
        r"(窃取|盗取|获取)\s*(他人|别人|用户)\s*(密码|账号|个人信息|隐私)",
        # 网络攻击
        r"(DDOS|DDoS|ddos)\s*(攻击|工具|脚本)",
        r"(木马|病毒|后门|勒索)\s*(生成|制作|开发|编写)",
        # 武器/管制
        r"(制作|合成)\s*(炸药|毒品|毒药|武器)",
    ],
    # 疑似级（记录但不拦截）
    "SUSPICIOUS": [
        r"(大量|批量|自动化)\s*(注册|登录|爬取|采集)",
        r"(绕过|跳过)\s*(验证码|captcha|人机验证)",
        r"(生成|伪造)\s*(评论|评价|评分|点赞)",
        r"(未经授权|未授权)\s*(访问|获取|读取)",
        r"(过度|过量)\s*(调用|请求|访问)\s*API",
    ],
    # 审计级（执行但重点记录）
    "AUDIT": [
        r"(删除|销毁|清除)\s*(数据库|日志|记录|文件)",
        r"(导出|下载|获取)\s*(全部|所有|完整)\s*数据",
        r"(修改|更改|篡改)\s*(系统|服务器)\s*(配置|设置)",
        r"(sudo|root|admin|管理员)\s*(权限|操作|执行)",
    ],
}


@dataclass
class ComplianceRecord:
    """合规日志记录"""

    id: str
    timestamp: str
    risk_level: RiskLevel
    triggered_keyword: str
    user_input_hash: str  # SHA256（不存原文）
    action: str  # "blocked" | "logged" | "audited"
    context: str = ""
    model_response_hash: str = ""  # 模型输出hash

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "risk_level": self.risk_level.value,
            "triggered_keyword": self.triggered_keyword,
            "user_input_hash": self.user_input_hash,
            "action": self.action,
            "context": self.context,
            "model_response_hash": self.model_response_hash,
        }


class ComplianceFirewall:
    """合规防火墙 — 关键词触发 + 全量日志 + 审计链"""

    def __init__(self, log_dir: str = None):
        self._log_dir = pathlib.Path(
            log_dir or os.path.join(os.path.dirname(__file__), "..", "..", "logs", "compliance")
        )
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._keywords = dict(COMPLIANCE_KEYWORDS)  # 可热更新
        self._recent_checks: list[ComplianceRecord] = []  # 最近检查
        self._max_recent = 100
        self._total_checks = 0
        self._total_blocked = 0
        self._total_audited = 0

    def check(self, user_input: str, context: str = "") -> RiskLevel:
        """检查用户输入

        Returns:
            RiskLevel: 风险等级

        """
        user_hash = hashlib.sha256(user_input.encode("utf-8")).hexdigest()[:16]
        now = datetime.now(UTC).isoformat()

        # 先检查阻断级（命中就返回，不继续检查）
        blocked = self._check_keywords(user_input, "BLOCKED")
        if blocked:
            record = ComplianceRecord(
                id=f"compl_{hashlib.sha256(user_hash.encode()).hexdigest()[:8]}",
                timestamp=now,
                risk_level=RiskLevel.BLOCKED,
                triggered_keyword=blocked,
                user_input_hash=user_hash,
                action="blocked",
                context=context,
            )
            self._log(record)
            self._total_checks += 1
            self._total_blocked += 1
            return RiskLevel.BLOCKED

        # 检查疑似级
        suspicious = self._check_keywords(user_input, "SUSPICIOUS")
        if suspicious:
            record = ComplianceRecord(
                id=f"compl_{hashlib.sha256(user_hash.encode()).hexdigest()[:8]}",
                timestamp=now,
                risk_level=RiskLevel.SUSPICIOUS,
                triggered_keyword=suspicious,
                user_input_hash=user_hash,
                action="logged",
                context=context,
            )
            self._log(record)
            self._total_checks += 1
            return RiskLevel.SUSPICIOUS

        # 检查审计级
        audit_hit = self._check_keywords(user_input, "AUDIT")
        if audit_hit:
            record = ComplianceRecord(
                id=f"compl_{hashlib.sha256(user_hash.encode()).hexdigest()[:8]}",
                timestamp=now,
                risk_level=RiskLevel.AUDIT,
                triggered_keyword=audit_hit,
                user_input_hash=user_hash,
                action="audited",
                context=context,
            )
            self._log(record)
            self._total_checks += 1
            self._total_audited += 1
            return RiskLevel.AUDIT

        # 安全
        self._total_checks += 1
        return RiskLevel.SAFE

    def log_response(self, user_input_hash: str, model_response: str, context: str = ""):
        """记录模型输出（事后审计用）"""
        now = datetime.now(UTC).isoformat()
        response_hash = hashlib.sha256(model_response.encode("utf-8")).hexdigest()[:16]

        record = ComplianceRecord(
            id=f"resp_{hashlib.sha256(response_hash.encode()).hexdigest()[:8]}",
            timestamp=now,
            risk_level=RiskLevel.AUDIT,
            triggered_keyword="response_logged",
            user_input_hash=user_input_hash,
            action="audited",
            context=context,
            model_response_hash=response_hash,
        )
        self._log(record)

    def add_keyword(self, level: str, pattern: str):
        """热更新关键词"""
        if level not in ["BLOCKED", "SUSPICIOUS", "AUDIT"]:
            raise ValueError(f"未知风险等级: {level}")
        self._keywords.setdefault(level, []).append(pattern)

    def remove_keyword(self, level: str, pattern: str):
        """移除关键词"""
        if level in self._keywords and pattern in self._keywords[level]:
            self._keywords[level].remove(pattern)

    def get_keywords(self) -> dict:
        """获取所有关键词"""
        return self._keywords

    def get_stats(self) -> dict:
        """获取统计"""
        return {
            "total_checks": self._total_checks,
            "total_blocked": self._total_blocked,
            "total_audited": self._total_audited,
            "block_rate": f"{self._total_blocked / max(self._total_checks, 1) * 100:.1f}%",
            "audit_rate": f"{self._total_audited / max(self._total_checks, 1) * 100:.1f}%",
        }

    def get_recent(self, limit: int = 20) -> list[dict]:
        """获取最近检查记录"""
        return [r.to_dict() for r in self._recent_checks[-limit:]]

    def _check_keywords(self, text: str, level: str) -> Optional[str]:
        """检查文本是否命中某级别的关键词

        Returns:
            命中的第一个关键词（或 None）

        """
        patterns = self._keywords.get(level, [])
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return pattern
        return None

    def _log(self, record: ComplianceRecord):
        """记录到内存 + 文件"""
        self._recent_checks.append(record)
        if len(self._recent_checks) > self._max_recent:
            self._recent_checks = self._recent_checks[-self._max_recent :]

        # 写文件
        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        log_path = self._log_dir / f"compliance_{date_str}.jsonl"
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
        except Exception:
            pass

    def audit_trail(self, user_hash: str) -> list[dict]:
        """回溯某用户的完整操作链"""
        trail = []
        for record in self._recent_checks:
            if record.user_input_hash == user_hash:
                trail.append(record.to_dict())
        return trail
