"""多平台聚合搜索
并行搜索 BOSS / 51job / 智联，去重后统一返回
"""
import asyncio
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from storage.manager import StorageManager

logger = logging.getLogger('jobtracer.jobs.multi_platform')


class MultiPlatformSearcher:
    """多平台聚合搜索器"""
    
    def __init__(self):
        self.storage = StorageManager()
    
    async def search_all(
        self,
        keywords: List[str],
        city: str = "上海",
        platforms: List[str] = None
    ) -> dict:
        """
        并行搜索多个平台
        
        Args:
            keywords: 搜索关键词
            city: 城市
            platforms: ["boss", "51job", "zhilian"] 或 None=全部
        
        Returns:
            {
                "boss": [...],
                "51job": [...],
                "zhilian": [...],
                "total": N,
                "deduped": M,
                "new_jobs": [...],  # 与已保存职位去重后的新职位
            }
        """
        if platforms is None:
            platforms = ["boss", "51job", "zhilian"]
        
        # 获取已保存的职位（用于去重）
        saved_job_keys = self._get_saved_job_keys()
        
        # 并行搜索
        tasks = []
        results = {}
        
        if "boss" in platforms:
            tasks.append(self._search_boss(keywords, city))
        if "51job" in platforms:
            tasks.append(self._search_51job(keywords, city))
        if "zhilian" in platforms:
            tasks.append(self._search_zhilian(keywords, city))
        
        # 执行搜索
        platform_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 整理结果
        idx = 0
        if "boss" in platforms:
            results["boss"] = platform_results[idx] if not isinstance(platform_results[idx], Exception) else []
            idx += 1
        if "51job" in platforms:
            results["51job"] = platform_results[idx] if not isinstance(platform_results[idx], Exception) else []
            idx += 1
        if "zhilian" in platforms:
            results["zhilian"] = platform_results[idx] if not isinstance(platform_results[idx], Exception) else []
            idx += 1
        
        # 合并所有职位
        all_jobs = []
        for platform, jobs in results.items():
            if isinstance(jobs, list):
                for job in jobs:
                    job["platform"] = platform
                    all_jobs.append(job)
        
        # 去重（按 company + title）
        deduped = self.dedup_jobs(all_jobs)
        
        # 找出新职位（不在已保存中）
        new_jobs = [j for j in deduped if self._make_key(j) not in saved_job_keys]
        
        return {
            **results,
            "total": len(all_jobs),
            "deduped": len(deduped),
            "new_jobs": new_jobs,
        }
    
    async def _search_boss(self, keywords: List[str], city: str) -> List[dict]:
        """搜索 BOSS 直聘"""
        try:
            from boss.search import BOSSSearcher
            searcher = BOSSSearcher()
            result = await searcher.search_jobs(keywords=keywords, city=city, page=1, page_size=20)
            jobs = result.get("jobs", []) if isinstance(result, dict) else []
            logger.info(f"BOSS 搜索到 {len(jobs)} 个职位")
            return jobs
        except Exception as e:
            logger.error(f"BOSS 搜索失败: {e}")
            return []
    
    async def _search_51job(self, keywords: List[str], city: str) -> List[dict]:
        """搜索 51job"""
        try:
            from platforms.zhaopin_search import ZhaopinSearcher
            searcher = ZhaopinSearcher()
            jobs = await searcher.search(keywords=keywords, city=city)
            logger.info(f"51job 搜索到 {len(jobs)} 个职位")
            return jobs
        except Exception as e:
            logger.error(f"51job 搜索失败: {e}")
            return []
    
    async def _search_zhilian(self, keywords: List[str], city: str) -> List[dict]:
        """搜索智联招聘"""
        try:
            from platforms.zhilian_search import ZhilianSearcher
            searcher = ZhilianSearcher()
            jobs = await searcher.search(keywords=keywords, city=city)
            logger.info(f"智联 搜索到 {len(jobs)} 个职位")
            return jobs
        except Exception as e:
            logger.error(f"智联 搜索失败: {e}")
            return []
    
    def dedup_jobs(self, jobs: List[dict]) -> List[dict]:
        """按 company + title 去重（保留第一个）"""
        seen = set()
        result = []
        for job in jobs:
            key = self._make_key(job)
            if key not in seen:
                seen.add(key)
                result.append(job)
        return result
    
    def _make_key(self, job: dict) -> str:
        """生成去重 key"""
        company = job.get("company", "").strip()
        title = job.get("title", "") or job.get("name", "")
        return f"{company}|{title}"
    
    def _get_saved_job_keys(self) -> set:
        """获取已保存职位的 key 集合"""
        jobs = self.storage.get_jobs()
        return {self._make_key(j) for j in jobs}


async def search_multi_platform(
    keywords: List[str],
    city: str = "上海",
    platforms: List[str] = None
) -> dict:
    """快捷函数：多平台搜索"""
    searcher = MultiPlatformSearcher()
    return await searcher.search_all(keywords, city, platforms)


if __name__ == "__main__":
    async def test():
        searcher = MultiPlatformSearcher()
        result = await searcher.search_all(["Python后端"], "上海", ["boss"])
        print(f"BOSS: {len(result.get('boss', []))} 个")
        print(f"总计: {result['total']} 个（去重后: {result['deduped']}）")
        print(f"新职位: {len(result['new_jobs'])} 个")
    
    asyncio.run(test())