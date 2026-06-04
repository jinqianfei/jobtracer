"""
JobTracer API Module - FastAPI 服务
供其他 Agent 调用 JobTracer 索引
"""

from .server import create_app, get_app

# 注意：不直接导入 app，使用 get_app() 避免版本兼容问题
__all__ = ["create_app", "get_app"]