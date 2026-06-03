# scanner/openclaw_scanner.py
# OpenClaw记忆扫描器 - 扫描 ~/.openclaw/workspace/ 工作区和记忆文件
import json
import os
import re
from pathlib import Path
from datetime import datetime, timezone, timedelta

# 扫描路径（按优先级）
OPENCLAW_SCAN_PATHS = [
    ("~/.openclaw/workspace/MEMORY.md", "long_term_memory"),
    ("~/.openclaw/workspace/SOUL.md", "agent_config"),
    ("~/.openclaw/workspace/USER.md", "agent_config"),
    ("~/.openclaw/workspace/AGENTS.md", "agent_config"),
    ("~/.openclaw/workspace/IDENTITY.md", "agent_config"),
    ("~/.openclaw/workspace/SOUL.md", "agent_config"),
]

# workspace 根目录
WORKSPACE_ROOT = Path("~/.openclaw/workspace").expanduser()

# 排除的临时文件/目录
EXCLUDE_NAMES = {".DS_Store", ".git", "node_modules", "__pycache__", ".venv", "venv"}

# 30天前的日期（判断哪些 daily log 需要扫描）
THIRTY_DAYS_AGO = datetime.now(timezone(timedelta(hours=8))) - timedelta(days=30)


def _is_temp_file(name: str) -> bool:
    """判断是否跳过临时文件"""
    name_lower = name.lower()
    return (
        name_lower.startswith(".")
        or name_lower in EXCLUDE_NAMES
        or name_lower.endswith(".lock")
        or name_lower.endswith(".log")
    )


def _extract_plain_text(content: str, max_chars: int = 500) -> str:
    """提取纯文本前max_chars字符，移除markdown标记"""
    # 移除常见markdown语法
    text = re.sub(r"```[\s\S]*?```", "", content)  # 代码块
    text = re.sub(r"`[^`]+`", "", text)  # 行内代码
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)  # 链接
    text = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", "", text)  # 图片
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)  # 列表标记
    text = re.sub(r"^\s*#+\s+", "", text, flags=re.MULTILINE)  # 标题标记
    text = re.sub(r"<[^>]+>", "", text)  # HTML标签
    text = re.sub(r"\s+", " ", text)  # 合并空白
    text = text.strip()
    return text[:max_chars]


def _get_file_modified(path: Path) -> str:
    """获取文件修改时间，ISO格式"""
    try:
        mtime = path.stat().st_mtime
        dt = datetime.fromtimestamp(mtime, tz=timezone(timedelta(hours=8)))
        return dt.isoformat()
    except Exception:
        return ""


def _scan_file(file_path: Path, category: str) -> dict:
    """扫描单个文件，返回结构化信息"""
    try:
        content = file_path.read_text(encoding="utf-8")
        return {
            "path": str(file_path),
            "category": category,
            "name": file_path.name,
            "modified": _get_file_modified(file_path),
            "size": file_path.stat().st_size,
            "content_preview": _extract_plain_text(content, max_chars=500),
        }
    except Exception as e:
        return {
            "path": str(file_path),
            "category": category,
            "name": file_path.name,
            "modified": _get_file_modified(file_path),
            "size": 0,
            "content_preview": "",
            "error": str(e),
        }


def _scan_memory_dir() -> list:
    """扫描 memory/ 目录，返回最近30天的每日日志"""
    memory_dir = WORKSPACE_ROOT / "memory"
    results = []
    if not memory_dir.exists():
        return results

    for f in memory_dir.iterdir():
        if f.is_file() and f.suffix == ".md" and not _is_temp_file(f.name):
            # 只扫描 YYYY-MM-DD.md 格式的文件
            name_without_ext = f.stem
            if re.match(r"^\d{4}-\d{2}-\d{2}$", name_without_ext):
                # 检查修改时间是否在30天内
                mtime = f.stat().st_mtime
                file_dt = datetime.fromtimestamp(mtime, tz=timezone(timedelta(hours=8)))
                if file_dt >= THIRTY_DAYS_AGO:
                    results.append(_scan_file(f, "daily_logs"))
    return results


