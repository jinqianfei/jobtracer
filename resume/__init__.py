"""
JobTracer Resume Module
简历生成器 - LLM + HTML模板生成简历
简历定制器 - 针对目标JD定制简历内容
"""

from .generator import ResumeGenerator
from .customizer import ResumeCustomizer

__all__ = ["ResumeGenerator", "ResumeCustomizer"]