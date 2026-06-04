# resume/intelligent_filler.py
# 简历内容智能填充 - 基于数字足迹扫描结果，自动补全简历空白内容
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# ============================================================
# 常量
# ============================================================

DEFAULT_PROJECTS_DIR = Path("~/.jobtracer/footprint/projects")
DEFAULT_RESUME_PATH = Path("~/.jobtracer/memory/resume.json")
PROJECTS_INDEX_PATH = Path("~/.jobtracer/footprint/projects_index.json")


# ============================================================
# 核心填充函数
# ============================================================

def fill_resume_gaps(base_resume: dict, footprint_projects: list) -> dict:
    """
    读取数字足迹项目，发现简历中缺失的项目经历，自动补充到简历的「项目经历」部分。

    对比逻辑：
    1. 扫描 footprint_projects，提取每个项目的 {name, tags, description, tech_stack}
    2. 对比 base_resume['projects'] 中已有的项目名（模糊匹配）
    3. 发现缺失项目 → 加入 added_projects
    4. 返回带新增项目的完整简历 + 置信度评分

    Args:
        base_resume: 现有简历 dict（可能有部分项目）
        footprint_projects: 数字足迹聚类后的项目列表

    Returns:
        {
            "filled_resume": {...},          # 补充后的完整简历
            "added_projects": [...],          # 新增的项目列表
            "confidence_scores": {
                "project_name": 0.85,         # 每个新增项目的置信度
                ...
            }
        }
    """
    existing_names = _extract_existing_project_names(base_resume)
    existing_tags = _extract_existing_tags(base_resume)

    # 去重后的项目列表
    all_projects = list(base_resume.get("projects", []))
    added_projects = []
    confidence_scores = {}

    for proj in footprint_projects:
        proj_name = proj.get("project_name", proj.get("name", ""))
        if not proj_name:
            continue

        # 模糊匹配：检查是否已存在
        if _is_project_existing(proj_name, existing_names):
            continue

        # 检查 tags 是否已覆盖（避免重复方向）
        proj_tags = proj.get("tags", [])
        tag_overlap = _compute_tag_overlap(proj_tags, existing_tags)
        if tag_overlap > 0.8:
            # 标签高度重合，跳过
            continue

        # 计算置信度
        confidence = _compute_fill_confidence(proj, base_resume)

        # 构建项目条目
        filled_project = _build_project_entry(proj, confidence)
        all_projects.append(filled_project)
        added_projects.append(filled_project)
        confidence_scores[proj_name] = confidence

        # 更新 existing_names 以支持后续项目的链式去重
        existing_names.add(proj_name)

    # 构建结果
    filled_resume = dict(base_resume)
    filled_resume["projects"] = all_projects
    filled_resume["meta"] = {
        **base_resume.get("meta", {}),
        "auto_filled": True,
        "filled_projects_count": len(added_projects),
        "filled_at": "",
    }

    return {
        "filled_resume": filled_resume,
        "added_projects": added_projects,
        "confidence_scores": confidence_scores,
    }


def _extract_existing_project_names(resume: dict) -> set:
    """从简历中提取已有项目名（用于去重）"""
    names = set()
    for proj in resume.get("projects", []):
        name = proj.get("name", "")
        if name:
            names.add(name.lower())
        # 也检查 role 和 description 中的项目名
        role = proj.get("role", "")
        desc = proj.get("description", "")
        if role:
            names.add(role.lower())
        # 尝试从 description 提取项目名（括号内或引号内）
        matches = re.findall(r'[`"\'(]([^`"\')]+)[`"\')]', desc)
        for m in matches:
            if 2 < len(m) < 60:
                names.add(m.lower())
    return names


def _extract_existing_tags(resume: dict) -> set:
    """从简历中提取已有技术标签（用于评估覆盖度）"""
    tags = set()
    for skill in resume.get("skills", []):
        tags.add(skill.lower())
    for proj in resume.get("projects", []):
        for tech in proj.get("tech_stack", []):
            tags.add(tech.lower())
    return tags


