"""
hr/reply_generator.py
HR 回复建议生成器 - 基于意图分类结果生成针对性回复建议
支持批量生成、智能填充、评分排序
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable
from enum import Enum

# 从 intent_classifier 导入意图类型和结果
try:
    from .intent_classifier import IntentType, IntentResult
except ImportError:
    from intent_classifier import IntentType, IntentResult  # fallback for direct run


# ============================================================
# 回复场景标签枚举
# ============================================================

class ReplyScenario(Enum):
    """回复适用场景"""
    ENTHUSIASTIC = "热情积极"
    PROFESSIONAL = "专业正式"
    CASUAL = "轻松随意"
    CAUTIOUS = "谨慎确认"
    FOLLOW_UP = "跟进催促"
    DEFERRED = "婉拒/推迟"
    POLITE_REJECT = "礼貌婉拒"
    REGRET_REJECT = "遗憾婉拒"


# ============================================================
# 回复建议数据类
# ============================================================

@dataclass
class ReplyOption:
    """单个回复选项"""
    text: str
    score: float
    scenario: str
    variables_filled: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "score": self.score,
            "scenario": self.scenario,
        }


@dataclass
class ReplyResult:
    """回复生成结果"""
    intent: str
    replies: List[ReplyOption]
    best_reply: str
    template_used: str = ""


# ============================================================
# 回复模板体系
# ============================================================

REPLY_TEMPLATES: Dict[IntentType, List[Dict[str, Any]]] = {
    IntentType.GREETING: [
        {
            "text": "您好！看到贵司正在招聘{name}岗位，我对贵司的产品很感兴趣，请问可以进一步了解吗？",
            "scenario": ReplyScenario.ENTHUSIASTIC.value,
            "score": 0.95,
        },
        {
            "text": "你好！感谢你的联系。我对{name}岗位很感兴趣，方便聊聊吗？",
            "scenario": ReplyScenario.PROFESSIONAL.value,
            "score": 0.90,
        },
        {
            "text": "您好！请问这个岗位还在招聘吗？我想了解一下具体情况。",
            "scenario": ReplyScenario.CASUAL.value,
            "score": 0.85,
        },
        {
            "text": "你好，在吗？很高兴收到你的消息，我对{name}岗位很感兴趣。",
            "scenario": ReplyScenario.ENTHUSIASTIC.value,
            "score": 0.88,
        },
        {
            "text": "您好！感谢联系，我对贵司这个岗位非常感兴趣，方便进一步沟通吗？",
            "scenario": ReplyScenario.PROFESSIONAL.value,
            "score": 0.92,
        },
    ],

    IntentType.JD_INQUIRY: [
        {
            "text": "您好！这个岗位主要负责{job_title}相关工作。我具备扎实的{skills}技能和项目经验，相信可以胜任。请问还有什么需要我补充说明的吗？",
            "scenario": ReplyScenario.PROFESSIONAL.value,
            "score": 0.92,
        },
        {
            "text": "感谢询问！这个岗位的工作内容我很了解，也很有兴趣。请问面试流程是怎样的？",
            "scenario": ReplyScenario.ENTHUSIASTIC.value,
            "score": 0.88,
        },
        {
            "text": "关于这个岗位，我之前有过相关的项目经验，对{skills}比较熟悉。请问贵司的团队规模和 技术栈是怎样的？",
            "scenario": ReplyScenario.PROFESSIONAL.value,
            "score": 0.85,
        },
    ],

    IntentType.RESUME_REQUEST: [
        {
            "text": "好的，这是我的简历，请您查收。我对{company}的{job_title}岗位非常感兴趣，期待有机会进一步沟通！",
            "scenario": ReplyScenario.PROFESSIONAL.value,
            "score": 0.95,
        },
        {
            "text": "感谢您的联系！简历已附上，请查阅。如果需要补充其他材料，请随时告诉我。",
            "scenario": ReplyScenario.PROFESSIONAL.value,
            "score": 0.90,
        },
        {
            "text": "您好！简历已发送，请查收。我对贵司这个岗位非常感兴趣，期待您的回复！",
            "scenario": ReplyScenario.ENTHUSIASTIC.value,
            "score": 0.88,
        },
    ],

    IntentType.INTERVIEW_INVITE: [
        {
            "text": "非常感谢面试邀请！我对{job_title}岗位非常感兴趣，以下是我方便的时间：周三下午2-4点 / 周四上午10-12点，请问哪个时间更方便？",
            "scenario": ReplyScenario.ENTHUSIASTIC.value,
            "score": 0.95,
        },
        {
            "text": "感谢您的邀请！我对贵司这个岗位非常感兴趣，愿意参加面试。请问方便在{company}进行线下面谈，还是支持视频面试？",
            "scenario": ReplyScenario.PROFESSIONAL.value,
            "score": 0.92,
        },
        {
            "text": "好的，非常期待！我这周周三和周四下午都有空，请问什么时间方便？我可以配合贵司的时间。",
            "scenario": ReplyScenario.ENTHUSIASTIC.value,
            "score": 0.90,
        },
        {
            "text": "感谢面试邀请！我对{company}的{job_title}岗位很感兴趣，愿意安排时间参加面试。请问需要我准备什么材料吗？",
            "scenario": ReplyScenario.PROFESSIONAL.value,
            "score": 0.88,
        },
    ],

    IntentType.SALARY_NEGOTIATION: [
        {
            "text": "感谢您发来薪资信息！我的期望薪资是{salary}，结合市场行情和我的经验，期待在合理范围内。如果您觉得有调整空间，我将非常感激。",
            "scenario": ReplyScenario.CAUTIOUS.value,
            "score": 0.90,
        },
        {
            "text": "薪资方面我比较关注综合待遇，包括基本工资、奖金和福利。请问贵司的绩效考核周期和奖金制度是怎样的？",
            "scenario": ReplyScenario.PROFESSIONAL.value,
            "score": 0.85,
        },
        {
            "text": "好的，我考虑一下。不过我的期望薪资是{salary}，方便的话能否再争取一下？",
            "scenario": ReplyScenario.CAUTIOUS.value,
            "score": 0.80,
        },
    ],

    IntentType.REJECTION: [
        {
            "text": "好的，感谢你的回复！请问是否方便告知具体是哪些方面不太匹配？我想作为未来发展的参考。",
            "scenario": ReplyScenario.POLITE_REJECT.value,
            "score": 0.85,
        },
        {
            "text": "理解，希望以后有机会合作，祝团队招聘顺利！",
            "scenario": ReplyScenario.REGRET_REJECT.value,
            "score": 0.90,
        },
        {
            "text": "感谢你的坦诚！虽然这次可能不太合适，但还是谢谢你的联系，祝招聘顺利。",
            "scenario": ReplyScenario.POLITE_REJECT.value,
            "score": 0.82,
        },
        {
            "text": "好的，明白了。感谢你的反馈，期待未来有机会再合作。祝好！",
            "scenario": ReplyScenario.REGRET_REJECT.value,
            "score": 0.78,
        },
    ],

    IntentType.FOLLOW_UP: [
        {
            "text": "抱歉让你久等了！我对贵司的{job_title}岗位非常感兴趣，期望薪资{salary}，可以接受面试。",
            "scenario": ReplyScenario.ENTHUSIASTIC.value,
            "score": 0.95,
        },
        {
            "text": "感谢提醒！我已经仔细考虑过了，愿意进一步沟通。请问方便约什么时间？",
            "scenario": ReplyScenario.PROFESSIONAL.value,
            "score": 0.90,
        },
        {
            "text": "好的，我这边没问题。对这个岗位很有兴趣，期待进一步交流！",
            "scenario": ReplyScenario.ENTHUSIASTIC.value,
            "score": 0.92,
        },
        {
            "text": "抱歉回复晚了，最近在忙。这周可以约个时间聊聊吗？",
            "scenario": ReplyScenario.CASUAL.value,
            "score": 0.82,
        },
        {
            "text": "我考虑好了，对这个岗位很有意向！请问什么时候方便进一步沟通？",
            "scenario": ReplyScenario.ENTHUSIASTIC.value,
            "score": 0.94,
        },
    ],

    IntentType.INFO_CONFIRM: [
        {
            "text": "好的，信息已确认。请问还有什么需要我补充的吗？",
            "scenario": ReplyScenario.PROFESSIONAL.value,
            "score": 0.90,
        },
        {
            "text": "确认收到！我这边信息都准确的，如果没其他问题就等你的进一步通知了。",
            "scenario": ReplyScenario.CASUAL.value,
            "score": 0.88,
        },
        {
            "text": "好的，核实无误。谢谢你的确认，期待下一步进展！",
            "scenario": ReplyScenario.PROFESSIONAL.value,
            "score": 0.85,
        },
    ],

    IntentType.POSITIVE: [
        {
            "text": "非常感谢！我也很期待进一步了解这个岗位，下周方便安排一次深入沟通吗？",
            "scenario": ReplyScenario.ENTHUSIASTIC.value,
            "score": 0.95,
        },
        {
            "text": "谢谢你的认可！我对贵司和这个岗位都很有信心，期待面谈！",
            "scenario": ReplyScenario.PROFESSIONAL.value,
            "score": 0.92,
        },
        {
            "text": "太好了！我也很感兴趣。请问面试流程是怎样的？需要准备什么吗？",
            "scenario": ReplyScenario.ENTHUSIASTIC.value,
            "score": 0.90,
        },
        {
            "text": "感谢你的正面反馈！我对这个机会非常期待，希望能顺利推进。",
            "scenario": ReplyScenario.PROFESSIONAL.value,
            "score": 0.88,
        },
    ],

    IntentType.NEGATIVE: [
        {
            "text": "好的，谢谢你的联系。考虑之后决定暂时不申请这个岗位了，祝招聘顺利。",
            "scenario": ReplyScenario.POLITE_REJECT.value,
            "score": 0.85,
        },
        {
            "text": "感谢你的联系，但可能不太适合我。麻烦你了，祝好。",
            "scenario": ReplyScenario.REGRET_REJECT.value,
            "score": 0.80,
        },
    ],

    IntentType.OTHER: [
        {
            "text": "好的，谢谢你的联系！我会认真考虑这个岗位，有消息会及时回复。",
            "scenario": ReplyScenario.PROFESSIONAL.value,
            "score": 0.85,
        },
        {
            "text": "收到，感谢你的消息！期待进一步交流。",
            "scenario": ReplyScenario.CASUAL.value,
            "score": 0.80,
        },
        {
            "text": "好的，我知道了。请问还有什么需要了解的吗？",
            "scenario": ReplyScenario.PROFESSIONAL.value,
            "score": 0.75,
        },
    ],
}


# ============================================================
# 变量填充器
# ============================================================

class VariableFiller:
    """智能填充回复模板中的变量"""

    DEFAULT_PLACEHOLDERS = {
        "{name}": "贵司",
        "{job_title}": "该岗位",
        "{company}": "贵司",
        "{salary}": "可商议",
        "{skills}": "相关技能",
    }

    def __init__(self, resume_json: dict = None, job_info: dict = None):
        self.resume = resume_json or {}
        self.job = job_info or {}

    def fill(self, template: str) -> tuple[str, List[str]]:
        """
        填充模板中的变量

        Args:
            template: 回复模板字符串

        Returns:
            (填充后的文本, 已填充的变量列表)
        """
        filled_vars = []
        result = template

        variables = {
            "{name}": self._get_name(),
            "{skills}": self._get_skills(),
            "{job_title}": self._get_job_title(),
            "{company}": self._get_company(),
            "{salary}": self._get_salary(),
        }

        for placeholder, value in variables.items():
            if placeholder in result:
                if value:
                    result = result.replace(placeholder, value)
                    filled_vars.append(placeholder)
                else:
                    default_val = self.DEFAULT_PLACEHOLDERS.get(placeholder, "")
                    result = result.replace(placeholder, default_val)

        return result, filled_vars

    def _get_name(self) -> str:
        for key in ["name", "姓名", "candidate_name"]:
            if key in self.resume:
                return str(self.resume[key])
        return ""

    def _get_skills(self) -> str:
        skills = self.resume.get("skills", [])
        if isinstance(skills, str):
            return skills
        if isinstance(skills, list):
            if skills:
                return "、".join(skills[:5])
        return ""

    def _get_job_title(self) -> str:
        for key in ["job_title", "title", "position", "岗位"]:
            if key in self.job:
                return str(self.job[key])
        return ""

    def _get_company(self) -> str:
        for key in ["company", "公司", "company_name"]:
            if key in self.job:
                return str(self.job[key])
        return ""

    def _get_salary(self) -> str:
        for key in ["salary", "expected_salary", "期望薪资", "salary_expectation"]:
            if key in self.resume:
                return str(self.resume[key])
        for key in ["salary_range", "薪资范围"]:
            if key in self.job:
                return str(self.job[key])
        return ""


# ============================================================
# ReplyGenerator 主类
# ============================================================

class ReplyGenerator:
    """
    HR 回复生成器
    支持基于模板生成、智能评分、LLM 增强
    """

    def __init__(
        self,
        resume_json: dict = None,
        job_info: dict = None,
        llm_client: Callable = None,
        templates: Dict[IntentType, List[Dict[str, Any]]] = None,
    ):
        """
        初始化回复生成器

        Args:
            resume_json: 简历 JSON 数据
            job_info: 职位信息 JSON 数据
            llm_client: LLM 客户端（如有则使用 LLM 增强）
            templates: 自定义模板字典（可选）
        """
        self.filler = VariableFiller(resume_json, job_info)
        self.llm = llm_client
        self._template_index = templates or REPLY_TEMPLATES

    def generate(
        self,
        intent_result: IntentResult,
        count: int = 3,
    ) -> ReplyResult:
        """
        根据意图分类结果生成回复建议

        Args:
            intent_result: 意图分类结果
            count: 返回的回复选项数量

        Returns:
            ReplyResult: 回复生成结果
        """
        intent = intent_result.intent

        # 获取该意图的模板
        templates = self._template_index.get(intent, self._template_index.get(IntentType.OTHER, []))

        if not templates:
            return ReplyResult(
                intent=intent.value,
                replies=[],
                best_reply="感谢您的联系，我会尽快回复您。",
                template_used="",
            )

        # 生成填充后的回复选项
        reply_options = []
        for tmpl in templates:
            text = tmpl.get("text", "")
            score = tmpl.get("score", 0.5)
            scenario = tmpl.get("scenario", "")

            # 填充变量
            filled_text, filled_vars = self.filler.fill(text)

            # 应用置信度调整
            adjusted_score = self._adjust_score(score, intent_result, scenario)

            reply_options.append(ReplyOption(
                text=filled_text,
                score=adjusted_score,
                scenario=scenario,
                variables_filled=filled_vars,
            ))

        # 按分数排序
        reply_options.sort(key=lambda x: x.score, reverse=True)

        # 取 top N
        top_replies = reply_options[:count]

        return ReplyResult(
            intent=intent.value,
            replies=top_replies,
            best_reply=top_replies[0].text if top_replies else "",
            template_used=intent.value,
        )

    def get_best_reply(self, intent_result: IntentResult) -> str:
        """
        获取最佳回复

        Args:
            intent_result: 意图分类结果

        Returns:
            str: 最佳回复文本
        """
        result = self.generate(intent_result, count=1)
        return result.best_reply

    def generate_batch(
        self,
        intent_results: List[IntentResult],
        count: int = 3,
    ) -> List[ReplyResult]:
        """
        批量生成回复

        Args:
            intent_results: 意图分类结果列表
            count: 每个结果返回的回复数量

        Returns:
            List[ReplyResult]: 回复结果列表
        """
        return [self.generate(r, count) for r in intent_results]

    def _adjust_score(
        self,
        base_score: float,
        intent_result: IntentResult,
        scenario: str,
    ) -> float:
        """根据上下文调整回复分数"""
        adjusted = base_score

        # 高置信度意图加权
        if intent_result.confidence >= 0.8:
            adjusted += 0.05
        elif intent_result.confidence < 0.5:
            adjusted -= 0.1

        # 场景标签调整
        positive_scenarios = {ReplyScenario.ENTHUSIASTIC.value, ReplyScenario.PROFESSIONAL.value}
        if scenario in positive_scenarios:
            adjusted += 0.03

        return max(0.0, min(1.0, adjusted))

    async def _enhance_with_llm(
        self,
        intent_result: IntentResult,
        rule_result: ReplyResult,
    ) -> Optional[ReplyResult]:
        """使用 LLM 增强回复质量"""
        if not self.llm:
            return None

        prompt = f"""你是一个 HR 回复优化助手。请根据以下信息，生成更自然、更个性化的回复建议。

