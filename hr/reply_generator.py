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
    # 积极响应
    ENTHUSIASTIC = "热情积极"           # 主动、热情
    PROFESSIONAL = "专业正式"           # 商务、正式
    CASUAL = "轻松随意"                 # 友好、随意
    CAUTIOUS = "谨慎确认"               # 需要确认/保留
    FOLLOW_UP = "跟进催促"              # 催促对方回复
    DEFERRED = "婉拒/推迟"             # 需要礼貌婉拒

    # 消极响应
    POLITE_REJECT = "礼貌婉拒"          # 友好拒绝
    REGRET_REJECT = "遗憾婉拒"          # 表示遗憾


# ============================================================
# 回复建议数据类
# ============================================================

@dataclass
class ReplyOption:
    """单个回复选项"""
    text: str                          # 回复文本
    score: float                       # 推荐分数 0-1
    scenario: str                      # 适用场景
    variables_filled: List[str] = field(default_factory=list)  # 已填充的变量

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "score": self.score,
            "scenario": self.scenario,
        }


@dataclass
class ReplyResult:
    """回复生成结果"""
    intent: str                        # 意图类型
    replies: List[ReplyOption]          # 回复选项列表
    best_reply: str                    # 最佳回复
    template_used: str = ""            # 使用的模板标识


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
            "text": "谢谢你的解答！关于这个岗位，我还有几个问题：1）团队规模和分工是怎样的？2）入职后是否有mentor带我熟悉业务？",
            "scenario": ReplyScenario.PROFESSIONAL.value,
            "score": 0.95,
        },
        {
            "text": "请问该岗位的KPI考核标准是什么？希望提前了解一下。",
            "scenario": ReplyScenario.CAUTIOUS.value,
            "score": 0.85,
        },
        {
            "text": "好的，谢谢介绍！请问这个岗位的晋升通道是怎样的？一年大概能调薪几次？",
            "scenario": ReplyScenario.PROFESSIONAL.value,
            "score": 0.88,
        },
        {
            "text": "了解了～请问加班频率如何？周末是否需要值班？",
            "scenario": ReplyScenario.CASUAL.value,
            "score": 0.80,
        },
        {
            "text": "感谢详细说明！我想再了解一下：该岗位需要出差吗？出差频率大概多少？",
            "scenario": ReplyScenario.CAUTIOUS.value,
            "score": 0.82,
        },
    ],

    IntentType.RESUME_REQUEST: [
        {
            "text": "好的，简历已发送，请查收！非常期待能进一步沟通。",
            "scenario": ReplyScenario.ENTHUSIASTIC.value,
            "score": 0.95,
        },
        {
            "text": "感谢！我的简历已发送，如果需要补充任何材料请告诉我。",
            "scenario": ReplyScenario.PROFESSIONAL.value,
            "score": 0.92,
        },
        {
            "text": "已发送简历，请查收～请问贵司的面试流程是怎样的？一般有几轮？",
            "scenario": ReplyScenario.CASUAL.value,
            "score": 0.88,
        },
        {
            "text": "好的，简历已补发，请留意查收。感谢您的关注，期待进一步交流！",
            "scenario": ReplyScenario.PROFESSIONAL.value,
            "score": 0.90,
        },
    ],

    IntentType.INTERVIEW_INVITE: [
        {
            "text": "非常感谢面试邀请！我这周基本都有空，请问什么时间比较方便？",
            "scenario": ReplyScenario.ENTHUSIASTIC.value,
            "score": 0.95,
        },
        {
            "text": "好的，我确认一下时间，稍后回复你具体可以的时间段。",
            "scenario": ReplyScenario.CAUTIOUS.value,
            "score": 0.85,
        },
        {
            "text": "感谢邀请！我对这次面试非常期待，请问是视频面试还是线下面试？",
            "scenario": ReplyScenario.PROFESSIONAL.value,
            "score": 0.92,
        },
        {
            "text": "没问题，下周三下午可以。请问面试地点在哪里？我好提前安排。",
            "scenario": ReplyScenario.PROFESSIONAL.value,
            "score": 0.88,
        },
        {
            "text": "好的，我查了一下日历，这周四周五下午都可以，方便的话约哪个时间？",
            "scenario": ReplyScenario.ENTHUSIASTIC.value,
            "score": 0.90,
        },
    ],

    IntentType.SALARY_NEGOTIATION: [
        {
            "text": "我的期望薪资是{salary}，考虑到我的经验和技能，相信可以为团队带来相应价值。",
            "scenario": ReplyScenario.PROFESSIONAL.value,
            "score": 0.95,
        },
        {
            "text": "谢谢你的诚意！我的期望是{salary}，不知道这个范围是否合适？",
            "scenario": ReplyScenario.CAUTIOUS.value,
            "score": 0.88,
        },
        {
            "text": "了解贵司的预算范围了。我的期望是{salary}，如果有一定弹性的话可以进一步沟通。",
            "scenario": ReplyScenario.PROFESSIONAL.value,
            "score": 0.90,
        },
        {
            "text": "感谢你坦诚沟通！基于市场行情和我的背景，期望薪资是{salary}，你觉得可行吗？",
            "scenario": ReplyScenario.PROFESSIONAL.value,
            "score": 0.92,
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

    # 默认占位符（当变量未提供时使用）
    DEFAULT_PLACEHOLDERS = {
        "{name}": "贵司",
        "{job_title}": "该岗位",
        "{company}": "贵司",
        "{salary}": "可商议",
        "{skills}": "相关技能",
    }

    def __init__(self, resume_json: dict = None, job_info: dict = None):
        """
        初始化变量填充器

        Args:
            resume_json: 简历 JSON 数据
            job_info: 职位信息 JSON 数据
        """
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

        # 可用变量映射
        variables = {
            # 简历数据
            "{name}": self._get_name(),
            "{skills}": self._get_skills(),
            # 职位数据
            "{job_title}": self._get_job_title(),
            "{company}": self._get_company(),
            "{salary}": self._get_salary(),
        }

        # 填充每个变量
        for placeholder, value in variables.items():
            if placeholder in result:
                if value:
                    result = result.replace(placeholder, value)
                    filled_vars.append(placeholder)
                else:
                    # 使用默认值
                    default_val = self.DEFAULT_PLACEHOLDERS.get(placeholder, "")
                    result = result.replace(placeholder, default_val)

        return result, filled_vars

    def _get_name(self) -> str:
        """从简历获取姓名"""
        # 尝试各种可能的字段名
        for key in ["name", "姓名", "candidate_name"]:
            if key in self.resume:
                return str(self.resume[key])
        return ""

    def _get_skills(self) -> str:
        """从简历获取技能列表"""
        skills = self.resume.get("skills", []) or self.resume.get("技能", [])
        if isinstance(skills, list):
            return "、".join(skills[:5])  # 最多5个技能
        return str(skills) if skills else ""

    def _get_job_title(self) -> str:
        """从职位信息获取岗位名称"""
        for key in ["title", "job_title", "position", "岗位", "职位"]:
            if key in self.job:
                return str(self.job[key])
        return ""

    def _get_company(self) -> str:
        """从职位信息获取公司名称"""
        for key in ["company", "公司", "company_name"]:
            if key in self.job:
                return str(self.job[key])
        return ""

    def _get_salary(self) -> str:
        """从职位信息或简历获取薪资期望"""
        # 先从简历获取期望薪资
        for key in ["expected_salary", "期望薪资", "salary_expectation", "salary"]:
            if key in self.resume:
                return str(self.resume[key])

        # 再从职位信息获取薪资范围
        for key in ["salary_range", "薪资范围", "salary", "pay_range"]:
            if key in self.job:
                return str(self.job[key])

        return ""


# ============================================================
# ReplyGenerator 主类
# ============================================================

class ReplyGenerator:
    """
    HR 回复建议生成器
    基于意图分类结果，生成针对性的回复建议
    支持批量生成、智能填充、评分排序
    """

    def __init__(
        self,
        resume_json: dict = None,
        job_info: dict = None,
        llm_client: Callable = None,
        llm_model: str = "gpt-4o",
    ):
        """
        初始化回复生成器

        Args:
            resume_json: 候选人简历数据（用于填充变量）
            job_info: 职位信息数据（用于填充变量）
            llm_client: LLM 客户端（用于增强回复生成）
            llm_model: LLM 模型名
        """
        self.resume = resume_json or {}
        self.job = job_info or {}
        self.llm = llm_client
        self.llm_model = llm_model
        self.filler = VariableFiller(self.resume, self.job)

        # 按意图类型索引模板（缓存）
        self._template_index = REPLY_TEMPLATES

    # --------------------------------------------------------
    # 主生成入口
    # --------------------------------------------------------

    def generate(
        self,
        intent_result: IntentResult,
        count: int = 3,
        context: dict = None,
    ) -> ReplyResult:
        """
        同步生成回复建议

        Args:
            intent_result: 意图分类结果
            count: 返回的回复数量
            context: 额外上下文（如对话历史）

        Returns:
            ReplyResult: 回复生成结果
        """
        intent = intent_result.intent
        confidence = intent_result.confidence

        # 获取该意图的模板
        templates = self._template_index.get(intent, self._template_index[IntentType.OTHER])

        # 填充变量并计算分数
        replies = []
        for tmpl in templates:
            text, filled_vars = self.filler.fill(tmpl["text"])

            # 根据置信度和场景调整分数
            adjusted_score = self._adjust_score(
                base_score=tmpl["score"],
                intent_confidence=confidence,
                context=context,
                scenario=tmpl["scenario"],
            )

            replies.append(ReplyOption(
                text=text,
                score=adjusted_score,
                scenario=tmpl["scenario"],
                variables_filled=filled_vars,
            ))

        # 按分数排序
        replies.sort(key=lambda x: x.score, reverse=True)

        # 取 top N
        top_replies = replies[:count]

        # 选择最佳回复（分数最高的）
        best_reply = top_replies[0].text if top_replies else ""

        return ReplyResult(
            intent=intent.value,
            replies=[r.to_dict() for r in top_replies],
            best_reply=best_reply,
            template_used=intent.value,
        )

    async def generate_async(
        self,
        intent_result: IntentResult,
        count: int = 3,
        context: dict = None,
    ) -> ReplyResult:
        """
        异步生成回复建议（LLM 增强模式）

        Args:
            intent_result: 意图分类结果
            count: 返回的回复数量
            context: 额外上下文

        Returns:
            ReplyResult: 回复生成结果
        """
        # 先用规则引擎快速生成
        rule_result = self.generate(intent_result, count, context)

        # 如果 LLM 可用且意图置信度较高，尝试 LLM 增强
        if self.llm is not None and intent_result.confidence >= 0.7:
            try:
                llm_result = await self._enhance_with_llm(intent_result, rule_result)
                if llm_result:
                    return llm_result
            except Exception:
                pass

        return rule_result

    # --------------------------------------------------------
    # 便捷方法
    # --------------------------------------------------------

    def get_best_reply(self, intent_result: IntentResult) -> str:
        """
        获取最佳回复（单条）

        Args:
            intent_result: 意图分类结果

        Returns:
            str: 最佳回复文本
        """
        result = self.generate(intent_result, count=1)
        return result.best_reply

    def generate_for_message(self, message: str, count: int = 3) -> ReplyResult:
        """
        便捷方法：对消息同时做意图分类和回复生成

        Args:
            message: HR 消息文本
            count: 返回的回复数量

        Returns:
            ReplyResult: 回复生成结果
        """
        from .intent_classifier import IntentClassifier

        classifier = IntentClassifier()

        intent_result = classifier.classify(message)

        return self.generate(intent_result, count)

    # --------------------------------------------------------
    # 内部方法
    # --------------------------------------------------------

    def _adjust_score(
        self,
        base_score: float,
        intent_confidence: float,
        context: dict,
        scenario: str,
    ) -> float:
        """
        根据上下文调整回复分数

        Args:
            base_score: 基础分数（模板预设）
            intent_confidence: 意图分类置信度
            context: 额外上下文
            scenario: 场景标签

        Returns:
            float: 调整后的分数
        """
        adjusted = base_score

        # 意图置信度高 -> 提高分数
        if intent_confidence >= 0.8:
            adjusted += 0.05
        elif intent_confidence < 0.5:
            adjusted -= 0.1

        # 根据场景标签调整
        # 积极场景在积极意图时加权
        if context:
            is_positive_intent = context.get("is_positive", False)
            if scenario == ReplyScenario.ENTHUSIASTIC.value and is_positive_intent:
                adjusted += 0.08
            elif scenario == ReplyScenario.REGRET_REJECT.value and not is_positive_intent:
                adjusted += 0.05

        # 确保分数在 0-1 范围内
        return max(0.0, min(1.0, adjusted))

    async def _enhance_with_llm(
        self,
        intent_result: IntentResult,
        rule_result: ReplyResult,
    ) -> Optional[ReplyResult]:
        """
        使用 LLM 增强回复质量

        Args:
            intent_result: 意图分类结果
            rule_result: 规则引擎生成的结果

        Returns:
            Optional[ReplyResult]: LLM 增强后的结果，失败时返回 None
        """
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

            # LLM 生成的回复替换最佳回复
            enhanced_replies = rule_result.replies.copy()
            if enhanced_replies and isinstance(response, str) and response.strip():
                enhanced_replies[0]["text"] = response.strip()
                enhanced_replies[0]["score"] = min(enhanced_replies[0]["score"] + 0.1, 0.99)

            return ReplyResult(
                intent=rule_result.intent,
                replies=enhanced_replies,
                best_reply=response.strip() if isinstance(response, str) else rule_result.best_reply,
                template_used=f"{rule_result.template_used}_llm_enhanced",
            )
        except Exception:
            return None

    # --------------------------------------------------------
    # 模板管理
    # --------------------------------------------------------

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
# 便捷函数
# ============================================================

_default_generator: Optional[ReplyGenerator] = None


def get_generator(
    resume_json: dict = None,
    job_info: dict = None,
    llm_client = None,
) -> ReplyGenerator:
    """获取默认生成器实例"""
    global _default_generator
    if _default_generator is None:
        _default_generator = ReplyGenerator(
            resume_json=resume_json,
            job_info=job_info,
            llm_client=llm_client,
        )
    return _default_generator


def generate_reply(
    intent_result: IntentResult,
    count: int = 3,
    resume_json: dict = None,
    job_info: dict = None,
) -> ReplyResult:
    """便捷函数：使用默认生成器生成回复"""
    generator = get_generator(resume_json, job_info)
    return generator.generate(intent_result, count)


def get_best_reply(
    intent_result: IntentResult,
    resume_json: dict = None,
    job_info: dict = None,
) -> str:
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

    # 测试数据
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

    # 初始化生成器
    generator = ReplyGenerator(
        resume_json=sample_resume,
        job_info=sample_job,
    )

    # 测试用例
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
        # 先分类
        intent_result = classifier.classify(msg)

        # 再生成回复
        reply_result = generator.generate(intent_result, count=3)

        print(f"[{desc}] {msg[:30]}...")
        print(f"  意图: {intent_result.intent.value} ({intent_result.confidence:.0%})")
        print(f"  最佳回复: {reply_result.best_reply[:40]}...")
        print(f"  候选回复数: {len(reply_result.replies)}")
        print()

    print("=" * 60)
    print("测试完成")
    print("=" * 60)