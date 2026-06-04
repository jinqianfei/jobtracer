"""AI 模拟面试
基于 JD + 简历的多轮对话模拟面试
支持 LLM 评估，LLM 不可用时自动降级为规则方法
"""
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
import re


@dataclass
class ConversationTurn:
    role: str      # "interviewer" / "candidate"
    message: str
    timestamp: str


@dataclass
class InterviewReport:
    overall_score: float        # 0-100
    technical_score: float
    communication_score: float
    strengths: List[str]
    weaknesses: List[str]
    improvement_suggestions: List[str]
    conversation_history: List[ConversationTurn]


class InterviewSimulator:
    """模拟面试官"""
    
    def __init__(self, jd_text: str, resume_json: dict):
        self.jd = jd_text
        self.resume = resume_json
        self.conversation: List[ConversationTurn] = []
        self.current_question_index = 0
        self.current_phase = "introduction"  # introduction → project → technical → behavioral → qa → end
        self._llm_available = False  # 默认降级到规则方法
    
    def start_interview(self) -> str:
        """开始面试，返回第一个问题"""
        name = self.resume.get("name", "候选人")
        work_years = self.resume.get("work_years", "N")
        
        intro = f"你好，我是今天的面试官。看到你有 {work_years} 年工作经验，"
        intro += f"应聘产品经理岗位。请问你最近做的项目是什么，能简单介绍一下吗？"
        
        self._add_turn("interviewer", intro)
        return intro
    
    def ask_next_question(self) -> Optional[str]:
        """根据简历和上一轮回答，决定下一个问题"""
        if self.current_phase == "introduction":
            self.current_phase = "project"
            return "能详细介绍一下这个项目的背景、你的角色和主要成果吗？"
        
        elif self.current_phase == "project":
            self.current_phase = "technical"
            return "针对这个项目，我在技术实现上有些问题想深入了解一下。请问你们当时的技术架构是怎样的？"
        
        elif self.current_phase == "technical":
            self.current_phase = "behavioral"
            return "假设入职后，我们需要在一个很紧的 deadline 内完成一个需求变更，你会如何处理？"
        
        elif self.current_phase == "behavioral":
            self.current_phase = "qa"
            return "好的，我这边的问题差不多了。请问你有什么想问我的吗？"
        
        elif self.current_phase == "qa":
            self.current_phase = "end"
            return None
        
        return None
    
    def process_answer(self, answer: str) -> str:
        """处理候选人回答，生成下一个问题或反馈"""
        self._add_turn("candidate", answer)
        next_q = self.ask_next_question()
        
        if next_q is None:
            return "[面试结束] 感谢你的时间，面试到此结束。稍后我们会通知你结果。"
        
        self._add_turn("interviewer", next_q)
        return next_q
    
    def evaluate_answer(self, question: str, answer: str, context: dict = None) -> dict:
        """评估回答质量（规则方法 fallback）"""
        score = 0
        tech_keywords = ["技术", "架构", "实现", "开发", "算法", "系统", "方案", "设计", "优化", "性能"]
        comm_keywords = ["首先", "然后", "最后", "因为", "所以", "但是", "我认为", "总结", "STAR", "背景", "任务", "行动", "结果"]
        star_keywords = ["背景", "任务", "行动", "结果", "S:", "T:", "A:", "R:", "Situation", "Task", "Action", "Result"]
        quant_keywords = ["提升了", "降低了", "增长了", "优化了", "提高了", "减少了", "%", "倍", "K", "万", "天", "人"]
        
        answer_lower = answer.lower()
        question_lower = question.lower()
        
        # 长度评分
        if len(answer) < 20:
            score -= 20
        elif len(answer) > 500:
            score -= 5
        else:
            score += 10
        
        # 技术维度
        tech_hits = sum(1 for kw in tech_keywords if kw in answer)
        score += min(tech_hits * 5, 40)
        
        # 沟通结构维度
        comm_hits = sum(1 for kw in comm_keywords if kw in answer)
        score += min(comm_hits * 5, 30)
        
        # STAR 法则
        star_hits = sum(1 for kw in star_keywords if kw.lower() in answer_lower)
        score += min(star_hits * 8, 24)
        
        # 量化数据
        quant_hits = sum(1 for kw in quant_keywords if kw in answer)
        score += min(quant_hits * 6, 18)
        
        # 产品经理专项
        if any(kw in question_lower for kw in ["产品", "需求", "pm", "项目"]):
            if any(kw in answer_lower for kw in ["需求分析", "用户研究", "prd", " roadmap", "规划", "优先级"]):
                score += 10
        
        # 归一化到 0-100
        score = max(0, min(score, 100))
        
        # 生成评语
        strengths = []
        weaknesses = []
        suggestions = []
        
        if star_hits >= 2:
            strengths.append("回答结构清晰，使用了 STAR 法则")
        if quant_hits >= 2:
            strengths.append("有量化数据支撑")
        if tech_hits >= 3:
            strengths.append("技术描述较为深入")
        if comm_hits >= 2:
            strengths.append("表达有逻辑层次")
        
        if len(answer) < 20:
            weaknesses.append("回答过于简短，建议补充更多细节")
        if star_hits == 0:
            weaknesses.append("建议使用 STAR 法则组织回答")
        if quant_hits == 0:
            weaknesses.append("建议增加量化数据（如提升了X%）")
        if tech_hits < 2:
            weaknesses.append("技术细节描述不足")
        
        if score < 60:
            suggestions.append("建议系统练习 STAR 法则回答方式")
            suggestions.append("准备一个详细的项目介绍，控制在 3 分钟内")
        elif score < 80:
            suggestions.append("继续加强量化数据的表达")
            suggestions.append("可以多练习技术方案的系统性描述")
        else:
            suggestions.append("继续保持，建议关注行业最新动态")
        
        return {
            "overall_score": score,
            "technical_score": min(tech_hits * 15, 100),
            "communication_score": min((star_hits + comm_hits) * 10, 100),
            "strengths": strengths,
            "weaknesses": weaknesses,
            "improvement_suggestions": suggestions,
            "reference_answer": self._generate_reference_answer(question, answer),
        }
    
    def _generate_reference_answer(self, question: str, answer: str) -> str:
        """生成参考回答"""
        q_lower = question.lower()
        if "技术" in question or "架构" in question:
            return "我负责的XX系统采用了A/B/C架构，通过XX技术解决了YY问题。具体实现中，我主导了XX模块的设计，最终将性能提升了Z%。"
        elif any(kw in q_lower for kw in ["star", "描述", "经历", "项目"]):
            return "S(背景)：当时团队面临XX问题...\nT(任务)：我负责XXX...\nA(行动)：我通过XXX方案...\nR(结果)：最终实现了XX%的提升（具体数字）"
        elif "如何处理" in question or "假设" in question:
            return "我会分三步处理：1）快速评估影响范围和紧迫性；2）与相关方沟通确认需求和资源；3）制定分阶段方案并持续同步进度。"
        else:
            return "建议从以下角度回答：1）明确自己的角色和贡献；2）说明具体行动；3）量化结果和影响。"
    
    def end_interview(self) -> InterviewReport:
        """结束面试，生成反馈报告"""
        tech_score = 0
        comm_score = 0
        
        tech_keywords = ["技术", "架构", "实现", "开发", "算法", "系统"]
        comm_keywords = ["首先", "然后", "最后", "因为", "所以", "但是"]
        
        for turn in self.conversation:
            if turn.role == "candidate":
                msg = turn.message
                if any(kw in msg for kw in tech_keywords):
                    tech_score += 5
                if any(kw in msg for kw in comm_keywords):
                    comm_score += 5
        
        tech_score = min(tech_score, 100)
        comm_score = min(comm_score, 100)
        overall = (tech_score * 0.6 + comm_score * 0.4)
        
        strengths = []
        weaknesses = []
        suggestions = []
        
        if tech_score >= 70:
            strengths.append("技术理解较深入，能清晰描述技术方案")
        elif tech_score < 50:
            weaknesses.append("技术表达不够清晰，建议多练习技术方案描述")
        
        if comm_score >= 70:
            strengths.append("沟通表达流畅，逻辑清晰")
        elif comm_score < 50:
            weaknesses.append("表达可以更结构化，建议使用 STAR 法则")
        
        if overall >= 80:
            suggestions.append("继续保持，建议加强 STAR 回答的量化数据")
        else:
            suggestions.append("建议系统练习 STAR 法则回答，增加量化数据")
            suggestions.append("准备一个详细的项目介绍，控制在 3 分钟内")
        
        return InterviewReport(
            overall_score=overall,
            technical_score=tech_score,
            communication_score=comm_score,
            strengths=strengths,
            weaknesses=weaknesses,
            improvement_suggestions=suggestions,
            conversation_history=self.conversation.copy()
        )
    
    def _add_turn(self, role: str, message: str) -> None:
        """添加对话轮次"""
        self.conversation.append(ConversationTurn(
            role=role,
            message=message,
            timestamp=datetime.now().isoformat()
        ))
    
    def get_conversation_summary(self) -> str:
        """获取对话摘要"""
        summary = f"共 {len(self.conversation)} 轮对话\n"
        for i, turn in enumerate(self.conversation):
            role_label = "🙋 候选人" if turn.role == "candidate" else "👔 面试官"
            msg_preview = turn.message[:50] + "..." if len(turn.message) > 50 else turn.message
            summary += f"{i+1}. {role_label}: {msg_preview}\n"
        return summary


if __name__ == "__main__":
    # 测试
    sim = InterviewSimulator("Python后端开发", {"name": "test", "work_years": "8"})
    result = sim.evaluate_answer("请描述你最近做的项目", 
        "我最近主导了仓配网络优化项目，通过运筹优化算法将配送效率提升了30%，同时降低了15%的运输成本。")
    print(f"评分: {result['overall_score']}")
    print(f"优势: {result['strengths']}")
    print(f"改进建议: {result['improvement_suggestions']}")