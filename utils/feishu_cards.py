"""
feishu_cards.py
飞书消息卡片生成模块
实现 CARD-001/CARD-002/CARD-005 三种卡片模板
"""

from typing import List, Optional


# =============================================================================
# 基础卡片结构
# =============================================================================

def _base_card(header_title: str, header_template: str, elements: List[dict]) -> dict:
    """
    构建基础飞书卡片结构

    Args:
        header_title: 卡片标题
        header_template: header 配色（blue/grey/red/orange/purple/green）
        elements: 元素列表

    Returns:
        符合飞书规范的卡片 dict
    """
    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": header_title},
                "template": header_template
            },
            "elements": elements
        }
    }


def _div(text: str) -> dict:
    """创建文本 div 元素"""
    return {
        "tag": "div",
        "text": {"tag": "lark_md", "content": text}
    }


def _hr() -> dict:
    """创建分隔线元素"""
    return {"tag": "hr"}


def _action_buttons(buttons: List[dict]) -> dict:
    """创建 action 元素（按钮组）"""
    return {"tag": "action", "actions": buttons}


def _button(text: str, button_type: str = "secondary", value: str = "") -> dict:
    """
    创建单个按钮

    Args:
        text: 按钮文字
        button_type: primary / secondary / danger
        value: 按钮值（用于回调）
    """
    return {
        "tag": "button",
        "text": {"tag": "plain_text", "content": text},
        "type": button_type,
        "value": value
    }


# =============================================================================
# CARD-001：新职位发现通知
# =============================================================================

