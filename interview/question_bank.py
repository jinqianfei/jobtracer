"""个性化面题库生成器
基于 JD + 简历 → 生成针对性面试题
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import json


@dataclass
class InterviewQuestion:
    question: str
    type: str          # technical / behavioral / situational / domain
    difficulty: str     # easy / medium / hard
    focus_point: str   # 考察点
    sample_answer: Optional[str] = None


class QuestionBankGenerator:
    """生成个性化面题库"""
    
    def __init__(self, llm_provider: str = "openai"):
        self.llm_provider = llm_provider
    
    def generate_from_jd_and_resume(self, jd_text: str, resume_json: dict) -> List[InterviewQuestion]:
        """基于 JD 和简历生成面题
        
        Args:
            jd_text: 职位描述文本
            resume_json: 简历 JSON 数据
            
        Returns:
            List[InterviewQuestion]: 生成的面试题列表
        """
        # LLM prompt:
        # 你是一个资深面试官。根据以下 JD 和简历，生成 15-20 道面试题。
        # 要求：
        # - 覆盖技术问题、业务问题、情景问题
        # - 难度分布：简单 30% / 中等 50% / 困难 20%
        # - 每个问题标注考察点
        # - 每类问题给出参考答案要点
        
        # 返回 List[InterviewQuestion]
        questions = []
        
        # TODO: 调用 LLM 生成
        # 这里返回示例数据，实际使用时替换为 LLM 调用
        return questions
    
    def generate_technical_questions(self, skills: List[str], projects: List[dict]) -> List[InterviewQuestion]:
        """针对技能和项目生成技术题
        
        Args:
            skills: 技能列表
            projects: 项目经历列表
            
        Returns:
            List[InterviewQuestion]: 技术类面试题
        """
        questions = []
        
        for skill in skills:
            questions.append(InterviewQuestion(
                question=f"请描述一下您对 {skill} 的掌握程度，以及在项目中是如何应用的？",
                type="technical",
                difficulty="medium",
                focus_point=f"{skill} 技术深度与实践能力",
                sample_answer=None
            ))
        
        # TODO: 调用 LLM 生成更精准的技术题
        return questions
    
    def generate_behavioral_questions(self, work_experience: List[dict]) -> List[InterviewQuestion]:
        """生成行为面试题（STAR 法则）
        
        Args:
            work_experience: 工作经历列表
            
        Returns:
            List[InterviewQuestion]: 行为类面试题
        """
        questions = []
        
        # 基于工作经历中的量化成果生成行为问题
        for exp in work_experience:
            company = exp.get("company", "上一家公司")
            if "achievements" in exp:
                for achievement in exp.get("achievements", []):
                    if any(keyword in achievement for keyword in ["提升", "优化", "降低", "增长", "提高"]):
                        # 生成 STAR 类问题
                        questions.append(InterviewQuestion(
                            question=f"请描述在 {company} 时，您是如何实现 {achievement} 的？",
                            type="behavioral",
                            difficulty="medium",
                            focus_point="STAR法则 / 量化成果还原",
                            sample_answer=None
                        ))
        
        return questions
    
    def generate_situational_questions(self, jd_requirements: List[str]) -> List[InterviewQuestion]:
        """生成情景面试题
        
        Args:
            jd_requirements: JD 中的关键要求
            
        Returns:
            List[InterviewQuestion]: 情景类面试题
        """
        questions = []
        
        for req in jd_requirements:
            questions.append(InterviewQuestion(
                question=f"假设您入职后遇到 {req} 相关的问题，您会如何处理？",
                type="situational",
                difficulty="hard",
                focus_point=f"{req} 场景应变能力",
                sample_answer=None
            ))
        
        return questions