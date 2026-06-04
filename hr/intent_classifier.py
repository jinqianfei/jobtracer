"""
hr/intent_classifier.py
HR 意图分类引擎 - 对 HR 回复进行意图识别和分类
支持规则引擎（无 LLM fallback）和 LLM 增强模式
"""
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Callable, Any

# ============================================================
# 意图类型枚举
# ============================================================

class IntentType(Enum):
    """HR 消息意图类型"""
    GREETING = "greeting"               # 主动打招呼
    JD_INQUIRY = "jd_inquiry"           # 询问职位详情
    RESUME_REQUEST = "resume_request"    # 要求发送简历
    INTERVIEW_INVITE = "interview_invite" # 面试邀请
    SALARY_NEGOTIATION = "salary_negotiation" # 薪资沟通
    REJECTION = "rejection"             # 不匹配/婉拒
    FOLLOW_UP = "follow_up"             # 催促回复
    INFO_CONFIRM = "info_confirm"       # 信息确认
    POSITIVE = "positive"               # 积极反馈（感兴趣）
    NEGATIVE = "negative"               # 消极反馈
    OTHER = "other"                     # 其他


# ============================================================
# 意图结果数据类
# ============================================================

@dataclass
class IntentResult:
    """意图分类结果"""
    intent: IntentType
    confidence: float          # 置信度 0-1
    reasoning: str            # 判断依据
    keywords: List[str]       # 匹配的关键词
    raw_message: str = ""     # 原始消息（用于调试）
    alternatives: List[tuple] = field(default_factory=list)  # [(intent, confidence), ...]


# ============================================================
# 关键词规则库
# ============================================================

# 意图 -> 关键词映射（多对一）
INTENT_PATTERNS = {
    IntentType.GREETING: {
        "keywords": [
            "你好", "在吗", "您好", "hi", "hello", "嗨", "hey",
            "打扰", "想联系", "有空", "最近在", "看到你", "搜到",
        ],
        "weight": 1.0,
    },
    IntentType.JD_INQUIRY: {
        "keywords": [
            "职位", "岗位", "工作内容", "做什么", "具体做", "职责",
            "要求", "需要什么", "加班", "出差", "福利", "休息",
            "假期", "发展", "晋升", "团队", "部门", "领导",
        ],
        "weight": 1.0,
    },
    IntentType.RESUME_REQUEST: {
        "keywords": [
            "简历", "发一下", "发给我", "发简历", "简历发", "看简历",
            "简历已", "简历查", "没收到简历", "补发", "再发",
        ],
        "weight": 1.2,  # 高权重
    },
    IntentType.INTERVIEW_INVITE: {
        "keywords": [
            "面试", "面谈", "沟通一下", "当面聊", "约一下", "约时间",
            "什么时候方便", "这周", "下周", "哪天", "开个会",
            "电话", "视频", "线下面", "面试时间", "面试地点",
        ],
        "weight": 1.2,
    },
    IntentType.SALARY_NEGOTIATION: {
        "keywords": [
            "薪资", "工资", "薪酬", "待遇", "报酬", "package", "salary",
            "期望", "月薪", "年薪", "税前", "税后", "到手",
            "可谈", "可以给", "可以接受", "预算", "范围",
        ],
        "weight": 1.3,
    },
    IntentType.REJECTION: {
        "keywords": [
            "不太合适", "不合适", "可能不太", "暂时没有", "没有hc",
            "停止招聘", "已招到", "简历库", "放入", "不合适",
            "不太匹配", "不匹配", "不符合", "条件不满足",
        ],
        "weight": 1.5,
    },
    IntentType.FOLLOW_UP: {
        "keywords": [
            "还没", "没有回复", "方便回复", "尽快", "什么时候",
            "还在考虑", "考虑好了吗", "回复一下", "给我消息",
            "联系我", "回复我", "给我回复", "等消息",
        ],
        "weight": 1.0,
    },
    IntentType.INFO_CONFIRM: {
        "keywords": [
            "确认", "核实", "核实一下", "是否", "是不是", "有没有",
            "告诉我", "问一下", "想确认", "需要确认", "核对",
        ],
        "weight": 1.0,
    },
    IntentType.POSITIVE: {
        "keywords": [
            "感兴趣", "很感兴趣", "非常感兴趣", "有兴趣", "看中",
            "觉得不错", "很不错", "很好", "符合", "匹配",
            "很合适", "非常合适", "合适", "推荐", "靠谱",
        ],
        "weight": 1.2,
    },
    IntentType.NEGATIVE: {
        "keywords": [
            "算了", "不用了", "算了不用", "暂时不需要", "不需要",
            "不考虑", "没意向", "不需要了", "不考虑了",
        ],
        "weight": 1.3,
    },
}