def _is_project_existing(project_name: str, existing_names: set) -> bool:
    """模糊判断项目是否已存在"""
    pn_lower = project_name.lower().strip()
    if pn_lower in existing_names:
        return True

    # 检查包含关系
    for existing in existing_names:
        if len(existing) > 3 and (existing in pn_lower or pn_lower in existing):
            return True
        # 相似度：Levenshtein-like 简单判断
        if _simple_similarity(existing, pn_lower) > 0.7:
            return True
    return False


def _simple_similarity(a: str, b: str) -> float:
    """简单的字符串相似度（交集/长度比）"""
    if not a or not b:
        return 0.0
    set_a = set(a)
    set_b = set(b)
    intersection = len(set_a & set_b)
    return intersection / max(len(set_a), len(set_b))


def _compute_tag_overlap(tags: List[str], existing_tags: set) -> float:
    """计算新增项目标签与已有标签的重叠率"""
    if not tags:
        return 0.0
    overlap = sum(1 for t in tags if t.lower() in existing_tags)
    return overlap / len(tags)


def _compute_fill_confidence(project: dict, base_resume: dict) -> float:
    """
    计算项目填充置信度 (0.0 - 1.0)

    依据：
    - 项目本身置信度 (clustering engine 输出的 confidence)
    - 与目标职位的匹配度
    - 是否有描述
    - 是否有指标（metrics）
    """
    base_conf = project.get("confidence", 0.5)

    # 有描述 +0.1
    has_desc = bool(project.get("description") and len(project.get("description", "")) > 20)

    # 有 metrics +0.15
    has_metrics = bool(project.get("metrics"))

    # 有 tech_stack +0.1
    has_tech = bool(project.get("tech_stack"))

    # 有多个文件 +0.05
    file_count = len(project.get("files", []))
    has_files = file_count >= 3

    confidence = base_conf
    if has_desc:
        confidence += 0.1
    if has_metrics:
        confidence += 0.15
    if has_tech:
        confidence += 0.1
    if has_files:
        confidence += 0.05

    return min(confidence, 0.98)


def _build_project_entry(project: dict, confidence: float) -> dict:
    """将 footprint 项目构建为简历项目条目"""
    name = project.get("project_name", project.get("name", "Unknown"))
    description = project.get("description", "")

    # 如果没有描述，尝试用 summary 或 tags 构造
    if not description:
        summary = project.get("summary", "")
        if summary:
            description = summary[:300]
        else:
            tags = project.get("tags", [])
            if tags:
                description = f"使用 {'/'.join(tags[:5])} 技术栈完成的项目"

    return {
        "name": name,
        "role": project.get("role", "项目成员"),
        "description": description,
        "metrics": project.get("metrics", ""),
        "tech_stack": project.get("tags", [])[:8],  # 最多8个技术标签
        "source": "digital_footprint",
        "_fill_confidence": confidence,
    }


# ============================================================
# 从 projects_index.json 加载足迹项目
# ============================================================

