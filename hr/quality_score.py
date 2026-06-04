"""
hr/quality_score.py
HR 回复质量评分器
评估回复建议的专业度、匹配度、完整性、礼貌性
"""
import re
from dataclasses import dataclass
from typing import List, Dict, Optional

# ============================================================
# 评分维度常量
# ============================================================

# 专业度关键词
PROFESSIONAL_KEYWORDS = [
    "岗位", "职位", "薪资", "薪酬", "福利", "面试", "入职",
    "团队", "部门", "KPI", "OKR", "晋升", "发展", "培训",
    "职责", "要求", "经验", "技能", "匹配", "合适",
]

# 匹配度关键词
MATCH_KEYWORDS = [
    "贵司", "公司", "团队", "产品", "业务", "岗位", "职位",
    "背景", "经验", "技能", "匹配",
]

# 礼貌性关键词
POLITE_KEYWORDS = [
    "您好", "谢谢", "感谢", "打扰", "方便", "请问", "麻烦",
    "期待", "希望", "渴望", "荣幸", "抱歉",
]

# 完整性要素
COMPLETENESS_ITEMS = [
    ("称呼", ["您好", "你好", "Hi", "Hello", "嗨"]),
    ("署名", ["张", "李", "王", "刘", "陈", "简历", "应聘"]),
    ("期待动作", ["期待", "希望", "请问", "方便", "回复"]),
]


# ============================================================
# 评分结果数据类
# ============================================================

@dataclass
class ScoreResult:
    """评分结果"""
    overall: float          # 综合得分 0-100
    professional: float     # 专业度
    match: float            # 匹配度
    completeness: float     # 完整性
    politeness: float       # 礼貌性
    suggestions: List[str]  # 改进建议
    strengths: List[str]    # 优点
    intent_hint: str        # 意图提示（参考）


# ============================================================
# ReplyQualityScore 主类
# ============================================================

class ReplyQualityScore:
    """
    HR 回复质量评分器

    无 LLM 时使用规则评分，有 LLM 时可增强评估
    """

    def __init__(self, llm_client=None):
        """
        初始化评分器

        Args:
            llm_client: LLM 客户端（可选，有则增强评分）
        """
        self.llm = llm_client

    def score(self, reply_text: str, context: dict = None) -> ScoreResult:
        """
        评估回复质量

        Args:
            reply_text: 回复文本
            context: 上下文信息（可选）
                    {
                        'intent': str,    # 意图类型
                        'job_title': str, # 职位名称
                        'company': str,    # 公司名称
                    }

        Returns:
            ScoreResult: 评分结果
        """
        if not reply_text or not reply_text.strip():
            return ScoreResult(
                overall=0, professional=0, match=0,
                completeness=0, politeness=0,
                suggestions=["回复内容为空"],
                strengths=[],
                intent_hint=""
            )

        # 各维度评分
        prof = self._score_professional(reply_text)
        match = self._score_match(reply_text, context)
        comp = self._score_completeness(reply_text)
        poli = self._score_politeness(reply_text)

        # 综合得分（加权平均）
        overall = prof * 0.3 + match * 0.3 + comp * 0.2 + poli * 0.2

        # 生成建议
        suggestions = self._generate_suggestions(reply_text, prof, match, comp, poli)
        strengths = self._extract_strengths(reply_text, prof, match, comp, poli)

        # 意图提示
        intent_hint = context.get('intent', '') if context else ''

        return ScoreResult(
            overall=round(overall, 1),
            professional=round(prof, 1),
            match=round(match, 1),
            completeness=round(comp, 1),
            politeness=round(poli, 1),
            suggestions=suggestions,
            strengths=strengths,
            intent_hint=intent_hint
        )

    # --------------------------------------------------------
    # 各维度评分
    # --------------------------------------------------------

    def _score_professional(self, text: str) -> float:
        """专业度评分"""
        score = 0

        # 包含专业术语
        text_lower = text.lower()
        prof_count = sum(1 for kw in PROFESSIONAL_KEYWORDS if kw in text_lower)
        if prof_count >= 3:
            score += 40
        elif prof_count >= 1:
            score += prof_count * 15

        # 长度适中（30-200字符为佳）
        length = len(text)
        if 30 <= length <= 200:
            score += 20
        elif length > 200:
            score += 10

        # 无错别字/语法错误（简单检测）
        if len(text) > 10:
            # 检查是否有明显的语法错误特征
            has_error_markers = any(m in text for m in ["。。", "，，", "。。", "!!", "??"])
            if not has_error_markers:
                score += 10

        # 结构化程度（有换行/序号）
        if "\n" in text or re.search(r"^\d+[.、]", text, re.MULTILINE):
            score += 10

        return min(score, 100)

    def _score_match(self, text: str, context: dict = None) -> float:
        """匹配度评分"""
        score = 0

        # 提及公司/职位
        if context:
            company = context.get('company', '')
            job_title = context.get('job_title', '')

            if company and company in text:
                score += 25
            elif any(name in text for name in ["贵司", "贵公司", "公司"]):
                score += 15

            if job_title and job_title in text:
                score += 25
            elif any(title in text for title in ["岗位", "职位", "工作"]):
                score += 15
        else:
            # 无 context 时检查通用匹配词
            match_count = sum(1 for kw in MATCH_KEYWORDS if kw in text)
            score += min(match_count * 10, 40)

        # 包含量化信息（如薪资范围）
        if re.search(r'\d+[Kk万]', text):
            score += 10

        return min(score, 100)

    def _score_completeness(self, text: str) -> float:
        """完整性评分"""
        score = 0

        # 检查各完整性要素
        for item_name, keywords in COMPLETENESS_ITEMS:
            if any(kw in text for kw in keywords):
                score += 20
            else:
                # 缺少该要素的提示
                pass

        # 有明确的结尾（标点、期待动作）
        text_stripped = text.strip()
        if text_stripped[-1] in "。！？.":
            score += 10

        # 字数在合理范围（不能太短）
        if len(text_stripped) >= 20:
            score += 10

        return min(score, 100)

    def _score_politeness(self, text: str) -> float:
        """礼貌性评分"""
        score = 0

        text_lower = text.lower()

        # 敬语/礼貌词
        polite_count = sum(1 for kw in POLITE_KEYWORDS if kw in text_lower)
        score += min(polite_count * 15, 45)

        # 没有不礼貌的语气
        rude_markers = ["滚", "不要", "别来", "烦", "没空", "算了"]
        has_rude = any(m in text_lower for m in rude_markers)
        if not has_rude:
            score += 30
        else:
            score -= 30

        return max(0, min(score, 100))

    # --------------------------------------------------------
    # 建议生成
    # --------------------------------------------------------

    def _generate_suggestions(
        self,
        text: str,
        prof: float,
        match: float,
        comp: float,
        poli: float
    ) -> List[str]:
        """生成改进建议"""
        suggestions = []

        if prof < 60:
            suggestions.append("建议加入更多职位相关的专业术语（如岗位职责、技能要求等）")
        if match < 60:
            suggestions.append("建议提及公司名称或职位名称，提高相关性")
        if comp < 60:
            suggestions.append("建议添加称呼（您好）和署名，提高完整性")
        if poli < 60:
            suggestions.append("建议使用礼貌用语（您好、谢谢、期待）")

        if len(text) < 20:
            suggestions.append("回复内容过短，建议适当扩展")

        if not suggestions:
            suggestions.append("整体表现良好，可以继续保持")

        return suggestions

    def _extract_strengths(
        self,
        text: str,
        prof: float,
        match: float,
        comp: float,
        poli: float
    ) -> List[str]:
        """提取优点"""
        strengths = []

        if prof >= 70:
            strengths.append("使用了专业术语，表达专业")
        if match >= 70:
            strengths.append("内容与目标职位/公司匹配度高")
        if comp >= 70:
            strengths.append("回复结构完整，包含必要要素")
        if poli >= 70:
            strengths.append("语气礼貌，用词得当")

        return strengths

    # --------------------------------------------------------
    # 便捷方法
    # --------------------------------------------------------

    def suggest_improvements(self, reply_text: str, intent: str = "") -> List[str]:
        """针对意图类型给出改进建议（简化版）"""
        result = self.score(reply_text, {'intent': intent})
        return result.suggestions

    def compare(self, replies: List[str], context: dict = None) -> List[tuple]:
        """
        对比多个回复，返回排序后的 (index, score) 列表

        Args:
            replies: 回复列表
            context: 上下文信息

        Returns:
            List[tuple]: [(index, overall_score), ...]，按得分降序
        """
        results = []
        for i, reply in enumerate(replies):
            score_result = self.score(reply, context)
            results.append((i, score_result.overall, score_result))

        # 按得分降序
        results.sort(key=lambda x: x[1], reverse=True)
        return [(i, score) for i, score, _ in results]


