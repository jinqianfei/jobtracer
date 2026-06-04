"""
platforms/zhilian_search.py
智联招聘搜索器 - 基于 requests 爬虫
"""
import logging
import json
import asyncio
import re
from typing import List, Dict, Any
from urllib.parse import urlencode
import random

import requests

from platforms.base import PlatformSearcher

logger = logging.getLogger('jobtracer.platforms.zhilian')


class ZhilianSearcher(PlatformSearcher):
    """
    智联招聘搜索器
    基于 requests 爬取智联搜索页
    """

    platform_name = "智联招聘"
    base_url = "https://www.zhaopin.com"
    search_url = "https://sou.zhaopin.com/jobs/searchresult.ashx"

    # 常用 User-Agent 池
    USER_AGENTS = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    ]

    def __init__(self, timeout: int = 15):
        super().__init__(timeout=timeout)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": "https://www.zhaopin.com/",
        })

    async def search(
        self,
        keywords: List[str],
        city: str,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        搜索智联招聘职位

        Args:
            keywords: 搜索关键词列表
            city: 工作城市
            **kwargs: page, page_size 等

        Returns:
            List[dict]: 职位列表（统一格式）
        """
        page = kwargs.get('page', 1)
        page_size = min(kwargs.get('page_size', 20), 50)

        query = ' '.join(keywords[:2])

        jobs = []
        try:
            # 使用 asyncio.to_thread 避免阻塞事件循环
            raw_jobs = await asyncio.to_thread(
                self._fetch_jobs, query, city, page, page_size
            )
            for raw in raw_jobs:
                job = self.parse_job(raw)
                if job.get('job_id'):
                    jobs.append(job)

            logger.info(f"[智联] 搜索完成: {len(jobs)} 个职位")
            self._last_jobs_count = len(jobs)
        except Exception as e:
            logger.error(f"[智联] 搜索异常: {e}")

        return jobs

    def _fetch_jobs(
        self,
        keyword: str,
        city: str,
        page: int = 1,
        page_size: int = 20
    ) -> List[Dict[str, Any]]:
        """
        通过 requests 爬取智联搜索结果

        Args:
            keyword: 搜索关键词
            city: 工作城市
            page: 页码
            page_size: 每页数量

        Returns:
            List[dict]: 原始职位数据列表
        """
        # 城市映射（简化的几个城市）
        city_map = {
            "上海": 755, "北京": 763, "深圳": 765, "广州": 773,
            "杭州": 754, "南京": 753, "成都": 736, "武汉": 735,
            "西安": 854, "苏州": 765, "重庆": 744, "天津": 741,
            "长沙": 749, "郑州": 769, "东莞": 770, "佛山": 773,
        }
        city_code = city_map.get(city, 0)

        params = {
            "jl": city if city_code else city,
            "kw": keyword,
            "p": page,
            "ps": page_size,
        }

        try:
            resp = self.session.get(
                self.search_url,
                params=params,
                timeout=self.timeout
            )
            if resp.status_code != 200:
                logger.warning(f"[智联] HTTP {resp.status_code}")
                return []

            html = resp.text
            return self._parse_html(html)

        except requests.Timeout:
            logger.error("[智联] 请求超时")
            return []
        except Exception as e:
            logger.error(f"[智联] 请求异常: {e}")
            return []

    def _parse_html(self, html: str) -> List[Dict[str, Any]]:
        """
        解析智联搜索页 HTML

        Args:
            html: 页面 HTML 文本

        Returns:
            List[dict]: 解析后的职位数据列表
        """
        jobs = []

        # 方法1: JSON-LD 脚本块（最可靠）
        json_pattern = re.compile(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            re.DOTALL
        )
        for match in json_pattern.finditer(html):
            try:
                data = json.loads(match.group(1))
                if data.get("@type") == "ItemList":
                    item_list = data.get("itemListElement", [])
                    for item in item_list:
                        if isinstance(item, dict):
                            job = item.get("item", {})
                            if job.get("@type") == "JobPosting":
                                jobs.append(self._convert_jsonld(job))
            except (json.JSONDecodeError, TypeError):
                continue

        if jobs:
            return jobs

        # 方法2: data-jobid 属性
        job_blocks = re.findall(
            r'<[^>]*\sdata-jobid=["\'](\d+)["\'][^>]*>(.*?)</[^>]+>',
            html, re.DOTALL
        )
        for job_id, block_html in job_blocks:
            job_data = self._extract_from_block(job_id, block_html)
            if job_data:
                jobs.append(job_data)

        return jobs

    def _convert_jsonld(self, job: Dict) -> Dict[str, Any]:
        """
        将 JSON-LD JobPosting 转换为统一格式
        """
        raw = {
            "jobId": job.get("identifier", {}).get("value", ""),
            "title": job.get("title", ""),
            "company": job.get("hiringOrganization", {}).get("name", ""),
            "city": job.get("jobLocation", {}).get("addressRegion", ""),
            "salary": job.get("baseSalary", {}).get("text", "") if job.get("baseSalary") else "",
            "workYear": job.get("experienceRequirements", {}).get("text", "") if job.get("experienceRequirements") else "",
            "degree": job.get("educationRequirements", {}).get("text", "") if job.get("educationRequirements") else "",
            "url": job.get("url", ""),
            "published_at": job.get("datePosted", "")[:10] if job.get("datePosted") else "",
        }
        return raw

    def _extract_from_block(self, job_id: str, block_html: str) -> Dict[str, Any]:
        """
        从 HTML 块中提取职位信息
        """
        def get_text(pattern: str) -> str:
            m = re.search(pattern, block_html, re.DOTALL)
            if not m:
                return ""
            text = m.group(1)
            # 清理 HTML 标签
            text = re.sub(r'<[^>]+>', '', text)
            return text.strip()

        title = get_text(r'class="[^"]*job_title[^"]*"[^>]*>([^<]+)')
        if not title:
            title = get_text(r'class="[^"]*zwmc[^"]*"[^>]*>([^<]+)')
        company = get_text(r'class="[^"]*gsmc[^"]*"[^>]*>([^<]+)')
        salary = get_text(r'class="[^"]*gzdd[^"]*"[^>]*>([^<]+)')
        area = get_text(r'class="[^"]*gzdd[^"]*"[^>]*>([^<]+)')

        # URL
        url_match = re.search(r'href=["\']([^"\']+)["\'][^>]*>.*?class="[^"]*job_title',
                             block_html, re.DOTALL)
        if not url_match:
            url_match = re.search(r'href=["\']([^"\']+)["\']', block_html)

        url = url_match.group(1) if url_match else f"https://jobs.zhaopin.com/{job_id}.htm"

        return {
            "jobId": job_id,
            "title": title,
            "company": company,
            "salary": salary,
            "city": area,
            "url": url,
        }

    def parse_job(self, raw_data: Dict) -> Dict[str, Any]:
        """
        解析智联原始数据为统一格式
        """
        if not raw_data:
            return self.normalize_job({})

        job_id = str(raw_data.get('jobId', raw_data.get('job_id', '')))
        title = raw_data.get('title', '')
        company = raw_data.get('company', '')
        city_text = raw_data.get('city', '')
        salary_text = raw_data.get('salary', '')
        experience = raw_data.get('workYear', '')
        degree = raw_data.get('degree', '')

        salary_info = self._parse_salary(salary_text)

        # 处理 tags
        tags_raw = raw_data.get('tags', [])
        if isinstance(tags_raw, str):
            tags = [t.strip() for t in tags_raw.split(',') if t.strip()]
        elif isinstance(tags_raw, list):
            tags = tags_raw
        else:
            tags = []

        # URL
        url = raw_data.get('url', '')
        if not url and job_id:
            url = f"https://jobs.zhaopin.com/{job_id}.htm"

        # 发布日期
        published_at = raw_data.get('published_at', '')[:10]
        if not published_at:
            issue = raw_data.get('issueDate', raw_data.get('updated', ''))
            published_at = issue[:10] if issue else ''

        return self.normalize_job({
            'job_id': job_id,
            'title': title,
            'company': company,
            'city': city_text,
            'salary': salary_info['raw'],
            'experience': experience,
            'degree': degree,
            'tags': tags,
            'highlights': [],
            'url': url,
            'published_at': published_at,
            'raw_data': raw_data,
        })


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
        print("=== 智联招聘 搜索测试 ===")
        searcher = ZhilianSearcher()
        print(f"平台名称: {searcher.platform_name}")
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