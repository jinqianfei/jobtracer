"""学习路线图生成器
基于职业路径 → 生成阶段性学习计划 + 资源推荐
"""
from typing import List, Dict, Optional
from dataclasses import dataclass
import json
import re


# 学习资源库
LEARNING_RESOURCES = {
    "需求分析": [
        {"type": "book", "name": "俞军产品方法论", "url": ""},
        {"type": "course", "name": "人人都是产品经理 - 产品经理课程", "url": "https://www.jianshi.com"},
    ],
    "数据分析": [
        {"type": "course", "name": "Python数据分析实战", "url": ""},
        {"type": "book", "name": "利用Python进行数据分析", "url": ""},
    ],
    "PRD撰写": [
        {"type": "template", "name": "PRD模板", "url": ""},
        {"type": "article", "name": "如何写好PRD", "url": ""},
    ],
    "项目管理": [
        {"type": "course", "name": "PMP项目管理认证", "url": ""},
        {"type": "book", "name": "Scrum敏捷开发", "url": ""},
    ],
    "团队管理": [
        {"type": "book", "name": "非暴力沟通", "url": ""},
        {"type": "book", "name": "经理人的书架", "url": ""},
    ],
    "供应链": [
        {"type": "course", "name": "供应链管理概论", "url": ""},
        {"type": "book", "name": "供应链架构", "url": ""},
    ],
    "运筹优化": [
        {"type": "course", "name": "运筹学基础", "url": ""},
        {"type": "book", "name": "算法导论", "url": ""},
    ],
    "Roadmap规划": [
        {"type": "article", "name": "如何做产品路线图规划", "url": ""},
    ],
    "跨部门协作": [
        {"type": "course", "name": "横向领导力", "url": ""},
    ],
    "战略规划": [
        {"type": "book", "name": "战略管理", "url": ""},
    ],
    "商业模式设计": [
        {"type": "course", "name": "商业模式设计", "url": ""},
    ],
}


@dataclass
class LearningActivity:
    month: int
    focus: str
    activities: List[str]
    deliverable: str
    resources: List[dict]


def generate_learning_roadmap(career_path: dict, current_skills: dict = None) -> dict:
    """
    生成学习路线图
    
    Args:
        career_path: 来自 CareerPlanner.suggest_career_paths() 的路径
        current_skills: 当前技能（来自 analyze_background 的 skills）
    
    Returns:
        {
            "path_name": "...",
            "gap_skills": [...],
            "learning_plan": [
                {"month": 1, "focus": "...", "activities": [...], "deliverable": "..."},
                ...
            ],
            "resources": [{type, name, url}, ...]
        }
    """
    current = current_skills or {}
    current_flat = [s for sl in current.values() for s in sl]
    
    gap_skills = career_path.get("skill_gaps", [])
    target_skills = career_path.get("required_skills", [])
    
    # 构建月度计划
    plan = []
    skill_buckets = _bucket_skills_by_priority(gap_skills)
    
    # Month 1-2: 基础知识
    if skill_buckets["must_have"]:
        plan.append({
            "month": 1,
            "focus": f"夯实基础：{', '.join(skill_buckets['must_have'][:2])}",
            "activities": [
                f"学习《{skill_buckets['must_have'][0]}》核心概念",
                "整理笔记，形成自己的理解框架",
                "找1个实际案例分析",
            ],
            "deliverable": f"掌握{skill_buckets['must_have'][0] if skill_buckets['must_have'] else '核心技能'}基础",
            "resources": _get_resources_for_skills(skill_buckets["must_have"][:2]),
        })
    
    # Month 3-4: 实战应用
    if skill_buckets["nice_to_have"]:
        plan.append({
            "month": 3,
            "focus": f"实战应用：{', '.join(skill_buckets['nice_to_have'][:2])}",
            "activities": [
                "找到1个相关项目机会（内部或外部）",
                "尝试在工作中主动应用",
                "输出实践总结（文章或文档）",
            ],
            "deliverable": "完成1个实战项目",
            "resources": _get_resources_for_skills(skill_buckets["nice_to_have"][:2]),
        })
    
    # Month 5-6: 深化拓展
    plan.append({
        "month": 5,
        "focus": "简历与面试准备",
        "activities": [
            "更新简历，体现新技能",
            "准备新方向面试题",
            "找该领域从业者模拟面试",
        ],
        "deliverable": "完成简历更新 + 拿到1个offer",
        "resources": [],
    })
    
    # 收集所有资源
    all_resources = []
    for skill in gap_skills:
        all_resources.extend(_get_resources_for_skills([skill]))
    
    return {
        "path_name": career_path.get("path_name", "未知路径"),
        "target_roles": career_path.get("target_roles", []),
        "gap_skills": gap_skills,
        "learning_plan": plan,
        "resources": all_resources[:12],  # 最多12个资源
        "generated_at": "",  # 填充时机
    }


