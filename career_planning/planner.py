"""职业规划核心引擎
基于用户背景 + 数字足迹 → 职业路径建议 + 学习路线图
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, TypedDict
from datetime import datetime
import json
import re


# 职业阶段定义
WORK_STAGES = {
    "entry": {"label": "初入职场", "years": (0, 2), "level": "junior"},
    "growing": {"label": "成长期", "years": (2, 5), "level": "mid"},
    "experienced": {"label": "成熟期", "years": (5, 8), "level": "senior"},
    "expert": {"label": "专家期", "years": (8, 12), "level": "expert"},
    "leadership": {"label": "管理层", "years": (12, 99), "level": "manager"},
}


# 技能分类体系
SKILL_CATEGORIES = {
    "technical": [
        "Python", "Java", "Go", "JavaScript", "SQL", "数据结构", "算法",
        "Django", "Flask", "FastAPI", "React", "Vue", "Node.js",
        "MySQL", "PostgreSQL", "MongoDB", "Redis", "Kafka",
        "Docker", "Kubernetes", "CI/CD", "Git",
        "Machine Learning", "Deep Learning", "NLP", "CV",
        "AWS", "Azure", "GCP",
    ],
    "product": [
        "需求分析", "用户研究", "竞品分析", "PRD撰写", "Roadmap规划",
        "数据分析", "AB测试", "增长黑客", "用户画像", "体验设计",
        "项目管理", "敏捷开发", "Sprint", "OKR",
    ],
    "business": [
        "供应链", "仓储物流", "ERP", "MES", "APS", "WMS", "TMS",
        "电商", "SaaS", "B2B", "B2C", "跨境电商",
        "市场分析", "商务拓展", "渠道管理",
    ],
    "management": [
        "团队管理", "项目管理", "跨部门协作", "沟通表达",
        "目标管理", "绩效评估", "招聘面试", "人才培养",
    ],
}


# 职业路径库
CAREER_PATHS = {
    "tech_to_pm": {
        "name": "技术转产品",
        "description": "从技术实现者转型为产品设计者",
        "target_roles": ["产品经理", "高级产品经理", "产品总监"],
        "success_rate": "high",
        "required_skills": ["需求分析", "数据分析", "PRD撰写", "跨部门协作"],
        "transition_tips": ["用技术背景建立信任", "主动参与产品讨论", "培养业务思维"],
    },
    "pm_to_pdl": {
        "name": "产品转产品线负责人",
        "description": "从单一产品经理走向产品线管理",
        "target_roles": ["高级产品经理", "产品线负责人", "产品总监"],
        "success_rate": "medium",
        "required_skills": ["团队管理", "Roadmap规划", "战略思维", "跨部门领导力"],
        "transition_tips": ["争取带项目机会", "学习商业分析", "建立跨部门影响力"],
    },
    "pm_to_cpo": {
        "name": "产品转首席产品官",
        "description": "从执行层走向战略层",
        "target_roles": ["产品总监", "VP of Product", "CPO"],
        "success_rate": "low",
        "required_skills": ["战略规划", "商业模式设计", "团队建设", "行业洞察"],
        "transition_tips": ["积累多行业经验", "建立行业影响力", "培养商业与财务思维"],
    },
    "supply_chain_consultant": {
        "name": "供应链咨询/专家",
        "description": "深耕供应链领域，成为行业专家",
        "target_roles": ["供应链专家", "解决方案架构师", "咨询顾问", "讲师"],
        "success_rate": "high",
        "required_skills": ["供应链全链路", "运筹优化", "系统设计", "方案输出"],
        "transition_tips": ["沉淀方法论", "输出行业文章", "参与行业峰会"],
    },
    "product_ops": {
        "name": "产品运营一体化",
        "description": "打破产品与运营边界，做复合型人才",
        "target_roles": ["产品运营", "增长负责人", "COO"],
        "success_rate": "medium",
        "required_skills": ["数据分析", "用户增长", "A/B测试", "活动策划"],
        "transition_tips": ["主动承担运营指标", "学习增长黑客方法", "建立数据驱动思维"],
    },
}


class CareerPlanner:
    """职业规划引擎"""
    
    def __init__(self, resume_json: dict = None, footprint_projects: list = None):
        self.resume = resume_json or {}
        self.footprint = footprint_projects or []
    
    def analyze_background(self) -> dict:
        """分析用户职业背景"""
        work_years = self._extract_work_years()
        stage = self._determine_stage(work_years)
        skills = self._extract_skills()
        industries = self._extract_industries()
        level = self._assess_level(skills, work_years)
        strengths = self._extract_strengths()
        gaps = self._analyze_gaps(skills, stage)
        
        return {
            "work_years": work_years,
            "stage": stage,
            "skills": skills,
            "industry_experience": industries,
            "level": level,
            "strengths": strengths,
            "gaps": gaps,
            "analyzed_at": datetime.now().isoformat(),
        }
    
    def _extract_work_years(self) -> int:
        """提取工作年限"""
        if "work_years" in self.resume:
            wy = self.resume["work_years"]
            if isinstance(wy, int):
                return wy
            if isinstance(wy, str):
                match = re.search(r'(\d+)', wy)
                return int(match.group(1)) if match else 0
        return 0
    
    def _determine_stage(self, work_years: int) -> str:
        for key, val in WORK_STAGES.items():
            lo, hi = val["years"]
            if lo <= work_years < hi:
                return key
        return "leadership"
    
    def _extract_skills(self) -> dict:
        """从简历和足迹中提取技能"""
        result = {"technical": [], "product": [], "business": [], "management": []}
        
        # 从简历提取
        for cat, kw_list in SKILL_CATEGORIES.items():
            for kw in kw_list:
                if self._skill_match(kw):
                    if kw not in result[cat]:
                        result[cat].append(kw)
        
        return result
    
    def _skill_match(self, skill: str) -> bool:
        """检查技能是否出现在简历或足迹中"""
        text = json.dumps(self.resume, ensure_ascii=False)
        text += " " + " ".join(json.dumps(p, ensure_ascii=False) for p in self.footprint)
        return skill in text
    
    def _extract_industries(self) -> list:
        """提取行业经验"""
        industries = []
        industry_kw = {
            "供应链": ["供应链", "仓配", "物流", "仓储", "冷链", "运输"],
            "互联网": ["互联网", "SaaS", "电商", "在线", "平台"],
            "制造业": ["制造业", "工厂", "生产", "MES", "ERP"],
            "咨询": ["咨询", "解决方案", "实施", "顾问"],
        }
        text = json.dumps(self.resume, ensure_ascii=False)
        for ind, kws in industry_kw.items():
            if any(kw in text for kw in kws):
                industries.append(ind)
        return industries or ["互联网"]
    
    def _assess_level(self, skills: dict, work_years: int) -> str:
        """评估职级"""
        tech_count = len(skills.get("technical", []))
        pm_count = len(skills.get("product", []))
        mgmt_count = len(skills.get("management", []))
        
        if work_years < 3:
            return "junior" if tech_count > pm_count else "entry_pm"
        elif work_years < 6:
            return "mid_pm" if pm_count >= tech_count else "senior_dev"
        elif work_years < 10:
            return "senior_pm"
        else:
            return "expert_pm" if mgmt_count > 0 else "senior_pm"
    
    def _extract_strengths(self) -> list:
        """提取优势"""
        strengths = []
        skills = self.resume.get("skills", [])
        projects = self.resume.get("projects", [])
        
        if len(projects) >= 5:
            strengths.append("项目经验丰富，独立负责多个项目")
        if skills:
            strengths.append(f"技能栈多元：{', '.join(skills[:5])}")
        if self.footprint and len(self.footprint) > 100:
            strengths.append("数字足迹丰富，持续输出")
        
        return strengths or ["有技术背景，学习能力强"]
    
    def _analyze_gaps(self, skills: dict, stage: str) -> list:
        """分析能力差距"""
        gaps = []
        
        if len(skills.get("technical", [])) > 0 and len(skills.get("product", [])) < 2:
            gaps.append("产品专业技能不足，建议加强需求分析和数据分析")
        if len(skills.get("management", [])) < 1 and stage in ("experienced", "expert"):
            gaps.append("管理能力欠缺，建议尝试带团队或项目管理")
        if len(skills.get("business", [])) < 2:
            gaps.append("业务理解深度不足，建议加强供应链/行业知识")
        
        return gaps or ["建议持续积累项目深度，提高业务影响力"]
    
    def suggest_career_paths(self, background: dict = None) -> List[dict]:
        """生成职业发展路径建议"""
        if background is None:
            background = self.analyze_background()
        
        level = background["level"]
        skills = background["skills"]
        industries = background["industry_experience"]
        
        paths = []
        
        # 匹配适合的路径
        if level in ("entry_pm", "junior", "mid_pm"):
            paths.append(self._build_path("tech_to_pm", background))
            paths.append(self._build_path("supply_chain_consultant", background))
        
        if level in ("mid_pm", "senior_pm", "expert_pm"):
            paths.append(self._build_path("pm_to_pdl", background))
            paths.append(self._build_path("supply_chain_consultant", background))
        
        if level in ("senior_pm", "expert_pm"):
            paths.append(self._build_path("pm_to_cpo", background))
            paths.append(self._build_path("product_ops", background))
        
        return paths[:3]
    
    def _build_path(self, path_key: str, background: dict) -> dict:
        """构建单条路径"""
        path_template = CAREER_PATHS[path_key]
        skills = background["skills"]
        
        # 评估路径成功率
        skill_match = sum(1 for rs in path_template["required_skills"] if any(rs in sl for sl in skills.values()))
        match_rate = skill_match / len(path_template["required_skills"])
        
        if match_rate >= 0.6:
            success = "high"
        elif match_rate >= 0.3:
            success = "medium"
        else:
            success = "low"
        
        return {
            "path_key": path_key,
            "path_name": path_template["name"],
            "description": path_template["description"],
            "target_roles": path_template["target_roles"],
            "success_rate": success,
            "match_score": round(match_rate * 100),
            "next_steps": self._generate_steps(path_template, background),
            "transition_tips": path_template["transition_tips"],
            "required_skills": path_template["required_skills"],
            "skill_gaps": [rs for rs in path_template["required_skills"] if not any(rs in sl for sl in skills.values())],
        }
    
    def _generate_steps(self, path_template: dict, background: dict) -> List[dict]:
        """生成行动步骤"""
        steps = []
        gap_skills = [rs for rs in path_template["required_skills"] if not any(rs in sl for sl in background["skills"].values())]
        
        if gap_skills:
            steps.append({
                "phase": "立即行动",
                "timeline": "1个月",
                "actions": [f"学习《{g}》基础知识" for g in gap_skills[:3]],
                "deliverable": f"掌握{gap_skills[0] if gap_skills else '核心技能'}基础",
            })
        
        steps.append({
            "phase": "短期提升",
            "timeline": "3个月",
            "actions": [
                "找到1个相关项目实践",
                "输出1篇总结文章",
                "找1位该领域的导师交流",
            ],
            "deliverable": "完成1个项目实战",
        })
        
        steps.append({
            "phase": "中期突破",
            "timeline": "6个月",
            "actions": [
                "在简历中体现新技能",
                "争取内部转岗或新项目机会",
                "更新 LinkedIn/BOSS 职位期望",
            ],
            "deliverable": "成功切换到目标角色",
        })
        
        return steps


# ===================== 快捷函数 =====================

def analyze_background(resume_json: dict = None, footprint_projects: list = None) -> dict:
    """分析职业背景"""
    planner = CareerPlanner(resume_json, footprint_projects)
    return planner.analyze_background()


def suggest_career_paths(resume_json: dict = None, footprint_projects: list = None) -> List[dict]:
    """生成职业路径"""
    planner = CareerPlanner(resume_json, footprint_projects)
    analysis = planner.analyze_background()
    return planner.suggest_career_paths(analysis)


if __name__ == "__main__":
    # 测试
    test_resume = {
        "name": "金倩菲",
        "work_years": 8,
        "skills": ["Python", "产品经理", "供应链", "数据分析", "项目管理", "运筹优化"],
        "projects": [
            {"name": "仓配网络优化", "role": "PM", "skills": ["Python", "运筹优化"]},
            {"name": "TMS运输管理系统", "role": "PM", "skills": ["供应链", "TMS"]},
        ],
    }
    
    planner = CareerPlanner(test_resume, [])
    bg = planner.analyze_background()
    print(f"工作年限: {bg['work_years']}年")
    print(f"阶段: {bg['stage']}")
    print(f"级别: {bg['level']}")
    print(f"技能: {json.dumps(bg['skills'], ensure_ascii=False)}")
    print(f"优势: {bg['strengths']}")
    print(f"差距: {bg['gaps']}")
    print()
    
    paths = planner.suggest_career_paths(bg)
    print(f"职业路径建议 ({len(paths)}条):")
    for p in paths:
        print(f"  → {p['path_name']} (成功率:{p['success_rate']}, 匹配度:{p['match_score']}%)")