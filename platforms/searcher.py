"""
platforms/searcher.py
多平台统一搜索入口
"""

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional

from platforms.base import PlatformSearcher
from platforms.boss_search import BossPlatformSearcher
from platforms.zhaopin_search import ZhaopinSearcher
from platforms.zhilian_search import ZhilianSearcher

logger = logging.getLogger('jobtracer.platforms.searcher')


# 平台注册表
_PLATFORM_REGISTRY: Dict[str, type] = {
    'boss': BossPlatformSearcher,
    '51job': ZhaopinSearcher,
    'zhilian': ZhilianSearcher,
}

# 默认启用的平台
DEFAULT_ENABLED = ['boss', '51job', 'zhilian']


class MultiPlatformSearcher:
    """
    多平台统一搜索入口

    支持同时查询多个招聘平台，统一返回格式
    """

    def __init__(self, enabled_platforms: Optional[List[str]] = None):
        """
        初始化多平台搜索器

        Args:
            enabled_platforms: 启用的平台列表，默认 ['boss', '51job', 'zhilian']
        """
        self.enabled_platforms = enabled_platforms or DEFAULT_ENABLED.copy()
        self._platforms: Dict[str, PlatformSearcher] = {}
        self._init_platforms()

    def _init_platforms(self) -> None:
        """初始化所有平台搜索器"""
        for platform in self.enabled_platforms:
            if platform not in _PLATFORM_REGISTRY:
                logger.warning(f"未知平台: {platform}，跳过")
                continue
            try:
                self._platforms[platform] = _PLATFORM_REGISTRY[platform]()
                logger.debug(f"初始化平台: {platform}")
            except Exception as e:
                logger.error(f"初始化平台 {platform} 失败: {e}")

    async def search_all(
        self,
        keywords: List[str],
        city: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        并行搜索所有启用的平台

        Args:
            keywords: 搜索关键词列表
            city: 工作城市
            **kwargs: 其他参数透传给各平台

        Returns:
            dict: {
                'total': int,          # 总职位数
                'results': {
                    'platform_name': {
                        'platform': str,
                        'total': int,
                        'jobs': List[dict],
                        'errors': str,
                        'duration_ms': float,
                    }
                }
            }
        """
        start_time = time.time()
        tasks = {}
        for name, searcher in self._platforms.items():
            task = asyncio.create_task(
                self._search_platform(name, searcher, keywords, city, **kwargs)
            )
            tasks[name] = task

        results = {}
        total = 0

        for name, task in tasks.items():
            try:
                result = await task
                results[name] = result
                total += result['total']
            except Exception as e:
                logger.error(f"平台 {name} 搜索异常: {e}")
                results[name] = {
                    'platform': name,
                    'total': 0,
                    'jobs': [],
                    'errors': str(e),
                    'duration_ms': 0.0,
                }

        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(f"[MultiPlatform] 搜索完成，总计 {total} 个职位，耗时 {elapsed_ms:.1f}ms")

        return {
            'total': total,
            'results': results,
            'duration_ms': elapsed_ms,
        }

    async def search_platform(
        self,
        platform: str,
        keywords: List[str],
        city: str,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        搜索指定平台

        Args:
            platform: 平台名称 (boss / 51job / zhilian)
            keywords: 搜索关键词列表
            city: 工作城市
            **kwargs: 其他参数

        Returns:
            List[dict]: 职位列表
        """
        searcher = self._platforms.get(platform)
        if searcher is None:
            logger.warning(f"平台不存在或未启用: {platform}")
            return []

        result = await self._search_platform(platform, searcher, keywords, city, **kwargs)
        return result['jobs']

    async def _search_platform(
        self,
        platform: str,
        searcher: PlatformSearcher,
        keywords: List[str],
        city: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行单个平台搜索（内部方法）

        Args:
            platform: 平台名称
            searcher: 搜索器实例
            keywords: 关键词
            city: 城市
            **kwargs: 其他参数

        Returns:
            dict: 平台搜索结果
        """
        start_time = time.time()
        errors = ""

        try:
            jobs = await asyncio.wait_for(
                searcher.search(keywords, city, **kwargs),
                timeout=searcher.timeout
            )

            # 标准化所有职位
            normalized_jobs = [searcher.parse_job(job) for job in jobs]

            elapsed_ms = (time.time() - start_time) * 1000
            return {
                'platform': platform,
                'total': len(normalized_jobs),
                'jobs': normalized_jobs,
                'errors': "",
                'duration_ms': elapsed_ms,
            }

        except asyncio.TimeoutError:
            elapsed_ms = (time.time() - start_time) * 1000
            searcher.mark_unavailable("搜索超时")
            logger.warning(f"[{platform}] 搜索超时 ({searcher.timeout}s)")
            return {
                'platform': platform,
                'total': 0,
                'jobs': [],
                'errors': '搜索超时',
                'duration_ms': elapsed_ms,
            }

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            errors = str(e)
            logger.error(f"[{platform}] 搜索异常: {e}")
            return {
                'platform': platform,
                'total': 0,
                'jobs': [],
                'errors': errors,
                'duration_ms': elapsed_ms,
            }

    def get_platform_status(self) -> Dict[str, bool]:
        """
        获取各平台可用状态

        Returns:
            dict: { 'boss': True, '51job': False, ... }
        """
        return {
            name: searcher.is_available()
            for name, searcher in self._platforms.items()
        }

    def get_available_platforms(self) -> List[str]:
        """获取当前可用的平台列表"""
        return [
            name for name, searcher in self._platforms.items()
            if searcher.is_available()
        ]
