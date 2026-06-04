"""
JobTracer PDF生成模块
基于 ReportLab 的纯 Python PDF 生成器，支持中文字体
"""

import io
import logging
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger("jobtracer.pdf")

# ─── 注册中文字体（macOS 内置） ───────────────────────────────
_CHINESE_FONTS_REGISTERED = False


def _register_chinese_fonts():
    """注册中文字体（一次性，全局生效）"""
    global _CHINESE_FONTS_REGISTERED
    if _CHINESE_FONTS_REGISTERED:
        return
    try:
        pdfmetrics.registerFont(TTFont("Heiti", "/System/Library/Fonts/STHeiti Light.ttc"))
        pdfmetrics.registerFont(TTFont("Songti", "/System/Library/Fonts/Supplemental/Songti.ttc"))
        _CHINESE_FONTS_REGISTERED = True
        logger.debug("Chinese fonts registered: Heiti, Songti")
    except Exception as e:
        logger.warning(f"Failed to register Chinese fonts: {e}")
        _CHINESE_FONTS_REGISTERED = False


# ─── 颜色常量 ────────────────────────────────────────────────
_CLR_PRIMARY = colors.HexColor("#2563eb")
_CLR_PRIMARY_DARK = colors.HexColor("#1e40af")
_CLR_PRIMARY_LIGHT = colors.HexColor("#dbeafe")
_CLR_SUCCESS = colors.HexColor("#059669")
_CLR_BG = colors.HexColor("#f8fafc")
_CLR_TEXT = colors.HexColor("#333333")
_CLR_TEXT_MUTED = colors.HexColor("#666666")
_CLR_BORDER = colors.HexColor("#e2e8f0")

# ─── 页面尺寸 ────────────────────────────────────────────────
PAGE_W, PAGE_H = A4
MARGIN = 2 * cm
CONTENT_W = PAGE_W - 2 * MARGIN

