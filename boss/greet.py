# boss/greet.py
# BOSS发招呼模块 - opencli boss greet
# 指数退避重试 + 失败记录

import subprocess
import json
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from pathlib import Path as _PP

import sys
sys.path.insert(0, str(_PP(__file__).parent.parent))
from storage.manager import StorageManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('jobtracer.boss.greet')


# 指数退避延迟（秒）
RETRY_DELAYS = [2, 4, 8]


class BOSSGreeter:
    """
    BOSS直聘发招呼模块
    通过 opencli boss greet 命令发送招呼
    """

    def __init__(self, cookies_path: str = "~/.jobtracer/cookies/boss.json"):
        """
        初始化BOSS招呼器

        Args:
            cookies_path: BOSS cookies 文件路径
        """
        self.cookies_path = _PP(cookies_path).expanduser()
        self.storage = StorageManager()
        self.logs_dir = self.storage.ensure_subdir('logs')

    async def greet(
        self,
        security_id: str,
        greeting_text: str = None,
        resume_path: str = None,
        max_retries: int = 3
    ) -> dict:
        """
        发送招呼

        Args:
            security_id: BOSS职位ID
            greeting_text: 招呼语（None时自动生成）
            resume_path: 简历路径（None时使用默认路径）
            max_retries: 最大重试次数（最多3次，对应延迟 2s→4s→8s）

        Returns:
            dict: {
                "success": True/False,
                "greeting_text": "实际发送的招呼语",
                "error": "错误信息（失败时）",
                "manual_remedy": True/False,
                "retries": 实际重试次数
            }
        """
        # 限制重试次数
        max_retries = min(max_retries, 3)

        # 生成招呼语
        if greeting_text is None:
            greeting_text = self._generate_default_greeting()

        # 指数退避重试
        for attempt in range(max_retries):
            result = await self._send_greet(security_id, greeting_text)

            if result.get("success"):
                logger.info(f"招呼发送成功: security_id={security_id}")
                return {
                    "success": True,
                    "greeting_text": greeting_text,
                    "retries": attempt,
                    "error": None,
                    "manual_remedy": False
                }

            error_msg = result.get("error", "未知错误")
            logger.warning(
                f"招呼发送失败（第{attempt + 1}/{max_retries}次）: "
                f"security_id={security_id}, error={error_msg}"
            )

            # 非最后一次，等待指数退避时间后重试
            if attempt < max_retries - 1:
                delay = RETRY_DELAYS[attempt]
                logger.info(f"等待 {delay}s 后重试...")
                await asyncio.sleep(delay)

        # 全部失败
        logger.error(f"招呼发送最终失败: security_id={security_id}, 尝试 {max_retries} 次")

        # 记录失败日志
        self._save_failure_log(security_id, greeting_text, result.get("error", "未知错误"), max_retries)

        return {
            "success": False,
            "greeting_text": greeting_text,
            "error": result.get("error", "未知错误"),
            "manual_remedy": True,
            "retries": max_retries
        }

    async def _send_greet(self, security_id: str, greeting_text: str) -> dict:
        """
        调用 opencli boss greet 命令

        Args:
            security_id: BOSS职位ID
            greeting_text: 招呼语

        Returns:
            dict: 命令执行结果
        """
        cmd = [
            'opencli', 'boss', 'greet',
            '--security-id', security_id,
            '--message', greeting_text,
            '-f', 'json'
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=30
            )

            stdout_text = stdout.decode('utf-8', errors='replace').strip()
            stderr_text = stderr.decode('utf-8', errors='replace').strip()

            if proc.returncode != 0:
                error_msg = stderr_text if stderr_text else '未知错误'
                logger.error(f"opencli boss greet 失败: {error_msg}")
                return {
                    "success": False,
                    "error": f"命令执行失败: {error_msg}"
                }

            # 解析输出
            try:
                if stdout_text:
                    result_data = json.loads(stdout_text)
                else:
                    result_data = {}

                # 判断是否真正成功（有些CLI成功时不返回JSON，只返回空或成功标识）
                # 这里做宽松判断：returncode==0 即认为成功
                return {
                    "success": True,
                    "data": result_data,
                    "error": None
                }
            except json.JSONDecodeError as e:
                # 输出非JSON但命令成功
                logger.warning(f"输出解析JSON失败（非致命）: {e}, raw: {stdout_text[:200]}")
                return {
                    "success": True,
                    "data": {"raw": stdout_text},
                    "error": None
                }

        except asyncio.TimeoutError:
            logger.error("opencli boss greet 超时")
            return {
                "success": False,
                "error": "命令执行超时（30s）"
            }
        except FileNotFoundError:
            logger.error("opencli 命令未找到，请确保 opencli 已安装")
            return {
                "success": False,
                "error": "opencli 命令未找到，请安装 opencli"
            }
        except Exception as e:
            logger.error(f"opencli boss greet 异常: {e}")
            return {
                "success": False,
                "error": f"执行异常: {str(e)}"
            }

    def _generate_default_greeting(self, job: dict = None) -> str:
        """
        生成默认招呼语

        格式：
        你好，我看贵司的[职位名称]正在招聘，我认为我的背景很匹配：
        - [技能1]：[相关项目/经历]
        - [技能2]：[相关项目/经历]
        希望有机会进一步交流，谢谢！

        Args:
            job: 职位信息（可选）

        Returns:
            str: 生成的招呼语
        """
        # 读取简历获取技能信息
        resume = self.storage.get_resume()
        job_title = job.get('title', '该职位') if job else '该职位'

        greeting_parts = [f"你好，我看贵司的{job_title}正在招聘，我认为我的背景很匹配："]

        if resume:
            skills = resume.get('skills', [])
            projects = resume.get('projects', [])

            # 添加技能
            if skills:
                # 取前3个技能
                top_skills = skills[:3]
                for skill in top_skills:
                    greeting_parts.append(f"- {skill}")

            # 添加项目经历
            if projects:
                for proj in projects[:2]:
                    proj_name = proj.get('name', '')
                    proj_role = proj.get('role', '')
                    if proj_name:
                        desc = f"{proj_role} - {proj_name}" if proj_role else proj_name
                        greeting_parts.append(f"- {desc}")

        greeting_parts.append("希望有机会进一步交流，谢谢！")

        return '\n'.join(greeting_parts)

    def _save_failure_log(
        self,
        security_id: str,
        greeting_text: str,
        error: str,
        retries: int
    ) -> None:
        """
        写入失败日志到 logs/greet_failures.log

        Args:
            security_id: BOSS职位ID
            greeting_text: 尝试发送的招呼语
            error: 错误信息
            retries: 重试次数
        """
        log_file = self.logs_dir / 'greet_failures.log'

        # 读取已有日志
        existing = []
        if log_file.exists():
            try:
                content = log_file.read_text(encoding='utf-8')
                if content.strip():
                    existing = json.loads(content)
                if not isinstance(existing, list):
                    existing = []
            except Exception:
                existing = []

        # 构建失败记录
        failure_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "security_id": security_id,
            "greeting_text": greeting_text,
            "error": error,
            "retries": retries
        }

        existing.append(failure_entry)

        # 写入日志
        try:
            log_file.write_text(
                json.dumps(existing, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
            logger.info(f"失败日志已写入: {log_file}")
        except Exception as e:
            logger.error(f"写入失败日志失败: {e}")


# ─────────────────────────────────────────────────────────────
# 便捷函数
# ─────────────────────────────────────────────────────────────

async def greet(
    security_id: str,
    greeting_text: str = None,
    resume_path: str = None,
    max_retries: int = 3
) -> dict:
    """
    发送BOSS招呼（便捷函数）

    Args:
        security_id: BOSS职位ID
        greeting_text: 招呼语
        resume_path: 简历路径
        max_retries: 最大重试次数

    Returns:
        dict: 发送结果
    """
    greeter = BOSSGreeter()
    return await greeter.greet(security_id, greeting_text, resume_path, max_retries)


if __name__ == '__main__':
    # 测试代码
    import asyncio

    print("=" * 60)
    print("BOSS发招呼模块测试")
    print("=" * 60)

    async def test():
        greeter = BOSSGreeter()

        # 测试招呼语生成
        print("\n测试招呼语生成:")
        greeting = greeter._generate_default_greeting()
        print(f"生成的招呼语:\n{greeting}")

        print("\n测试招呼语生成（带职位信息）:")
        greeting_with_job = greeter._generate_default_greeting({
            'title': 'Python后端工程师'
        })
        print(f"生成的招呼语:\n{greeting_with_job}")

        # 测试实际发送（需要真实的 security_id）
        print("\n" + "-" * 40)
        print("注意：实际发送需要真实的 security_id")
        print("-" * 40)

        return {
            "greeting_generated": True,
            "greeting": greeting
        }

    asyncio.run(test())

    print("\n" + "=" * 60)
    print("BOSS发招呼模块测试完成")
    print("=" * 60)
