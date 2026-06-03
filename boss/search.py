"""
boss/search.py
BOSS搜索模块 - 基于 opencli boss search 命令
"""

import subprocess
import json
import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from pathlib import Path

# 导入存储管理器
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from storage.manager import StorageManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('jobtracer.boss.search')


class BOSSSearcher:
    """
    BOSS直聘搜索模块
    通过 opencli boss search 命令搜索职位
    """

    def __init__(self, storage_manager: StorageManager = None):
        """
        初始化BOSS搜索器

        Args:
            storage_manager: 存储管理器实例（可选）
        """
        self.storage = storage_manager or StorageManager()
        self.cache_dir = self.storage.ensure_subdir('jobs/jd_cache')
        self.platform = 'BOSS直聘'

    async def search_jobs(
        self,
        keywords: List[str],
        city: str = "全国",
        experience: str = "不限",
        degree: str = "不限",
        salary: str = "不限",
        page: int = 1,
        page_size: int = 20
    ) -> dict:
        """
        搜索BOSS直聘职位

        Args:
            keywords: 搜索关键词列表
            city: 工作城市，默认"全国"
            experience: 经验要求，默认"不限"
            degree: 学历要求，默认"不限"
            salary: 薪资要求，默认"不限"
            page: 页码，默认1
            page_size: 每页数量，默认20

        Returns:
            dict: 搜索结果，包含 jobs, total, page, page_size
        """
        # 组合关键词（最多取前3个）
        query = ' '.join(keywords[:3])
        cmd = [
            'opencli', 'boss', 'search', query,
            '--city', city,
            '--experience', experience,
            '--degree', degree,
            '--salary', salary,
            '--page', str(page),
            '--limit', str(page_size),
            '-f', 'json'
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                encoding='utf-8'
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else '未知错误'
                logger.error(f"BOSS搜索失败: {error_msg}")
                return {
                    'success': False,
                    'error': f'BOSS搜索失败: {error_msg}',
                    'jobs': [],
                    'total': 0,
                    'page': page,
                    'page_size': page_size
                }

            # 解析JSON输出
            try:
                raw_jobs = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}, raw output: {result.stdout[:500]}")
                return {
                    'success': False,
                    'error': f'JSON解析失败: {e}',
                    'jobs': [],
                    'total': 0,
                    'page': page,
                    'page_size': page_size
                }

            # 标准化职位数据
            normalized_jobs = []
            for job in raw_jobs:
                job_id = 'boss_' + job.get('security_id', '')
                normalized = self._normalize_job(job, job_id)
                normalized_jobs.append(normalized)

                # 缓存职位详情
                self._cache_job(job_id, job)

            # 更新 job-tracker.json
            self._update_job_tracker(normalized_jobs)

            logger.info(f"BOSS搜索成功: 找到 {len(normalized_jobs)} 个职位")

            return {
                'success': True,
                'jobs': normalized_jobs,
                'total': len(normalized_jobs),
                'page': page,
                'page_size': page_size
            }

        except subprocess.TimeoutExpired:
            logger.error("BOSS搜索超时")
            return {
                'success': False,
                'error': '搜索超时，请重试',
                'jobs': [],
                'total': 0,
                'page': page,
                'page_size': page_size
            }
        except FileNotFoundError:
            logger.error("opencli 命令未找到，请确保 opencli 已安装")
            return {
                'success': False,
                'error': 'opencli 命令未找到，请安装 opencli',
                'jobs': [],
                'total': 0,
                'page': page,
                'page_size': page_size
            }
        except Exception as e:
            logger.error(f"BOSS搜索异常: {e}")
            return {
                'success': False,
                'error': f'搜索异常: {str(e)}',
                'jobs': [],
                'total': 0,
                'page': page,
                'page_size': page_size
            }

    def search_jobs_with_retry(
        self,
        keywords: List[str],
        city: str = "全国",
        experience: str = "不限",
        degree: str = "不限",
        salary: str = "不限",
        page: int = 1,
        page_size: int = 20,
        max_retries: int = 1
    ) -> dict:
        """
        带重试的搜索（网络超时重试1次）

        Args:
            keywords: 搜索关键词列表
            city: 工作城市
            experience: 经验要求
            degree: 学历要求
            salary: 薪资要求
            page: 页码
            page_size: 每页数量
            max_retries: 最大重试次数

        Returns:
            dict: 搜索结果
        """
        result = self.search_jobs(keywords, city, experience, degree, salary, page, page_size)

        # 如果失败且是超时错误，尝试重试
        if not result['success'] and '超时' in result.get('error', ''):
            if max_retries > 0:
                logger.info("网络超时，执行重试...")
                result = self.search_jobs(keywords, city, experience, degree, salary, page, page_size)

        return result

    def get_job_detail(self, security_id: str) -> dict:
        """
        获取BOSS职位详情

        Args:
            security_id: BOSS职位ID

        Returns:
            dict: 职位详情
        """
        # 先检查缓存
        cache_file = self.cache_dir / (security_id + '.json')
        if cache_file.exists():
            try:
                cached = json.loads(cache_file.read_text(encoding='utf-8'))
                logger.debug(f"从缓存读取职位详情: {security_id}")
                return {
                    'success': True,
                    'data': cached,
                    'from_cache': True
                }
            except Exception as e:
                logger.warning(f"读取缓存失败: {e}")

        # 调用 opencli boss detail
        cmd = ['opencli', 'boss', 'detail', security_id, '-f', 'json']

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                encoding='utf-8'
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else '未知错误'
                logger.error(f"获取职位详情失败: {error_msg}")
                return {
                    'success': False,
                    'error': f'获取详情失败: {error_msg}'
                }

            detail = json.loads(result.stdout)

            # 更新缓存
            cache_file.write_text(json.dumps(detail, ensure_ascii=False), encoding='utf-8')

            return {
                'success': True,
                'data': detail,
                'from_cache': False
            }

        except Exception as e:
            logger.error(f"获取职位详情异常: {e}")
            return {
                'success': False,
                'error': f'获取详情异常: {str(e)}'
            }

    def _normalize_job(self, job: dict, job_id: str) -> dict:
        """
        标准化职位数据格式

        Args:
            job: 原始职位数据
            job_id: 标准化后的职位ID

        Returns:
            dict: 标准化后的职位数据
        """
        salary_info = self._parse_salary(job.get('salary', ''))

        return {
            'job_id': job_id,
            'security_id': job.get('security_id', ''),
            'title': job.get('name', ''),
            'company': job.get('company', ''),
            'salary': salary_info['raw'],
            'salary_min': salary_info['min'],
            'salary_max': salary_info['max'],
            'location': job.get('area', ''),
            'experience': job.get('experience', ''),
            'degree': job.get('degree', ''),
            'tags': job.get('skills', []) or [],
            'hr_name': job.get('boss', ''),
            'hr_avatar': job.get('bossAvatar', ''),
            'hr_online': job.get('bossOnline', False),
            'job_detail_url': job.get('url', ''),
            'company_url': job.get('companyUrl', ''),
            'published_at': job.get('updated', ''),
            'platform': self.platform,
            'status': 'new',
            'created_at': datetime.now().isoformat()
        }

    def _parse_salary(self, salary_text: str) -> dict:
        """
        解析薪资文本

        Args:
            salary_text: 薪资文本，如 "15-25K" 或 "1-2万"

        Returns:
            dict: 包含 min, max, raw 的字典
        """
        if not salary_text:
            return {'min': 0, 'max': 0, 'raw': ''}

        # 匹配 K 或万
        match = re.search(r'(\d+)-(\d+)(K|k|万)', salary_text)
        if match:
            min_sal, max_sal, unit = match.groups()
            multiplier = 1000 if unit.upper() in ('K',) else 10000
            return {
                'min': int(min_sal) * multiplier,
                'max': int(max_sal) * multiplier,
                'raw': salary_text
            }

        # 匹配只有数字的情况（如 "面议"）
        return {'min': 0, 'max': 0, 'raw': salary_text}

    def _cache_job(self, job_id: str, job_data: dict) -> None:
        """
        缓存职位数据

        Args:
            job_id: 职位ID
            job_data: 职位数据
        """
        try:
            cache_file = self.cache_dir / (job_id + '.json')
            cache_file.write_text(
                json.dumps(job_data, ensure_ascii=False),
                encoding='utf-8'
            )
            logger.debug(f"缓存职位: {job_id}")
        except Exception as e:
            logger.warning(f"缓存职位失败: {e}")

    def _update_job_tracker(self, new_jobs: List[dict]) -> None:
        """
        更新 job-tracker.json

        Args:
            new_jobs: 新职位列表
        """
        try:
            current_data = self.storage.read('job-tracker.json') or {
                'jobs': [],
                'last_updated': datetime.now().isoformat()
            }

            existing_ids = {job['job_id'] for job in current_data.get('jobs', [])}

            # 只添加不重复的职位
            for job in new_jobs:
                if job['job_id'] not in existing_ids:
                    current_data['jobs'].append(job)

            current_data['last_updated'] = datetime.now().isoformat()
            self.storage.write('job-tracker.json', current_data)

            logger.debug(f"更新 job-tracker.json，新增 {len(new_jobs)} 个职位")

        except Exception as e:
            logger.error(f"更新 job-tracker.json 失败: {e}")

    def get_cached_jobs(self) -> List[dict]:
        """
        获取所有缓存的职位

        Returns:
            List[dict]: 职位列表
        """
        return self.storage.get_jobs()