def _scan_workspace_other_md() -> list:
    """扫描 workspace 根目录下其他的 .md 文件（排除已扫描的核心文件）"""
    core_files = {
        "MEMORY.md", "SOUL.md", "USER.md", "AGENTS.md",
        "IDENTITY.md", "TOOLS.md", "BOOTSTRAP.md",
    }
    results = []
    if not WORKSPACE_ROOT.exists():
        return results

    for f in WORKSPACE_ROOT.iterdir():
        if f.is_file() and f.suffix == ".md" and not _is_temp_file(f.name):
            if f.name not in core_files:
                results.append(_scan_file(f, "workspace_docs"))
    return results


def scan_openclaw(user_id: str = "") -> dict:
    """
    扫描 OpenClaw 用户的工作区和记忆文件

    Args:
        user_id: 用户标识（可选）

    Returns:
        JSON格式扫描结果，包含：
        - source: "openclaw"
        - files: 文件列表（含 path, category, content_preview, modified）
        - summary: 统计摘要（total_files, categories）
    """
    files = []
    categories = {}

    # 1. 扫描核心配置/人格文件（按优先级）
    priority_files = [
        ("~/.openclaw/workspace/MEMORY.md", "long_term_memory"),
        ("~/.openclaw/workspace/SOUL.md", "agent_config"),
        ("~/.openclaw/workspace/USER.md", "agent_config"),
        ("~/.openclaw/workspace/AGENTS.md", "agent_config"),
        ("~/.openclaw/workspace/IDENTITY.md", "agent_config"),
        ("~/.openclaw/workspace/TOOLS.md", "agent_config"),
    ]

    for path_str, category in priority_files:
        path = Path(path_str).expanduser()
        if path.exists() and path.is_file():
            entry = _scan_file(path, category)
            files.append(entry)
            categories[category] = categories.get(category, 0) + 1

    # 2. 扫描 memory/ 目录（最近30天的每日日志）
    memory_files = _scan_memory_dir()
    files.extend(memory_files)
    categories["daily_logs"] = categories.get("daily_logs", 0) + len(memory_files)

    # 3. 扫描 workspace 其他 .md 文件
    other_md_files = _scan_workspace_other_md()
    files.extend(other_md_files)
    categories["workspace_docs"] = categories.get("workspace_docs", 0) + len(other_md_files)

    # 4. 会话记录（可选，仅最近10个，取 summary 而非完整 jsonl）
    sessions_dir = Path("~/.openclaw/agents/main/sessions").expanduser()
    if sessions_dir.exists():
        session_files = sorted(
            [f for f in sessions_dir.iterdir() if f.suffix == ".jsonl" and not _is_temp_file(f.name)],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )[:10]
        for sf in session_files:
            # 只取前100行作为 preview，不读取完整 jsonl（太大）
            try:
                lines = sf.read_text(encoding="utf-8").splitlines()[:100]
                preview = " | ".join(
                    line[:80] for line in lines
                    if line.strip() and not line.strip().startswith("{")
                )[:500]
                files.append({
                    "path": str(sf),
                    "category": "session",
                    "name": sf.name,
                    "modified": _get_file_modified(sf),
                    "size": sf.stat().st_size,
                    "content_preview": preview,
                })
                categories["session"] = categories.get("session", 0) + 1
            except Exception:
                pass

    return {
        "source": "openclaw",
        "files": files,
        "summary": {
            "total_files": len(files),
            "categories": dict(sorted(categories.items())),
        },
    }


if __name__ == "__main__":
    import pprint

    result = scan_openclaw()
    print("=== OpenClaw Scan Result ===")
    print(f"Total files: {result['summary']['total_files']}")
    print(f"Categories: {result['summary']['categories']}")
    print()
    for f in result["files"]:
        print(f"  [{f['category']}] {f['name']} ({f.get('size', 0)} bytes)")
        print(f"    Preview: {f['content_preview'][:100]}...")
        print()