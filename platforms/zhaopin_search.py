"""
platforms/zhaopin_search.py
前程无忧(51job)搜索器 - 基于 opencli 51job search
"""
import logging
import subprocess
import json
import asyncio
from typing import List, Dict, Any

from platforms.base import PlatformSearcher

logger = logging.getLogger('jobtracer.platforms.zhaopin')


class ZhaopinSearcher(PlatformSearcher):
    """
    前程无忧(51job)搜索器
    基于 opencli 51job search 命令
    """

    platform_name = "前程无忧"
    base_url = "https://www.51job.com"

    async def search(
        self,
        keywords: List[str],
        city: str = "全国",
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        搜索 51job 职位

        Args:
            keywords: 搜索关键词列表
            city: 工作城市
            **kwargs: 其他参数（experience, degree, salary, page, page_size）

        Returns:
            List[dict]: 职位列表（统一格式）
        """
        query = ' '.join(keywords[:2])
        page = kwargs.get('page', 1)
        page_size = min(kwargs.get('page_size', 20), 50)
        salary = kwargs.get('salary', '')
        experience = kwargs.get('experience', '')
        degree = kwargs.get('degree', '')

        cmd = [
            'opencli', '51job', 'search', query,
            '--area', city,
            '--page', str(page),
            '--limit', str(page_size),
            '-f', 'json'
        ]

        if salary:
            cmd.extend(['--salary', salary])
        if experience:
            cmd.extend(['--experience', experience])
        if degree:
            cmd.extend(['--degree', degree])

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=30
            )

            if proc.returncode != 0:
                logger.error(f"[51job] 搜索失败: {stderr.decode()}")
                return []

            output = stdout.decode('utf-8', errors='replace').strip()

            try:
                jobs_data = json.loads(output) if output else []
            except json.JSONDecodeError as e:
                logger.warning(f"[51job] JSON解析失败: {e}")
                return []

            if not isinstance(jobs_data, list):
                jobs_data = []

            # 解析并返回统一格式
            jobs = []
            for raw in jobs_data:
                job = self.parse_job(raw)
                jobs.append(job)

            logger.info(f"[51job] 搜索完成: {len(jobs)} 个职位")
            self._last_jobs_count = len(jobs)
            return jobs

        except asyncio.TimeoutError:
            logger.error("[51job] 搜索超时（30s）")
            return []
        except Exception as e:
            logger.error(f"[51job] 搜索异常: {e}")
            return []

    def parse_job(self, raw_data: Dict) -> Dict:
        """
        解析 51job 原始数据为统一格式
        """
        if not raw_data:
            return self.normalize_job({})

        # 51job 返回字段映射
        job_id = str(raw_data.get('jobId', raw_data.get('job_id', '')))
        title = raw_data.get('title', '')
        company = raw_data.get('company', '')
        city_name = raw_data.get('city', '')
        district = raw_data.get('district', '')
        salary_text = raw_data.get('salary', '')

        # 解析薪资
        salary_info = self._parse_salary(salary_text)

        # 处理标签
        tags = raw_data.get('tags', [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',') if t.strip()]
        elif not isinstance(tags, list):
            tags = []

        # 工作经验/学历
        experience = raw_data.get('workYear', '')
        degree = raw_data.get('degree', '')

        # 公司信息
        company_type = raw_data.get('companyType', '')
        company_size = raw_data.get('companySize', '')
        industry = raw_data.get('industry', '')

        # HR/发布时间
        hr = raw_data.get('hr', '')
        published_at = raw_data.get('issueDate', '')

        # URL
        url = raw_data.get('url', '')
        if not url and job_id:
            url = f"https://search.51job.com/list/{city_name},{job_id}.html"

        # 亮点/描述
        # 亮点/描述
        highlights = []
        if industry or company_type:
            highlights = [f"{industry}/{company_type}"]

        return self.normalize_job({
            'job_id': job_id,
            'title': title,
            'company': company,
            'city': f"{city_name}-{district}" if district else city_name,
            'salary': salary_text,
            'experience': experience,
            'degree': degree,
            'tags': tags,
            'highlights': highlights,
            'url': url,
            'published_at': published_at,
            'raw_data': {
                **raw_data,
                'company_type': company_type,
                'company_size': company_size,
                'industry': industry,
                'hr': hr,
            },
        })

    def _parse_salary(self, salary_text: str) -> Dict[str, Any]:
        """解析薪资文本"""
        import re

        if not salary_text:
            return {'min': 0, 'max': 0, 'raw': ''}

        # 匹配 10-15K / 10-15k
        match = re.search(r'(\d+)-(\d+)(K|k)', salary_text)
        if match:
            return {
                'min': int(match.group(1)),
                'max': int(match.group(2)),
                'raw': salary_text
            }

        # 匹配 1-1.5万
        match = re.search(r'(\d+)-(\d+\.?\d*)万', salary_text)
        if match:
            return {
                'min': int(float(match.group(1)) * 10),
                'max': int(float(match.group(2)) * 10),
                'raw': salary_text
            }

        # 匹配面议
        if '面议' in salary_text:
            return {'min': 0, 'max': 0, 'raw': salary_text}

        return {'min': 0, 'max': 0, 'raw': salary_text}


# ============================================================
# 测试入口
# ============================================================

if __name__ == "__main__":
    import asyncio
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    async def test():
        print("=== 51job 搜索测试 ===")
        searcher = ZhaopinSearcher()
        print(f"平台名称: {searcher.platform_name}")
        print(f"是否可用: {searcher.is_available()}")
        print()

        print("执行搜索: Python 后端，上海...")
        jobs = await searcher.search(
            keywords=['Python', '后端'],
            city='上海',
            page=1,
            page_size=5
        )

        print(f"结果: {len(jobs)} 个职位")
        print()

        for i, job in enumerate(jobs[:5], 1):
            print(f"{i}. {job['title']} @ {job['company']}")
            print(f"   薪资: {job['salary']} | 城市: {job['city']}")
            print(f"   经验: {job['experience']} | 学历: {job['degree']}")
            print()

        return jobs

    asyncio.run(test())