def _bucket_skills_by_priority(skills: List[str]) -> dict:
    """将技能按优先级分桶"""
    return {
        "must_have": skills[:3],  # 前3个最重要
        "nice_to_have": skills[3:],
    }


def _get_resources_for_skills(skills: List[str]) -> List[dict]:
    """获取技能对应的学习资源"""
    resources = []
    for skill in skills:
        if skill in LEARNING_RESOURCES:
            resources.extend(LEARNING_RESOURCES[skill][:2])
    return resources


def generate_career_roadmap(career_path: dict, current_skills: dict = None) -> str:
    """
    生成 Markdown 格式的职业路线图（可视化）
    使用 Mermaid 格式
    """
    plan = generate_learning_roadmap(career_path, current_skills)
    
    md = f"""# 🎯 职业规划路线图

## {plan['path_name']}
**目标岗位**: {', '.join(plan['target_roles'])}

---

## 📊 能力差距分析

| 技能 | 状态 | 说明 |
|------|------|------|
"""
    for skill in career_path.get("required_skills", []):
        status = "✅ 已掌握" if any(skill in sl for sl in (current_skills or {}).values()) else "❌ 待提升"
        md += f"| {skill} | {status} | {'需要学习' if status.startswith('❌') else '继续保持'} |\n"
    
    md += """
---

## 🗺️ 学习路线图（Mermaid）

```mermaid
gantt
    title 学习计划
    dateFormat  YYYY-MM-DD
    section 阶段一
    基础知识                :a1, 2026-07-01, 60d
    section 阶段二
    实战应用                :a2, after a1, 60d
    section 阶段三
    简历面试                :a3, after a2, 30d
```
"""
    
    md += """
---

## 📅 月度学习计划

"""
    for item in plan["learning_plan"]:
        md += f"""### Month {item['month']}: {item['focus']}

**成果目标**: {item['deliverable']}

**学习活动**:
"""
        for act in item["activities"]:
            md += f"- [ ] {act}\n"
        if item.get("resources"):
            md += f"\n**推荐资源**:\n"
            for r in item["resources"]:
                md += f"- [{r['type']}] {r['name']}\n"
        md += "\n"
    
    if plan["resources"]:
        md += """---

## 📚 推荐学习资源

"""
        for r in plan["resources"][:8]:
            md += f"- **{r['type']}**: {r['name']}\n"
    
    return md


def generate_markdown_report(career_paths: List[dict], background: dict) -> str:
    """生成完整的职业规划报告（Markdown）"""
    md = f"""# 📋 职业规划报告

**生成时间**: {background.get('analyzed_at', '')[:10]}
**工作年限**: {background.get('work_years', 0)}年
**当前级别**: {background.get('level', 'unknown')}

---

## 🎯 职业背景分析

**优势**:
"""
    for s in background.get("strengths", []):
        md += f"- {s}\n"
    
    md += "\n**能力差距**:\n"
    for g in background.get("gaps", []):
        md += f"- {g}\n"
    
    md += "\n**技能图谱**:\n"
    for cat, skills in background.get("skills", {}).items():
        if skills:
            md += f"- **{cat}**: {', '.join(skills)}\n"
    
    md += "\n---\n\n## 🚀 推荐职业路径\n"
    
    for i, path in enumerate(career_paths, 1):
        md += f"""### 路径{i}: {path['path_name']}
- **描述**: {path['description']}
- **目标岗位**: {', '.join(path['target_roles'])}
- **匹配度**: {path['match_score']}%
- **成功率**: {path['success_rate']}

**下一步行动**:
"""
        for step in path.get("next_steps", [])[:2]:
            md += f"- [{step['phase']} / {step['timeline']}] {step['deliverable']}\n"
        
        if path.get("transition_tips"):
            md += f"\n**转型建议**: {'; '.join(path['transition_tips'][:2])}\n"
        
        md += "\n---\n"
    
    return md


if __name__ == "__main__":
    # 测试
    path = {
        "path_key": "pm_to_pdl",
        "path_name": "产品转产品线负责人",
        "description": "从单一产品经理走向产品线管理",
        "target_roles": ["高级产品经理", "产品线负责人"],
        "match_score": 55,
        "success_rate": "medium",
        "skill_gaps": ["团队管理", "Roadmap规划", "战略思维"],
        "required_skills": ["团队管理", "Roadmap规划", "战略思维"],
        "next_steps": [],
        "transition_tips": ["争取带项目机会", "学习商业分析"],
    }
    current_skills = {"product": ["需求分析", "数据分析"], "technical": ["Python"]}
    
    roadmap = generate_learning_roadmap(path, current_skills)
    print("Gap skills:", roadmap["gap_skills"])
    print("Plan months:", [p["month"] for p in roadmap["learning_plan"]])
    print()
    print(generate_career_roadmap(path, current_skills))