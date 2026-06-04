"""
platforms/zhilian_search.py
智联招聘搜索器 - 占位实现
"""

import logging
from typing import List, Dict, Any

from platforms.base import PlatformSearcher

logger = logging.getLogger('jobtracer.platforms.zhilian')


class ZhilianSearcher(PlatformSearcher):
    """
    智联招聘搜索器
    当前为占位 stub，后续迭代实现
    """

    platform_name = "智联招聘"
    base_url = "https://www.zhaopin.com"

    async def search(
        self,
        keywords: List[str],
        city: str,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        占位实现 - 暂时返回空列表
        """
        logger.info(f"[智联] 占位 stub，keywords={keywords}, city={city}")
        return []

    def parse_job(self, raw_data: Dict) -> Dict:
        """
        占位实现
        """
        return self.normalize_job({
            'job_id': '',
            'title': '',
            'company': '',
            'city': '',
            'salary': '',
            'experience': '',
            'degree': '',
            'tags': [],
            'highlights': [],
            'url': '',
            'published_at': '',
            'raw_data': raw_data,
        })
