# utils/error_handler.py
# JobTracer 异常处理模块
# 处理扫描器异常、冷启动引导、发招呼中断

import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# ============================================================
# 日志配置
# ============================================================

LOG_DIR = Path("~/.openclaw-workspaces/product-solution/jobtracer/logs").expanduser()
ERROR_LOG_FILE = LOG_DIR / "errors.log"


def _ensure_log_dir():
    """确保日志目录存在"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _setup_logger(name: str = "jobtracer.errors") -> logging.Logger:
    """配置专用错误日志器"""
    _ensure_log_dir()
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # 文件Handler - 记录完整错误
        file_handler = logging.FileHandler(ERROR_LOG_FILE, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s %(levelname)s %(name)s [%(scenario)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # 控制台Handler - 简化输出
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('[%(scenario)s] %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    logger.setLevel(logging.DEBUG)
    return logger


# ============================================================
# 异常分类
# ============================================================

class ScanErrorType:
    """扫描错误类型标识"""
    PLATFORM_FAILURE = "A1"      # 平台失效
    COLD_START = "B1"            # 冷启动（数字足迹为空）
    GREET_INTERRUPT = "C2"       # 发招呼中断


# ============================================================
# 可恢复错误定义
# ============================================================

RECOVERABLE_ERRORS = (
    TimeoutError,
    ConnectionError,
    ConnectionRefusedError,
    ConnectionResetError,
)

NON_RECOVERABLE_ERRORS = (
    PermissionError,
    FileNotFoundError,
    OSError,  # 系统级错误，如磁盘满
)


# ============================================================
# ErrorHandler 核心类
# ============================================================

class ErrorHandler:
    """
    统一的异常处理和降级策略
    
    处理场景：
    - A1: 扫描器平台失效（本地/OpenClaw/GitHub）
    - B1: 冷启动路径（数字足迹为空）
    - C2: 发招呼中断
    """
    
    def __init__(self):
        self.logger = _setup_logger()
        self._retry_counts: Dict[str, int] = {}  # 每个安全候选人的重试计数
        self._max_retries = 3
    
    # ============================================================
    # A1: 扫描器异常处理
    # ============================================================
    
    def handle_scan_error(
        self,
        scanner_name: str,
        error: Exception,
        context: Optional[dict] = None
    ) -> dict:
        """
        处理扫描器异常
        
        Args:
            scanner_name: 扫描器名称 (local/openclaw/github)
            error: 捕获的异常
            context: 附加上下文信息
            
        Returns:
            降级策略决策：
            {
                "continue_other_scanners": bool,
                "degradation": str,  # "skip_this" / "retry" / "abort_all"
                "error_message": str,
                "recoverable": bool,
                "fallback_action": str
            }
        """
        context = context or {}
        error_msg = str(error)
        error_type = type(error).__name__
        
        # 判断是否可恢复
        is_recoverable = self.is_recoverable_error(error)
        
        # 记录错误日志
        self._log_scan_error(scanner_name, error, error_type, context)
        
        # 根据扫描器类型决定降级策略
        degradation = self._determine_degradation(scanner_name, error, is_recoverable)
        
        result = {
            "continue_other_scanners": degradation["continue"],
            "degradation": degradation["action"],
            "error_message": f"[{scanner_name.upper()}] {error_type}: {error_msg}",
            "recoverable": is_recoverable,
            "fallback_action": degradation["fallback"],
            "scanner": scanner_name,
            "error_type": error_type,
            "timestamp": datetime.now().isoformat()
        }
        
        self.logger.info(
            f"扫描器 [{scanner_name}] 异常处理完成: degradation={degradation['action']}, "
            f"continue={degradation['continue']}",
            extra={"scenario": f"{ScanErrorType.PLATFORM_FAILURE}"}
        )
        
        return result
    
    def should_continue_other_scanners(self, scanner_name: str, error: Exception) -> bool:
        """
        判断是否继续其他扫描器
        
        规则：
        - local 失败 → 继续 openclaw/github
        - openclaw 失败 → 继续 github/local
        - github 失败 → 记录warn，继续其他
        - 全部不可恢复错误 → 不继续
        """
        if not self.is_recoverable_error(error):
            return False
        
        # GitHub 是最外围的，可以容忍更多失败
        if scanner_name == "github":
            return True
        
        # local 和 openclaw 失败不影响其他扫描器
        if scanner_name in ("local", "openclaw"):
            return True
        
        return False
    
    # ============================================================
    # B1: 冷启动处理（数字足迹为空）
    # ============================================================
    
    def handle_empty_footprint(
        self,
        scan_results: Optional[dict] = None,
        user_id: Optional[str] = None
    ) -> dict:
        """
        处理数字足迹为空的情况（冷启动）
        
        Args:
            scan_results: 扫描结果（可能为空或部分）
            user_id: 用户ID
            
        Returns:
            引导建议：
            {
                "is_empty": bool,
                "guidance_type": str,  # "upload_resume" / "manual_entry" / "retry"
                "message": str,
                "suggestions": list,
                "card_content": dict  # 用于渲染引导卡片
            }
        """
        scan_results = scan_results or {}
        total_files = scan_results.get("total_files", 0)
        
        # 判断是否真的为空
        sources = scan_results.get("sources", {})
        all_failed = all(
            s.get("status") in ("error", "timeout", "not_started")
            for s in sources.values()
        )
        
        is_empty = (total_files == 0) or all_failed
        
        if is_empty:
            self.logger.warning(
                f"数字足迹为空 (cold start detected)",
                extra={"scenario": ScanErrorType.COLD_START}
            )
            
            return {
                "is_empty": True,
                "guidance_type": "upload_resume",
                "message": "未发现数字足迹，请上传简历以继续",
                "suggestions": [
                    "上传您的简历文件（PDF/DOCX）",
                    "或手动填写基本信息",
                    "我们会基于您提供的信息为您匹配合适的工作"
                ],
                "card_content": {
                    "title": "📋 数字足迹为空",
                    "description": "我们未能发现您的数字足迹，请选择以下方式之一：",
                    "options": [
                        {"label": "上传简历", "action": "upload_resume", "icon": "📄"},
                        {"label": "手动填写信息", "action": "manual_entry", "icon": "✏️"},
                        {"label": "稍后重试", "action": "retry", "icon": "🔄"}
                    ],
                    "retry_allowed": True
                },
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            }
        else:
            # 有数据但可能较少
            return {
                "is_empty": False,
                "guidance_type": "partial",
                "message": f"发现 {total_files} 条数字足迹，继续处理",
                "suggestions": [],
                "card_content": None,
                "total_files": total_files,
                "timestamp": datetime.now().isoformat()
            }
    
    # ============================================================
    # C2: 发招呼异常处理
    # ============================================================
    
    def handle_greet_error(
        self,
        security_id: str,
        error: Exception,
        greeting_text: str,
        context: Optional[dict] = None
    ) -> dict:
        """
        处理发招呼异常
        
        Args:
            security_id: 安全候选人ID
            error: 捕获的异常
            greeting_text: 原本要发送的招呼内容
            context: 附加上下文（retry_count等）
            
        Returns:
            错误处理结果：
            {
                "manual_remedy": bool,  # 是否需要手动补救
                "retry_recommended": bool,
                "retry_count": int,
                "max_retries": int,
                "error_message": str,
                "remedy_suggestion": str,
                "greeting_saved": bool,
                "saved_greeting": str
            }
        """
        context = context or {}
        error_msg = str(error)
        error_type = type(error).__name__
        retry_count = context.get("retry_count", 0)
        
        # 记录错误日志
        self._log_greet_error(security_id, error, error_type, retry_count, greeting_text)
        
        # 判断是否可重试
        is_recoverable = self.is_recoverable_error(error)
        should_retry = is_recoverable and retry_count < self._max_retries
        
        # 判断是否需要手动补救
        manual_remedy = not is_recoverable or retry_count >= self._max_retries
        
        # 错误类型对应的补救建议
        remedy_suggestion = self._get_remedy_suggestion(error, error_type)
        
        result = {
            "manual_remedy": manual_remedy,
            "retry_recommended": should_retry,
            "retry_count": retry_count,
            "max_retries": self._max_retries,
            "error_message": f"{error_type}: {error_msg}",
            "remedy_suggestion": remedy_suggestion,
            "greeting_saved": True,  # 保存招呼以便手动补救
            "saved_greeting": greeting_text,
            "security_id": security_id,
            "timestamp": datetime.now().isoformat(),
            "can_proceed": manual_remedy  # 是否可以继续（手动补救后）
        }
        
        self.logger.info(
            f"发招呼失败: security_id={security_id}, "
            f"manual_remedy={manual_remedy}, retry={should_retry}",
            extra={"scenario": ScanErrorType.GREET_INTERRUPT}
        )
        
        return result
    
    def get_retry_delay(self, retry_count: int) -> float:
        """
        获取指数退避重试延迟
        
        Args:
            retry_count: 当前重试次数
            
        Returns:
            延迟秒数（指数退避：2^retry_count，最小1秒，最大30秒）
        """
        delay = min(2 ** retry_count, 30)
        return max(delay, 1.0)
    
    # ============================================================
    # 辅助方法
    # ============================================================
    
    def is_recoverable_error(self, error: Exception) -> bool:
        """
        判断错误是否可恢复（可重试）
        
        可恢复：
        - TimeoutError
        - ConnectionError / ConnectionRefusedError / ConnectionResetError
        - HTTP 错误（通过错误消息判断）
        
        不可恢复：
        - PermissionError（权限问题，重试也无法解决）
        - FileNotFoundError（文件不存在）
        - 认证失败（Cookie失效）→ 需要手动干预
        """
        # 直接检查异常类型
        if isinstance(error, NON_RECOVERABLE_ERRORS):
            return False
        
        if isinstance(error, RECOVERABLE_ERRORS):
            return True
        
        # 通过错误消息判断
        error_msg = str(error).lower()
        
        # 不可恢复的错误关键词
        non_recoverable_keywords = [
            "permission",
            "access denied",
            "not found",
            "cookie expired",
            "auth failed",
            "unauthorized",
            "invalid token",
            "forbidden",
        ]
        
        if any(kw in error_msg for kw in non_recoverable_keywords):
            return False
        
        # 网络相关错误通常可恢复
        recoverable_keywords = [
            "timeout",
            "connection",
            "network",
            "reset",
            "refused",
            "temporary",
            "unavailable",
        ]
        
        if any(kw in error_msg for kw in recoverable_keywords):
            return True
        
        # 默认视为可恢复（保守策略）
        return True
    
    # ============================================================
    # 私有方法
    # ============================================================
    
    def _determine_degradation(
        self,
        scanner_name: str,
        error: Exception,
        is_recoverable: bool
    ) -> dict:
        """根据错误类型确定降级策略"""
        
        error_msg = str(error).lower()
        
        # local 扫描器失败 - 降级到其他平台
        if scanner_name == "local":
            if is_recoverable:
                return {
                    "action": "skip_this",
                    "continue": True,
                    "fallback": "使用 OpenClaw/GitHub 数据源"
                }
            else:
                return {
                    "action": "skip_this",
                    "continue": True,
                    "fallback": "跳过本地扫描，继续其他平台"
                }
        
        # openclaw 扫描器失败 - 继续其他
        elif scanner_name == "openclaw":
            if is_recoverable:
                return {
                    "action": "skip_this",
                    "continue": True,
                    "fallback": "使用 GitHub/Local 数据源"
                }
            else:
                return {
                    "action": "skip_this",
                    "continue": True,
                    "fallback": "跳过 OpenClaw 扫描，继续其他平台"
                }
        
        # github 扫描器失败 - 记录warn但继续
        elif scanner_name == "github":
            if is_recoverable:
                return {
                    "action": "skip_this",
                    "continue": True,
                    "fallback": "使用 OpenClaw/Local 数据源"
                }
            else:
                return {
                    "action": "skip_this",
                    "continue": True,
                    "fallback": "跳过 GitHub 扫描（需要手动授权）"
                }
        
        # 未知扫描器
        return {
            "action": "skip_this",
            "continue": True,
            "fallback": "跳过未知扫描器"
        }
    
    def _get_remedy_suggestion(self, error: Exception, error_type: str) -> str:
        """获取错误补救建议"""
        error_msg = str(error).lower()
        
        # Cookie失效
        if "cookie" in error_msg or "expired" in error_msg:
            return "请重新授权BOSS直聘账号，点击「重新登录」按钮刷新Cookie"
        
        # 网络超时
        if "timeout" in error_msg:
            return "网络超时，建议稍后重试。如果问题持续，请检查网络连接"
        
        # 权限拒绝
        if "permission" in error_msg or "denied" in error_msg:
            return "权限不足，请检查BOSS直聘账号是否具有发消息权限"
        
        # Rate limit
        if "rate" in error_msg or "limit" in error_msg:
            return "操作过于频繁，请在1小时后再试"
        
        # 默认建议
        return "遇到问题，您的招呼内容已保存。您可以稍后手动发送，或联系技术支持"
    
    def _log_scan_error(
        self,
        scanner_name: str,
        error: Exception,
        error_type: str,
        context: dict
    ):
        """记录扫描器错误日志"""
        extra = {"scenario": ScanErrorType.PLATFORM_FAILURE}
        
        self.logger.error(
            f"[A1] {scanner_name.upper()} 扫描失败: {error_type} - {str(error)}",
            extra=extra
        )
        
        if context:
            user_id = context.get("user_id", "unknown")
            self.logger.debug(
                f"[A1] Context: user_id={user_id}, context_keys={list(context.keys())}",
                extra=extra
            )
    
    def _log_greet_error(
        self,
        security_id: str,
        error: Exception,
        error_type: str,
        retry_count: int,
        greeting_text: str
    ):
        """记录发招呼错误日志"""
        extra = {"scenario": ScanErrorType.GREET_INTERRUPT}
        
        self.logger.error(
            f"[C2] 发招呼失败: security_id={security_id}, "
            f"retries={retry_count}/{self._max_retries}, error={error_type}",
            extra=extra
        )
        
        # 记录招呼内容（脱敏）
        greeting_preview = greeting_text[:50] + "..." if len(greeting_text) > 50 else greeting_text
        self.logger.debug(
            f"[C2] Greeting preview: {greeting_preview}",
            extra=extra
        )


# ============================================================
# 全局单例（便于复用）
# ============================================================

_global_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """获取全局ErrorHandler单例"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