# 便捷函数
async def search_jobs(
    keywords: List[str],
    city: str = "全国",
    experience: str = "不限",
    degree: str = "不限",
    salary: str = "不限",
    page: int = 1,
    page_size: int = 20
) -> dict:
    """
    搜索BOSS直聘职位（便捷函数）

    Args:
        keywords: 搜索关键词列表
        city: 工作城市
        experience: 经验要求
        degree: 学历要求
        salary: 薪资要求
        page: 页码
        page_size: 每页数量

    Returns:
        dict: 搜索结果
    """
    searcher = BOSSSearcher()
    return await searcher.search_jobs(keywords, city, experience, degree, salary, page, page_size)


if __name__ == '__main__':
    # 测试代码
    import asyncio

    print("=" * 60)
    print("BOSS搜索模块测试")
    print("=" * 60)

    async def test():
        searcher = BOSSSearcher()

        # 测试搜索
        print("\n测试搜索: Python 工程师")
        result = await searcher.search_jobs(
            keywords=['Python', '工程师'],
            city='北京',
            page=1,
            page_size=5
        )

        print(f"\n搜索结果:")
        print(f"  success: {result['success']}")
        print(f"  jobs count: {len(result.get('jobs', []))}")
        print(f"  total: {result.get('total', 0)}")

        if result['success'] and result['jobs']:
            print(f"\n第一个职位:")
            job = result['jobs'][0]
            for key in ['job_id', 'title', 'company', 'salary', 'location', 'experience', 'degree']:
                print(f"  {key}: {job.get(key, '')}")

        # 测试获取缓存的职位
        print("\n\n测试获取缓存职位:")
        cached = searcher.get_cached_jobs()
        print(f"  缓存职位数: {len(cached)}")

        return result

    asyncio.run(test())

    print("\n" + "=" * 60)
    print("BOSS搜索模块测试完成")
    print("=" * 60)