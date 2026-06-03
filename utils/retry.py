"""
retry.py
异常处理与重试模块
A1: 扫描失败降级
B1: 冷启动路径（数字足迹为空）
C2: 发招呼中断恢复
"""

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Any, Optional

logger = logging.getLogger("jobtracer.utils.retry")


# =============================================================================
# ErrorCode 枚举
# =============================================================================

class ErrorCode(Enum):
    """JobTracer 错误码"""
    # A 类 - 扫描相关
    A1_PLATFORM_TOKEN_INVALID = "A1"   # 平台 Token 失效
    A2_SCAN_TIMEOUT = "A2"              # 扫描超时
    A3_PERMISSION_DENIED = "A3"         # 权限不足

    # B 类 - 数据相关
    B1_EMPTY_FOOTPRINT = "B1"           # 数字足迹为空
    B2_INSUFFICIENT_DATA = "B2"         # 数据不足

    # C 类 - 投递相关
    C1_DELIVERY_FAILED = "C1"          # 投递失败
    C2_GREET_INTERRUPTED = "C2"        # 发招呼中断
    C3_COOKIE_EXPIRED = "C3"           # Cookie 过期


# =============================================================================
# JobTracerError
# =============================================================================

@dataclass
class JobTracerError(Exception):
    """
    JobTracer 自定义异常

    Attributes:
        code: 错误码（ErrorCode 枚举值）
        message: 错误消息
        platform: 相关平台名称（可选）
        recoverable: 是否可恢复（True 表示可以重试，False 表示不可重试）
    """
    code: ErrorCode
    message: str
    platform: Optional[str] = None
    recoverable: bool = True  # 是否可恢复

    def __str__(self) -> str:
        platform_info = f" [{self.platform}]" if self.platform else ""
        return f"[{self.code.value}] {self.message}{platform_info}"

    def __repr__(self) -> str:
        return (
            f"JobTracerError(code={self.code!r}, message={self.message!r}, "
            f"platform={self.platform!r}, recoverable={self.recoverable!r})"
        )


# =============================================================================
# RetryHandler
# =============================================================================

class RetryHandler:
    """
    统一重试处理器
    支持指数退避重试策略
    """

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        """
        初始化重试处理器

        Args:
            max_retries: 最大重试次数（默认 3 次）
            base_delay: 基础延迟时间秒数（默认 1.0s）
                       实际延迟 = base_delay * (2 ** attempt)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay

    async def retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        执行函数并在失败时重试

        Args:
            func: 异步可调用对象
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            函数返回值

        Raises:
            JobTracerError: 当不可恢复错误或重试耗尽时抛出
        """
        for attempt in range(self.max_retries):
            try:
                result = await func(*args, **kwargs)
                if attempt > 0:
                    logger.info(f"{func.__name__} succeeded after {attempt + 1} attempts")
                return result
            except JobTracerError as e:
                if not e.recoverable:
                    logger.error(f"{e.code.value} is not recoverable, giving up")
                    raise
                if attempt == self.max_retries - 1:
                    logger.error(f"{e.code.value} failed after {self.max_retries} attempts")
                    raise
                delay = self.base_delay * (2 ** attempt)
                logger.warning(f"{e.code.value} failed: {e.message}, "
                               f"retrying in {delay:.1f}s (attempt {attempt + 1}/{self.max_retries})")
                await asyncio.sleep(delay)
            except Exception as e:
                # 非 JobTracerError 的异常默认视为不可恢复
                logger.error(f"Unexpected error in {func.__name__}: {e}")
                raise

    def handle_scan_error(self, error: JobTracerError, scanner_name: str) -> dict:
        """
        扫描错误降级处理
        返回降级结果，不阻塞其他扫描器

        Args:
            error: JobTracerError 异常
            scanner_name: 扫描器名称

        Returns:
            降级结果 dict，格式：
            {
                "source": str,          # 扫描器名称
                "status": "failed",     # 固定为 failed
                "error_code": str,      # 错误码，如 "A1"
                "error_message": str,  # 错误消息
                "files": [],           # 空文件列表
                "projects": []         # 空项目列表
            }
        """
        logger.warning(
            f"Scan error handler: {scanner_name} failed with "
            f"{error.code.value} - {error.message}"
        )
        return {
            "source": scanner_name,
            "status": "failed",
            "error_code": error.code.value,
            "error_message": error.message,
            "files": [],
            "projects": []
        }

    def handle_cold_start(self) -> dict:
        """
        冷启动路径（数字足迹为空时）
        引导用户上传简历作为冷启动

        Returns:
            冷启动引导 dict，格式：
            {
                "status": "cold_start",
                "message": str,        # 提示用户的消息
                "next_action": str     # 下一步操作建议
            }
        """
        return {
            "status": "cold_start",
            "message": "数字足迹较少，建议手动上传简历作为冷启动",
            "next_action": "等待用户上传简历 PDF"
        }

    def is_empty_footprint(self, footprint: dict) -> bool:
        """
        检查数字足迹是否为空（小于阈值）

        Args:
            footprint: 数字足迹 dict，需包含 total_files 或 files 字段

        Returns:
            True 如果足迹过少（< 3 个项目），否则 False
        """
        total = footprint.get("total_files", 0)
        files = footprint.get("files", [])
        project_count = footprint.get("projects", [])

        # 有项目列表时检查项目数量
        if project_count:
            return len(project_count) < 3

        # 有文件列表时检查文件数量
        if files:
            return len(files) < 3

        # 只剩 total_files 字段
        return total < 3


