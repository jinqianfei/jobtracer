# matching/scorer.py
# JD匹配评分模块 - 多维度匹配度评分

import re
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('jobtracer.matching.scorer')


class JDMatcher:
    """
    JD匹配评分器
    对每个职位进行多维度匹配度评分
    """

    # 评分权重配置
    DEFAULT_WEIGHTS = {
        "skill": 0.4,       # 技能匹配
        "project": 0.2,     # 项目匹配
        "experience": 0.2,   # 经验匹配
        "salary": 0.2       # 薪资匹配
    }

    def __init__(self, weights: Dict[str, float] = None, llm_client=None):
        """
        初始化JD匹配器

        Args:
            weights: 权重配置，默认为 DEFAULT_WEIGHTS
            llm_client: LLM客户端（可选，用于语义评分）
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self.llm = llm_client

        # 常用技能关键词（用于提取）
        self.tech_keywords = {
            'python', 'java', 'javascript', 'typescript', 'go', 'rust', 'c++', 'c#',
            'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
            'react', 'vue', 'angular', 'nodejs', 'django', 'flask', 'fastapi',
            'docker', 'kubernetes', 'aws', 'gcp', 'azure', 'linux', 'git',
            'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'nlp',
            'html', 'css', 'sass', 'webpack', 'nginx', 'kafka', 'rabbitmq',
            'spring', 'springboot', 'mybatis', 'hadoop', 'spark', 'flink',
            'pandas', 'numpy', 'scipy', 'sklearn', 'keras', 'opencv', 'pillow',
            'restful', 'graphql', 'grpc', 'websocket', 'microservices', 'devops',
            'ci/cd', 'agile', 'scrum', 'api', 'json', 'xml', 'yaml', 'tomcat',
            'git', 'svn', 'jira', 'confluence', 'slack', 'tableau', 'powerbi',
            'etl', 'data pipeline', 'airflow', 'luigi', 'dbt', 'snowflake', 'bigquery'
        }

    async def match(self, job: dict, resume: dict) -> dict:
        """
        对单个JD进行匹配评分

        Args:
            job: 职位数据，包含 title, skills, experience, salary 等
            resume: 简历数据，包含 skills, projects, experience 等

        Returns:
            dict: 匹配结果，包含:
                - total_score: 总分 (0-100)
                - breakdown: 各维度分数
                - matching_skills: 匹配的技能列表
                - missing_skills: 缺失的技能列表
                - related_projects: 关联项目列表
        """
        # 计算各维度分数
        skill_score, skill_details = self._calculate_skill_score(job, resume)
        project_score, project_details = self._calculate_project_score(job, resume)
        experience_score, experience_details = self._calculate_experience_score(job, resume)
        salary_score, salary_details = self._calculate_salary_score(job, resume)

        # 加权计算总分
        total_score = (
            skill_score * self.weights['skill'] +
            project_score * self.weights['project'] +
            experience_score * self.weights['experience'] +
            salary_score * self.weights['salary']
        )

        # 查找关联项目
        related_projects = self._find_related_projects(job, resume)

        # 提取匹配和缺失技能
        job_skills = self._extract_skills(job)
        resume_skills = self._extract_resume_skills(resume)
        matching_skills = list(resume_skills & job_skills)
        missing_skills = list(job_skills - resume_skills)

        result = {
            'total_score': round(total_score, 1),
            'breakdown': {
                'skill_score': round(skill_score, 1),
                'project_score': round(project_score, 1),
                'experience_score': round(experience_score, 1),
                'salary_score': round(salary_score, 1)
            },
            'matching_skills': matching_skills,
            'missing_skills': missing_skills,
            'related_projects': related_projects,
            'details': {
                'skill': skill_details,
                'project': project_details,
                'experience': experience_details,
                'salary': salary_details
            }
        }

        logger.info(f"JD匹配评分完成: {job.get('title', 'unknown')} - 总分: {total_score:.1f}")
        return result

    async def batch_match(
        self,
        jobs: List[dict],
        resume: dict
    ) -> List[dict]:
        """
        批量评分，返回按分数排序的职位列表

        Args:
            jobs: 职位列表
            resume: 简历数据

        Returns:
            List[dict]: 按分数降序排列的职位列表，每项包含原始job数据+match_result
        """
        results = []

        for job in jobs:
            try:
                match_result = await self.match(job, resume)
                results.append({
                    'job': job,
                    'match': match_result
                })
            except Exception as e:
                logger.error(f"评分失败 {job.get('title', 'unknown')}: {e}")
                results.append({
                    'job': job,
                    'match': {
                        'total_score': 0,
                        'error': str(e)
                    }
                })

        # 按总分降序排序
        results.sort(key=lambda x: x['match'].get('total_score', 0), reverse=True)

        logger.info(f"批量评分完成: {len(results)} 个职位")
        return results

    def _calculate_skill_score(self, job: dict, resume: dict) -> Tuple[float, dict]:
        """
        计算技能匹配分 (40%)

        逻辑：
        - 提取JD中的技能关键词
        - 与resume.skills交集计算比例
        - 匹配度 = 交集数量 / JD技能总数
        """
        job_skills = self._extract_skills(job)
        resume_skills = self._extract_resume_skills(resume)

        if not job_skills:
            return 50.0, {'reason': 'JD无技能要求', 'matched': [], 'required': []}

        matched = job_skills & resume_skills
        score = (len(matched) / len(job_skills)) * 100

        details = {
            'matched': list(matched),
            'required': list(job_skills),
            'resume_has': list(resume_skills),
            'match_rate': len(matched) / len(job_skills) if job_skills else 0
        }

        return round(score, 1), details

    def _calculate_project_score(self, job: dict, resume: dict) -> Tuple[float, dict]:
        """
        计算项目匹配分 (20%)

        逻辑：
        - 提取JD中的领域关键词（电商/金融/物流 等）
        - 与resume.projects的描述匹配
        - 匹配项目数量作为分数
        """
        job_domain = self._extract_job_domain(job)
        resume_projects = resume.get('projects', [])

        if not resume_projects:
            return 30.0, {'reason': '简历无项目经验', 'matched_projects': []}

        matched_projects = []
        for proj in resume_projects:
            proj_text = (proj.get('description', '') + ' ' + proj.get('name', '')).lower()
            proj_words = set(re.findall(r'[\u4e00-\u9fa5a-zA-Z]{2,}', proj_text))

            overlap = proj_words & job_domain
            if overlap:
                matched_projects.append({
                    'name': proj.get('name', ''),
                    'overlap': list(overlap),
                    'match_count': len(overlap)
                })

        # 评分：每匹配一个项目得25分，最高100分
        score = min(len(matched_projects) * 25, 100)

        details = {
            'matched_projects': [p['name'] for p in matched_projects],
            'job_domain': list(job_domain),
            'matched_count': len(matched_projects)
        }

        return round(score, 1), details

    def _extract_project_keywords(self, resume: dict) -> set:
        """
        从简历项目中提取关键词
        """
        keywords = set()
        for proj in resume.get('projects', []):
            text = proj.get('description', '') + ' ' + proj.get('name', '')
            words = re.findall(r'[\u4e00-\u9fa5a-zA-Z]{2,}', text)
            keywords.update([w.lower() for w in words if len(w) > 1])
        return keywords

    def _extract_job_domain(self, job: dict) -> set:
        """
        从职位信息中提取领域关键词
        """
        text = (
            job.get('title', '') + ' ' +
            job.get('jd_summary', '') + ' ' +
            job.get('description', '') + ' ' +
            ' '.join(job.get('skills', [])) + ' ' +
            ' '.join(job.get('tags', []))
        )
        words = re.findall(r'[\u4e00-\u9fa5a-zA-Z]{2,}', text)
        return set([w.lower() for w in words if len(w) > 1])

    def _calculate_experience_score(self, job: dict, resume: dict) -> Tuple[float, dict]:
        """
        计算经验匹配分 (20%)

        逻辑：
        - JD要求年限 vs 用户工作年限
        - 完全匹配=100分，适当放宽/严格=递减
        """
        exp_text = job.get('experience', job.get('experience_required', ''))

        # 经验要求映射
        exp_map_cn = {
            '在校生': 0, '应届生': 0, '经验不限': 0,
            '1年以内': 1, '1-3年': 2, '3-5年': 4, '5-10年': 7, '10年以上': 10,
            '1-3年': 2, '3-5年': 4, '5-10年': 7
        }

        exp_map_en = {
            'student': 0, 'fresh': 0, 'any': 0, '不限': 0,
            'less_than_1': 1, '1-3': 2, '3-5': 4, '5-10': 7, 'above_10': 10
        }

        required_years = exp_map_cn.get(exp_text) or exp_map_en.get(exp_text.lower(), None)

        if required_years is None:
            return 60.0, {'reason': '无法解析经验要求', 'required': exp_text, 'resume_years': 0}

        resume_years = self._estimate_resume_years(resume)

        if resume_years >= required_years:
            score = 100.0
        else:
            score = (resume_years / required_years) * 100 if required_years > 0 else 100.0

        details = {
            'required': exp_text,
            'required_years': required_years,
            'resume_years': resume_years,
            'fit_ratio': resume_years / required_years if required_years > 0 else 1.0
        }

        return round(score, 1), details

    def _estimate_resume_years(self, resume: dict) -> int:
        """
        估算简历工作年限
        基于工作经验数量和项目数量
        """
        exp_years = len(resume.get('experience', [])) * 2
        proj_years = len(resume.get('projects', [])) * 0.5
        return int(min(exp_years + proj_years, 15))  # 最多15年

    def _calculate_salary_score(self, job: dict, resume: dict) -> Tuple[float, dict]:
        """
        计算薪资匹配分 (20%)

        逻辑：
        - JD薪资范围 vs 用户期望薪资
        - 在范围内=100分，过高/过低=递减
        """
        job_salary = job.get('salary', {})
        pref_salary = resume.get('preferences', {}).get('expected_salary', {})
        resume_salary = resume.get('expected_salary', {})

        # 尝试多种薪资字段
        if isinstance(job_salary, str):
            job_salary = self._parse_salary_text(job_salary)

        if not job_salary.get('min') and not job_salary.get('max'):
            # 尝试从 raw 文本解析
            salary_raw = job.get('salary', '')
            if salary_raw:
                job_salary = self._parse_salary_text(salary_raw)

        job_min = job_salary.get('min', 0)
        job_max = job_salary.get('max', 0)

        # 获取用户期望薪资
        user_min = (
            pref_salary.get('min') or
            resume_salary.get('min') or
            resume.get('expected_salary_min', 0)
        )
        user_max = (
            pref_salary.get('max') or
            resume_salary.get('max') or
            resume.get('expected_salary_max', 0)
        )

        if not job_min or not job_max:
            return 60.0, {'reason': '薪资范围不明确', 'job_salary': job_salary}

        # 完全匹配：用户期望在JD薪资范围内
        if user_min and user_max:
            if user_min >= job_min and user_max <= job_max:
                score = 100.0
            elif user_min > job_max:
                # 期望过高
                ratio = job_max / user_min
                score = max(0, ratio * 80)
            elif user_max < job_min:
                # 期望过低（可能被认为资质不够）
                ratio = user_max / job_min
                score = max(20, ratio * 60)
            else:
                # 部分重叠
                overlap_min = max(user_min, job_min)
                overlap_max = min(user_max, job_max)
                overlap_ratio = (overlap_max - overlap_min) / (job_max - job_min) if job_max > job_min else 0.5
                score = 60 + overlap_ratio * 40
        else:
            # 无期望薪资信息
            score = 65.0

        details = {
            'job_salary_range': f"{job_min}-{job_max}",
            'user_salary_range': f"{user_min}-{user_max}" if user_min else "未设置",
            'score_reason': '匹配' if score >= 80 else '部分匹配' if score >= 50 else '偏差较大'
        }

        return round(score, 1), details

    def _parse_salary_text(self, salary_text: str) -> dict:
        """
        解析薪资文本

        Args:
            salary_text: 薪资文本，如 "15-25K" 或 "1-2万"

        Returns:
            dict: 包含 min, max 的字典
        """
        if not salary_text or salary_text in ('面议', '薪资面议'):
            return {'min': 0, 'max': 0}

        # 匹配 K 或万
        match = re.search(r'(\d+)-(\d+)(K|k|万|w|W)', salary_text)
        if match:
            min_sal, max_sal, unit = match.groups()
            multiplier = 1000 if unit.upper() in ('K',) else 10000
            return {
                'min': int(min_sal) * multiplier,
                'max': int(max_sal) * multiplier
            }

        # 匹配只有数字的情况
        match2 = re.search(r'(\d+)-(\d+)', salary_text)
        if match2:
            return {
                'min': int(match2.group(1)),
                'max': int(match2.group(2))
            }

        return {'min': 0, 'max': 0}

    def _find_related_projects(self, job: dict, resume: dict) -> List[dict]:
        """
        查找与JD相关的项目

        Args:
            job: 职位数据
            resume: 简历数据

        Returns:
            List[dict]: 关联项目列表（最多3个）
        """
        job_skills = self._extract_skills(job)
        job_domain = self._extract_job_domain(job)
        resume_projects = resume.get('projects', [])

        if not resume_projects:
            return []

        scored_projects = []
        for proj in resume_projects:
            proj_text = (proj.get('description', '') + ' ' + proj.get('name', '')).lower()
            proj_words = set(re.findall(r'[\u4e00-\u9fa5a-zA-Z]{2,}', proj_text))

            skill_overlap = len(proj_words & job_skills)
            domain_overlap = len(proj_words & job_domain)

            # 计算匹配分数：技能重叠*10 + 领域重叠*5
            match_score = skill_overlap * 10 + domain_overlap * 5

            if skill_overlap >= 1 or domain_overlap >= 2:
                scored_projects.append({
                    'name': proj.get('name', ''),
                    'role': proj.get('role', proj.get('position', '')),
                    'description': proj.get('description', '')[:100],
                    'match_score': match_score,
                    'skill_overlap': skill_overlap,
                    'domain_overlap': domain_overlap
                })

        # 按分数降序排列
        scored_projects.sort(key=lambda x: x['match_score'], reverse=True)

        # 返回最多3个项目
        return scored_projects[:3]

    def _extract_skills(self, job: dict) -> set:
        """
        从职位信息中提取技能关键词

        Args:
            job: 职位数据

        Returns:
            set: 技能关键词集合
        """
        skills = set()

        # 从 tags 字段提取
        if job.get('tags'):
            for tag in job['tags']:
                tag_lower = tag.lower()
                if tag_lower in self.tech_keywords:
                    skills.add(tag_lower)

        # 从 skills 字段提取
        if job.get('skills'):
            for skill in job['skills']:
                skill_lower = skill.lower()
                if skill_lower in self.tech_keywords:
                    skills.add(skill_lower)
                # 处理复合技能名
                for kw in self.tech_keywords:
                    if kw in skill_lower:
                        skills.add(kw)

        # 从 title 和 description 提取
        text = job.get('title', '') + ' ' + job.get('description', '') + ' ' + job.get('jd_summary', '')
        text_lower = text.lower()
        for kw in self.tech_keywords:
            if kw in text_lower:
                skills.add(kw)

        return skills

    def _extract_resume_skills(self, resume: dict) -> set:
        """
        从简历中提取技能

        Args:
            resume: 简历数据

        Returns:
            set: 技能关键词集合
        """
        skills = set()

        # resume.skills 可以是 list 或 dict，兼容处理
        raw_skills = resume.get('skills', [])
        if isinstance(raw_skills, list):
            tech_skills = raw_skills
        elif isinstance(raw_skills, dict):
            tech_skills = raw_skills.get('technical', [])
        else:
            tech_skills = []

        if isinstance(tech_skills, list):
            for skill in tech_skills:
                skill_lower = skill.lower()
                if skill_lower in self.tech_keywords:
                    skills.add(skill_lower)
                for kw in self.tech_keywords:
                    if kw in skill_lower:
                        skills.add(kw)

        # 从 projects 提取技能相关词
        for proj in resume.get('projects', []):
            text = (proj.get('description', '') + ' ' + proj.get('name', '')).lower()
            for kw in self.tech_keywords:
                if kw in text:
                    skills.add(kw)

        return skills


# 便捷函数
async def match_job(job: dict, resume: dict) -> dict:
    """
    对单个JD进行匹配评分（便捷函数）

    Args:
        job: 职位数据
        resume: 简历数据

    Returns:
        dict: 匹配结果
    """
    matcher = JDMatcher()
    return await matcher.match(job, resume)


async def batch_match_jobs(jobs: List[dict], resume: dict) -> List[dict]:
    """
    批量评分（便捷函数）

    Args:
        jobs: 职位列表
        resume: 简历数据

    Returns:
        List[dict]: 按分数降序排列的职位列表
    """
    matcher = JDMatcher()
    return await matcher.batch_match(jobs, resume)


if __name__ == '__main__':
    # 测试代码
    import asyncio

    print("=" * 60)
    print("JD匹配评分模块测试")
    print("=" * 60)

    async def test():
        matcher = JDMatcher()

        # 测试数据
        test_resume = {
            'name': '张三',
            'skills': {
                'technical': ['Python', 'Java', 'MySQL', 'Redis', 'Docker', 'Kubernetes', 'Flask', 'Django']
            },
            'projects': [
                {
                    'name': '电商平台重构',
                    'role': '后端开发',
                    'description': '使用 Python Django 开发的电商平台，日活10万，使用 Redis 做缓存，Docker 容器化部署'
                },
                {
                    'name': '数据采集系统',
                    'role': '全栈开发',
                    'description': '使用 Python Flask + Vue 开发的爬虫数据采集系统，采集电商数据用于分析'
                },
                {
                    'name': '企业内部管理系统',
                    'role': '后端开发',
                    'description': '使用 Java SpringBoot + MySQL 开发的企业内部ERP系统'
                }
            ],
            'experience': [
                {'company': 'A公司', 'title': '高级工程师', 'duration': '3年'},
                {'company': 'B公司', 'title': '中级工程师', 'duration': '2年'}
            ],
            'expected_salary': {'min': 20000, 'max': 35000}
        }

        test_job = {
            'title': 'Python高级工程师',
            'company': '某互联网公司',
            'experience': '3-5年',
            'salary': '25-40K',
            'skills': ['Python', 'Django', 'MySQL', 'Redis', 'Docker'],
            'tags': ['Python', 'Django', 'MySQL', 'Redis', 'Docker'],
            'description': '要求：熟练掌握Python Django/Flask，有大型项目经验，精通MySQL/Redis，熟悉Docker部署'
        }

        print("\n测试单个JD匹配:")
        result = await matcher.match(test_job, test_resume)

        print(f"\n匹配结果:")
        print(f"  总分: {result['total_score']}")
        print(f"  breakdown:")
        for key, val in result['breakdown'].items():
            print(f"    {key}: {val}")
        print(f"  匹配技能: {result['matching_skills']}")
        print(f"  缺失技能: {result['missing_skills']}")
        print(f"  关联项目:")
        for proj in result['related_projects']:
            print(f"    - {proj['name']} (分数: {proj['match_score']})")

        # 测试批量匹配
        print("\n\n测试批量匹配:")
        test_jobs = [
            test_job,
            {
                'title': 'Java开发工程师',
                'company': '某金融公司',
                'experience': '1-3年',
                'salary': '15-25K',
                'skills': ['Java', 'Spring', 'MySQL', 'Kafka'],
                'tags': ['Java', 'Spring', 'MySQL'],
                'description': '要求：熟练Java Spring开发，有金融项目经验'
            },
            {
                'title': 'Go后端工程师',
                'company': '某科技公司',
                'experience': '3-5年',
                'salary': '30-50K',
                'skills': ['Go', 'Kubernetes', '微服务', 'AWS'],
                'tags': ['Go', 'K8s', '微服务'],
                'description': '要求：熟练Go语言，有微服务架构经验，熟悉K8s'
            }
        ]

        batch_results = await matcher.batch_match(test_jobs, test_resume)

        print(f"\n批量匹配结果（按分数降序）:")
        for i, item in enumerate(batch_results):
            job = item['job']
            match = item['match']
            print(f"\n  {i+1}. {job['title']} @ {job['company']}")
            print(f"     总分: {match.get('total_score', 0)}")
            print(f"     匹配技能: {match.get('matching_skills', [])}")

        return result

    asyncio.run(test())

    print("\n" + "=" * 60)
    print("JD匹配评分模块测试完成")
    print("=" * 60)