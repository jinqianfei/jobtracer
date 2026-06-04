"""
platforms/linkedin_search.py
LinkedIn 职位搜索器 - 基于 opencli linkedin search
作为国际化职位补充搜索（英文/外资岗位）
"""
import logging
import subprocess
import json
import asyncio
from typing import List, Dict, Any

from platforms.base import PlatformSearcher

logger = logging.getLogger('jobtracer.platforms.linkedin')


class LinkedInSearcher(PlatformSearcher):
    """
    LinkedIn 职位搜索器
    基于 opencli linkedin search 命令
    作为国际化职位补充搜索（英文/外资岗位）
    """

    platform_name = "LinkedIn"
    base_url = "https://www.linkedin.com"

    async def search(
        self,
        keywords: List[str],
        city: str = "",
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        搜索 LinkedIn 职位

        Args:
            keywords: 搜索关键词列表
            city: 工作城市（英文）
            **kwargs: 其他参数（experience_level, job_type, date_posted, remote, page, page_size）

        Returns:
            List[dict]: 职位列表（统一格式）
        """
        query = ' '.join(keywords[:2])
        limit = min(kwargs.get('page_size', kwargs.get('limit', 20)), 50)
        start = kwargs.get('start', 0)
        experience_level = kwargs.get('experience_level', '')
        job_type = kwargs.get('job_type', '')
        date_posted = kwargs.get('date_posted', '')
        remote = kwargs.get('remote', '')
        details = kwargs.get('details', False)

        cmd = [
            'opencli', 'linkedin', 'search', query,
            '--limit', str(limit),
            '--start', str(start),
            '-f', 'json'
        ]

        if city:
            cmd.extend(['--location', city])
        if experience_level:
            cmd.extend(['--experience-level', experience_level])
        if job_type:
            cmd.extend(['--job-type', job_type])
        if date_posted:
            cmd.extend(['--date-posted', date_posted])
        if remote:
            cmd.extend(['--remote', remote])

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=40
            )

            if proc.returncode != 0:
                stderr_text = stderr.decode(errors='replace').strip()
                # AUTH_REQUIRED 是常见的（需要 LinkedIn 登录）
                if 'AUTH_REQUIRED' in stderr_text or 'login' in stderr_text.lower():
                    logger.warning("[LinkedIn] 需要登录 LinkedIn，搜索跳过")
                else:
                    logger.error(f"[LinkedIn] 搜索失败: {stderr_text[:200]}")
                return []

            output = stdout.decode('utf-8', errors='replace').strip()

            try:
                jobs_data = json.loads(output) if output else []
            except json.JSONDecodeError as e:
                logger.warning(f"[LinkedIn] JSON解析失败: {e}")
                return []

            if not isinstance(jobs_data, list):
                jobs_data = []

            # 解析并返回统一格式
            jobs = []
            for raw in jobs_data:
                job = self.parse_job(raw)
                jobs.append(job)

            logger.info(f"[LinkedIn] 搜索完成: {len(jobs)} 个职位")
            self._last_jobs_count = len(jobs)
            return jobs

        except asyncio.TimeoutError:
            logger.error("[LinkedIn] 搜索超时（40s）")
            return []
        except Exception as e:
            logger.error(f"[LinkedIn] 搜索异常: {e}")
            return []

    def parse_job(self, raw_data: Dict) -> Dict:
        """
        解析 LinkedIn 原始数据为统一格式
        """
        if not raw_data:
            return self.normalize_job({})

        # LinkedIn 返回字段
        job_id = str(raw_data.get('jobId', raw_data.get('id', '')))
        title = raw_data.get('title', '')
        company = raw_data.get('companyName', raw_data.get('company', ''))
        city_name = raw_data.get('location', '')
        salary_text = raw_data.get('salary', raw_data.get('salaryRange', ''))

        # 解析薪资
        salary_info = self._parse_salary(salary_text)

        # 工作经验级别
        experience_level = raw_data.get('experienceLevel', '')

        # 职位类型
        job_type = raw_data.get('jobType', '')

        # 技能标签
        skills = raw_data.get('skills', [])
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(',') if s.strip()]
        elif not isinstance(skills, list):
            skills = []

        # 描述/亮点
        description = raw_data.get('description', raw_data.get('snippet', ''))
        highlights = [description[:200].strip()] if description else []

        # URL
        url = raw_data.get('url', raw_data.get('link', ''))
        if not url and job_id:
            url = f"https://www.linkedin.com/jobs/view/{job_id}"

        # 发布时间
        posted_time = raw_data.get('postedTime', raw_data.get('date', ''))

        return self.normalize_job({
            'job_id': job_id,
            'title': title,
            'company': company,
            'city': city_name,
            'salary': salary_text,
            'experience': experience_level,
            'degree': '',  # LinkedIn 通常不返回学历
            'tags': skills,
            'highlights': highlights,
            'url': url,
            'published_at': posted_time,
            'raw_data': {
                **raw_data,
                'job_type': job_type,
                'experience_level': experience_level,
            },
        })

    def _parse_salary(self, salary_text: str) -> Dict[str, Any]:
        """解析薪资文本（LinkedIn 通常返回范围如 "$80K - $120K"）"""
        import re

        if not salary_text:
            return {'min': 0, 'max': 0, 'raw': ''}

        # 匹配 $80K - $120K 或 $80,000 - $120,000
        match = re.search(r'\$?([\d,]+)K?\s*[-–]\s*\$?([\d,]+)K?', salary_text)
        if match:
            min_k = int(match.group(1).replace(',', ''))
            max_k = int(match.group(2).replace(',', ''))
            # 如果数字 > 1000，认为是美元数字，转为K
            if min_k > 1000:
                min_k = min_k // 1000
            if max_k > 1000:
                max_k = max_k // 1000
            return {
                'min': min_k,
                'max': max_k,
                'raw': salary_text
            }

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
        print("=== LinkedIn 搜索测试 ===")
        searcher = LinkedInSearcher()
        print(f"平台名称: {searcher.platform_name}")
        print(f"是否可用: {searcher.is_available()}")
        print()

        print("执行搜索: Python Engineer, Shanghai...")
        jobs = await searcher.search(
            keywords=['Python', 'Engineer'],
            city='Shanghai',
            page_size=5
        )

        print(f"结果: {len(jobs)} 个职位")
        print()

        for i, job in enumerate(jobs[:5], 1):
            print(f"{i}. {job['title']} @ {job['company']}")
            print(f"   城市: {job['city']} | 薪资: {job['salary']}")
            print()

        return jobs

    asyncio.run(test())