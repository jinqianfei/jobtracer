# scanner/footprint_scanner.py
# 数字足迹扫描编排器 - 并行调度多数据源扫描,统一输出格式
import asyncio
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# 导入各扫描器
from .local_scanner import scan_local
from .openclaw_scanner import scan_openclaw, scan_openclaw_sessions
from .github_scanner import scan_github
from .agent_scanner import scan_agent_platforms, AgentProject

# ============================================================
# 常量配置
# ============================================================

# 全局超时时间(秒)
GLOBAL_TIMEOUT_SECONDS = 300

# 输出路径
OUTPUT_DIR = Path("~/.openclaw-workspaces/product-solution/jobtracer/scanner/results").expanduser()
OUTPUT_FILE = OUTPUT_DIR / "footprint_scan.json"

# 并发扫描顺序（优先级：OpenClaw > GitHub > Local > Agent）
SCAN_PRIORITY = ["openclaw", "github", "local", "agent"]


# ============================================================
# 辅助函数
# ============================================================

def generate_scan_id() -> str:
    """生成唯一扫描ID"""
    return str(uuid.uuid4())[:12]


def ensure_output_dir():
    """确保输出目录存在"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_github_token() -> Optional[str]:
    """从环境变量读取 GitHub Token"""
    return os.environ.get("GITHUB_TOKEN")


# ============================================================
# 各扫描器的异步包装
# ============================================================

async def _run_openclaw_scanner(user_id: str) -> dict:
    """运行 OpenClaw 扫描器(同步→异步)"""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, scan_openclaw, user_id)
    return result


async def _run_github_scanner(user_id: str, github_token: Optional[str] = None) -> dict:
    """运行 GitHub 扫描器(同步→异步)"""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, scan_github, user_id, github_token)
    return result


async def _run_local_scanner(user_id: str) -> dict:
    """运行本地文件扫描器（原生异步）"""
    result = await scan_local(
        user_id=user_id,
        scan_paths=None,  # 使用默认路径
        preferences_path='~/.jobtracer/memory/preferences.json',
        output_path=str(OUTPUT_DIR / "local_files.json")
    )
    return result


async def _run_agent_scanner(user_id: str) -> dict:
    """运行 AI Agent 平台扫描器（原生异步）"""
    loop = asyncio.get_event_loop()
    projects = await scan_agent_platforms()
    return {
        "source": "agent_platforms",
        "projects": [p.to_dict() for p in projects],
        "total_projects": len(projects),
    }


async def _run_openclaw_sessions_scanner(user_id: str) -> dict:
    """运行 OpenClaw 会话扫描器（原生异步）"""
    sessions = await scan_openclaw_sessions(user_id)
    return {
        "source": "openclaw_sessions",
        "sessions": sessions,
        "total_sessions": len(sessions),
    }


# ============================================================
# 单个扫描器的超时包装器
# ============================================================

async def _scan_with_timeout(scanner_name: str, coro, timeout: float = 60.0) -> dict:
    """
    为单个扫描器添加超时控制

    Args:
        scanner_name: 扫描器名称(用于日志)
        coro: 协程对象
        timeout: 超时时间(秒)

    Returns:
        扫描结果或超时/错误信息
    """
    try:
        result = await asyncio.wait_for(coro, timeout=timeout)
        print(f"[FootprintScanner] {scanner_name} completed successfully")
        return {"status": "success", "data": result}
    except asyncio.TimeoutError:
        print(f"[FootprintScanner] {scanner_name} timed out after {timeout}s")
        return {"status": "timeout", "data": None, "error": f"{scanner_name} timeout after {timeout}s"}
    except Exception as e:
        print(f"[FootprintScanner] {scanner_name} failed: {e}")
        return {"status": "error", "data": None, "error": str(e)}


# ============================================================
# 核心编排器
# ============================================================

async def scan_all(
    user_id: str = "",
    scan_paths: List[str] = None,
    github_token: Optional[str] = None,
    timeout_per_scanner: float = 60.0,
    global_timeout: float = GLOBAL_TIMEOUT_SECONDS
) -> dict:
    """
    并行执行所有扫描器,返回聚合结果

    扫描顺序(优先级):
    1. OpenClaw(最快,核心配置)
    2. GitHub(需要Token)
    3. Local(最多文件)

    Args:
        user_id: 用户标识
        scan_paths: 自定义本地扫描路径(可选)
        github_token: GitHub Token(可选,默认从环境变量读取)
        timeout_per_scanner: 每个扫描器的超时时间(秒)
        global_timeout: 全局超时时间(秒)

    Returns:
        聚合扫描结果,格式:
        {
            "scan_id": "xxx",
            "scanned_at": "ISO时间",
            "duration_seconds": float,
            "sources": {
                "openclaw": {"files": int, "status": str, "error": str},
                "github": {"files": int, "status": str, "error": str},
                "local": {"files": int, "status": str, "error": str}
            },
            "files": [...],  # 合并后的文件列表
            "total_files": int
        }
    """
    start_time = datetime.now()
    scan_id = generate_scan_id()

    print(f"[FootprintScanner] Starting scan_all (scan_id={scan_id})")
    print(f"[FootprintScanner] Global timeout: {global_timeout}s, per-scanner timeout: {timeout_per_scanner}s")

    # 确定 GitHub Token
    token = github_token or load_github_token()

    # 构建扫描任务（按优先级顺序）
    scan_tasks = {
        "openclaw": _scan_with_timeout(
            "OpenClaw",
            _run_openclaw_scanner(user_id),
            timeout=timeout_per_scanner
        ),
        "github": _scan_with_timeout(
            "GitHub",
            _run_github_scanner(user_id, token),
            timeout=timeout_per_scanner
        ),
        "local": _scan_with_timeout(
            "Local",
            _run_local_scanner(user_id),
            timeout=timeout_per_scanner
        ),
        "agent": _scan_with_timeout(
            "AgentPlatforms",
            _run_agent_scanner(user_id),
            timeout=timeout_per_scanner
        ),
    }

    # 并发执行所有扫描器
    try:
        results = await asyncio.wait_for(
            asyncio.gather(
                scan_tasks["openclaw"],
                scan_tasks["github"],
                scan_tasks["local"],
                return_exceptions=True
            ),
            timeout=global_timeout
        )
    except asyncio.TimeoutError:
        print(f"[FootprintScanner] Global timeout ({global_timeout}s) exceeded!")
        # 记录哪些任务可能未完成
        results = [
            {"status": "timeout", "data": None, "error": f"Global timeout after {global_timeout}s"},
            {"status": "timeout", "data": None, "error": f"Global timeout after {global_timeout}s"},
            {"status": "timeout", "data": None, "error": f"Global timeout after {global_timeout}s"}
        ]
    except Exception as e:
        print(f"[FootprintScanner] Unexpected error in gather: {e}")
        results = [
            {"status": "error", "data": None, "error": str(e)},
            {"status": "error", "data": None, "error": str(e)},
            {"status": "error", "data": None, "error": str(e)}
        ]

    # 解析结果
    openclaw_result = results[0] if len(results) > 0 else None
    github_result = results[1] if len(results) > 1 else None
    local_result = results[2] if len(results) > 2 else None
    agent_result = results[3] if len(results) > 3 else None

    # 构建源状态摘要
    sources = {
        "openclaw": _build_source_summary(openclaw_result, "openclaw"),
        "github": _build_source_summary(github_result, "github"),
        "local": _build_source_summary(local_result, "local"),
        "agent": _build_source_summary(agent_result, "agent"),
    }

    # 合并文件列表
    all_files = []

    # 合并 OpenClaw 文件
    if openclaw_result and openclaw_result.get("status") == "success":
        data = openclaw_result.get("data", {})
        openclaw_files = data.get("files", [])
        for f in openclaw_files:
            f["source"] = "openclaw"
        all_files.extend(openclaw_files)

    # 合并 GitHub 文件(转换为统一格式)
    if github_result and github_result.get("status") == "success":
        data = github_result.get("data", {})
        github_files = _normalize_github_files(data)
        for f in github_files:
            f["source"] = "github"
        all_files.extend(github_files)

    # 合并 Local 文件
    if local_result and local_result.get("status") == "success":
        data = local_result.get("data", {})
        local_files = data.get("files", [])
        for f in local_files:
            f["source"] = "local"
        all_files.extend(local_files)

    # 合并 Agent 平台项目
    agent_projects = []
    if agent_result and agent_result.get("status") == "success":
        data = agent_result.get("data", {})
        agent_projects = data.get("projects", [])
        for p in agent_projects:
            p["source"] = "agent"
            p["path"] = p.get("path", "")
            p["name"] = p.get("project_name", "")
            p["type"] = "agent_project"
            p["category"] = p.get("platform", "unknown")
            all_files.append(p)

    # 计算总耗时
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # 构建输出结果
    output = {
        "scan_id": scan_id,
        "scanned_at": end_time.isoformat(),
        "start_time": start_time.isoformat(),
        "duration_seconds": round(duration, 2),
        "user_id": user_id,
        "sources": sources,
        "total_files": len(all_files),
        "files": all_files,
        "agent_projects": agent_projects,
    }

    # 保存结果到 JSON 文件
    ensure_output_dir()
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[FootprintScanner] Scan completed in {duration:.2f}s")
    print(f"[FootprintScanner] Total files: {len(all_files)}")
    print(f"[FootprintScanner] Results saved to: {OUTPUT_FILE}")

    return output


def _build_source_summary(result: dict, source_name: str) -> dict:
    """构建单个源的状态摘要"""
    if result is None:
        return {"files": 0, "status": "not_started", "error": "No result"}

    status = result.get("status", "unknown")
    data = result.get("data")
    error = result.get("error")

    file_count = 0
    if status == "success" and data:
        if source_name == "openclaw":
            file_count = len(data.get("files", []))
        elif source_name == "github":
            file_count = len(data.get("repositories", []))
        elif source_name == "local":
            file_count = len(data.get("files", []))
        elif source_name == "agent":
            file_count = len(data.get("projects", []))

    return {
        "files": file_count,
        "status": status,
        "error": error or None
    }


def _normalize_github_files(github_data: dict) -> List[dict]:
    """
    将 GitHub 数据转换为统一文件格式

    GitHub 返回的是 repositories 列表,每个仓库包含 README 等信息。
    这里将每个仓库作为一个"文件条目"。
    """
    files = []
    repositories = github_data.get("repositories", [])

    for repo in repositories:
        files.append({
            "path": repo.get("html_url", ""),
            "name": repo.get("name", ""),
            "type": "repository",
            "category": "github",
            "description": repo.get("description", ""),
            "language": repo.get("language", ""),
            "topics": repo.get("topics", []),
            "stargazers_count": repo.get("stargazers_count", 0),
            "forks_count": repo.get("forks_count", 0),
            "modified": repo.get("updated_at", ""),
            "content_preview": repo.get("readme_preview", "")[:500],
            "issues": repo.get("recent_issues", [])
        })

    return files


# ============================================================
# 便捷入口
# ============================================================

async def scan_footprint(
    user_id: str = "",
    github_token: Optional[str] = None
) -> dict:
    """
    便捷入口:扫描所有数字足迹

    Args:
        user_id: 用户标识
        github_token: GitHub Token(可选)

    Returns:
        聚合扫描结果
    """
    return await scan_all(user_id=user_id, github_token=github_token)


# ============================================================
# 测试入口
# ============================================================

if __name__ == '__main__':
    async def test():
        print("[FootprintScanner] Starting test scan...")

        result = await scan_all(
            user_id='test_user',
            github_token=None,  # 不传则从环境变量读取
            timeout_per_scanner=60.0,
            global_timeout=300.0
        )

        print(f"\n[FootprintScanner] Scan Results:")
        print(f"  Scan ID: {result['scan_id']}")
        print(f"  Duration: {result['duration_seconds']}s")
        print(f"  Total files: {result['total_files']}")
        print(f"\n[FootprintScanner] Source Status:")
        for source, info in result['sources'].items():
            print(f"  [{source}] status={info['status']}, files={info['files']}")
            if info.get('error'):
                print(f"    Error: {info['error']}")

        return result

    asyncio.run(test())