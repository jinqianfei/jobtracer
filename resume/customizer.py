# resume/customizer.py
# 定制简历生成器 - 针对目标JD定制简历内容

import json
import logging
import shutil
from pathlib import Path
from typing import Dict, Optional, List
from copy import deepcopy

DEFAULT_RESUME_PATH = Path("~/.jobtracer/resume/resume.json").expanduser()
DEFAULT_CUSTOMIZED_DIR = Path("~/.jobtracer/resume/customized").expanduser()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('jobtracer.resume.customizer')


class ResumeCustomizer:
    """
    针对目标JD定制简历内容。

    核心功能：
    - 重排项目顺序（匹配度高的靠前）
    - 强调相关技能（matching_skills 靠前）
    - 弱化无关内容

    使用方式：
        customizer = ResumeCustomizer()
        customized = await customizer.customize_for_jd(job, match_result)
        customizer.save_customized(customized, job_id)
    """

    def __init__(self, base_resume: dict = None):
        """
        初始化定制器。

        Args:
            base_resume: 从 resume.json 读取的原始简历（None 时自动加载）
        """
        self.base_resume = base_resume or self._load_base_resume()

    def _load_base_resume(self) -> Optional[dict]:
        """从默认路径加载原始简历"""
        if not DEFAULT_RESUME_PATH.exists():
            return None
        try:
            return json.loads(DEFAULT_RESUME_PATH.read_text(encoding='utf-8'))
        except Exception as e:
            logger.warning(f"加载原始简历失败: {e}")
            return None

    # ── 核心定制逻辑 ──────────────────────────────────────────

    async def customize_for_jd(
        self,
        job: dict,
        match_result: dict = None
    ) -> dict:
        """
        针对JD定制简历。

        定制逻辑：
        1. 复制原始简历（不修改原始数据）
        2. 重排项目顺序（related_projects 顺序）
        3. 技能排序（matching_skills 靠前，missing_skills 可弱化）
        4. 项目描述增强（增加与JD相关的关键词）

        Args:
            job: 职位数据（包含 title, description, skills 等）
            match_result: JD匹配结果（来自 JDMatcher.match）
                           包含: matching_skills, missing_skills, related_projects

        Returns:
            dict: 定制后的 resume dict
        """
        if self.base_resume is None:
            raise ValueError("未找到原始简历数据，请先生成简历或传入 base_resume")

        # 深拷贝，确保不修改原始数据
        customized = deepcopy(self.base_resume)

        # 如果没有 match_result，跳过定制（返回原始副本）
        if not match_result:
            logger.warning("未提供 match_result，返回原始简历副本（未定制）")
            customized['_customized'] = False
            return customized

        # 1. 定制项目顺序
        customized = self._reorder_projects(customized, match_result)

        # 2. 定制技能顺序
        customized = self._reorder_skills(customized, match_result)

        # 3. 优化项目描述（增加JD相关关键词）
        customized = self._enhance_project_descriptions(customized, job, match_result)

        # 4. 标记定制元信息
        customized['_customized'] = True
        customized['_customization'] = {
            'job_id': job.get('id') or job.get('job_id') or job.get('title', 'unknown'),
            'job_title': job.get('title', ''),
            'match_score': match_result.get('total_score', 0),
            'matching_skills_count': len(match_result.get('matching_skills', [])),
            'missing_skills_count': len(match_result.get('missing_skills', [])),
        }

        logger.info(
            f"简历定制完成: {job.get('title', 'unknown')} "
            f"(匹配分: {match_result.get('total_score', 0):.1f})"
        )
        return customized

    def _reorder_projects(self, resume: dict, match_result: dict) -> dict:
        """
        重排项目顺序。

        逻辑：
        - related_projects 中的项目按 match_score 降序排列
        - 不在 related_projects 中的项目放在后面
        """
        related = match_result.get('related_projects', [])
        original_projects = resume.get('projects', [])

        if not related:
            return resume  # 无关联项目，不重排

        # 建立 project name -> related project 映射
        related_map = {p['name']: p for p in related}

        reordered = []
        remaining = []

        # 先按 related_projects 顺序添加
        for proj in original_projects:
            if proj.get('name') in related_map:
                # 更新 match_score 信息
                enhanced_proj = dict(proj)
                related_info = related_map[proj['name']]
                enhanced_proj['_match_score'] = related_info.get('match_score', 0)
                enhanced_proj['_skill_overlap'] = related_info.get('skill_overlap', 0)
                enhanced_proj['_domain_overlap'] = related_info.get('domain_overlap', 0)
                reordered.append(enhanced_proj)
            else:
                remaining.append(proj)

        # 合并：关联项目在前，非关联项目在后
        resume['projects'] = reordered + remaining
        return resume

    def _reorder_skills(self, resume: dict, match_result: dict) -> dict:
        """
        重排技能顺序。

        逻辑：
        - matching_skills 放在前面
        - 非匹配但相关的技能保持原位
        - missing_skills 不移除（用户可能有，只是未明确标注）
        """
        matching = set(match_result.get('matching_skills', []))
        missing = set(match_result.get('missing_skills', []))

        skills = resume.get('skills', [])
        if isinstance(skills, dict):
            # skills 可能是 dict 格式 {'technical': [...], 'soft': [...]}
            tech = skills.get('technical', [])
            if isinstance(tech, list):
                tech_sorted = self._sort_skill_list(tech, matching, missing)
                skills['technical'] = tech_sorted
            resume['skills'] = skills
        elif isinstance(skills, list):
            resume['skills'] = self._sort_skill_list(skills, matching, missing)

        return resume

    def _sort_skill_list(self, skills: List[str], matching: set, missing: set) -> List[str]:
        """对技能列表排序：匹配技能靠前"""
        matched = []
        others = []
        for s in skills:
            s_lower = s.lower()
            if s_lower in matching or any(m.lower() in s_lower for m in matching):
                matched.append(s)
            else:
                others.append(s)
        return matched + others

    def _enhance_project_descriptions(
        self,
        resume: dict,
        job: dict,
        match_result: dict
    ) -> dict:
        """
        优化项目描述。

        逻辑：
        - 提取 JD 中的关键技能/领域词
        - 在项目描述中自然融入这些关键词（不改变原意）
        """
        job_skills = self._extract_job_keywords(job)
        related_projects = {p['name']: p for p in match_result.get('related_projects', [])}

        for proj in resume.get('projects', []):
            if proj.get('name') not in related_projects:
                continue

            desc = proj.get('description', '')
            tech_stack = proj.get('tech_stack', [])

            # 将 JD 技能词融入 tech_stack（去重）
            existing_tech = set(t.lower() for t in tech_stack)
            new_tech = [s for s in job_skills if s.lower() not in existing_tech]
            if new_tech:
                proj['tech_stack'] = tech_stack + new_tech[:3]  # 最多加3个

        return resume

    def _extract_job_keywords(self, job: dict) -> List[str]:
        """从JD中提取关键技能词"""
        keywords = set()

        # 从 skills 和 tags
        for field in ('skills', 'tags'):
            for kw in job.get(field, []):
                keywords.add(kw)

        # 从 description 和 title
        text = job.get('title', '') + ' ' + job.get('description', '')
        import re
        words = re.findall(r'[A-Za-z#+]+', text)
        keywords.update([w for w in words if len(w) >= 2])

        return list(keywords)

    # ── 保存 / 读取 ──────────────────────────────────────────

    def save_customized(self, customized: dict, job_id: str) -> str:
        """
        保存定制简历到 resume/customized/{job_id}.json

        Args:
            customized: 定制后的 resume dict
            job_id: 职位ID（用于文件名）

        Returns:
            str: 文件路径
        """
        DEFAULT_CUSTOMIZED_DIR.mkdir(parents=True, exist_ok=True)

        # 清理 job_id 作为文件名（移除特殊字符）
        safe_job_id = self._sanitize_filename(job_id)
        file_path = DEFAULT_CUSTOMIZED_DIR / f"{safe_job_id}.json"

        try:
            file_path.write_text(
                json.dumps(customized, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
            logger.info(f"定制简历已保存: {file_path}")
            return str(file_path)
        except Exception as e:
            logger.error(f"保存定制简历失败: {e}")
            raise

    def load_customized(self, job_id: str) -> Optional[dict]:
        """
        读取定制简历。

        Args:
            job_id: 职位ID

        Returns:
            dict: 定制简历数据，不存在则返回 None
        """
        safe_job_id = self._sanitize_filename(job_id)
        file_path = DEFAULT_CUSTOMIZED_DIR / f"{safe_job_id}.json"

        if not file_path.exists():
            return None

        try:
            return json.loads(file_path.read_text(encoding='utf-8'))
        except Exception as e:
            logger.error(f"读取定制简历失败: {e}")
            return None

    def _sanitize_filename(self, name: str) -> str:
        """将字符串转为安全的文件名"""
        import re
        # 移除非字母数字下划线短横线的字符
        safe = re.sub(r'[^\w\-]', '_', str(name))
        # 限制长度
        return safe[:100] if safe else 'unknown'

    # ── 便捷工厂方法 ────────────────────────────────────────

    @classmethod
    async def from_resume_file(
        cls,
        resume_path: str = None,
        job: dict = None,
        match_result: dict = None
    ) -> dict:
        """
        从简历文件创建定制简历（便捷方法）。

        Args:
            resume_path: 简历文件路径
            job: 目标职位
            match_result: 匹配结果

        Returns:
            dict: 定制后的简历
        """
        path = Path(resume_path or str(DEFAULT_RESUME_PATH)).expanduser()
        base_resume = None
        if path.exists():
            try:
                base_resume = json.loads(path.read_text(encoding='utf-8'))
            except Exception:
                pass

        customizer = cls(base_resume=base_resume)
        if job:
            return await customizer.customize_for_jd(job, match_result)
        return base_resume


# ── 测试代码 ────────────────────────────────────────────────

if __name__ == '__main__':
    import asyncio

    print("=" * 60)
    print("定制简历生成器测试")
    print("=" * 60)

    async def test():
        # 构造模拟简历数据
        mock_resume = {
            "name": "张三",
            "contact": {"phone": "13800138000", "email": "zhangsan@example.com", "location": "北京"},
            "skills": ["Python", "Java", "MySQL", "Redis", "Docker", "Kubernetes", "Flask", "Django", "Vue.js"],
            "experience": [
                {"company": "A公司", "title": "高级工程师", "duration": "2020-2022", "description": "后端开发"}
            ],
            "projects": [
                {
                    "name": "电商平台重构",
                    "role": "后端开发",
                    "description": "使用 Python Django 开发的电商平台，日活10万，使用 Redis 做缓存，Docker 容器化部署",
                    "tech_stack": ["Python", "Django", "MySQL", "Redis", "Docker"]
                },
                {
                    "name": "数据采集系统",
                    "role": "全栈开发",
                    "description": "使用 Python Flask + Vue 开发的爬虫数据采集系统，采集电商数据用于分析",
                    "tech_stack": ["Python", "Flask", "Vue.js", "MySQL"]
                },
                {
                    "name": "企业内部管理系统",
                    "role": "后端开发",
                    "description": "使用 Java SpringBoot + MySQL 开发的企业内部ERP系统",
                    "tech_stack": ["Java", "SpringBoot", "MySQL"]
                }
            ],
            "education": [
                {"school": "北京理工大学", "degree": "本科", "major": "计算机科学", "graduation": "2018"}
            ],
            "summary": "资深后端工程师",
            "target_role": "Python高级工程师"
        }

        # 模拟 JD
        mock_job = {
            "id": "job_123",
            "title": "Python高级工程师",
            "company": "某互联网公司",
            "description": "要求：熟练掌握Python Django/Flask，有大型项目经验，精通MySQL/Redis，熟悉Docker部署",
            "skills": ["Python", "Django", "Flask", "MySQL", "Redis", "Docker"],
            "tags": ["Python", "Django", "Flask", "MySQL", "Redis", "Docker"]
        }

        # 模拟 match_result（来自 JDMatcher.match）
        mock_match_result = {
            "total_score": 85.0,
            "breakdown": {
                "skill_score": 83.3,
                "project_score": 75.0,
                "experience_score": 80.0,
                "salary_score": 100.0
            },
            "matching_skills": ["Python", "Django", "MySQL", "Redis", "Docker", "Flask"],
            "missing_skills": [],
            "related_projects": [
                {
                    "name": "电商平台重构",
                    "role": "后端开发",
                    "description": "使用 Python Django 开发的电商平台...",
                    "match_score": 35,
                    "skill_overlap": 3,
                    "domain_overlap": 1
                },
                {
                    "name": "数据采集系统",
                    "role": "全栈开发",
                    "description": "使用 Python Flask + Vue 开发的爬虫...",
                    "match_score": 25,
                    "skill_overlap": 2,
                    "domain_overlap": 1
                }
            ]
        }

        print("\n[测试] 定制简历")
        customizer = ResumeCustomizer(base_resume=mock_resume)
        customized = await customizer.customize_for_jd(mock_job, mock_match_result)

        print(f"\n✅ 定制完成:")
        print(f"   定制标识: {customized.get('_customized')}")
        print(f"   关联职位: {customized['_customization']['job_title']}")
        print(f"   匹配分: {customized['_customization']['match_score']}")

        print(f"\n📋 项目顺序（已重排）:")
        for i, p in enumerate(customized['projects'], 1):
            match_info = ""
            if '_match_score' in p:
                match_info = f" [匹配分: {p['_match_score']}]"
            print(f"   {i}. {p['name']}{match_info}")

        print(f"\n🛠️ 技能顺序（已重排）:")
        skills = customized['skills']
        print(f"   {skills}")

        print("\n💾 保存定制简历...")
        file_path = customizer.save_customized(customized, mock_job['id'])
        print(f"   保存路径: {file_path}")

        print("\n📖 读取定制简历...")
        loaded = customizer.load_customized(mock_job['id'])
        print(f"   读取成功: {loaded is not None}")
        print(f"   姓名: {loaded['name']}")

        return customized

    result = asyncio.run(test())

    print("\n" + "=" * 60)
    print("定制简历生成器测试完成")
    print("=" * 60)