def load_footprint_projects() -> list:
    """
    从 projects_index.json 加载聚类后的项目列表。
    如果文件不存在，尝试从 projects_dir 目录扫描。
    """
    # 优先从 projects_index.json 加载
    index_path = Path(PROJECTS_INDEX_PATH)
    if index_path.exists():
        try:
            data = json.loads(index_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
            # 如果是 dict，尝试提取 projects 字段
            if isinstance(data, dict) and "projects" in data:
                return data["projects"]
        except Exception as e:
            print(f"[IntelligentFiller] Failed to load projects_index: {e}")

    # Fallback: 扫描 projects_dir
    projects_dir = Path(DEFAULT_PROJECTS_DIR)
    if not projects_dir.exists():
        return []

    projects = []
    for d in projects_dir.iterdir():
        if not d.is_dir() or d.name.startswith("."):
            continue
        meta_path = d / "metadata.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                meta["project_id"] = d.name
                projects.append(meta)
            except Exception:
                pass
    return projects


# ============================================================
# 便捷入口
# ============================================================

def auto_fill_resume(resume_path: Optional[str] = None) -> dict:
    """
    自动填充简历：加载现有简历 + 足迹项目，执行智能填充。

    Returns:
        fill_resume_gaps 的输出
    """
    # 加载简历
    src = Path(resume_path or str(DEFAULT_RESUME_PATH)).expanduser()
    if src.exists():
        try:
            base_resume = json.loads(src.read_text(encoding="utf-8"))
        except Exception:
            base_resume = {"name": "Unknown", "projects": [], "skills": []}
    else:
        base_resume = {"name": "Unknown", "projects": [], "skills": []}

    # 加载足迹项目
    footprint_projects = load_footprint_projects()

    # 执行填充
    return fill_resume_gaps(base_resume, footprint_projects)


# ============================================================
# 辅助：增量更新已填充简历
# ============================================================

def merge_linkedin_into_resume(
    resume: dict,
    linkedin_data: dict,
    strategy: str = "prefer_linkedin"
) -> dict:
    """
    将 LinkedIn 数据合并到简历中。

    Args:
        resume: 当前简历 dict
        linkedin_data: LinkedIn 导入结果
        strategy: 合并策略
            - "prefer_linkedin": LinkedIn 数据优先
            - "prefer_existing": 现有简历数据优先

    Returns:
        合并后的简历 dict
    """
    merged = dict(resume)

    # 姓名：LinkedIn 通常更准确
    if strategy == "prefer_linkedin" and linkedin_data.get("name"):
        merged["name"] = linkedin_data["name"]

    # 工作经历
    from integrations.linkedin_importer import convert_to_resume_experience
    li_experience = convert_to_resume_experience(linkedin_data)
    if strategy == "prefer_linkedin":
        if li_experience:
            merged["experience"] = li_experience
    else:
        # 合并，LinkedIn 数据去重后追加
        existing_titles = {e.get("title", "") for e in resume.get("experience", [])}
        for exp in li_experience:
            if exp.get("title") not in existing_titles:
                merged.setdefault("experience", []).append(exp)

    # 教育经历
    from integrations.linkedin_importer import convert_to_resume_education
    li_education = convert_to_resume_education(linkedin_data)
    if strategy == "prefer_linkedin":
        if li_education:
            merged["education"] = li_education
    else:
        existing_schools = {e.get("school", "") for e in resume.get("education", [])}
        for edu in li_education:
            if edu.get("school") not in existing_schools:
                merged.setdefault("education", []).append(edu)

    # 技能：合并去重
    existing_skills = {s.lower() for s in resume.get("skills", [])}
    new_skills = [
        s for s in linkedin_data.get("skills", [])
        if s.lower() not in existing_skills
    ]
    if new_skills:
        merged["skills"] = resume.get("skills", []) + new_skills[:10]

    # 认证
    if linkedin_data.get("certifications"):
        merged["certifications"] = linkedin_data["certifications"]

    merged["meta"] = {
        **resume.get("meta", {}),
        "linkedin_imported": True,
        "linkedin_import_strategy": strategy,
    }
    return merged


# ============================================================
# 测试入口
# ============================================================

if __name__ == "__main__":
    print("[IntelligentFiller] Starting auto-fill...")

    result = auto_fill_resume()

    print(f"\n=== Fill Results ===")
    print(f"Added projects: {len(result['added_projects'])}")
    for p in result["added_projects"]:
        conf = result["confidence_scores"].get(p["name"], 0)
        print(f"  • {p['name']} (confidence: {conf:.0%})")
        if p.get("tech_stack"):
            print(f"    Tech: {', '.join(p['tech_stack'][:5])}")

    if result["added_projects"]:
        print(f"\nFilled resume has {len(result['filled_resume']['projects'])} total projects")