"""个性化面题库生成器
基于 JD + 简历 → 生成针对性面试题
支持 LLM 生成，LLM 不可用时自动降级为规则方法
"""
from dataclasses import dataclass
from typing import List, Dict, Optional
import re


@dataclass
class InterviewQuestion:
    question: str
    type: str          # technical / behavioral / situational / domain
    difficulty: str   # easy / medium / hard
    focus_point: str  # 考察点
    sample_answer: Optional[str] = None


# 技术栈关键词（用于从 JD 提取技能）
TECH_SKILLS = [
    "Python", "Java", "JavaScript", "TypeScript", "Go", "Rust", "C++", "C#",
    "React", "Vue", "Angular", "Node.js", "Django", "Flask", "Spring", "FastAPI",
    "MySQL", "PostgreSQL", "MongoDB", "Redis", "Kafka", "RabbitMQ",
    "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Git", "CI/CD",
    "Machine Learning", "Deep Learning", "NLP", "CV", "Algorithm",
    "API", "REST", "GraphQL", "Microservice", "分布式", "缓存", "队列",
    "供应链", "ERP", "MES", "APS", "WMS", "TMS", "SRM",
    "产品经理", "项目管理", "需求分析", "数据分析", "AB测试",
]


class QuestionBankGenerator:
    """生成个性化面题库"""
    
    def __init__(self, llm_provider: str = "openai"):
        self.llm_provider = llm_provider
        self._llm_available = False  # 默认降级到规则方法
    
    def _extract_skills_from_jd(self, jd_text: str) -> List[str]:
        """从 JD 文本提取技能关键词"""
        found = []
        jd_upper = jd_text.upper()
        for skill in TECH_SKILLS:
            if skill.upper() in jd_upper:
                found.append(skill)
        # 额外从英文技能名补充
        english_skills = re.findall(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', jd_text)
        for s in english_skills:
            if len(s) > 2 and s not in found:
                found.append(s)
        return found[:20]  # 最多20个
    
    def _extract_projects_from_resume(self, resume_json: dict) -> List[dict]:
        """从简历提取项目经历"""
        projects = resume_json.get("projects", [])
        if not projects and "work_experience" in resume_json:
            projects = resume_json.get("work_experience", [])
        return projects
    
    def generate_from_jd_and_resume(self, jd_text: str, resume_json: dict) -> List[InterviewQuestion]:
        """基于 JD 和简历生成面题"""
        questions = []
        
        # 1. 技术题
        skills = self._extract_skills_from_jd(jd_text)
        projects = self._extract_projects_from_resume(resume_json)
        questions.extend(self.generate_technical_questions(skills, projects))
        
        # 2. 项目题
        questions.extend(self.generate_behavioral_questions(projects))
        
        # 3. 情景题
        jd_requirements = self._extract_jd_requirements(jd_text)
        questions.extend(self.generate_situational_questions(jd_requirements))
        
        # 4. 产品经理专项
        if any(kw in jd_text for kw in ["产品", "PM", "产品经理"]):
            questions.extend(self._generate_pm_questions())
        
        return questions[:20]  # 最多20题
    
    def generate_technical_questions(self, skills: List[str], projects: List[dict]) -> List[InterviewQuestion]:
        """针对技能和项目生成技术题（规则方法）"""
        questions = []
        
        for skill in skills[:10]:  # 最多10个技能
            questions.append(InterviewQuestion(
                question=f"请描述一下您对 {skill} 的掌握程度，以及在项目中是如何应用的？",
                type="technical",
                difficulty="medium",
                focus_point=f"{skill} 技术深度与实践能力",
                sample_answer=f"我熟练掌握 {skill}，在项目中用于XXX，实现了YYY效果。"
            ))
            questions.append(InterviewQuestion(
                question=f"{skill} 的实现原理是什么？有什么优缺点？",
                type="technical",
                difficulty="medium",
                focus_point=f"{skill} 原理理解",
                sample_answer=None
            ))
            questions.append(InterviewQuestion(
                question=f"您在项目中遇到过最有挑战的 {skill} 相关问题是如何解决的？",
                type="technical",
                difficulty="hard",
                focus_point=f"{skill} 问题解决能力",
                sample_answer=None
            ))
        
        return questions
    
    def generate_behavioral_questions(self, work_experience: List[dict]) -> List[InterviewQuestion]:
        """生成行为面试题（STAR 法则）（规则方法）"""
        questions = []
        
        situations = [
            ("团队协作", "团队合作", "您是如何与团队成员协作完成复杂项目的？"),
            ("冲突解决", "冲突", "您遇到过团队内部意见分歧的情况，是如何解决的？"),
            ("高压 deadline", "紧的deadline", "您是否有过在高压 deadline 下完成重要任务的经历？"),
            ("创新改进", "优化", "您主导过什么创新或改进？结果如何？"),
            ("失败教训", "失败", "您经历过什么项目失败或挫折？从中吸取了什么教训？"),
        ]
        
        for label, kw, q in situations:
            questions.append(InterviewQuestion(
                question=q,
                type="behavioral",
                difficulty="medium",
                focus_point=f"STAR法则 / {label}",
                sample_answer="S(背景): ... T(任务): ... A(行动): ... R(结果): ..."
            ))
        
        return questions
    
    def generate_situational_questions(self, jd_requirements: List[str]) -> List[InterviewQuestion]:
        """生成情景面试题（规则方法）"""
        questions = []
        
        scenarios = [
            ("需求变更", "需求变更", "假设入职后需要在很紧的 deadline 内完成一个紧急需求变更，你会如何处理？"),
            ("跨部门协作", "跨部门", "需要跨部门协作推动一个项目，但对方不配合，你会怎么做？"),
            ("资源不足", "资源不足", "当资源（人/时间/预算）严重不足时，如何保证项目质量？"),
            ("技术选型", "技术选型", "如果让你做技术选型，你会考虑哪些因素？请举例说明。"),
        ]
        
        for req, kw, q in scenarios:
            questions.append(InterviewQuestion(
                question=q,
                type="situational",
                difficulty="hard",
                focus_point=f"{req}场景应变能力",
                sample_answer=None
            ))
        
        return questions
    
    def _extract_jd_requirements(self, jd_text: str) -> List[str]:
        """从 JD 提取关键要求"""
        requirements = []
        patterns = [
            r"熟练\s*[掌运撑]\s*([^\n，。,.]{2,10})",
            r"有\s*([^\n，。,.]{2,8})\s*经验",
            r"具备\s*([^\n，。,.]{2,8})\s*能力",
        ]
        for p in patterns:
            matches = re.findall(p, jd_text)
            requirements.extend(matches)
        return list(set(requirements))[:10]
    
    def _generate_pm_questions(self) -> List[InterviewQuestion]:
        """生成产品经理专项问题"""
        questions = [
            InterviewQuestion(
                question="请描述一个您主导的最成功的产品的背景、目标、方案和结果。",
                type="behavioral",
                difficulty="hard",
                focus_point="产品全局把控能力",
                sample_answer=None
            ),
            InterviewQuestion(
                question="您如何判断一个需求是否值得做？您的优先级决策逻辑是什么？",
                type="situational",
                difficulty="medium",
                focus_point="需求判断与优先级决策",
                sample_answer=None
            ),
            InterviewQuestion(
                question="面对业务方的「紧急需求」，但技术评估认为风险很大，你怎么办？",
                type="situational",
                difficulty="hard",
                focus_point="博弈与沟通能力",
                sample_answer=None
            ),
        ]
        return questions


if __name__ == "__main__":
    # 测试
    gen = QuestionBankGenerator()
    qs = gen.generate_from_jd_and_resume(
        "Python后端开发，熟练掌握Django/Flask，有供应链经验优先",
        {"projects": [{"name": "仓配网络优化", "skills": ["Python", "运筹优化"]}]}
    )
    print(f"生成题目数: {len(qs)}")
    for q in qs[:5]:
        print(f"  [{q.type}] {q.question}")