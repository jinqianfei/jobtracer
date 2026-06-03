"""
JobTracer - 求职足迹追踪系统
帮助用户自动扫描数字足迹、生成简历、搜索BOSS直聘职位
"""

__version__ = "1.0.0"
__author__ = "JobTracer Team"

from .scanner import FootprintScanner
from .storage import StorageManager

__all__ = ["FootprintScanner", "StorageManager"]