# ─── 样式工厂 ────────────────────────────────────────────────
def _make_styles():
    """构建样式字典"""

    def ps(name, **kw):
        return ParagraphStyle(name, **kw)

    return {
        "name": ps(
            "RName",
            fontName="Heiti",
            fontSize=22,
            leading=28,
            textColor=_CLR_PRIMARY_DARK,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "contact": ps(
            "RContact",
            fontName="Songti",
            fontSize=10,
            leading=14,
            textColor=_CLR_TEXT_MUTED,
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "section_title": ps(
            "RSectionTitle",
            fontName="Heiti",
            fontSize=13,
            leading=18,
            textColor=_CLR_PRIMARY,
            spaceBefore=14,
            spaceAfter=6,
        ),
        "summary": ps(
            "RSummary",
            fontName="Songti",
            fontSize=10,
            leading=16,
            textColor=_CLR_TEXT,
        ),
        "skill_tag": ps(
            "RSkillTag",
            fontName="Songti",
            fontSize=9,
            leading=12,
            textColor=_CLR_PRIMARY_DARK,
            alignment=TA_CENTER,
        ),
        "project_name": ps(
            "RProjectName",
            fontName="Heiti",
            fontSize=11,
            leading=15,
            textColor=_CLR_PRIMARY_DARK,
            spaceAfter=2,
        ),
        "project_role": ps(
            "RProjectRole",
            fontName="Songti",
            fontSize=9,
            leading=12,
            textColor=_CLR_TEXT_MUTED,
            spaceAfter=2,
        ),
        "project_tech": ps(
            "RProjectTech",
            fontName="Songti",
            fontSize=9,
            leading=12,
            textColor=_CLR_TEXT_MUTED,
            spaceAfter=3,
        ),
        "project_desc": ps(
            "RProjectDesc",
            fontName="Songti",
            fontSize=10,
            leading=14,
            textColor=_CLR_TEXT,
            spaceAfter=3,
        ),
        "project_metrics": ps(
            "RProjectMetrics",
            fontName="Heiti",
            fontSize=10,
            leading=14,
            textColor=_CLR_SUCCESS,
            spaceAfter=4,
        ),
        "timeline_title": ps(
            "RTimelineTitle",
            fontName="Heiti",
            fontSize=11,
            leading=15,
            textColor=_CLR_PRIMARY_DARK,
            spaceAfter=1,
        ),
        "timeline_meta": ps(
            "RTimelineMeta",
            fontName="Songti",
            fontSize=9,
            leading=12,
            textColor=_CLR_TEXT_MUTED,
            spaceAfter=3,
        ),
        "timeline_desc": ps(
            "RTimelineDesc",
            fontName="Songti",
            fontSize=10,
            leading=14,
            textColor=_CLR_TEXT,
        ),
        "edu_item": ps(
            "REduItem",
            fontName="Songti",
            fontSize=10,
            leading=14,
            textColor=_CLR_TEXT,
        ),
        "empty_hint": ps(
            "REmptyHint",
            fontName="Songti",
            fontSize=9,
            leading=12,
            textColor=_CLR_TEXT_MUTED,
        ),
    }


# ─── 页脚 ───────────────────────────────────────────────────
def _on_page(canvas, doc):
    """每页页脚"""
    canvas.saveState()
    canvas.setFont("Songti", 8)
    canvas.setFillColor(_CLR_TEXT_MUTED)
    canvas.drawString(MARGIN, 1.2 * cm, "JobTracer 简历")
    canvas.drawRightString(PAGE_W - MARGIN, 1.2 * cm, f"第 {doc.page} 页")
    canvas.restoreState()


# ─── 主类 ───────────────────────────────────────────────────
class PDFGenerator:
    """
    基于 ReportLab 的纯 Python PDF 生成器。

    输入 resume.json dict，输出 PDF 文件路径或 bytes。

    使用示例：
        gen = PDFGenerator()
        pdf_bytes = gen.generate(resume_json)
        gen.generate_to_file(resume_json, "/path/to/output.pdf")
    """

    def __init__(self, font_path: str = None):
        """
        初始化 PDF 生成器。

        Args:
            font_path: 中文字体文件路径（可选，默认使用系统内置 Heiti/Songti）
        """
        self.font_path = font_path
        _register_chinese_fonts()

    # ── 公开 API ──────────────────────────────────────────────

    def generate(self, resume_json: dict, output_path: str = None) -> bytes:
        """
        生成 PDF bytes。

        Args:
            resume_json: 简历数据字典
            output_path: 未使用，保留接口兼容

        Returns:
            PDF 内容的 bytes
        """
        buffer = io.BytesIO()
        self._build(buffer, resume_json)
        return buffer.getvalue()

    def generate_to_file(self, resume_json: dict, file_path: str) -> str:
        """
        生成 PDF 并写入文件。

        Args:
            resume_json: 简历数据字典
            file_path: 输出文件路径

        Returns:
            输出文件路径
        """
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "wb") as f:
            self._build(f, resume_json)
        return file_path

    async def generate_async(self, resume_json: dict, output_path: str = None) -> bytes:
        """
        异步生成（内部同步执行，保留 async 签名）。

        Args:
            resume_json: 简历数据字典
            output_path: 未使用

        Returns:
            PDF 内容的 bytes
        """
        return self.generate(resume_json, output_path)

    # ── 内部构建 ──────────────────────────────────────────────

    def _build(self, dest, resume_json: dict):
        """构建 PDF 文档"""
        styles = _make_styles()

        doc = SimpleDocTemplate(
            dest,
            pagesize=A4,
            leftMargin=MARGIN,
            rightMargin=MARGIN,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            title=f"{resume_json.get('name', '简历')} - JobTracer",
            author="JobTracer",
        )

        story = []
        story.extend(self._header(resume_json, styles))
        story.extend(self._summary_section(resume_json, styles))
        story.extend(self._skills_section(resume_json, styles))
        story.extend(self._experience_section(resume_json, styles))
        story.extend(self._projects_section(resume_json, styles))
        story.extend(self._education_section(resume_json, styles))

        doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)

    # ── 各区块 ────────────────────────────────────────────────

    def _header(self, data: dict, styles: dict):
        """头部：姓名 + 联系方式"""
        items = []
        name = data.get("name", "未填写姓名")
        items.append(Paragraph(name, styles["name"]))

        contact_parts = []
        c = data.get("contact") or {}
        if c.get("phone"):
            contact_parts.append(f"📱 {c['phone']}")
        if c.get("email"):
            contact_parts.append(f"✉️ {c['email']}")
        if c.get("location"):
            contact_parts.append(f"📍 {c['location']}")

        if contact_parts:
            items.append(Paragraph("  |  ".join(contact_parts), styles["contact"]))

        items.append(Spacer(1, 6))
        items.append(HRFlowable(width="100%", thickness=2, color=_CLR_PRIMARY))
        items.append(Spacer(1, 10))
        return items

    def _summary_section(self, data: dict, styles: dict):
        """个人总结"""
        summary = data.get("summary", "").strip()
        title = Paragraph("个人总结", styles["section_title"])
        if not summary:
            return [title, Paragraph("暂无个人总结", styles["empty_hint"])]

        cell = Paragraph(summary, styles["summary"])
        table = Table([[cell]], colWidths=[CONTENT_W])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
                    ("BOX", (0, 0), (-1, -1), 0.5, _CLR_BORDER),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        return [title, Spacer(1, 4), table, Spacer(1, 8)]

    def _skills_section(self, data: dict, styles: dict):
        """技能标签（云状布局）"""
        skills = data.get("skills") or []
        title = Paragraph("技术技能", styles["section_title"])
        if not skills:
            return [title, Paragraph("暂无技能数据", styles["empty_hint"])]

        COLS = 6
        rows = []
        for i in range(0, len(skills), COLS):
            chunk = skills[i : i + COLS]
            cells = [Paragraph(s, styles["skill_tag"]) for s in chunk]
            while len(cells) < COLS:
                cells.append(Paragraph("", styles["skill_tag"]))
            rows.append(cells)

        col_w = CONTENT_W / COLS
        t = Table(rows, colWidths=[col_w] * COLS)
        t.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        return [title, Spacer(1, 4), t, Spacer(1, 8)]

    def _experience_section(self, data: dict, styles: dict):
        """工作经历（时间线格式）"""
        experiences = data.get("experience") or []
        title = Paragraph("工作经历", styles["section_title"])

        if not experiences:
            return [title, Paragraph("工作经历数据待确认后填充", styles["empty_hint"])]

        items = [title]
        for exp in experiences:
            items.extend(self._timeline_item(exp, styles))
        return items

    def _timeline_item(self, item: dict, styles: dict):
        """单条时间线条目"""
        title_text = item.get("title") or item.get("name", "")
        company = item.get("company", "")
        duration = item.get("duration", "")
        description = item.get("description", "")

        elems = [
            Paragraph(title_text, styles["timeline_title"]),
            Paragraph(f"{company}  {duration}".strip(), styles["timeline_meta"]),
        ]
        if description:
            elems.append(Paragraph(description, styles["timeline_desc"]))
        elems.append(Spacer(1, 6))
        return [KeepTogether(elems)]

    def _projects_section(self, data: dict, styles: dict):
        """项目经历（卡片格式）"""
        projects = data.get("projects") or []
        title = Paragraph("项目经历", styles["section_title"])

        if not projects:
            return [title, Paragraph("暂无项目数据", styles["empty_hint"])]

        items = [title]
        for proj in projects:
            items.extend(self._project_card(proj, styles))
        return items

    def _project_card(self, proj: dict, styles: dict):
        """单个项目卡片（直接用 Table 实现，避免 KeepTogether 嵌套问题）"""
        name = proj.get("name", "")
        role = proj.get("role", "")
        tech_stack = proj.get("tech_stack") or []
        description = proj.get("description", "")
        metrics = proj.get("metrics", "")

        # 收集所有文字段落
        cell_content = []
        header_text = name
        if role:
            header_text += f"  |  {role}"
        cell_content.append(Paragraph(header_text, styles["project_name"]))

        if tech_stack:
            cell_content.append(Paragraph(" | ".join(tech_stack), styles["project_tech"]))

        if description:
            cell_content.append(Paragraph(description, styles["project_desc"]))

        if metrics:
            cell_content.append(Paragraph(f"🏆 {metrics}", styles["project_metrics"]))

        # 用 1 列 Table 作为卡片容器（左侧 3pt 色条通过 LINEBEFORE 实现）
        wrapper = Table([[cell_content]], colWidths=[CONTENT_W])
        wrapper.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), _CLR_BG),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("BOX", (0, 0), (-1, -1), 0.5, _CLR_BORDER),
                    ("LINEBEFORE", (0, 0), (0, -1), 3, _CLR_PRIMARY),
                ]
            )
        )
        return [Spacer(1, 4), wrapper, Spacer(1, 6)]

    def _education_section(self, data: dict, styles: dict):
        """教育背景"""
        education = data.get("education") or []
        title = Paragraph("教育背景", styles["section_title"])

        if not education:
            return [title, Paragraph("教育背景数据待确认后填充", styles["empty_hint"])]

        items = [title]
        for edu in education:
            school = edu.get("school", "")
            degree = edu.get("degree", "")
            major = edu.get("major", "")
            grad = edu.get("graduation") or edu.get("graduation_year", "")
            line = "  |  ".join(filter(None, [school, f"{degree} {major}".strip(), grad]))
            items.append(Paragraph(line, styles["edu_item"]))
            items.append(Spacer(1, 4))
        return items