# ============================================================
# 便捷函数
# ============================================================

def handle_scan_error(scanner_name: str, error: Exception, context: Optional[dict] = None) -> dict:
    """便捷函数：处理扫描器错误"""
    return get_error_handler().handle_scan_error(scanner_name, error, context)


def handle_empty_footprint(scan_results: Optional[dict] = None, user_id: Optional[str] = None) -> dict:
    """便捷函数：处理冷启动"""
    return get_error_handler().handle_empty_footprint(scan_results, user_id)


def handle_greet_error(
    security_id: str,
    error: Exception,
    greeting_text: str,
    context: Optional[dict] = None
) -> dict:
    """便捷函数：处理发招呼错误"""
    return get_error_handler().handle_greet_error(security_id, error, greeting_text, context)


# ============================================================
# 测试入口
# ============================================================

if __name__ == '__main__':
    handler = ErrorHandler()
    
    print("=" * 60)
    print("ErrorHandler 测试")
    print("=" * 60)
    
    # 测试 A1: 扫描器异常处理
    print("\n--- A1: 扫描器异常处理 ---")
    
    test_errors = [
        ("local", PermissionError("Permission denied: /path/to/file")),
        ("github", TimeoutError("Connection timeout")),
        ("openclaw", ConnectionError("Connection refused")),
    ]
    
    for scanner, err in test_errors:
        result = handler.handle_scan_error(scanner, err, {"user_id": "test_user"})
        print(f"  [{scanner}] continue={result['continue_other_scanners']}, "
              f"degradation={result['degradation']}")
    
    # 测试 B1: 冷启动
    print("\n--- B1: 冷启动（数字足迹为空） ---")
    
    empty_result = handler.handle_empty_footprint({"total_files": 0}, "test_user")
    print(f"  is_empty={empty_result['is_empty']}")
    print(f"  guidance_type={empty_result['guidance_type']}")
    print(f"  message={empty_result['message']}")
    
    # 测试 C2: 发招呼中断
    print("\n--- C2: 发招呼中断 ---")
    
    greet_err = ConnectionError("Cookie expired")
    greet_result = handler.handle_greet_error(
        security_id="abc123",
        error=greet_err,
        greeting_text="您好！我是XXX，对贵公司的XXX职位很感兴趣...",
        context={"retry_count": 3}
    )
    print(f"  manual_remedy={greet_result['manual_remedy']}")
    print(f"  retry_recommended={greet_result['retry_recommended']}")
    print(f"  remedy_suggestion={greet_result['remedy_suggestion']}")
    
    # 测试重试延迟计算
    print("\n--- 指数退避延迟 ---")
    for i in range(5):
        print(f"  retry {i}: {handler.get_retry_delay(i):.1f}s")
    
    print("\n" + "=" * 60)
    print(f"错误日志已写入: {ERROR_LOG_FILE}")
    print("=" * 60)