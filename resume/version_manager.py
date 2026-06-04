"""
resume/version_manager.py
简历多版本管理系统 - 支持技术版/管理版/国央企版 不同版本
"""

import json
import uuid
import copy
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('jobtracer.resume.version')


# ============================================================
# 版本类型定义
# ============================================================

class VersionType:
    """简历版本类型"""
    TECHNICAL = "technical"                 # 技术版 - 强调技术深度
    MANAGEMENT = "management"               # 管理版 - 强调团队管理和项目协调
    STATE_ENTERPRISE = "state_enterprise"  # 国央企版 - 强调稳定性和规范性
    GENERAL = "general"                     # 通用版 - 基础版本


# 版本的显示名称和描述
VERSION_META = {
    VersionType.TECHNICAL: {
        "name": "技术版",
        "description": "强调技术深度、项目难度和技术创新能力",
        "icon": "💻",
        "keywords": ["技术", "架构", "优化", "性能", "源码", "算法"],
    },
    VersionType.MANAGEMENT: {
        "name": "管理版",
        "description": "强调团队规模、项目管理和商业价值",
        "icon": "📊",
        "keywords": ["管理", "团队", "协调", "项目", "绩效", "OKR"],
    },
    VersionType.STATE_ENTERPRISE: {
        "name": "国央企版",
        "description": "强调稳定性、规范性和合规意识",
        "icon": "🏛️",
        "keywords": ["规范", "合规", "流程", "稳定", "制度", "执行"],
    },
    VersionType.GENERAL: {
        "name": "通用版",
        "description": "基础版本，适用于大多数场景",
        "icon": "📄",
        "keywords": [],
    },
}


# ============================================================
# 简历版本管理器
# ============================================================

