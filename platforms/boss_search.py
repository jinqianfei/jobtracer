"""
platforms/boss_search.py
Boss直聘平台搜索器
继承 PlatformSearcher 基类，封装 boss/search.py 的现有逻辑
"""
import logging
from typing import List, Dict, Any

from .base import PlatformSearcher

logger = logging.getLogger('jobtracer.platforms.boss_search')


class BossPlatformSearcher(PlatformSearcher):
    """
    Boss直聘平台搜索器
    封装 boss/search.py 的 BOSSSearcher，适配 PlatformSearcher 接口
    """

    platform_name: str = "boss"
    base_url: str = "https://www.zhipin.com"

    def __init__(self, timeout: int = 30):
        super().__init__(timeout=timeout)
        self._init_boss_searcher()

    def _init_boss_searcher(self) -> None:
        """延迟初始化 BOSSSearcher"""
        try:
            from boss.search import BOSSSearcher
            self._searcher = BOSSSearcher()
            logger.info("[BossPlatformSearcher] BOSSSearcher 初始化成功")
        except ImportError as e:
            logger.error(f"[BossPlatformSearcher] 无法导入 BOSSSearcher: {e}")
            self._searcher = None
            self.mark_unavailable(f"导入失败: {e}")

    async def search(
        self,
        keywords: List[str],
        city: str = "全国",
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        搜索 Boss 直聘职位

        Args:
            keywords: 搜索关键词列表
            city: 工作城市
            **kwargs: 其他参数（experience, degree, salary, page, page_size）

        Returns:
            List[dict]: 职位列表（统一格式）
        """
        if self._searcher is None:
            logger.error("[BossPlatformSearcher] BOSSSearcher 未初始化")
            return []

        # 获取搜索参数
        page = kwargs.get('page', 1)
        page_size = kwargs.get('page_size', 20)
        experience = kwargs.get('experience', '不限')
        degree = kwargs.get('degree', '不限')
        salary = kwargs.get('salary', '不限')

        try:
            # 调用 Boss 搜索（同步转异步）
            result = await self._searcher.search_jobs(
                keywords=keywords,
                city=city,
                experience=experience,
                degree=degree,
                salary=salary,
                page=page,
                page_size=page_size
            )

            if not result.get('success', False):
                jobs_data = result.get('jobs', [])
            else:
                jobs_data = result.get('jobs', [])

            # 解析并返回统一格式
            jobs = []
            for job_raw in jobs_data:
                job = self.parse_job(job_raw)
                jobs.append(job)

            # 记录最近搜索的职位数
            self._last_jobs_count = len(jobs)

            logger.info(f"[BossPlatformSearcher] 搜索完成: {len(jobs)} 个职位")
            return jobs

        except Exception as e:
            logger.error(f"[BossPlatformSearcher] 搜索异常: {e}")
            self.mark_unavailable(str(e))
            return []

    def parse_job(self, raw_data: Dict) -> Dict:
        """
        解析 Boss 原始数据为统一格式

        Args:
            raw_data: Boss API 返回的原始职位数据

        Returns:
            dict: 统一格式的职位数据
        """
        if not raw_data:
            return self.normalize_job({})

        # 从 raw_data 提取字段（BOSS 返回格式可能不同，需要适配）
        job_id = raw_data.get('job_id') or raw_data.get('security_id', '')
        title = raw_data.get('title') or raw_data.get('position', '') or raw_data.get('job_name', '')
        company = raw_data.get('company', '')
        city_name = raw_data.get('city', raw_data.get('location', ''))
        salary_text = raw_data.get('salary', '')

        # 解析薪资
        salary_info = self._parse_salary(salary_text)

        # 处理标签
        tags = []
        if 'tags' in raw_data and isinstance(raw_data['tags'], list):
            tags = raw_data['tags']
        elif 'skill' in raw_data:
            skill = raw_data['skill']
            if isinstance(skill, str):
                tags = [s.strip() for s in skill.split(',') if s.strip()]
            elif isinstance(skill, list):
                tags = skill

        # 处理亮点
        highlights = raw_data.get('highlights', [])
        if not highlights and 'description' in raw_data:
            # 从 JD 中提取亮点（简单处理）
            desc = raw_data.get('description', '')
            if desc:
                # 取前100字符作为亮点
                highlights = [desc[:100].strip()]

        # URL
        url = raw_data.get('url', '')
        if not url and job_id:
            url = f"https://www.zhipin.com/job_detail/{job_id}.html"

        # 发布时间
        published_at = raw_data.get('published_at', raw_data.get('update_time', ''))

        # 经验/学历
        experience = raw_data.get('experience', '')
        degree = raw_data.get('degree', '')

        return self.normalize_job({
            'job_id': str(job_id),
            'title': title,
            'company': company,
            'city': city_name,
            'salary': salary_text,
            'experience': experience,
            'degree': degree,
            'tags': tags,
            'highlights': highlights if isinstance(highlights, list) else [],
            'url': url,
            'published_at': published_at,
            'raw_data': raw_data,
        })

    def _parse_salary(self, salary_text: str) -> Dict[str, Any]:
        """
        重写薪资解析，支持 Boss 特殊格式

        Args:
            salary_text: 薪资文本，如 "20-40K" 或 "20-40k"

        Returns:
            dict: 包含 min, max, raw 的字典
        """
        import re

        if not salary_text:
            return {'min': 0, 'max': 0, 'raw': ''}

        # Boss 常见格式：15-25K · 13薪
        # 去掉薪资格式
        clean = re.sub(r'\s*·.*', '', salary_text)

        # 匹配 X-YK / X-YK
        match = re.search(r'(\d+)-(\d+)(K|k)', clean)
        if match:
            return {
                'min': int(match.group(1)),
                'max': int(match.group(2)),
                'raw': salary_text
            }

        # 匹配 X-Y万
        match = re.search(r'(\d+)-(\d+)万', clean)
        if match:
            return {
                'min': int(float(match.group(1)) * 10),
                'max': int(float(match.group(2)) * 10),
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
        print("=== Boss 直聘平台搜索器测试 ===")

        searcher = BossPlatformSearcher()
        print(f"平台名称: {searcher.platform_name}")
        print(f"是否可用: {searcher.is_available()}")
        print()

        # 测试搜索
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
            print(f"   URL: {job['url'][:60]}...")
            print()

        return jobs

    asyncio.run(test())