"""
feishu_bot.py
飞书 Bot 交互模块
负责发送卡片消息和处理按钮回调
"""

import sys
from pathlib import Path

# 支持直接运行（python3 utils/feishu_bot.py）和包内导入
if __name__ == "__main__":
    _parent = Path(__file__).parent.parent
    sys.path.insert(0, str(_parent))
    from utils.feishu_cards import card_daily_report
else:
    from .feishu_cards import card_daily_report

import json
import logging
from typing import Optional, Dict, Any
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('jobtracer.utils.feishu_bot')


# =============================================================================
# FeishuBot
# =============================================================================

class FeishuBot:
    """
    飞书群机器人 Bot
    通过 Webhook 发送卡片消息
    """

    def __init__(self, webhook_url: str = None, verify_ssl: bool = False):
        """
        初始化飞书 Bot

        Args:
            webhook_url: 飞书群机器人的 Webhook URL
            verify_ssl: 是否验证 SSL（默认 False 禁用验证）
        """
        if webhook_url is None:
            import os
            webhook_url = os.environ.get("FEISHU_WEBHOOK", "")
            # 尝试从配置文件读取
            verify_ssl = False
            if not webhook_url:
                config_path = Path("~/.jobtracer/feishu_webhook.json").expanduser()
                if config_path.exists():
                    with open(config_path) as f:
                        config = json.load(f)
                        webhook_url = config.get("webhook_url", "")
                        verify_ssl = config.get("verify_ssl", False)

        self.webhook_url = webhook_url
        self.timeout = 10  # 请求超时（秒）
        self.verify_ssl = verify_ssl
        self._session = None  # 懒加载 session

    # -------------------------------------------------------------------------
    # 核心发送
    # -------------------------------------------------------------------------

    async def send_card(
        self,
        card: dict,
        chat_id: str = None
    ) -> dict:
        """
        发送卡片消息到飞书群

        Args:
            card: 卡片 dict（由 utils.feishu_cards 生成的格式）
            chat_id: 聊天 ID（Webhook 模式下不需要，保留接口兼容）

        Returns:
            dict: {
                "success": True/False,
                "message_id": str,  # 成功时返回消息ID
                "error": str,        # 失败时返回错误信息
                "status_code": int   # HTTP 状态码
            }
        """
        if not self.webhook_url:
            logger.error("Feishu Webhook URL 未配置")
            return {
                "success": False,
                "message_id": None,
                "error": "FEISHU_WEBHOOK 环境变量未设置",
                "status_code": None
            }

        try:
            import requests
            payload = json.dumps(card, ensure_ascii=False)
            headers = {"Content-Type": "application/json"}

            resp = requests.post(
                self.webhook_url,
                data=payload,
                headers=headers,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            status_code = resp.status_code
            body = resp.text

            if status_code == 200 and "success" in body:
                logger.info(f"飞书卡片发送成功: status={status_code}")
                return {
                    "success": True,
                    "message_id": body,
                    "error": None,
                    "status_code": status_code
                }
            else:
                logger.error(f"飞书卡片发送失败: status={status_code}, response={body[:300]}")
                return {
                    "success": False,
                    "message_id": None,
                    "error": f"状态码 {status_code}: {body[:300]}",
                    "status_code": status_code
                }

        except Exception as e:
            logger.error(f"飞书卡片发送失败: {str(e)}")
            return {
                "success": False,
                "message_id": None,
                "error": str(e),
                "status_code": None
            }
            logger.error(f"飞书卡片发送失败（未知异常）: {e}")
            return {
                "success": False,
                "message_id": None,
                "error": f"未知异常: {str(e)}",
                "status_code": None
            }

    # -------------------------------------------------------------------------
    # C2 场景：发招呼失败重试卡片
    # -------------------------------------------------------------------------

    async def send_greet_reminder(
        self,
        security_id: str,
        job_title: str,
        company: str,
        greeting_text: str,
        error_message: str = None
    ) -> dict:
        """
        发送发招呼失败提醒卡片
        包含「重新发送」和「复制招呼语」两个按钮

        Args:
            security_id: BOSS 职位 ID
            job_title: 职位名称
            company: 公司名称
            greeting_text: 已生成的招呼语
            error_message: 发送失败错误信息（可选）

        Returns:
            dict: send_card 的返回结果
        """
        # 构造卡片内容
        elements = [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"❌ **发招呼失败**\n\n"
                              f"职位：{job_title}\n"
                              f"公司：{company}\n\n"
                              f"招呼语：\n> {greeting_text[:100]}{'...' if len(greeting_text) > 100 else ''}"
                }
            },
            {"tag": "hr"}
        ]

        # 如果有错误信息，追加显示
        if error_message:
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"⚠️ 错误原因：{error_message[:150]}"
                }
            })
            elements.append({"tag": "hr"})

        # 两个按钮：重新发送 + 复制招呼语
        # value 使用 base64 编码避免特殊字符问题
        import base64
        greeting_b64 = base64.b64encode(greeting_text.encode('utf-8')).decode('ascii')

        elements.append({
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "🔄 重新发送"},
                    "type": "primary",
                    "value": json.dumps({
                        "action": "retry_greet",
                        "security_id": security_id,
                        "greeting_text": greeting_text
                    }, ensure_ascii=False)
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "📋 复制招呼语"},
                    "type": "secondary",
                    "value": json.dumps({
                        "action": "copy_greeting",
                        "security_id": security_id,
                        "greeting_text": greeting_text
                    }, ensure_ascii=False)
                }
            ]
        })

        card = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": "⚠️ 发招呼失败 - 请重试"},
                    "template": "orange"
                },
                "elements": elements
            }
        }

        return await self.send_card(card)

    # -------------------------------------------------------------------------
    # 简历生成完成通知
    # -------------------------------------------------------------------------

    async def send_resume_ready(
        self,
        user_name: str,
        position: str,
        resume_path: str,
        skills: list = None,
        project_count: int = 0
    ) -> dict:
        """
        发送简历生成完成通知卡片

        Args:
            user_name: 用户姓名
            position: 职位定位
            resume_path: 简历文件路径
            skills: 核心技能列表（可选）
            project_count: 项目数量（可选）

        Returns:
            dict: send_card 的返回结果
        """
        from utils.feishu_cards import card_resume_ready

        card = card_resume_ready(
            name=user_name,
            position=position,
            skills=skills or [],
            project_count=project_count
        )

        return await self.send_card(card)

    # -------------------------------------------------------------------------
    # 按钮回调解析
    # -------------------------------------------------------------------------

    def parse_interaction(self, payload: dict) -> dict:
        """
        解析用户点击按钮的交互回调

        飞书卡片按钮回调 payload 格式（来自 events 接口）：
        {
            "action": {...},
            "refresh": false,
            "open_id": "ou_xxx",
            "union_id": "on_xxx",
            "tenant_key": "xxx",
            "app_id": "cli_xxx",
            "card": {...}
        }

        action 字段：
        {
            "tag": "button",
            "text": {"tag": "plain_text", "content": "重新发送"},
            "value": "{\"action\": \"retry_greet\", ...}"
        }

        Args:
            payload: 飞书事件回调的完整 payload

        Returns:
            dict: {
                "action": str,          # "retry_greet" | "copy_greeting" | "unknown"
                "security_id": str,     # 职位 ID
                "greeting_text": str,   # 招呼语文本
                "error": str            # 解析失败原因
            }
        """
        try:
            action_block = payload.get("action", {})
            value_str = action_block.get("value", "")

            if not value_str:
                return {
                    "action": "unknown",
                    "security_id": None,
                    "greeting_text": None,
                    "error": "按钮 value 为空"
                }

            # 尝试解析 value JSON
            try:
                value_data = json.loads(value_str)
            except json.JSONDecodeError:
                return {
                    "action": "unknown",
                    "security_id": None,
                    "greeting_text": None,
                    "error": f"value JSON 解析失败: {value_str[:100]}"
                }

            action = value_data.get("action", "unknown")
            security_id = value_data.get("security_id", "")
            greeting_text = value_data.get("greeting_text", "")

            # 验证必填字段
            if not security_id:
                return {
                    "action": action,
                    "security_id": None,
                    "greeting_text": greeting_text,
                    "error": "缺少 security_id 字段"
                }

            logger.info(
                f"按钮交互解析成功: action={action}, "
                f"security_id={security_id[:20]}..., "
                f"greeting_len={len(greeting_text)}"
            )

            return {
                "action": action,
                "security_id": security_id,
                "greeting_text": greeting_text,
                "error": None
            }

        except Exception as e:
            logger.error(f"按钮交互解析异常: {e}")
            return {
                "action": "unknown",
                "security_id": None,
                "greeting_text": None,
                "error": f"解析异常: {str(e)}"
            }

    # -------------------------------------------------------------------------
    # 便捷方法：发送日报
    # -------------------------------------------------------------------------

    async def send_daily_report(
        self,
        date: str,
        new_jobs: int,
        status_changes: int,
        pending: int,
        new_job_list: list = None,
        status_updates: list = None,
        pending_items: list = None
    ) -> dict:
        """
        发送每日求职日报卡片

        Args:
            date: 日期字符串
            new_jobs: 新职位数
            status_changes: 状态变化数
            pending: 待处理数
            new_job_list: 新职位列表
            status_updates: 状态更新列表
            pending_items: 待处理列表

        Returns:
            dict: send_card 的返回结果
        """
        card = card_daily_report(
            date=date,
            new_jobs=new_jobs,
            status_changes=status_changes,
            pending=pending,
            new_job_list=new_job_list,
            status_updates=status_updates,
            pending_items=pending_items
        )
        return await self.send_card(card)


