"""
feishu_notify.py
飞书实时通知模块
新职位 → 飞书卡片消息推送
投递状态变更 → 通知
扫描完成 → 摘要推送
"""

import json
import logging
from pathlib import Path
from typing import List, Optional

import requests

from utils.feishu_cards import (
    card_new_job,
    card_resume_ready,
    card_daily_report,
)

logger = logging.getLogger("jobtracer.notifications.feishu_notify")

# Webhook 配置文件路径
WEBHOOK_PATH = Path("~/.jobtracer/feishu_webhook.json")


def _load_webhook_url() -> Optional[str]:
    """从配置文件加载 webhook URL"""
    path = WEBHOOK_PATH.expanduser()
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("webhook_url")
    except Exception as e:
        logger.warning(f"Failed to load webhook config: {e}")
        return None


class FeishuNotifier:
    """
    飞书通知器
    通过 Webhook 发送卡片消息
    """

    def __init__(self, webhook_url: Optional[str] = None):
        """
        初始化飞书通知器

        Args:
            webhook_url: 飞书群机器人的 Webhook URL
                        如果不传，自动从 ~/.jobtracer/feishu_webhook.json 读取
        """
        self.webhook_url = webhook_url or _load_webhook_url()

    # -------------------------------------------------------------------------
    # 底层发送
    # -------------------------------------------------------------------------

    def send_card(self, card: dict) -> bool:
        """
        发送飞书卡片消息

        Args:
            card: 飞书卡片 dict，需包含：
                  - msg_type: "interactive"
                  - card: 卡片内容

        Returns:
            是否发送成功
        """
        if not self.webhook_url:
            logger.error("Webhook URL not configured")
            return False

        try:
            response = requests.post(
                self.webhook_url,
                json=card,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            response.raise_for_status()
            result = response.json()
            code = result.get("code", 0)
            if code == 0:
                logger.info("Card sent successfully")
                return True
            else:
                logger.warning(f"Feishu API error: {result.get('msg')}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send card: {e}")
            return False

    # -------------------------------------------------------------------------
    # notify_new_jobs - 新职位发现通知
    # -------------------------------------------------------------------------

    def notify_new_jobs(self, jobs: List[dict]) -> None:
        """
        新职位发现通知

        Args:
            jobs: 职位列表，每项 dict 需包含：
                  - title: 职位名称
                  - company: 公司名称
                  - city: 城市
                  - salary: 薪资范围
                  - highlights: 匹配亮点列表
                  - url: 职位链接（可选）
                  - match_score: 匹配度 0-100
        """
        count = len(jobs)
        title = f"📋 发现 {count} 个新职位" if count > 0 else "📋 暂无新职位"

        elements = []
        for job in jobs[:10]:  # 最多显示10个
            job_title = job.get("title", "未知职位")
            company = job.get("company", "未知公司")
            city = job.get("city", "未知城市")
            salary = job.get("salary", "薪资面议")
            score = job.get("match_score", 0)
            url = job.get("url", "")
            highlights = job.get("highlights", [])

            # 匹配度进度条（5格）
            filled = min(5, max(0, score // 20))
            bar = "█" * filled + "░" * (5 - filled)
            highlight_text = " · ".join(highlights) if highlights else "暂无亮点"

            job_text = (
                f"**{job_title}**\n"
                f"{company} · {city} · {salary}\n"
                f"📊 匹配度：[{bar}] {score}% · {highlight_text}"
            )

            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": job_text}
            })

            if url:
                elements.append({
                    "tag": "action",
                    "actions": [{
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🔗 查看详情"},
                        "type": "primary",
                        "value": "detail",
                        "url": url
                    }]
                })

            elements.append({"tag": "hr"})

        if not elements:
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": "没有发现新的匹配职位，继续加油！💪"}
            })

        elements.append({
            "tag": "note",
            "elements": [{"tag": "plain_text", "content": "来自 JobTracer · 上海"}]
        })

        card = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                    "template": "blue"
                },
                "elements": elements
            }
        }

        self.send_card(card)

    # -------------------------------------------------------------------------
    # notify_scan_complete - 扫描完成通知
    # -------------------------------------------------------------------------

    def notify_scan_complete(self, scan_summary: dict) -> None:
        """
        扫描完成通知

        Args:
            scan_summary: 扫描摘要 dict，需包含：
                          - total_files: 总文件数
                          - platform_distribution: 平台分布 dict
                          - new_projects: 新发现项目数
                          - clusters: 聚类结果数量
                          - duration_seconds: 耗时
                          - scanned_at: 扫描时间
        """
        total_files = scan_summary.get("total_files", 0)
        platform_dist = scan_summary.get("platform_distribution", {})
        new_projects = scan_summary.get("new_projects", 0)
        clusters = scan_summary.get("clusters", 0)
        duration = scan_summary.get("duration_seconds", 0.0)
        scanned_at = scan_summary.get("scanned_at", "")

        # 平台分布文本
        dist_lines = []
        for platform, count in platform_dist.items():
            dist_lines.append(f"  • {platform}: {count} 个文件")
        dist_text = "\n".join(dist_lines) if dist_lines else "  • 暂无数据"

        elements = [
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "**🔍 数字足迹扫描完成**"}
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**总文件数：** {total_files}"}
            },
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**扫描耗时：** {duration:.1f}s"}
            },
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**新发现项目：** {new_projects}"}
            },
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**聚类数量：** {clusters}"}
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "**📦 平台分布**"}
            },
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": dist_text}
            },
            {"tag": "hr"},
            {
                "tag": "note",
                "elements": [{"tag": "plain_text", "content": f"扫描时间：{scanned_at} · JobTracer"}]
            }
        ]

        card = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": "🔍 扫描完成"},
                    "template": "green"
                },
                "elements": elements
            }
        }

        self.send_card(card)

    # -------------------------------------------------------------------------
    # notify_delivery_status - 投递状态变更通知
    # -------------------------------------------------------------------------

    def notify_delivery_status(self, order_id: str, status: str, job_title: str = "", company: str = "") -> None:
        """
        投递状态变更通知

        Args:
            order_id: 投递记录 ID
            status: 状态值
                   - sent: 已投递
                   - viewed: 被查看
                   - replied: HR 回复
                   - rejected: 不匹配
                   - interview: 面试邀请
            job_title: 职位名称（可选）
            company: 公司名称（可选）
        """
        status_map = {
            "sent": ("📤 已投递", "blue", "你的简历已发送给 HR，等待查看中..."),
            "viewed": ("👀 被查看", "orange", "HR 查看了你的简历，继续保持！"),
            "replied": ("💬 HR 回复", "purple", "HR 主动回复了你，快去看看！"),
            "rejected": ("❌ 不匹配", "red", "该职位可能不太匹配，看看其他机会？"),
            "interview": ("🎉 面试邀请", "green", "恭喜收到面试邀请！记得确认时间。"),
        }

        emoji, template, message = status_map.get(
            status,
            ("📋 状态更新", "grey", f"投递状态已更新为：{status}")
        )

        header_title = f"{emoji} 投递状态更新"

        job_info = ""
        if job_title or company:
            job_info = f"\n**{job_title}** @ {company}" if job_title else f"\n**{company}**"

        elements = [
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": message}
            },
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**订单号：** `{order_id}`"}
            },
        ]

        if job_info:
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": job_info}
            })

        elements.append({"tag": "hr"})
        elements.append({
            "tag": "note",
            "elements": [{"tag": "plain_text", "content": f"状态：{status} · JobTracer"}]
        })

        card = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": header_title},
                    "template": template
                },
                "elements": elements
            }
        }

        self.send_card(card)


