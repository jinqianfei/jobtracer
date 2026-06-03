"""STAR 法则面试指导
提供 STAR 框架模板、高频问题参考答案、自我练习模式
"""
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class STARAnswer:
    situation: str      # 背景：当时的情况是什么
    task: str           # 任务：你的职责是什么
    action: str         # 行动：你具体做了什么
    result: str         # 结果：最终成果如何（带量化数据）
    
    def to_markdown(self) -> str:
        return f"""
## Situation（背景）
{self.situation}

## Task（任务）
{self.task}

## Action（行动）
{self.action}

## Result（结果）
{self.result}
"""


class STARCoach:
    """STAR 法则指导教练"""
    
    # 高频面题 → STAR 框架答案示例
    STAR_EXAMPLES = {
        "供应链优化": {
            "question": "请描述你如何优化某个供应链环节",
            "star": STARAnswer(
                situation="在富士康灯塔工厂项目中，生产线计划依赖人工排程，4小时才能出一版计划",
                task="我作为产品负责人，需要将计划时间缩短 50% 以上",
                action="1. 调研各产线约束条件（换线时间、模具产能）；2. 引入运筹优化算法（IP 模型）；3. 设计可视化排程看板；4. 迭代优化算法直至收敛",
                result="计划时间从 4 小时缩短至 15 分钟，产能利用率提升至 95%，获评灯塔工厂标杆"
            )
        },
        "跨部门协作": {
            "question": "请描述一次跨部门协作的经历",
            "star": STARAnswer(
                situation="蜀海供应链项目中，WMS/TMS/ERP 三个系统数据不通，客服每天花 2 小时查单",
                task="我需要协调研发、运维、第三方供应商，推动数据贯通",
                action="1. 召集三方会议对齐接口规范；2. 制定里程碑和责任人；3. 每周跟踪进度；4. 建立数据校验机制",
                result="三个系统数据贯通，客服查询时间从 2 小时降至 10 分钟，跨部门协作成为公司内部推广案例"
            )
        }
    }
    
    def get_framework(self) -> str:
        """返回 STAR 框架说明"""
        return """
# STAR 法则框架

## Situation（背景）
- 什么场景下？
- 当时的背景和环境是什么？
- 有哪些关键约束？

## Task（任务）
- 你的角色是什么？
- 需要达成什么目标？
- 有什么 deadline/ KPI？

## Action（行动）
- 你具体做了哪些事？
- 为什么这么做？
- 克服了哪些困难？

## Result（结果）
- 最终成果如何？
- **用数据说话**（效率提升 X%、成本降低 Y%）
- 学到了什么？
"""
    
    def suggest_questions(self, resume_json: dict) -> List[str]:
        """根据简历推荐可能的 STAR 面试题
        
        Args:
            resume_json: 简历 JSON 数据
            
        Returns:
            List[str]: 推荐的面试题列表
        """
        suggested = []
        
        work_exp = resume_json.get("work_experience", [])
        
        for exp in work_exp:
            company = exp.get("company", "")
            position = exp.get("position", "")
            achievements = exp.get("achievements", [])
            
            # 基于量化成果生成问题
            for ach in achievements:
                if any(k in ach for k in ["提升", "优化", "降低", "增长", "提高", "缩短", "扩大"]):
                    suggested.append(f"请描述在 {company} 担任 {position} 时，您是如何实现 {ach} 的？")
            
            # 基于项目经历生成问题
            projects = exp.get("projects", [])
            for proj in projects:
                proj_name = proj.get("name", "某个项目")
                suggested.append(f"请描述您在 {proj_name} 中的角色和主要贡献？")
        
        return suggested
    
    def evaluate_answer(self, answer: str) -> Dict[str, any]:
        """评估回答质量
        
        Args:
            answer: 候选人的回答
            
        Returns:
            Dict: 评估结果（分数、优点、改进建议）
        """
        evaluation = {
            "score": 0,
            "has_situation": False,
            "has_task": False,
            "has_action": False,
            "has_result": False,
            "has_quantitative": False,
            "strengths": [],
            "improvements": []
        }
        
        # 简单关键词检测
        keywords_s = ["当时", "场景", "背景下", "情况是"]
        keywords_t = ["我的职责", "目标是", "需要", "任务是"]
        keywords_a = ["我做了", "我主动", "我协调", "我推动", "我负责"]
        keywords_r = ["提升了", "降低了", "从 x 到 y", "最终", "结果"]
        keywords_q = ["%", "倍", "小时", "天", "万元", "万元", "小时", "分钟"]
        
        answer_lower = answer.lower()
        for kw in keywords_s:
            if kw in answer_lower:
                evaluation["has_situation"] = True
                break
        
        for kw in keywords_t:
            if kw in answer_lower:
                evaluation["has_task"] = True
                break
        
        for kw in keywords_a:
            if kw in answer_lower:
                evaluation["has_action"] = True
                break
        
        for kw in keywords_r:
            if kw in answer_lower:
                evaluation["has_result"] = True
                break
        
        for kw in keywords_q:
            if kw in answer_lower:
                evaluation["has_quantitative"] = True
                break
        
        # 计算分数
        score = 0
        if evaluation["has_situation"]:
            score += 20
            evaluation["strengths"].append("✓ 清晰描述了背景情况")
        else:
            evaluation["improvements"].append("✗ 建议补充背景情况（Situation）")
        
        if evaluation["has_task"]:
            score += 20
            evaluation["strengths"].append("✓ 明确了任务目标")
        else:
            evaluation["improvements"].append("✗ 建议明确你的职责和目标（Task）")
        
        if evaluation["has_action"]:
            score += 30
            evaluation["strengths"].append("✓ 描述了具体行动")
        else:
            evaluation["improvements"].append("✗ 建议详细说明你采取了什么行动（Action）")
        
        if evaluation["has_result"]:
            score += 20
            evaluation["strengths"].append("✓ 展示了最终成果")
        else:
            evaluation["improvements"].append("✗ 建议补充结果（Result）")
        
        if evaluation["has_quantitative"]:
            score += 10
            evaluation["strengths"].append("✓ 使用了量化数据")
        else:
            evaluation["improvements"].append("建议用数据说话（如：效率提升 50%）")
        
        evaluation["score"] = min(score, 100)
        return evaluation