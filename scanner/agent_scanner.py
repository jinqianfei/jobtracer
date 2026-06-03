# scanner/agent_scanner.py
# AI 智能体平台扫描器 - 并发扫描各 AI Agent 平台的本地项目
from __future__ import annotations

import asyncio
import json
import os
import re
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional

# ============================================================
# 数据模型
# ============================================================

@dataclass
class AgentProject:
    platform: str           # claude_code / codex / trae / qoder / workbuddy
    project_name: str
    path: str
    description: str
    last_modified: str
    files: List[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================
# 常量配置
# ============================================================

# 各平台扫描路径
PLATFORM_PATHS = {
    "claude_code": Path("~/.claude/projects").expanduser(),
    "codex": Path("~/.codex").expanduser(),
    "trae": Path("~/.trae").expanduser(),
    "qoder": Path("~/.qoder").expanduser(),
    "workbuddy": Path("~/.workbuddy").expanduser(),
}

# 排除目录
EXCLUDE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv",
                "build", "dist", ".idea", ".vscode", "target", ".pytest_cache"}

# 敏感文件关键词（跳过）
SENSITIVE_KEYWORDS = {"password", "key", "token", "secret", ".env", "credentials"}

# 文件读取行数上限
MAX_LINES = 500

# 30天前的时间戳
THIRTY_DAYS_AGO = datetime.now(timezone(timedelta(hours=8))) - timedelta(days=30)


# ============================================================
# 辅助函数
# ============================================================

def _is_sensitive(path: Path) -> bool:
    name_lower = path.name.lower()
    return any(kw in name_lower for kw in SENSITIVE_KEYWORDS)


def _should_exclude(path: Path) -> bool:
    parts = path.parts
    return any(d in parts for d in EXCLUDE_DIRS)


def _mtime(path: Path) -> str:
    try:
        dt = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone(timedelta(hours=8)))
        return dt.isoformat()
    except Exception:
        return ""


def _read_preview(path: Path, max_chars: int = 300) -> str:
    """读取文件前 MAX_LINES 行，提取纯文本预览"""
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()[:MAX_LINES]
        text = "\n".join(lines)
        # 移除 markdown/code 标记
        text = re.sub(r"```[\s\S]*?```", "", text)
        text = re.sub(r"`[^`]+`", "", text)
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
    except Exception:
        return ""


def _scan_dir_files(top_dir: Path, max_depth: int = 2) -> List[str]:
    """扫描目录下可读文件（限深度），返回相对路径列表"""
    files = []
    if not top_dir.exists():
        return files
    try:
        for f in top_dir.iterdir():
            if f.is_file() and not _is_sensitive(f) and f.suffix in {".md", ".txt", ".py", ".js", ".ts", ".json", ".toml"}:
                files.append(f.name)
            elif f.is_dir() and not _should_exclude(f) and max_depth > 0:
                files.extend(_scan_dir_files(f, max_depth - 1))
    except PermissionError:
        pass
    return files


