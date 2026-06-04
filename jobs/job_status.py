"""
jobs/job_status.py
职位投递状态枚举及状态机定义
"""

from enum import Enum
from typing import List, Optional


class DeliveryStatus(str, Enum):
    """投递状态枚举"""
    SAVED = "saved"           # 已保存
    APPLIED = "applied"       # 已投递
    SCREENING = "screening"   # 笔试/笔试中
    INTERVIEW_T1 = "interview_t1"  # 一面
    INTERVIEW_T2 = "interview_t2"  # 二面
    INTERVIEW_T3 = "interview_t3"  # 三面
    OFFER = "offer"           # Offer
    HIRED = "hired"           # 已入职
    REJECTED = "rejected"     # 已拒绝
    WITHDRAWN = "withdrawn"   # 已撤回
    EXPIRED = "expired"       # 已失效


# 状态显示名称（中文）
STATUS_DISPLAY = {
    DeliveryStatus.SAVED: "已保存",
    DeliveryStatus.APPLIED: "已投递",
    DeliveryStatus.SCREENING: "笔试中",
    DeliveryStatus.INTERVIEW_T1: "一面",
    DeliveryStatus.INTERVIEW_T2: "二面",
    DeliveryStatus.INTERVIEW_T3: "三面",
    DeliveryStatus.OFFER: "Offer",
    DeliveryStatus.HIRED: "已入职",
    DeliveryStatus.REJECTED: "已拒绝",
    DeliveryStatus.WITHDRAWN: "已撤回",
    DeliveryStatus.EXPIRED: "已失效",
}

# 状态进度顺序（用于计算进度）
STATUS_PROGRESSION = [
    DeliveryStatus.SAVED,
    DeliveryStatus.APPLIED,
    DeliveryStatus.SCREENING,
    DeliveryStatus.INTERVIEW_T1,
    DeliveryStatus.INTERVIEW_T2,
    DeliveryStatus.INTERVIEW_T3,
    DeliveryStatus.OFFER,
    DeliveryStatus.HIRED,
]

# 终态（不可继续推进）
TERMINAL_STATUSES = {
    DeliveryStatus.HIRED,
    DeliveryStatus.REJECTED,
    DeliveryStatus.WITHDRAWN,
    DeliveryStatus.EXPIRED,
}

# 面试状态（用于统计）
INTERVIEW_STATUSES = {
    DeliveryStatus.SCREENING,
    DeliveryStatus.INTERVIEW_T1,
    DeliveryStatus.INTERVIEW_T2,
    DeliveryStatus.INTERVIEW_T3,
    DeliveryStatus.OFFER,
}


def get_status_display(status: str) -> str:
    """获取状态的中文显示名称"""
    try:
        return STATUS_DISPLAY[DeliveryStatus(status)]
    except (ValueError, KeyError):
        return status


def get_next_status(current: str) -> Optional[str]:
    """获取下一状态（如果存在）"""
    try:
        current_enum = DeliveryStatus(current)
    except ValueError:
        return None
    
    if current_enum in TERMINAL_STATUSES:
        return None
    
    try:
        idx = STATUS_PROGRESSION.index(current_enum)
        if idx + 1 < len(STATUS_PROGRESSION):
            return STATUS_PROGRESSION[idx + 1].value
    except ValueError:
        pass
    return None


def get_status_progress(status: str) -> int:
    """获取状态进度百分比"""
    try:
        current_enum = DeliveryStatus(status)
    except ValueError:
        return 0
    
    if current_enum in TERMINAL_STATUSES:
        return 100
    
    try:
        idx = STATUS_PROGRESSION.index(current_enum)
        return int((idx / (len(STATUS_PROGRESSION) - 1)) * 100)
    except ValueError:
        return 0


def get_next_action(status: str) -> str:
    """根据状态返回下一步建议"""
    suggestions = {
        DeliveryStatus.SAVED.value: "投递职位，记录求职意向",
        DeliveryStatus.APPLIED.value: "等待HR回复，3天后未读可考虑跟进",
        DeliveryStatus.SCREENING.value: "准备笔试，复习相关知识",
        DeliveryStatus.INTERVIEW_T1.value: "准备一面，查看相关面经",
        DeliveryStatus.INTERVIEW_T2.value: "准备二面，深入项目经历",
        DeliveryStatus.INTERVIEW_T3.value: "准备三面/HR面，保持状态",
        DeliveryStatus.OFFER.value: "薪资谈判，使用 salary_negotiator",
        DeliveryStatus.HIRED.value: "恭喜入职！",
        DeliveryStatus.REJECTED.value: "总结经验，继续投递",
        DeliveryStatus.WITHDRAWN.value: "已撤回，关注其他机会",
        DeliveryStatus.EXPIRED.value: "职位已失效，查看其他机会",
    }
    return suggestions.get(status, "未知状态")