"""
JobTracer db module
包含数据库迁移脚本
"""

from .migration import Migration, main

__all__ = ['Migration', 'main']