def _extract_project_name(path_str: str) -> str:
    """从路径字符串中提取可读的项目名称"""
    # 去掉前缀路径
    name = os.path.basename(path_str)
    # 解码连字符和下划线
    name = name.replace("-", " ").replace("_", " ")
    # 移除 UUID 片段
    name = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "", name, flags=re.IGNORECASE)
    name = re.sub(r"[0-9a-f]{32}", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+", " ", name).strip()
    return name or path_str


# ============================================================
# 各平台扫描器（同步）
# ============================================================

def _scan_claude_code() -> List[AgentProject]:
    """扫描 Claude Code 项目 (~/.claude/projects/)"""
    projects_dir = PLATFORM_PATHS["claude_code"]
    results = []
    if not projects_dir.exists():
        return results

    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        try:
            # 查找项目描述文件（.md 文件）
            md_files = sorted([f for f in project_dir.iterdir() if f.suffix == ".md" and not _is_sensitive(f)])
            description = ""
            files = []
            for md in md_files:
                description = _read_preview(md, max_chars=300)
                break

            # 扫描目录中的文件（限制深度）
            files = _scan_dir_files(project_dir, max_depth=1)

            # 统计代码行数
            total_lines = 0
            code_files = [f for f in project_dir.rglob("*.py")] + [f for f in project_dir.rglob("*.js")]
            for cf in code_files:
                if _should_exclude(cf):
                    continue
                try:
                    total_lines += len(cf.read_text(encoding="utf-8", errors="ignore").splitlines()[:MAX_LINES])
                except Exception:
                    pass

            results.append(AgentProject(
                platform="claude_code",
                project_name=_extract_project_name(str(project_dir)),
                path=str(project_dir),
                description=description,
                last_modified=_mtime(project_dir),
                files=files,
                metadata={
                    "language": "Python" if any(f.suffix == ".py" for f in code_files) else "Unknown",
                    "lines_of_code": total_lines,
                    "last_session": _mtime(max((project_dir / f) for f in project_dir.iterdir() if f.suffix == ".jsonl"), default=project_dir) if any(project_dir.iterdir()) else "",
                }
            ))
        except Exception as e:
            pass
    return results


def _scan_codex() -> List[AgentProject]:
    """扫描 Codex 项目 (~/.codex/)"""
    codex_root = PLATFORM_PATHS["codex"]
    results = []
    if not codex_root.exists():
        return results

    # Codex sessions 目录
    sessions_dir = codex_root / "sessions"
    memories_db = codex_root / "memories_1.sqlite"

    # 从 SQLite 数据库读取项目信息
    project_name = "Codex Default"
    description = ""
    if memories_db.exists():
        try:
            conn = sqlite3.connect(str(memories_db))
            cursor = conn.cursor()
            # 尝试读取 memories 表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cursor.fetchall()]
            if "memories" in tables:
                cursor.execute("SELECT content FROM memories LIMIT 1")
                row = cursor.fetchone()
                if row:
                    description = str(row[0])[:300]
            conn.close()
        except Exception:
            pass

    # sessions 文件列表
    sessions_files = []
    if sessions_dir.exists():
        try:
            sessions_files = sorted(sessions_dir.rglob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)[:20]
        except PermissionError:
            pass

    last_modified = ""
    if sessions_files:
        last_modified = _mtime(sessions_files[0])

    results.append(AgentProject(
        platform="codex",
        project_name=project_name,
        path=str(codex_root),
        description=description or "Codex 工作区",
        last_modified=last_modified,
        files=[f.name for f in sessions_files],
        metadata={
            "sessions_count": len(sessions_files),
        }
    ))
    return results


def _scan_trae() -> List[AgentProject]:
    """扫描 Trae 项目 (~/.trae/)"""
    trae_root = PLATFORM_PATHS["trae"]
    results = []
    if not trae_root.exists():
        return results

    # Trae 的 projects 目录
    projects_dir = trae_root / "projects"
    if not projects_dir.exists():
        # fallback: 把整个 trae 当作一个项目
        projects_dir = trae_root

    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        try:
            files = _scan_dir_files(project_dir, max_depth=1)
            # 查找描述
            description = ""
            for md in project_dir.glob("*.md"):
                description = _read_preview(md, max_chars=300)
                break

            results.append(AgentProject(
                platform="trae",
                project_name=_extract_project_name(str(project_dir)),
                path=str(project_dir),
                description=description,
                last_modified=_mtime(project_dir),
                files=files,
                metadata={}
            ))
        except Exception:
            pass
    return results


def _scan_qoder() -> List[AgentProject]:
    """扫描 Qoder 项目 (~/.qoder/)"""
    qoder_root = PLATFORM_PATHS["qoder"]
    results = []
    if not qoder_root.exists():
        return results

    projects_dir = qoder_root / "projects"
    if not projects_dir.exists():
        projects_dir = qoder_root

    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        try:
            files = _scan_dir_files(project_dir, max_depth=1)
            description = ""
            for md in project_dir.glob("*.md"):
                description = _read_preview(md, max_chars=300)
                break

            results.append(AgentProject(
                platform="qoder",
                project_name=_extract_project_name(str(project_dir)),
                path=str(project_dir),
                description=description,
                last_modified=_mtime(project_dir),
                files=files,
                metadata={}
            ))
        except Exception:
            pass
    return results


def _scan_workbuddy() -> List[AgentProject]:
    """扫描 WorkBuddy 项目 (~/.workbuddy/projects/)"""
    wb_root = PLATFORM_PATHS["workbuddy"]
    results = []
    if not wb_root.exists():
        return results

    projects_dir = wb_root / "projects"
    if not projects_dir.exists():
        return results

    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        try:
            files = _scan_dir_files(project_dir, max_depth=1)
            description = ""
            for md in project_dir.glob("*.md"):
                description = _read_preview(md, max_chars=300)
                break

            results.append(AgentProject(
                platform="workbuddy",
                project_name=_extract_project_name(str(project_dir)),
                path=str(project_dir),
                description=description,
                last_modified=_mtime(project_dir),
                files=files,
                metadata={}
            ))
        except Exception:
            pass
    return results


# ============================================================
# 并发总入口
# ============================================================

async def scan_agent_platforms() -> List[AgentProject]:
    """
    并发扫描所有 AI Agent 平台，返回项目列表
    
    Returns:
        List[AgentProject]: 所有扫描到的项目
    """
    loop = asyncio.get_event_loop()
    
    # 使用 run_in_executor 将同步扫描函数放到线程池
    tasks = [
        loop.run_in_executor(None, _scan_claude_code),
        loop.run_in_executor(None, _scan_codex),
        loop.run_in_executor(None, _scan_trae),
        loop.run_in_executor(None, _scan_qoder),
        loop.run_in_executor(None, _scan_workbuddy),
    ]
    
    # 并发执行
    results_list = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 合并结果
    all_projects = []
    for i, result in enumerate(results_list):
        if isinstance(result, Exception):
            platform_names = ["claude_code", "codex", "trae", "qoder", "workbuddy"]
            print(f"[AgentScanner] {platform_names[i]} scan error: {result}")
            continue
        all_projects.extend(result)
    
    return all_projects


async def scan_agent_platforms_verbose() -> dict:
    """
    详细版本：并发扫描所有平台，返回带摘要的结构
    
    Returns:
        {
            "total_projects": int,
            "by_platform": dict,
            "projects": List[AgentProject]
        }
    """
    projects = await scan_agent_platforms()
    
    by_platform: dict = {}
    for p in projects:
        by_platform.setdefault(p.platform, []).append(p.to_dict())
    
    return {
        "total_projects": len(projects),
        "by_platform": {k: len(v) for k, v in by_platform.items()},
        "projects": [p.to_dict() for p in projects],
    }


# ============================================================
# 同步包装（兼容非 async 调用）
# ============================================================

def scan_agent_platforms_sync() -> List[AgentProject]:
    """同步版本：扫描所有平台"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(scan_agent_platforms())


# ============================================================
# 测试入口
# ============================================================

if __name__ == "__main__":
    import pprint
    
    async def test():
        print("[AgentScanner] Scanning all AI Agent platforms...")
        result = await scan_agent_platforms_verbose()
        
        print(f"\nTotal projects found: {result['total_projects']}")
        print(f"By platform: {result['by_platform']}")
        print()
        for p in result["projects"]:
            print(f"  [{p['platform']}] {p['project_name']}")
            print(f"    path: {p['path']}")
            print(f"    description: {p['description'][:80]}...")
            print()
        
        return result
    
    asyncio.run(test())