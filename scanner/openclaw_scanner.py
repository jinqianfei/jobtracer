# scanner/openclaw_scanner.py
# OpenClaw记忆扫描器 - 扫描 ~/.openclaw/workspace/ 工作区和记忆文件
import asyncio
import json
import os
import re
import sqlite3
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Optional

# ============================================================
# 数据模型
# ============================================================

@dataclass
class SessionProject:
    """从会话记录中提取的项目信息"""
    session_id: str
    session_path: str
    project_name: str
    last_active: str
    tech_stack: List[str] = field(default_factory=list)
    collaboration: List[str] = field(default_factory=list)
    message_count: int = 0
    content_preview: str = ""


# ============================================================
# 常量配置
# ============================================================

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

# OpenClaw sessions 目录
SESSIONS_ROOT = Path("~/.openclaw/agents/main/sessions").expanduser()

# 排除的临时文件/目录
EXCLUDE_NAMES = {".DS_Store", ".git", "node_modules", "__pycache__", ".venv", "venv"}

# 30天前的日期（判断哪些 daily log 需要扫描）
THIRTY_DAYS_AGO = datetime.now(timezone(timedelta(hours=8))) - timedelta(days=30)

# 技术栈关键词（用于从消息中识别）
TECH_KEYWORDS = [
    "Python", "JavaScript", "TypeScript", "Go", "Rust", "Java", "C++", "C#",
    "React", "Vue", "Angular", "Node.js", "FastAPI", "Django", "Flask",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
    "Docker", "Kubernetes", "AWS", "GCP", "Azure",
    "Git", "GitHub", "GitLab",
    "LangChain", "OpenAI", "Anthropic", "Claude", "LLaMA",
    "TensorFlow", "PyTorch", "scikit-learn", "pandas", "numpy",
    "REST", "GraphQL", "gRPC", "WebSocket",
    "React Native", "Flutter", "Swift", "Kotlin",
    "Linux", "macOS", "Windows",
]

# 项目名提取模式
PROJECT_PATTERNS = [
    (r"project[_\s]?name[:\s]+([^\s,\n]+)", "explicit_project"),
    (r"project[:\s]+([a-zA-Z0-9_\-]+)", "explicit_project"),
    (r"正在开发[的as]*(.+?)[。，,\n]", "chinese_project"),
    (r"working on[:\s]+(.+?)[。，,\n]", "english_project"),
    (r"/([a-zA-Z0-9_\-]{3,20})(?:/|$)", "url_path"),
]