# =============================================================================
# 便捷函数
# =============================================================================

# 全局默认处理器（延迟初始化）
_default_handler: Optional[RetryHandler] = None


def get_handler() -> RetryHandler:
    """获取默认 RetryHandler 实例"""
    global _default_handler
    if _default_handler is None:
        _default_handler = RetryHandler()
    return _default_handler


def handle_scan_error(error: JobTracerError, scanner_name: str) -> dict:
    """便捷函数：处理扫描错误（使用默认处理器）"""
    return get_handler().handle_scan_error(error, scanner_name)


def handle_empty_footprint() -> dict:
    """便捷函数：处理空足迹（冷启动）"""
    return get_handler().handle_cold_start()


# =============================================================================
# 测试入口
# =============================================================================

if __name__ == "__main__":
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    print("=== ErrorCode 枚举测试 ===")
    print(f"A1: {ErrorCode.A1_PLATFORM_TOKEN_INVALID.value}")
    print(f"B1: {ErrorCode.B1_EMPTY_FOOTPRINT.value}")
    print(f"C2: {ErrorCode.C2_GREET_INTERRUPTED.value}")

    print("\n=== JobTracerError 测试 ===")
    err1 = JobTracerError(
        code=ErrorCode.A1_PLATFORM_TOKEN_INVALID,
        message="GitHub Token 已过期",
        platform="GitHub",
        recoverable=True
    )
    print(f"err1: {err1}")

    print("\n=== RetryHandler.handle_scan_error 测试 ===")
    handler = RetryHandler(max_retries=3, base_delay=0.5)
    result = handler.handle_scan_error(err1, "github")
    print(f"result: {result}")

    print("\n=== RetryHandler.handle_cold_start 测试 ===")
    result = handler.handle_cold_start()
    print(f"result: {result}")

    print("\n=== RetryHandler.is_empty_footprint 测试 ===")
    empty_fp = {"total_files": 2}
    normal_fp = {"total_files": 100}
    print(f"empty_fp is empty: {handler.is_empty_footprint(empty_fp)}")
    print(f"normal_fp is empty: {handler.is_empty_footprint(normal_fp)}")
    print(f"fp with projects < 3: {handler.is_empty_footprint({'projects': ['p1', 'p2']})}")