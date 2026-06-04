"""
platforms/base.py
招聘平台搜索基类
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import re
import logging

logger = logging.getLogger('jobtracer.platforms.base')


class PlatformSearcher(ABC):
    """
    招聘平台搜索基类
    所有平台搜索器需继承此类并实现抽象方法
    """

    platform_name: str = "unknown"
    base_url: str = ""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self._available = True

    @abstractmethod
    async def search(
        self,
        keywords: List[str],
        city: str,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        执行搜索，返回职位列表

        Args:
            keywords: 搜索关键词列表
            city: 工作城市
            **kwargs: 其他参数（如 experience, degree, salary, page, page_size）

        Returns:
            List[dict]: 职位列表
        """
        pass

    @abstractmethod
    def parse_job(self, raw_data: Dict) -> Dict:
        """
        解析原始数据为统一格式

        Args:
            raw_data: 原始数据

        Returns:
            dict: 统一格式的职位数据
        """
        pass

    def normalize_job(self, job: Dict) -> Dict:
        """
        统一格式：
        {
            'job_id': str,
            'platform': str,
            'title': str,
            'company': str,
            'city': str,
            'salary': str,           # '20-30K' 格式
            'salary_min': int,       # 以K为单位
            'salary_max': int,
            'experience': str,      # '3-5年'
            'degree': str,          # '本科'
            'tags': List[str],
            'highlights': List[str],
            'url': str,
            'published_at': str,
            'raw_data': dict,
        }
        """
        salary_info = self._parse_salary(job.get('salary', ''))

        normalized = {
            'job_id': job.get('job_id', ''),
            'platform': self.platform_name,
            'title': job.get('title', ''),
            'company': job.get('company', ''),
            'city': job.get('city', '') or job.get('location', ''),
            'salary': salary_info['raw'],
            'salary_min': salary_info['min'],
            'salary_max': salary_info['max'],
            'experience': job.get('experience', ''),
            'degree': job.get('degree', ''),
            'tags': job.get('tags', []),
            'highlights': job.get('highlights', []),
            'url': job.get('url', ''),
            'published_at': job.get('published_at', ''),
            'raw_data': job.get('raw_data', {}),
        }

        return normalized

    def _parse_salary(self, salary_text: str) -> Dict[str, Any]:
        """
        解析薪资文本，转换为统一格式

        Args:
            salary_text: 薪资文本，如 "15-25K" 或 "1-2万"

        Returns:
            dict: 包含 min, max, raw 的字典（薪资以K为单位）
        """
        if not salary_text:
            return {'min': 0, 'max': 0, 'raw': ''}

        # 匹配 15-25K / 15-25k
        match = re.search(r'(\d+)-(\d+)(K|k)', salary_text)
        if match:
            return {
                'min': int(match.group(1)),
                'max': int(match.group(2)),
                'raw': salary_text
            }

        # 匹配 1-2万
        match = re.search(r'(\d+)-(\d+)万', salary_text)
        if match:
            return {
                'min': int(float(match.group(1)) * 10),
                'max': int(float(match.group(2)) * 10),
                'raw': salary_text
            }

        # 匹配面议等
        return {'min': 0, 'max': 0, 'raw': salary_text}

    def is_available(self) -> bool:
        """平台是否可用"""
        return self._available

    def mark_unavailable(self, reason: str = "") -> None:
        """标记平台不可用"""
        self._available = False
        logger.warning(f"[{self.platform_name}] 平台不可用: {reason}")

    def mark_available(self) -> None:
        """标记平台可用"""
        self._available = True
