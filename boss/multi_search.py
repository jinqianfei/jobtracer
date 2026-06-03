"""
JobTracer 多平台招聘搜索
统一接口：BOSS直聘 / 51job / 牛客 / 拉勾
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("jobtracer.multi_search")

# 检查 opencli 是否可用
import shutil

def _check_command(cmd: str) -> bool:
    return shutil.which(cmd) is not None

HAS_OPENCLI = _check_command("opencli")


class BaseJobSearcher(ABC):
    """招聘平台搜索器基类"""
    
    platform_name: str = "unknown"
    
    @abstractmethod
    async def search(
        self,
        keywords: List[str],
        city: str = "全国",
        experience: str = "不限",
        degree: str = "不限",
        salary: str = "不限",
        page: int = 1,
        page_size: int = 20
    ) -> List[Dict]:
        """搜索职位"""
        pass
    
    @abstractmethod
    async def get_job_detail(self, job_id: str) -> Optional[Dict]:
        """获取职位详情"""
        pass
    
    def normalize_job(self, raw_job: dict) -> dict:
        """标准化职位数据"""
        return {
            "job_id": raw_job.get("job_id", ""),
            "title": raw_job.get("title", ""),
            "company": raw_job.get("company", ""),
            "salary": raw_job.get("salary", ""),
            "location": raw_job.get("location", ""),
            "experience": raw_job.get("experience", ""),
            "degree": raw_job.get("degree", ""),
            "tags": raw_job.get("tags", []),
            "hr_name": raw_job.get("hr_name", ""),
            "published_at": raw_job.get("published_at", ""),
            "platform": self.platform_name,
            "raw_data": raw_job,
        }
    
    async def _call_opencli(self, command: List[str]) -> dict:
        """调用 opencli 命令"""
        if not HAS_OPENCLI:
            return {"success": False, "error": "opencli not installed"}
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                return {"success": False, "error": stderr.decode()}
            
            import json
            try:
                result = json.loads(stdout.decode())
                return {"success": True, "data": result}
            except json.JSONDecodeError:
                return {"success": False, "error": "Invalid JSON output"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}


class BOSSJobSearcher(BaseJobSearcher):
    """BOSS直聘搜索器"""
    
    platform_name = "BOSS直聘"
    
    async def search(
        self,
        keywords: List[str],
        city: str = "全国",
        experience: str = "不限",
        degree: str = "不限",
        salary: str = "不限",
        page: int = 1,
        page_size: int = 20
    ) -> List[Dict]:
        keyword_str = ",".join(keywords)
        result = await self._call_opencli([
            "opencli", "boss", "search", keyword_str,
            "--city", city,
            "-f", "json"
        ])
        
        if not result.get("success"):
            logger.warning(f"BOSS search failed: {result.get('error')}")
            return []
        
        jobs = result.get("data", {}).get("jobs", [])
        return [self.normalize_job(j) for j in jobs]
    
    async def get_job_detail(self, job_id: str) -> Optional[Dict]:
        return None  # BOSS 使用 security_id 而非 job_id


class Job51Searcher(BaseJobSearcher):
    """51job搜索器"""
    
    platform_name = "51job"
    
    async def search(
        self,
        keywords: List[str],
        city: str = "全国",
        experience: str = "不限",
        degree: str = "不限",
        salary: str = "不限",
        page: int = 1,
        page_size: int = 20
    ) -> List[Dict]:
        keyword_str = ",".join(keywords)
        
        # 尝试 opencli job51 search
        if HAS_OPENCLI:
            result = await self._call_opencli([
                "opencli", "job51", "search", keyword_str,
                "--city", city,
                "-f", "json"
            ])
            
            if result.get("success"):
                jobs = result.get("data", {}).get("jobs", [])
                return [self._handle_51job_platform(j) for j in jobs]
        
        # 如果 opencli 不可用，返回空结果（占位）
        logger.info("51job search: opencli job51 not available, returning empty")
        return []
    
    def _handle_51job_platform(self, raw_job: dict) -> dict:
        """51job 特殊字段处理"""
        normalized = self.normalize_job(raw_job)
        normalized["job_id"] = f"51job_{raw_job.get('jobid', raw_job.get('job_id', ''))}"
        return normalized
    
    async def get_job_detail(self, job_id: str) -> Optional[Dict]:
        return None


class NiukeSearcher(BaseJobSearcher):
    """牛客搜索器"""
    
    platform_name = "牛客"
    
    async def search(
        self,
        keywords: List[str],
        city: str = "全国",
        experience: str = "不限",
        degree: str = "不限",
        salary: str = "不限",
        page: int = 1,
        page_size: int = 20
    ) -> List[Dict]:
        keyword_str = ",".join(keywords)
        
        if HAS_OPENCLI:
            result = await self._call_opencli([
                "opencli", "niuke", "search", keyword_str,
                "--city", city,
                "-f", "json"
            ])
            
            if result.get("success"):
                jobs = result.get("data", {}).get("jobs", [])
                return [self._handle_niuke_platform(j) for j in jobs]
        
        logger.info("Niuke search: opencli niuke not available, returning empty")
        return []
    
    def _handle_niuke_platform(self, raw_job: dict) -> dict:
        """牛客特殊字段处理"""
        normalized = self.normalize_job(raw_job)
        normalized["job_id"] = f"niuke_{raw_job.get('positionId', raw_job.get('job_id', ''))}"
        return normalized
    
    async def get_job_detail(self, job_id: str) -> Optional[Dict]:
        return None


class MultiPlatformSearcher:
    """多平台聚合搜索"""
    
    def __init__(self):
        self.searchers: Dict[str, BaseJobSearcher] = {
            "boss": BOSSJobSearcher(),
            "51job": Job51Searcher(),
            "niuke": NiukeSearcher(),
        }
    
    async def search_all(
        self,
        keywords: List[str],
        platforms: List[str] = None,
        city: str = "全国",
        **kwargs
    ) -> Dict:
        """
        并发搜索多个平台
        
        Args:
            keywords: 关键词列表
            platforms: 指定平台列表，None 表示全部
            city: 城市
            
        Returns:
            {
                "jobs": [...],  # 去重后的职位列表
                "sources": {
                    "boss": {"count": 10, "status": "success"},
                    "51job": {"count": 0, "status": "no_opencli"},
                    ...
                }
            }
        """
        if platforms is None:
            platforms = list(self.searchers.keys())
        
        # 并发搜索
        tasks = {}
        for platform in platforms:
            if platform in self.searchers:
                searcher = self.searchers[platform]
                tasks[platform] = searcher.search(keywords, city=city, **kwargs)
        
        results = {}
        sources = {}
        
        async def safe_search(platform: str, coro):
            try:
                jobs = await asyncio.wait_for(coro, timeout=30)
                return platform, jobs, "success"
            except asyncio.TimeoutError:
                return platform, [], "timeout"
            except Exception as e:
                return platform, [], f"error: {str(e)}"
        
        # 执行所有搜索
        search_coros = [safe_search(p, t) for p, t in tasks.items()]
        search_results = await asyncio.gather(*search_coros)
        
        all_jobs = []
        for platform, jobs, status in search_results:
            results[platform] = jobs
            sources[platform] = {
                "count": len(jobs),
                "status": status
            }
            all_jobs.extend(jobs)
        
        # 去重（基于 job_id）
        deduplicated = self._deduplicate_jobs(all_jobs)
        
        return {
            "jobs": deduplicated,
            "sources": sources,
            "total": len(deduplicated)
        }
    
    def _deduplicate_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """去重：同一职位多平台出现时保留一个"""
        seen = {}
        for job in jobs:
            # 用 (title + company) 作为去重键
            key = f"{job.get('title')}_{job.get('company')}"
            if key not in seen:
                seen[key] = job
            else:
                # 如果已存在，优先保留有更多信息的那条
                existing = seen[key]
                if len(job.get('raw_data', {}).get('raw_data', {})) > len(existing.get('raw_data', {}).get('raw_data', {})):
                    seen[key] = job
        
        return list(seen.values())
    
    def get_available_platforms(self) -> List[str]:
        """获取可用的平台列表"""
        available = []
        for name, searcher in self.searchers.items():
            # 可以添加平台特定检测
            available.append(name)
        return available