# =============================================================================
# 便捷单例（从配置文件加载 webhook）
# =============================================================================

_default_notifier: Optional[FeishuNotifier] = None


def get_notifier() -> FeishuNotifier:
    """获取默认通知器实例（延迟加载）"""
    global _default_notifier
    if _default_notifier is None:
        _default_notifier = FeishuNotifier()
    return _default_notifier


# =============================================================================
# 测试入口
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # 测试 notify_new_jobs
    print("=== 测试 notify_new_jobs ===")
    notifier = FeishuNotifier()
    test_jobs = [
        {
            "title": "高级后端工程师",
            "company": "XX科技",
            "city": "上海",
            "salary": "30-50K·16薪",
            "match_score": 85,
            "highlights": ["Python", "电商", "后端"],
            "url": "https://example.com/job/1",
        },
        {
            "title": "Python开发工程师",
            "company": "YY网络",
            "city": "北京",
            "salary": "25-40K",
            "match_score": 72,
            "highlights": ["Django", "REST API"],
            "url": "https://example.com/job/2",
        },
    ]
    notifier.notify_new_jobs(test_jobs)

    # 测试 notify_delivery_status
    print("\n=== 测试 notify_delivery_status ===")
    notifier.notify_delivery_status(
        order_id="ord_abc123",
        status="replied",
        job_title="后端工程师",
        company="XX科技"
    )

    # 测试 notify_scan_complete
    print("\n=== 测试 notify_scan_complete ===")
    notifier.notify_scan_complete({
        "total_files": 156,
        "platform_distribution": {
            "GitHub": 42,
            "OpenClaw": 15,
            "Local": 99
        },
        "new_projects": 8,
        "clusters": 5,
        "duration_seconds": 12.3,
        "scanned_at": "2026-06-04T01:19:00"
    })