# 正则模式（用于更精确的匹配）
INTENT_REGEX = {
    IntentType.INTERVIEW_INVITE: [
        r"面试",
        r"约[你我他]?[何时哪号天]",
        r"开个会",
        r"电话沟通",
        r"视频面",
    ],
    IntentType.SALARY_NEGOTIATION: [
        r"期望薪资?[:：]?\s*[\d,，、]+",
        r"月薪?\s*[\d,，、]+",
        r"年薪?\s*[\d,，、]+",
        r"可以?给?[\d,，、]+",
    ],
    IntentType.REJECTION: [
        r"不太合适",
        r"不合适",
        r"没有hc",
        r"已招到",
    ],
    IntentType.RESUME_REQUEST: [
        r"发[个份]?简历",
        r"简历发",
        r"没收到简历",
    ],
}

# 组合模式（多关键词同时出现增加置信度）
COMBO_PATTERNS = [
    # (关键词组合, 意图, 置信度加成)
    (["面试", "时间"], IntentType.INTERVIEW_INVITE, 0.3),
    (["面试", "地点"], IntentType.INTERVIEW_INVITE, 0.3),
    (["简历", "发"], IntentType.RESUME_REQUEST, 0.3),
    (["简历", "看一下"], IntentType.RESUME_REQUEST, 0.3),
    (["薪资", "可以"], IntentType.SALARY_NEGOTIATION, 0.3),
    (["期望", "多少"], IntentType.SALARY_NEGOTIATION, 0.3),
    (["你好", "在吗"], IntentType.GREETING, 0.2),
    (["感兴趣", "职位"], IntentType.POSITIVE, 0.3),
]


# ============================================================
# IntentClassifier 主类
# ============================================================