# ============================================================
# 辅助函数
# ============================================================

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
    text = re.sub(r"```[\s\S]*?```", "", content)
    text = re.sub(r"`[^`]+`", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", "", text)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*#+\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
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
            name_without_ext = f.stem
            if re.match(r"^\d{4}-\d{2}-\d{2}$", name_without_ext):
                mtime = f.stat().st_mtime
                file_dt = datetime.fromtimestamp(mtime, tz=timezone(timedelta(hours=8)))
                if file_dt >= THIRTY_DAYS_AGO:
                    results.append(_scan_file(f, "daily_logs"))
    return results


def _scan_workspace_other_md() -> list:
    """扫描 workspace 根目录下其他的 .md 文件"""
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


def _extract_tech_stack(text: str) -> List[str]:
    """从文本中识别技术栈关键词"""
    found = []
    text_lower = text.lower()
    for kw in TECH_KEYWORDS:
        if kw.lower() in text_lower:
            found.append(kw)
    return list(set(found))


def _extract_project_names(text: str) -> List[str]:
    """从文本中提取项目名称"""
    names = []
    for pattern, ptype in PROJECT_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            name = m.strip() if isinstance(m, str) else str(m).strip()
            if len(name) >= 2 and len(name) <= 30 and not name.startswith("http"):
                names.append(name)
    return list(set(names))


def _parse_session_jsonl(file_path: Path, max_lines: int = 200) -> dict:
    """解析 session JSONL 文件，提取项目相关信息"""
    try:
        lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()[:max_lines]
    except Exception:
        return {}

    tech_stack: set = set()
    project_names: set = set()
    message_count = 0
    last_timestamp = ""
    preview_lines = []

    for line in lines:
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except Exception:
            continue

        # 统计消息数量
        if entry.get("type") == "message":
            message_count += 1

        # 提取时间戳
        ts = entry.get("timestamp", "")
        if ts:
            last_timestamp = ts

        # 从消息内容中提取技术栈和项目名
        content = ""
        if entry.get("type") == "message":
            msg = entry.get("message", {})
            if isinstance(msg, dict):
                content = msg.get("content", "")
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            content += block.get("text", "")
                elif not isinstance(content, str):
                    content = str(content)
            elif isinstance(content, str):
                pass
            else:
                content = str(content)

        if content:
            # 提取预览（前500字符）
            clean = _extract_plain_text(content, max_chars=200)
            if clean:
                preview_lines.append(clean[:100])
            # 提取技术栈
            tech_stack.update(_extract_tech_stack(content))
            # 提取项目名
            project_names.update(_extract_project_names(content))

    return {
        "tech_stack": list(tech_stack),
        "project_names": list(project_names),
        "message_count": message_count,
        "last_timestamp": last_timestamp,
        "preview": " | ".join(preview_lines)[:500],
    }


# ============================================================
# 会话扫描（核心新增功能）
# ============================================================

async def scan_openclaw_sessions(user_id: str = "") -> List[dict]:
    """
    扫描 OpenClaw 会话记录，提取项目相关讨论
    
    Args:
        user_id: 用户标识（可选）
        
    Returns:
        List[dict]: 会话项目列表，每项包含：
        - session_id: str
        - session_path: str
        - project_name: str
        - tech_stack: List[str]
        - collaboration: List[str]
        - last_active: str
        - message_count: int
        - content_preview: str
    """
    sessions_dir = SESSIONS_ROOT
    if not sessions_dir.exists():
        return []

    # 获取所有 session 文件（按修改时间倒序）
    session_files = sorted(
        [f for f in sessions_dir.iterdir() if f.suffix == ".jsonl" and not _is_temp_file(f.name)],
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )

    results: List[dict] = []
    seen_session_ids: set = set()

    # 并发读取 session 文件（限制最多30个，取最新的）
    async def parse_session(file_path: Path) -> Optional[dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _parse_session_jsonl, file_path)

    tasks = [parse_session(f) for f in session_files[:30]]
    parsed_list = await asyncio.gather(*tasks, return_exceptions=True)

    for file_path, parsed in zip(session_files[:30], parsed_list):
        if isinstance(parsed, Exception):
            continue
        if not parsed or parsed.get("message_count", 0) == 0:
            continue

        session_id = file_path.stem
        if session_id in seen_session_ids:
            continue
        seen_session_ids.add(session_id)

        # 提取主项目名（取第一个或最长的）
        project_names = parsed.get("project_names", [])
        project_name = project_names[0] if project_names else f"Session-{session_id[:8]}"

        # 提取协作记录（subagent 相关）
        collaboration: List[str] = []
        preview = parsed.get("preview", "")
        if "subagent" in preview.lower() or "sub-agent" in preview.lower():
            collaboration.append("subagent")
        if "jobtracer" in preview.lower():
            collaboration.append("jobtracer")

        # 格式化最后活跃时间
        last_active = ""
        ts = parsed.get("last_timestamp", "")
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                dt_local = dt.astimezone(timezone(timedelta(hours=8)))
                last_active = dt_local.isoformat()
            except Exception:
                last_active = ts

        results.append({
            "session_id": session_id,
            "session_path": str(file_path),
            "project_name": project_name,
            "tech_stack": parsed.get("tech_stack", []),
            "collaboration": collaboration,
            "last_active": last_active,
            "message_count": parsed.get("message_count", 0),
            "content_preview": preview[:300],
        })

    return results


async def scan_openclaw_sessions_verbose(user_id: str = "") -> dict:
    """
    详细版本：扫描会话记录，返回带摘要的结构
    
    Returns:
        {
            "total_sessions": int,
            "sessions": List[dict],
            "tech_stacks": List[str],
            "projects": List[str],
        }
    """
    sessions = await scan_openclaw_sessions(user_id)

    all_tech: set = set()
    all_projects: set = set()
    for s in sessions:
        all_tech.update(s.get("tech_stack", []))
        all_projects.add(s.get("project_name", ""))

    return {
        "total_sessions": len(sessions),
        "sessions": sessions,
        "tech_stacks": sorted(all_tech),
        "projects": sorted(all_projects),
    }


# ============================================================
# 原有函数（保持兼容）
# ============================================================

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

    # 4. 会话记录（保留旧逻辑，仅取 summary）
    sessions_dir = SESSIONS_ROOT
    if sessions_dir.exists():
        session_files = sorted(
            [f for f in sessions_dir.iterdir() if f.suffix == ".jsonl" and not _is_temp_file(f.name)],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )[:10]
        for sf in session_files:
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


# ============================================================
# 测试入口
# ============================================================

if __name__ == "__main__":
    import pprint

    print("=== Running scan_openclaw ===")
    result = scan_openclaw()
    print(f"Total files: {result['summary']['total_files']}")
    print(f"Categories: {result['summary']['categories']}")
    print()

    print("=== Running scan_openclaw_sessions ===")
    
    async def test_sessions():
        sessions_result = await scan_openclaw_sessions_verbose()
        print(f"Total sessions: {sessions_result['total_sessions']}")
        print(f"Tech stacks: {sessions_result['tech_stacks']}")
        print(f"Projects: {sessions_result['projects']}")
        print()
        for s in sessions_result["sessions"][:5]:
            print(f"  [{s['session_id'][:8]}] {s['project_name']}")
            print(f"    tech: {s['tech_stack']}")
            print(f"    messages: {s['message_count']}")
            print(f"    preview: {s['content_preview'][:80]}...")
            print()
        return sessions_result
    
    asyncio.run(test_sessions())