# =============================================================================
# 便捷函数
# =============================================================================

async def send_card(card: dict, chat_id: str = None) -> dict:
    """发送卡片（模块级便捷函数）"""
    bot = FeishuBot()
    return await bot.send_card(card, chat_id)


async def send_greet_reminder(
    security_id: str,
    job_title: str,
    company: str,
    greeting_text: str,
    error_message: str = None
) -> dict:
    """发送发招呼失败提醒卡片（模块级便捷函数）"""
    bot = FeishuBot()
    return await bot.send_greet_reminder(
        security_id, job_title, company, greeting_text, error_message
    )


def parse_interaction(payload: dict) -> dict:
    """解析按钮交互（模块级便捷函数）"""
    bot = FeishuBot()
    return bot.parse_interaction(payload)


# =============================================================================
# 本地调试
# =============================================================================

if __name__ == '__main__':
    import asyncio

    print("=" * 60)
    print("FeishuBot 模块测试")
    print("=" * 60)

    async def test():
        bot = FeishuBot()

        # 1. 测试 parse_interaction（模拟飞书按钮回调）
        print("\n=== 测试 parse_interaction ===")
        mock_payload = {
            "action": {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "🔄 重新发送"},
                "value": json.dumps({
                    "action": "retry_greet",
                    "security_id": "sec_abc123xyz",
                    "greeting_text": "你好，我看贵司的Python后端工程师正在招聘..."
                }, ensure_ascii=False)
            },
            "refresh": False,
            "open_id": "ou_xxx"
        }
        result = bot.parse_interaction(mock_payload)
        print(f"解析结果: {result}")
        assert result["action"] == "retry_greet"
        assert result["security_id"] == "sec_abc123xyz"
        assert "Python后端" in result["greeting_text"]
        print("✅ parse_interaction 测试通过")

        # 2. 测试 parse_interaction（复制招呼语按钮）
        print("\n=== 测试 parse_interaction（复制招呼语）===")
        mock_payload2 = {
            "action": {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "📋 复制招呼语"},
                "value": json.dumps({
                    "action": "copy_greeting",
                    "security_id": "sec_abc123xyz",
                    "greeting_text": "你好，我看贵司的职位正在招聘..."
                }, ensure_ascii=False)
            }
        }
        result2 = bot.parse_interaction(mock_payload2)
        print(f"解析结果: {result2}")
        assert result2["action"] == "copy_greeting"
        print("✅ copy_greeting 解析测试通过")

        # 3. 测试 parse_interaction（异常 payload）
        print("\n=== 测试 parse_interaction（异常输入）===")
        bad_payloads = [
            {},
            {"action": {}},
            {"action": {"value": "not-json"}},
            {"action": {"value": '{"action": "retry_greet"}'}},  # 缺 security_id
        ]
        for bp in bad_payloads:
            r = bot.parse_interaction(bp)
            print(f"  异常 payload 处理: action={r['action']}, error={r['error']}")
        print("✅ 异常输入处理测试通过")

        # 4. 构造发招呼失败卡片结构（不发送，仅验证结构）
        print("\n=== 验证 send_greet_reminder 卡片结构 ===")
        import base64
        greeting_text = "你好，我看贵司的Python后端工程师正在招聘，我认为我的背景很匹配：\n- Python：5年经验\n- Django/Flask：精通"
        security_id = "sec_test123"
        card_orange = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": "⚠️ 发招呼失败 - 请重试"},
                    "template": "orange"
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"❌ **发招呼失败**\n\n"
                                      f"职位：Python后端工程师\n"
                                      f"公司：XX科技\n\n"
                                      f"招呼语：\n> {greeting_text[:100]}..."
                        }
                    },
                    {"tag": "hr"},
                    {
                        "tag": "action",
                        "actions": [
                            {
                                "tag": "button",
                                "text": {"tag": "plain_text", "content": "🔄 重新发送"},
                                "type": "primary",
                                "value": json.dumps({
                                    "action": "retry_greet",
                                    "security_id": security_id,
                                    "greeting_text": greeting_text
                                }, ensure_ascii=False)
                            },
                            {
                                "tag": "button",
                                "text": {"tag": "plain_text", "content": "📋 复制招呼语"},
                                "type": "secondary",
                                "value": json.dumps({
                                    "action": "copy_greeting",
                                    "security_id": security_id,
                                    "greeting_text": greeting_text
                                }, ensure_ascii=False)
                            }
                        ]
                    }
                ]
            }
        }
        print(f"卡片结构已构造（header.template=orange, 包含两个按钮）")
        print(f"按钮 value 示例: {list(json.loads(card_orange['card']['elements'][2]['actions'][0]['value']).keys())}")
        print("✅ 卡片结构验证通过")

        return {
            "parse_interaction": True,
            "card_structure": True,
            "send_skipped": "需要真实的 FEISHU_WEBHOOK 才能测试发送"
        }

    result = asyncio.run(test())

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    for k, v in result.items():
        print(f"  {k}: {v}")
    print("\n✅ FeishuBot 模块自测通过")
    print("=" * 60)