class IntentClassifier:
    """
    HR 意图分类器
    支持基于规则的分类（无需 LLM）和 LLM 增强模式
    """

    def __init__(
        self,
        llm_client: Callable = None,
        llm_model: str = "gpt-4o",
        min_confidence: float = 0.3
    ):
        """
        初始化意图分类器

        Args:
            llm_client: LLM 客户端（如有则使用 LLM 增强）
            llm_model: LLM 模型名
            min_confidence: 最低置信度阈值，低于此值返回 OTHER
        """
        self.llm = llm_client
        self.llm_model = llm_model
        self.min_confidence = min_confidence

    # --------------------------------------------------------
    # 主分类入口
    # --------------------------------------------------------

    def classify(self, message: str) -> IntentResult:
        """
        同步分类（基于规则引擎）

        Args:
            message: HR 消息文本

        Returns:
            IntentResult: 分类结果
        """
        if not message or not message.strip():
            return IntentResult(
                intent=IntentType.OTHER,
                confidence=0.0,
                reasoning="空消息",
                keywords=[],
                raw_message=message
            )

        message_clean = message.strip()

        # 1. 正则模式匹配（最高优先级）
        for intent, patterns in INTENT_REGEX.items():
            for pattern in patterns:
                if re.search(pattern, message_clean):
                    return IntentResult(
                        intent=intent,
                        confidence=0.9,
                        reasoning=f"正则匹配: {pattern}",
                        keywords=[pattern],
                        raw_message=message_clean
                    )

        # 2. 组合模式匹配（多关键词加成）
        combo_boost = {}
        for keywords, intent, boost in COMBO_PATTERNS:
            if all(kw in message_clean for kw in keywords):
                combo_boost[intent] = combo_boost.get(intent, 0) + boost

        # 3. 关键词权重匹配
        intent_scores: dict = {}
        intent_keywords: dict = {}

        for intent, config in INTENT_PATTERNS.items():
            keywords = config["keywords"]
            weight = config["weight"]
            matched = [kw for kw in keywords if kw in message_clean]
            if matched:
                score = len(matched) * weight
                intent_scores[intent] = intent_scores.get(intent, 0) + score
                intent_keywords[intent] = matched

        # 应用组合加成
        for intent, boost in combo_boost.items():
            intent_scores[intent] = intent_scores.get(intent, 0) + boost

        # 4. 找最佳匹配
        if not intent_scores:
            return IntentResult(
                intent=IntentType.OTHER,
                confidence=0.2,
                reasoning="无关键词匹配",
                keywords=[],
                raw_message=message_clean
            )

        # 计算置信度并归一化
        best_intent = max(intent_scores.items(), key=lambda x: x[1])
        intent = best_intent[0]
        raw_score = best_intent[1]

        # 归一化到 0-1（基于经验阈值）
        if raw_score >= 3:
            confidence = 0.95
        elif raw_score >= 2:
            confidence = 0.8
        elif raw_score >= 1.5:
            confidence = 0.65
        elif raw_score >= 1:
            confidence = 0.5
        else:
            confidence = 0.35

        # 如果有关键词匹配加成
        matched_count = len(intent_keywords.get(intent, []))
        if matched_count >= 3:
            confidence = min(confidence + 0.1, 0.99)

        # 置信度低于阈值则返回 OTHER
        if confidence < self.min_confidence:
            return IntentResult(
                intent=IntentType.OTHER,
                confidence=confidence,
                reasoning="置信度低于阈值",
                keywords=intent_keywords.get(intent, []),
                raw_message=message_clean
            )

        # 构建替代选项（top 3）
        alternatives = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)[:3]
        alternatives = [(i, s / raw_score * confidence) for i, s in alternatives[:3]]

        reasoning = f"匹配到 {matched_count} 个关键词: {intent_keywords.get(intent, [])}"

        return IntentResult(
            intent=intent,
            confidence=confidence,
            reasoning=reasoning,
            keywords=intent_keywords.get(intent, []),
            raw_message=message_clean,
            alternatives=alternatives
        )

    async def classify_async(self, message: str) -> IntentResult:
        """
        异步分类入口（LLM 增强模式）

        Args:
            message: HR 消息文本

        Returns:
            IntentResult: 分类结果
        """
        # 规则引擎快速分类
        rule_result = self.classify(message)

        # 如果 LLM 可用且置信度 < 0.8，尝试 LLM 增强
        if self.llm is not None and rule_result.confidence < 0.8:
            try:
                llm_result = await self._classify_with_llm(message)
                # LLM 结果置信度高则采纳
                if llm_result.confidence > rule_result.confidence:
                    return llm_result
            except Exception as e:
                # LLM 失败时 fallback 到规则结果
                pass

        return rule_result

    # --------------------------------------------------------
    # LLM 增强
    # --------------------------------------------------------

    async def _classify_with_llm(self, message: str) -> IntentResult:
        """使用 LLM 进行意图分类"""
        prompt = f"""你是一个 HR 消息意图分类器。请分析以下 HR 消息，判断其意图。

意图类型：
- greeting: 主动打招呼（"你好"、"在吗"）
- jd_inquiry: 询问职位详情
- resume_request: 要求发送简历
- interview_invite: 面试邀请
- salary_negotiation: 薪资沟通
- rejection: 不匹配/婉拒
- follow_up: 催促回复
- info_confirm: 信息确认
- positive: 积极反馈（感兴趣）
- negative: 消极反馈
- other: 其他

HR 消息：{message}

请以 JSON 格式返回：
{{"intent": "意图类型", "confidence": 0.0-1.0, "reasoning": "判断依据"}}
"""

        try:
            response = await self.llm.generate(prompt, schema="json")
            data = response if isinstance(response, dict) else {}
            if isinstance(response, str):
                import json
                data = json.loads(response)

            intent_str = data.get("intent", "other")
            confidence = float(data.get("confidence", 0.5))
            reasoning = data.get("reasoning", "")

            # 转换字符串到枚举
            try:
                intent = IntentType(intent_str)
            except ValueError:
                intent = IntentType.OTHER

            return IntentResult(
                intent=intent,
                confidence=confidence,
                reasoning=f"[LLM] {reasoning}",
                keywords=[],
                raw_message=message
            )
        except Exception as e:
            raise Exception(f"LLM classification failed: {e}")

    # --------------------------------------------------------
    # 便捷方法
    # --------------------------------------------------------

    def get_confidence(self) -> float:
        """返回最近一次分类的置信度（需配合 classify 使用）"""
        return getattr(self, "_last_confidence", 0.0)

    def get_reasoning(self) -> str:
        """返回最近一次分类的依据"""
        return getattr(self, "_last_reasoning", "")