class ResumeVersionManager:
    """
    简历多版本管理器
    支持创建、存储、检索、导出不同版本的简历
    """

    def __init__(self, storage_dir: str = "~/.jobtracer/customized_resumes"):
        """
        初始化版本管理器

        Args:
            storage_dir: 版本简历存储目录
        """
        self.storage_dir = Path(storage_dir).expanduser()
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.versions_file = self.storage_dir / "versions_index.json"
        self._load_index()

        logger.info(f"ResumeVersionManager initialized at {self.storage_dir}")

    def _load_index(self) -> None:
        """加载版本索引"""
        if self.versions_file.exists():
            try:
                with open(self.versions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._versions: List[Dict[str, Any]] = data.get("versions", [])
                self._base_resume: Dict[str, Any] = data.get("base_resume", {})
            except Exception as e:
                logger.error(f"Failed to load versions index: {e}")
                self._versions = []
                self._base_resume = {}
        else:
            self._versions = []
            self._base_resume = {}

    def _save_index(self) -> None:
        """保存版本索引"""
        try:
            with open(self.versions_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "versions": self._versions,
                    "base_resume": self._base_resume,
                    "last_updated": datetime.now().isoformat(),
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save versions index: {e}")

    # --------------------------------------------------------
    # 主接口
    # --------------------------------------------------------

    def set_base_resume(self, base_resume: dict) -> None:
        """
        设置基础简历（所有版本的来源）

        Args:
            base_resume: 基础简历数据 dict
        """
        self._base_resume = copy.deepcopy(base_resume)
        self._save_index()
        logger.info(f"Base resume updated: {len(str(base_resume))} chars")

    def get_base_resume(self) -> dict:
        """获取基础简历"""
        return copy.deepcopy(self._base_resume)

    def create_resume_version(
        self,
        base_resume: dict = None,
        version_type: str = VersionType.GENERAL,
        focus_skills: List[str] = None,
        custom_title: str = None,
    ) -> Dict[str, Any]:
        """
        创建简历新版本（符合指定接口）

        Args:
            base_resume: 基础简历 dict（如果未设置基础简历则使用当前基础）
            version_type: 版本类型 "technical"|"management"|"state_enterprise"
            focus_skills: 需要重点突出的技能列表
            custom_title: 自定义版本标题

        Returns:
            dict: {
                "version_id": "uuid",
                "version_type": "technical",
                "version_name": "技术版",
                "created_at": "...",
                "resume_data": {...},
                "export_path": null,
            }
        """
        # 优先使用传入的 base_resume，否则使用已存储的基础简历
        source = copy.deepcopy(base_resume) if base_resume else copy.deepcopy(self._base_resume)
        if not source:
            raise ValueError("No base resume available. Please set base_resume first.")

        # 更新基础简历（如果传入新的）
        if base_resume:
            self._base_resume = copy.deepcopy(base_resume)

        focus_skills = focus_skills or []

        # 根据版本类型定制简历
        customized = self._customize_resume(source, version_type, focus_skills)

        # 生成版本记录
        version_id = str(uuid.uuid4())[:8]
        version_meta = VERSION_META.get(version_type, VERSION_META[VersionType.GENERAL])

        version_record = {
            "version_id": version_id,
            "version_type": version_type,
            "version_name": custom_title or version_meta["name"],
            "description": version_meta["description"],
            "focus_skills": focus_skills,
            "created_at": datetime.now().isoformat(),
            "resume_data": customized,
            "export_path": None,
            "export_count": 0,
        }

        self._versions.append(version_record)
        self._save_index()

        logger.info(f"Created resume version: {version_id} ({version_type})")
        return version_record

    def list_resume_versions(self) -> List[Dict[str, Any]]:
        """
        返回已创建的版本列表（符合指定接口）

        Returns:
            List[dict]: 版本列表，每项包含 version_id, version_type, version_name, created_at 等
        """
        return [
            {
                "version_id": v["version_id"],
                "version_type": v["version_type"],
                "version_name": v["version_name"],
                "description": v.get("description", ""),
                "focus_skills": v.get("focus_skills", []),
                "created_at": v["created_at"],
                "export_count": v.get("export_count", 0),
            }
            for v in self._versions
        ]

    def get_version(self, version_id: str) -> Optional[Dict[str, Any]]:
        """获取指定版本详情"""
        for v in self._versions:
            if v["version_id"] == version_id:
                return copy.deepcopy(v)
        return None

    def delete_version(self, version_id: str) -> bool:
        """删除指定版本"""
        original_count = len(self._versions)
        self._versions = [v for v in self._versions if v["version_id"] != version_id]
        if len(self._versions) < original_count:
            self._save_index()
            logger.info(f"Deleted resume version: {version_id}")
            return True
        return False

    def export_resume_version(
        self,
        version_id: str,
        format: str = "json",
    ) -> str:
        """
        导出指定版本的简历（符合指定接口）

        Args:
            version_id: 版本 ID
            format: 导出格式 "json"|"pdf"|"html"

        Returns:
            str: 导出文件路径（json/pdf/html）或 JSON 字符串
        """
        version = self.get_version(version_id)
        if not version:
            raise ValueError(f"Version not found: {version_id}")

        if format == "json":
            export_path = self.storage_dir / f"resume_{version_id}.json"
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(version["resume_data"], f, ensure_ascii=False, indent=2)
            logger.info(f"Exported to {export_path}")
            return str(export_path)

        elif format == "html":
            export_path = self.storage_dir / f"resume_{version_id}.html"
            html_content = self._render_html(version)
            with open(export_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"Exported to {export_path}")
            return str(export_path)

        elif format == "pdf":
            # PDF 导出依赖外部库，这里先生成 HTML 再提示用户
            export_path = self.storage_dir / f"resume_{version_id}.pdf"
            html_path = self.storage_dir / f"resume_{version_id}.html"
            html_content = self._render_html(version)
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            version["export_path"] = str(html_path)
            version["export_count"] = version.get("export_count", 0) + 1
            self._save_index()
            logger.info(f"PDF export: generated HTML at {html_path} (use browser print to PDF)")
            return str(export_path)

        else:
            raise ValueError(f"Unsupported format: {format}")

    # --------------------------------------------------------
    # 简历定制逻辑
    # --------------------------------------------------------

    def _customize_resume(
        self,
        base: dict,
        version_type: str,
        focus_skills: List[str],
    ) -> dict:
        """
        根据版本类型定制简历内容

        Args:
            base: 基础简历
            version_type: 版本类型
            focus_skills: 重点技能

        Returns:
            dict: 定制后的简历
        """
        resume = copy.deepcopy(base)

        if version_type == VersionType.TECHNICAL:
            resume = self._make_technical_version(resume, focus_skills)
        elif version_type == VersionType.MANAGEMENT:
            resume = self._make_management_version(resume, focus_skills)
        elif version_type == VersionType.STATE_ENTERPRISE:
            resume = self._make_state_enterprise_version(resume, focus_skills)

        # 添加版本标识
        if "meta" not in resume:
            resume["meta"] = {}
        resume["meta"]["version_type"] = version_type
        resume["meta"]["version_name"] = VERSION_META.get(version_type, VERSION_META[VersionType.GENERAL])["name"]
        resume["meta"]["customized_at"] = datetime.now().isoformat()

        return resume

    def _make_technical_version(self, resume: dict, focus_skills: List[str]) -> dict:
        """生成技术版简历"""
        result = copy.deepcopy(resume)

        # 强化技术栈描述
        skills = result.get("skills", [])
        if isinstance(skills, list):
            # 按技术深度排序（如果有 proficiency 字段）
            skills.sort(key=lambda x: x.get("proficiency", 0) if isinstance(x, dict) else 0, reverse=True)
            result["skills"] = skills

        # 强化项目中的技术挑战和创新点
        projects = result.get("projects", [])
        if isinstance(projects, list):
            for project in projects:
                if "technical_challenges" not in project and "highlights" in project:
                    project["technical_challenges"] = project.pop("highlights", [])
                # 添加技术标签
                if "tech_stack" in project and isinstance(project["tech_stack"], list):
                    project["tech_tags"] = project["tech_stack"][:5]

        # 突出算法能力和系统设计经验
        summary = result.get("summary", "")
        if summary:
            tech_keywords = ["架构", "优化", "性能", "算法", "源码", "分布式", "高并发", "微服务"]
            for kw in tech_keywords:
                if kw in summary and kw not in summary.replace(kw, f"**{kw}**"):
                    pass  # 简单处理，不做复杂替换

        # 添加技术专长标签
        if focus_skills:
            if "highlights" not in result:
                result["highlights"] = []
            for skill in focus_skills[:3]:
                if skill not in result["highlights"]:
                    result["highlights"].append(f"擅长{skill}技术实战")

        return result

    def _make_management_version(self, resume: dict, focus_skills: List[str]) -> dict:
        """生成管理版简历"""
        result = copy.deepcopy(resume)

        # 强调团队规模和协作经验
        projects = result.get("projects", [])
        if isinstance(projects, list):
            for project in projects:
                # 添加团队规模描述
                if "team_size" not in project:
                    project["team_size"] = project.get("people", "若干人")
                # 强调项目协调和管理
                if "management_highlights" not in project:
                    highlights = []
                    if "outcome" in project:
                        highlights.append(f"项目成果: {project['outcome']}")
                    if "delivery" in project:
                        highlights.append(f"按时交付: {project['delivery']}")
                    project["management_highlights"] = highlights

        # 补充领导力相关描述
        summary = result.get("summary", "")
        if summary:
            mgmt_keywords = ["团队", "协调", "推动", "落地", "跨部门", "OKR", "绩效"]
            for kw in mgmt_keywords:
                if kw in summary:
                    pass  # 已有关键词，保持不变

        # 添加管理维度的高亮
        if focus_skills:
            if "highlights" not in result:
                result["highlights"] = []
            for skill in focus_skills[:3]:
                if skill not in result["highlights"]:
                    result["highlights"].append(f"{skill}管理与实践经验")

        return result

    def _make_state_enterprise_version(self, resume: dict, focus_skills: List[str]) -> dict:
        """生成国央企版简历"""
        result = copy.deepcopy(resume)

        # 淡化商业敏感信息
        if "projects" in result:
            projects = result["projects"]
            if isinstance(projects, list):
                for project in projects:
                    # 移除具体商业数据
                    if "revenue" in project:
                        del project["revenue"]
                    if "商业化" in project.get("description", ""):
                        project["description"] = project["description"].replace("商业化", "项目化")
                    # 强调合规和规范
                    if "compliance" not in project:
                        project["compliance"] = "遵循公司制度规范流程"

        # 强调稳定性和规范性
        summary = result.get("summary", "")
        if summary:
            state_keywords = ["规范", "流程", "制度", "执行", "稳定", "合规"]
            for kw in state_keywords:
                if kw in summary:
                    pass

        # 调整自我评价风格
        if "about" in result:
            result["about"] = result["about"].replace("野狼", "稳健").replace("颠覆", "优化")

        # 添加国央企适用的高亮
        if focus_skills:
            if "highlights" not in result:
                result["highlights"] = []
            for skill in focus_skills[:3]:
                if skill not in result["highlights"]:
                    result["highlights"].append(f"{skill}规范化应用")

        return result

    # --------------------------------------------------------
    # HTML 渲染
    # --------------------------------------------------------

    def _render_html(self, version: Dict[str, Any]) -> str:
        """将简历数据渲染为 HTML"""
        data = version.get("resume_data", {})

        name = data.get("name", "未命名")
        title = data.get("title", "")
        email = data.get("email", "")
        phone = data.get("phone", "")
        skills = data.get("skills", [])
        projects = data.get("projects", [])

        skills_html = ""
        if isinstance(skills, list):
            for skill in skills:
                if isinstance(skill, dict):
                    skills_html += f'<span class="skill-tag">{skill.get("name", skill)}</span>'
                else:
                    skills_html += f'<span class="skill-tag">{skill}</span>'

        projects_html = ""
        if isinstance(projects, list):
            for p in projects:
                p_name = p.get("name", "项目")
                p_role = p.get("role", "")
                p_desc = p.get("description", "")
                p_outcome = p.get("outcome", "")
                projects_html += f"""
                <div class="project-item">
                    <div class="project-header">
                        <span class="project-name">{p_name}</span>
                        <span class="project-role">{p_role}</span>
                    </div>
                    <p class="project-desc">{p_desc}</p>
                    {'<p class="project-outcome"><strong>成果:</strong> ' + p_outcome + '</p>' if p_outcome else ''}
                </div>
                """

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} - 简历</title>
<style>
    body {{ font-family: "PingFang SC", "Microsoft YaHei", sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #333; }}
    .resume-header {{ border-bottom: 2px solid #2563eb; padding-bottom: 16px; margin-bottom: 24px; }}
    .resume-name {{ font-size: 28px; font-weight: bold; margin: 0 0 8px; }}
    .resume-title {{ font-size: 16px; color: #666; margin: 0 0 12px; }}
    .contact-info {{ font-size: 14px; color: #888; }}
    .section {{ margin-bottom: 24px; }}
    .section-title {{ font-size: 18px; font-weight: bold; color: #2563eb; border-left: 3px solid #2563eb; padding-left: 10px; margin-bottom: 12px; }}
    .skill-tag {{ display: inline-block; background: #eff6ff; color: #2563eb; padding: 4px 10px; border-radius: 4px; font-size: 13px; margin: 3px; }}
    .project-item {{ margin-bottom: 16px; padding: 12px; background: #f9fafb; border-radius: 8px; }}
    .project-header {{ display: flex; justify-content: space-between; margin-bottom: 6px; }}
    .project-name {{ font-weight: bold; }}
    .project-role {{ color: #666; font-size: 14px; }}
    .project-desc {{ margin: 0 0 6px; color: #555; font-size: 14px; }}
    .project-outcome {{ margin: 0; color: #2563eb; font-size: 13px; }}
    .highlights {{ list-style: none; padding: 0; }}
    .highlights li {{ padding: 4px 0; font-size: 14px; }}
    .highlights li::before {{ content: "✓ "; color: #2563eb; }}
</style>
</head>
<body>
<div class="resume-header">
    <h1 class="resume-name">{name}</h1>
    {'<p class="resume-title">' + title + '</p>' if title else ''}
    <p class="contact-info">{email}  {phone}</p>
</div>

<div class="section">
    <h2 class="section-title">技能专长</h2>
    <div>{skills_html}</div>
</div>

<div class="section">
    <h2 class="section-title">项目经历</h2>
    {projects_html}
</div>
</body>
</html>"""
        return html


# ============================================================
# 便捷函数
# ============================================================

_default_manager: Optional[ResumeVersionManager] = None


def get_version_manager() -> ResumeVersionManager:
    """获取默认版本管理器"""
    global _default_manager
    if _default_manager is None:
        _default_manager = ResumeVersionManager()
    return _default_manager


def create_resume_version(base_resume: dict, version_type: str, focus_skills: list = None) -> dict:
    """便捷函数：创建简历版本"""
    manager = get_version_manager()
    return manager.create_resume_version(base_resume, version_type, focus_skills)


def list_resume_versions() -> list:
    """便捷函数：列出所有版本"""
    manager = get_version_manager()
    return manager.list_resume_versions()


def export_resume_version(version_id: str, format: str = "json") -> str:
    """便捷函数：导出简历版本"""
    manager = get_version_manager()
    return manager.export_resume_version(version_id, format)


# ============================================================
# 测试入口
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("简历多版本管理测试")
    print("=" * 60)

    # 样例基础简历
    sample_resume = {
        "name": "李明",
        "title": "高级后端工程师",
        "email": "liming@example.com",
        "phone": "138****1234",
        "skills": [
            {"name": "Python", "proficiency": 5},
            {"name": "Go", "proficiency": 4},
            {"name": "系统架构", "proficiency": 4},
            {"name": "分布式系统", "proficiency": 5},
            {"name": "微服务", "proficiency": 4},
        ],
        "projects": [
            {
                "name": "电商平台重构项目",
                "role": "技术负责人",
                "description": "负责将单体架构重构为微服务架构，处理高并发场景",
                "outcome": "QPS 从 500 提升至 5000",
                "team_size": "8人",
            },
            {
                "name": "实时数据同步系统",
                "role": "核心开发",
                "description": "基于 CDC 方案实现多数据源实时同步",
                "outcome": "延迟从小时级降至秒级",
            },
        ],
        "summary": "8年+后端开发经验，擅长高并发系统架构和性能优化",
        "about": "工作严谨，注重工程规范和团队协作",
    }

    manager = ResumeVersionManager()

    # 设置基础简历
    manager.set_base_resume(sample_resume)
    print(f"✓ 基础简历已设置: {sample_resume['name']}")

    # 创建三个版本
    versions = []
    for vt, skills in [
        (VersionType.TECHNICAL, ["Python", "分布式系统", "性能优化"]),
        (VersionType.MANAGEMENT, ["团队管理", "OKR", "跨部门协调"]),
        (VersionType.STATE_ENTERPRISE, ["合规", "流程规范", "稳定性"]),
    ]:
        v = manager.create_resume_version(version_type=vt, focus_skills=skills)
        versions.append(v)
        print(f"✓ 创建版本: {v['version_name']} (ID: {v['version_id']})")

    print()

    # 列出所有版本
    all_versions = manager.list_resume_versions()
    print(f"已创建版本数: {len(all_versions)}")
    for v in all_versions:
        print(f"  [{v['version_id']}] {v['version_name']} ({v['version_type']}) - {v['created_at'][:10]}")

    print()

    # 测试导出
    v0 = versions[0]
    json_path = manager.export_resume_version(v0["version_id"], "json")
    print(f"✓ JSON 导出: {json_path}")

    html_path = manager.export_resume_version(v0["version_id"], "html")
    print(f"✓ HTML 导出: {html_path}")

    print()
    print("=" * 60)
    print("测试完成")
    print("=" * 60)