意图类型: {intent_result.intent.value}
置信度: {intent_result.confidence:.0%}
判断依据: {intent_result.reasoning}
原始消息: {intent_result.raw_message}

候选人背景:
- 姓名: {self.filler._get_name() or '未知'}
- 技能: {self.filler._get_skills() or '未知'}
- 期望薪资: {self.filler._get_salary() or '可商议'}

职位信息:
- 岗位: {self.filler._get_job_title() or '未知'}
- 公司: {self.filler._get_company() or '未知'}

当前候选回复:
{rule_result.best_reply}

请生成 1 条更优化的回复，保持原意但更自然、更符合候选人身份。
只返回回复文本，不要解释。
"""

        try:
            response = await self.llm.generate(prompt)

            enhanced_replies = rule_result.replies.copy()
            if enhanced_replies and isinstance(response, str) and response.strip():
                enhanced_replies[0].text = response.strip()
                enhanced_replies[0].score = min(enhanced_replies[0].score + 0.1, 0.99)

            return ReplyResult(
                intent=rule_result.intent,
                replies=enhanced_replies,
                best_reply=response.strip() if isinstance(response, str) else rule_result.best_reply,
                template_used=f"{rule_result.template_used}_llm_enhanced",
            )
        except Exception:
            return None

    def add_template(self, intent: IntentType, template: dict):
        """添加自定义模板"""
        if intent not in self._template_index:
            self._template_index[intent] = []
        self._template_index[intent].append(template)

    def get_templates(self, intent: IntentType) -> List[dict]:
        """获取指定意图的所有模板"""
        return self._template_index.get(intent, [])

    def reload_templates(self, templates: dict):
        """重新加载模板字典"""
        self._template_index = templates


# ============================================================
# 便捷函数（符合指定接口）
# ============================================================

_default_generator: Optional[ReplyGenerator] = None
_default_classifier: Optional[Any] = None


def get_classifier() -> Any:
    """获取默认意图分类器（延迟导入避免循环）"""
    global _default_classifier
    if _default_classifier is None:
        from hr.intent_classifier import IntentClassifier
        _default_classifier = IntentClassifier()
    return _default_classifier


def get_generator(
    resume_json: dict = None,
    job_info: dict = None,
    llm_client: Callable = None,
) -> ReplyGenerator:
    """获取默认生成器实例"""
    global _default_generator
    if _default_generator is None:
        _default_generator = ReplyGenerator(resume_json=resume_json, job_info=job_info, llm_client=llm_client)
    return _default_generator


def generate_hr_reply(
    intent: str,
    hr_message: str,
    my_background: dict,
) -> dict:
    """
    根据 HR 意图生成回复（符合指定接口）

    Args:
        intent: 意图类型字符串 "interested"|"salary_negotiate"|"interview_invite"|"reject"|"follow_up"|"other"
        hr_message: HR 的原始消息
        my_background: 候选人背景信息 dict，包含 name, skills, expected_salary 等

    Returns:
        dict: {
            "reply_text": "...",
            "reply_tone": "formal|friendly|concise",
            "tips": [...]
        }
    """
    # 意图字符串映射到 IntentType
    INTENT_MAP = {
        "interested": "positive",
        "salary_negotiate": "salary_negotiation",
        "interview_invite": "interview_invite",
        "reject": "rejection",
        "follow_up": "follow_up",
        "other": "other",
    }

    # 构建 resume_json 和 job_info
    resume_json = {
        "name": my_background.get("name", ""),
        "skills": my_background.get("skills", []),
        "expected_salary": my_background.get("expected_salary", ""),
    }
    job_info = {
        "job_title": my_background.get("job_title", ""),
        "company": my_background.get("company", ""),
        "salary_range": my_background.get("salary_range", ""),
    }

    # 先用分类器对 HR 消息进行分类
    classifier = get_classifier()
    intent_result = classifier.classify(hr_message)

    # 如果传入的 intent 有效，优先使用传入的 intent
    if intent in INTENT_MAP:
        try:
            from hr.intent_classifier import IntentType as JTIntentType
            mapped_intent = JTIntentType(INTENT_MAP[intent])
            # 构造一个 IntentResult
            from hr.intent_classifier import IntentResult
            intent_result = IntentResult(
                intent=mapped_intent,
                confidence=0.9,
                reasoning=f"使用传入意图: {intent}",
                keywords=[],
                raw_message=hr_message,
            )
        except Exception:
            pass

    # 生成回复
    generator = get_generator(resume_json=resume_json, job_info=job_info)
    reply_result = generator.generate(intent_result, count=3)

    # 确定语气
    tone_map = {
        ReplyScenario.ENTHUSIASTIC.value: "friendly",
        ReplyScenario.PROFESSIONAL.value: "formal",
        ReplyScenario.CASUAL.value: "friendly",
        ReplyScenario.CAUTIOUS.value: "concise",
        ReplyScenario.FOLLOW_UP.value: "concise",
        ReplyScenario.POLITE_REJECT.value: "formal",
        ReplyScenario.REGRET_REJECT.value: "concise",
        ReplyScenario.DEFERRED.value: "concise",
    }
    reply_tone = tone_map.get(reply_result.replies[0].scenario, "formal") if reply_result.replies else "formal"

    # 生成 tips
    tips = []
    if intent_result.confidence < 0.7:
        tips.append("该意图置信度较低，建议结合 HR 的完整消息内容判断")
    if my_background.get("expected_salary"):
        tips.append(f"期望薪资 {my_background['expected_salary']} 已填入回复模板")
    if intent == "salary_negotiate":
        tips.append("薪资谈判时建议展示自身优势和市场竞争价值")
    if intent == "interview_invite":
        tips.append("面试邀请建议尽快回复并提供多个时间选项")

    return {
        "reply_text": reply_result.best_reply,
        "reply_tone": reply_tone,
        "tips": tips,
    }


def generate_reply(intent_result: IntentResult, count: int = 3, resume_json: dict = None, job_info: dict = None) -> ReplyResult:
    """便捷函数：使用默认生成器生成回复"""
    generator = get_generator(resume_json, job_info)
    return generator.generate(intent_result, count)


def get_best_reply(intent_result: IntentResult, resume_json: dict = None, job_info: dict = None) -> str:
    """便捷函数：获取最佳回复"""
    generator = get_generator(resume_json, job_info)
    return generator.get_best_reply(intent_result)


# ============================================================
# 测试入口
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("HR 回复建议生成器测试")
    print("=" * 60)

    sample_resume = {
        "name": "张三",
        "skills": ["Python", "数据分析", "机器学习", "SQL", "TensorFlow"],
        "expected_salary": "25K",
    }

    sample_job = {
        "title": "高级算法工程师",
        "company": "某知名互联网公司",
        "salary_range": "20-35K",
    }

    generator = ReplyGenerator(resume_json=sample_resume, job_info=sample_job)

    test_messages = [
        ("你好，在吗？看到你的简历，想了解一下", "打招呼"),
        ("这个岗位主要做什么？需要加班吗？", "JD询问"),
        ("可以发一下你的简历吗？", "简历请求"),
        ("你的简历我们觉得不错，想约个时间面试", "面试邀请"),
        ("你期望的薪资是多少？", "薪资沟通"),
        ("不好意思，你的经验可能不太匹配这个岗位", "婉拒"),
        ("还没收到你的回复，方便尽快回复一下吗？", "催促"),
        ("很感兴趣，想进一步了解一下", "积极反馈"),
    ]

    print()
    try:
        from .intent_classifier import IntentClassifier
    except ImportError:
        from intent_classifier import IntentClassifier

    classifier = IntentClassifier()

    for msg, desc in test_messages:
        intent_result = classifier.classify(msg)
        reply_result = generator.generate(intent_result, count=3)

        print(f"[{desc}] {msg[:30]}...")
        print(f"  意图: {intent_result.intent.value} ({intent_result.confidence:.0%})")
        print(f"  最佳回复: {reply_result.best_reply[:40]}...")
        print(f"  候选回复数: {len(reply_result.replies)}")
        print()

    # 测试 generate_hr_reply 接口
    print("=" * 60)
    print("测试 generate_hr_reply 接口")
    print("=" * 60)
    print()

    my_background = {
        "name": "李明",
        "skills": ["Python", "Go", "系统架构", "分布式系统"],
        "expected_salary": "30K",
        "job_title": "后端架构师",
        "company": "某一线大厂",
    }

    for intent_key in ["interested", "salary_negotiate", "interview_invite", "reject", "follow_up", "other"]:
        result = generate_hr_reply(intent_key, "你好，我们看到你的简历，想了解一下", my_background)
        print(f"[{intent_key}] reply_text: {result['reply_text'][:40]}...")
        print(f"         reply_tone: {result['reply_tone']}, tips: {result['tips']}")
        print()

    print("=" * 60)
    print("测试完成")
    print("=" * 60)