# ============================================================
# 便捷函数
# ============================================================

_default_classifier: Optional[IntentClassifier] = None


def get_classifier(llm_client=None) -> IntentClassifier:
    """获取默认分类器实例"""
    global _default_classifier
    if _default_classifier is None:
        _default_classifier = IntentClassifier(llm_client=llm_client)
    return _default_classifier


def classify(message: str) -> IntentResult:
    """便捷函数：使用默认分类器分类"""
    return get_classifier().classify(message)


# ============================================================
# 测试入口
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("HR 意图分类器测试")
    print("=" * 60)

    classifier = IntentClassifier()

    test_messages = [
        # 打招呼
        "你好，在吗？看到你的简历，想了解一下",
        "你好呀，打扰一下",

        # JD 询问
        "这个岗位主要做什么？需要加班吗？",
        "请问这个职位的工作内容和招聘要求是什么",

        # 简历请求
        "可以发一下你的简历吗？",
        "没收到你的简历，能再发一下吗？",

        # 面试邀请
        "你的简历我们觉得不错，想约个时间面试",
        "什么时候方便来公司面谈一下？",
        "这周三下午可以吗？我们视频面试",

        # 薪资沟通
        "你期望的薪资是多少？",
        "我们这边预算可以给到 25-30K",
        "月薪 2 万可以接受吗？",

        # 婉拒
        "不好意思，你的经验可能不太匹配这个岗位",
        "暂时没有 hc 了，简历我们会放入人才库",
        "不太合适，感谢投递",

        # 催促
        "还没收到你的回复，方便尽快回复一下吗？",
        "考虑好了吗？什么时候可以入职？",

        # 积极
        "很感兴趣，想进一步了解一下",
        "你的背景很不错，下周约个时间聊聊？",

        # 其他
        "好的，收到",
        "稍等，我查一下",
    ]

    print()
    for msg in test_messages:
        result = classifier.classify(msg)
        confidence_emoji = "🟢" if result.confidence >= 0.8 else "🟡" if result.confidence >= 0.5 else "🔴"
        print(f"[{confidence_emoji}] {result.intent.value:20s} ({result.confidence:.0%}) | {msg[:40]}")
        if result.confidence < 0.8:
            print(f"    reasoning: {result.reasoning}")

    print()
    print("=" * 60)
    print("测试完成")
    print("=" * 60)