def card_new_job(job: dict, match_score: int) -> dict:
    """
    CARD-001：新职位发现通知卡片

    Args:
        job: 职位信息 dict，需包含：
            - title: 职位名称
            - company: 公司名称
            - city: 城市
            - salary: 薪资范围（如 "30-50K·16薪"）
            - highlights: 匹配亮点列表[List[str]]
        match_score: 匹配度 0-100

    Returns:
        飞书卡片 dict

    卡片结构：
        - header: 🎯 新职位发现（蓝色）
        - 职位名称 / 公司 · 城市 · 薪资
        - 匹配度进度条 + 百分比
        - 匹配亮点标签
        - 3个按钮：[查看详情] [投递] [不感兴趣]
    """
    title = job.get("title", "未知职位")
    company = job.get("company", "未知公司")
    city = job.get("city", "未知城市")
    salary = job.get("salary", "薪资面议")
    highlights: List[str] = job.get("highlights", [])

    # 匹配度进度条（10格）
    filled = min(10, max(0, match_score // 10))
    bar = "█" * filled + "░" * (10 - filled)

    highlight_text = " · ".join(highlights) if highlights else "暂无匹配亮点"

    elements = [
        _div(f"**{title}**"),
        _div(f"{company} · {city} · {salary}"),
        _hr(),
        _div(f"📊 匹配度：[{bar}] {match_score}%"),
        _div(f"🏷️ 匹配亮点：{highlight_text}"),
        _hr(),
        _action_buttons([
            _button("查看详情", "secondary", "detail"),
            _button("投递", "primary", "apply"),
            _button("不感兴趣", "secondary", "ignore"),
        ])
    ]

    return _base_card("🎯 新职位发现", "blue", elements)


# =============================================================================
# CARD-002：简历生成完成通知
# =============================================================================

def card_resume_ready(name: str, position: str, skills: List[str], project_count: int) -> dict:
    """
    CARD-002：简历生成完成通知卡片

    Args:
        name: 用户姓名
        position: 职位定位（如 "高级后端工程师"）
        skills: 核心技能列表[List[str]]（Top 5）
        project_count: 纳入简历的项目数量

    Returns:
        飞书卡片 dict

    卡片结构：
        - header: 📄 简历已生成（紫色）
        - 问候语 + 简历摘要
        - 职位定位 / 核心技能 / 项目经验数量
        - 3个按钮：[预览 PDF] [修改内容] [确认投递]
    """
    skill_text = " · ".join(skills) if skills else "待完善"

    elements = [
        _div(f"你好 **{name}**，你的简历已准备就绪！"),
        _hr(),
        _div(f"▪ **职位定位：** {position}"),
        _div(f"▪ **核心技能：** {skill_text}"),
        _div(f"▪ **项目经验：** {project_count} 个项目"),
        _hr(),
        _action_buttons([
            _button("预览 PDF", "secondary", "preview"),
            _button("修改内容", "secondary", "edit"),
            _button("确认投递", "primary", "confirm"),
        ])
    ]

    return _base_card("📄 简历已生成", "purple", elements)


# =============================================================================
# CARD-005：每日求职日报
# =============================================================================

def card_daily_report_v2(
    date: str,
    saved_jobs: int,
    new_jobs: int,
    applied: int,
    interviewing: int,
    offer_count: int,
    new_job_list: Optional[List[dict]] = None,
    status_updates: Optional[List[str]] = None,
    pending_items: Optional[List[str]] = None,
    project_count: int = 0,
    project_new: int = 0,
) -> dict:
    """
    CARD-005-v2：每日求职日报卡片（完整版）

    Args:
        date: 报表日期（如 "2026-06-03"）
        saved_jobs: 已保存职位总数
        new_jobs: 今日新增职位数
        applied: 已投递数
        interviewing: 面试中数
        offer_count: Offer数
        new_job_list: 新职位列表（Top 3）
        status_updates: 状态更新列表
        pending_items: 待处理列表
        project_count: 数字足迹项目总数
        project_new: 新增项目数

    Returns:
        飞书卡片 dict

    卡片结构：
        - header: 📊 求职日报 · YYYY-MM-DD（绿色）
        - 今日概览：已保存 / 新发现 / 已投递 / 面试中 / Offer
        - 新职位列表（Top 3）
        - 状态更新列表
        - 待处理列表
        - 下次行动建议
        - 2个按钮：[查看全部职位] [查看Bitable]
    """
    elements = [
        _div("**📈 求职状态概览**"),
        _div(
            f"已保存: {saved_jobs} 个"
            f" · 新发现: {new_jobs} 个\n"
            f"已投递: {applied} 个"
            f" · 面试中: {interviewing} 个"
            f" · **Offer: {offer_count} 个**"
        ),
        _hr(),
        _div(f"**📁 数字足迹**：{project_count} 个项目 | 新增: {project_new} 个"),
        _hr(),
    ]

    # 新职位列表
    if new_job_list:
        elements.append(_div("**🆕 新职位（匹配度 ≥ 75%）**"))
        for job in new_job_list[:3]:
            title = job.get("title", "未知职位")
            company = job.get("company", "未知公司")
            score = job.get("match_score", 0)
            elements.append(_div(f"• {title} @ {company} — 匹配度 {score}%"))
        elements.append(_hr())

    # 状态更新
    if status_updates:
        elements.append(_div("**📋 HR 反馈**"))
        for update in status_updates:
            elements.append(_div(f"• {update}"))
        elements.append(_hr())

    # 待处理
    if pending_items:
        elements.append(_div("**⚠️ 待处理**"))
        for item in pending_items:
            elements.append(_div(f"• {item}"))
        elements.append(_hr())

    elements.append(_action_buttons([
        _button("查看全部职位", "secondary", "all_jobs"),
        _button("查看Bitable", "secondary", "bitable"),
    ]))

    return _base_card(f"📊 求职日报 · {date}", "green", elements)


def card_daily_report(date: str, new_jobs: int, status_changes: int, pending: int,
                      new_job_list: Optional[List[dict]] = None,
                      status_updates: Optional[List[str]] = None,
                      pending_items: Optional[List[str]] = None) -> dict:
    """
    CARD-005：每日求职日报卡片

    Args:
        date: 报表日期（如 "2026-06-03"）
        new_jobs: 今日新增职位数
        status_changes: 投递状态变化数
        pending: 待处理事项数
        new_job_list: 新职位列表，每项为 dict:
            - title: 职位名称
            - company: 公司名称
            - match_score: 匹配度
        status_updates: 状态更新列表，每项为 str（如 "HR回复：询问薪资期望"）
        pending_items: 待处理列表，每项为 str（如 "二面确认 — 截止 2026-06-05"）

    Returns:
        飞书卡片 dict

    卡片结构：
        - header: 📊 求职日报 · YYYY-MM-DD（绿色）
        - 今日概览：新增职位 / 状态变化 / 待处理
        - 新职位列表（Top 3，高匹配度）
        - 状态更新列表
        - 待处理列表
        - 2个按钮：[查看全部职位] [查看Bitable]
    """
    elements = [
        _div("**📈 今日概览**"),
        _div(f"▪ 新发现职位：{new_jobs} 个"),
        _div(f"▪ 投递状态变化：{status_changes} 个"),
        _div(f"▪ 待处理事项：{pending} 项"),
        _hr(),
    ]

    # 新职位列表
    if new_job_list:
        elements.append(_div("**🆕 新职位（匹配度 ≥ 75%）**"))
        for job in new_job_list[:3]:
            title = job.get("title", "未知职位")
            company = job.get("company", "未知公司")
            score = job.get("match_score", 0)
            elements.append(_div(f"• {title} @ {company} — 匹配度 {score}%"))
        elements.append(_hr())

    # 状态更新
    if status_updates:
        elements.append(_div("**📋 状态更新**"))
        for update in status_updates:
            elements.append(_div(f"• {update}"))
        elements.append(_hr())

    # 待处理
    if pending_items:
        elements.append(_div("**⚠️ 待处理**"))
        for item in pending_items:
            elements.append(_div(f"• {item}"))
        elements.append(_hr())

    elements.append(_action_buttons([
        _button("查看全部职位", "secondary", "all_jobs"),
        _button("查看Bitable", "secondary", "bitable"),
    ]))

    return _base_card(f"📊 求职日报 · {date}", "green", elements)


# =============================================================================
# CARD-006：新职位推送摘要（每日自动搜索后发送）
# =============================================================================

def card_new_jobs_digest(jobs: List[dict], date: str = None) -> dict:
    """
    CARD-006：新职位推送摘要卡片（每日 cron 搜索后发送）

    Args:
        jobs: 新职位列表，每项 dict 需包含：
            - title: 职位名称
            - company: 公司名称
            - city: 城市
            - salary: 薪资（如 "30-50K·16薪"）
            - match_score: 匹配度 0-100
            - url: 职位链接（可选）
        date: 日期字符串（默认今天）

    Returns:
        飞书卡片 dict

    卡片结构：
        - header: 🔔 今日新职位 · YYYY-MM-DD（蓝色）
        - 统计行：新职位数量
        - 职位列表（每条含名称/公司/薪资/匹配度）
        - 没有新职位时显示鼓励语
    """
    import datetime
    date_str = date or datetime.datetime.now().strftime("%Y-%m-%d")

    elements = [
        _div(f"**🔔 今日新职位 · {date_str}**"),
        _div(f"共发现 **{len(jobs)}** 个新职位"),
        _hr(),
    ]

    if jobs:
        for i, job in enumerate(jobs, 1):
            title = job.get("title", "未知职位")
            company = job.get("company", "未知公司")
            city = job.get("city", "")
            salary = job.get("salary", "薪资面议")
            score = job.get("match_score", 0)
            url = job.get("url", "")

            # 匹配度进度条
            filled = min(10, max(0, score // 10))
            bar = "█" * filled + "░" * (10 - filled)

            job_text = f"**{i}. {title}**\n{company}" + (f" · {city}" if city else "") + f" · {salary}\n📊 匹配度 [{bar}] {score}%"

            if url:
                job_text += f"\n[查看职位]({url})"

            elements.append(_div(job_text))
            if i < len(jobs):
                elements.append(_hr())
    else:
        elements.append(_div("🎉 今日暂无新增职位，保持简历更新，机会随时到来！"))

    elements.append(_hr())
    elements.append(_action_buttons([
        _button("查看全部职位", "secondary", "all_jobs"),
        _button("刷新搜索", "secondary", "refresh_search"),
    ]))

    return _base_card(f"🔔 今日新职位 · {date_str}", "blue", elements)


# =============================================================================
# 发送测试（本地调试用）
# =============================================================================

if __name__ == "__main__":
    import json

    # 测试 CARD-001
    print("=== CARD-001 测试 ===")
    job1 = {
        "title": "高级后端工程师",
        "company": "XX科技",
        "city": "上海",
        "salary": "30-50K·16薪",
        "highlights": ["Python", "电商", "后端"]
    }
    card1 = card_new_job(job1, 85)
    print(json.dumps(card1, ensure_ascii=False, indent=2))

    # 测试 CARD-002
    print("\n=== CARD-002 测试 ===")
    card2 = card_resume_ready(
        name="张三",
        position="高级后端工程师",
        skills=["Python", "Java", "MySQL", "Redis", "Go"],
        project_count=8
    )
    print(json.dumps(card2, ensure_ascii=False, indent=2))

    # 测试 CARD-005
    print("\n=== CARD-005 测试 ===")
    card5 = card_daily_report(
        date="2026-06-03",
        new_jobs=3,
        status_changes=2,
        pending=1,
        new_job_list=[
            {"title": "后端工程师", "company": "A公司", "match_score": 88},
            {"title": "Python开发", "company": "B公司", "match_score": 82},
            {"title": "全栈工程师", "company": "C公司", "match_score": 76},
        ],
        status_updates=["A公司 HR回复：询问薪资期望"],
        pending_items=["B公司 二面确认 — 截止 2026-06-05"]
    )
    print(json.dumps(card5, ensure_ascii=False, indent=2))