# ============================================================
# 便捷函数
# ============================================================

_default_scorer: Optional[ReplyQualityScore] = None


def get_scorer(llm_client=None) -> ReplyQualityScore:
    """获取默认评分器实例"""
    global _default_scorer
    if _default_scorer is None:
        _default_scorer = ReplyQualityScore(llm_client=llm_client)
    return _default_scorer


def score_reply(reply_text: str, context: dict = None) -> ScoreResult:
    """便捷函数：使用默认评分器评分"""
    return get_scorer().score(reply_text, context)


# ============================================================
# 测试入口
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("HR 回复质量评分器测试")
    print("=" * 60)

    scorer = ReplyQualityScore()

    test_cases = [
        {
            "text": "您好！看到贵司正在招聘Python后端工程师，我对贵司的产品非常感兴趣，希望能进一步沟通，谢谢！",
            "context": {"intent": "greeting", "job_title": "Python后端工程师", "company": "XX科技"}
        },
        {
            "text": "在吗？",
            "context": {"intent": "greeting"}
        },
        {
            "text": "您好，感谢您的回复。关于薪资，我的期望是25-30K，不知道是否合适？期待您的反馈。",
            "context": {"intent": "salary_negotiation", "job_title": "后端工程师"}
        },
        {
            "text": "可以",
            "context": {"intent": "other"}
        },
    ]

    print()
    for i, case in enumerate(test_cases, 1):
        result = scorer.score(case["text"], case["context"])
        print(f"[{i}] 意图: {case['context'].get('intent', 'unknown')}")
        print(f"    文本: {case['text'][:50]}...")
        print(f"    评分: overall={result.overall}, prof={result.professional}, match={result.match}, comp={result.completeness}, poli={result.politeness}")
        if result.suggestions:
            print(f"    建议: {result.suggestions[0]}")
        print()

    print("=" * 60)
    print("对比测试")
    print("=" * 60)

    replies = [
        "您好，感谢您的联系，期待进一步沟通",
        "在吗",
        "您好！看到贵司招聘Python工程师，我有5年经验，熟悉Django/FastAPI，期待面谈",
    ]

    ranked = scorer.compare(replies, {"job_title": "Python工程师"})
    print(f"排名: {ranked}")
    for idx, score in ranked:
        print(f"  #{idx+1}: {score}分 - {replies[idx][:40]}...")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)