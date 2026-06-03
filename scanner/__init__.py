"""
JobTracer Scanner Module
数字足迹扫描器 - 扫描本地/飞书/GitHub/OpenClaw
"""

# 已实现的扫描器 - 直接导入（立即可用）
from .local_scanner import scan_local
from .openclaw_scanner import scan_openclaw
from .github_scanner import scan_github

__all__ = ["scan_local", "scan_openclaw", "scan_github"]

# 延迟导入 - Phase 2 模块，避免占位符阻塞导入
def __getattr__(name):
    if name == "FootprintScanner":
        from .footprint_scanner import FootprintScanner
        return FootprintScanner
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")