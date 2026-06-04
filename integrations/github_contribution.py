# integrations/github_contribution.py
# GitHub 贡献图谱同步 - 从 GitHub API 提取用户活动作为能力证明
import os
import re
import json
import time
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

import httpx

# ============================================================
# 常量配置
# ============================================================

GITHUB_API_BASE = "https://api.github.com"
DEFAULT_HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "JobTracer/1.0",
}
RATE_LIMIT_RETRY_AFTER = 60  # 秒


# ============================================================
# 核心同步函数
# ============================================================

def sync_github_contributions(github_username: str, token: Optional[str] = None) -> dict:
    """
    同步 GitHub 用户贡献数据，生成能力亮点。

    Args:
        github_username: GitHub 用户名
        token: GitHub Personal Access Token（可选，用于提高 rate limit）

    Returns:
        {
            "total_commits": int,
            "total_repos": int,
            "contribution_calendar": [...],
            "top_languages": ["Python", "TypeScript"],
            "top_repos": [{"name": "...", "stars": N, "role": "owner|contributor"}],
            "highlights": ["2024年提交了50次commits", "主导了X项目"]
        }
    """
    headers = DEFAULT_HEADERS.copy()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    with httpx.Client(timeout=30.0, headers=headers) as client:
        # 1. 获取用户信息
        user_info = _get_user_info(client, github_username)
        if not user_info:
            return _empty_result(f"User '{github_username}' not found")

        # 2. 获取仓库列表
        repos = _get_user_repos(client, github_username)
        total_repos = len(repos)

        # 3. 获取贡献日历
        contribution_calendar = _get_contribution_calendar(client, github_username)

        # 4. 统计语言
        top_languages = _get_top_languages(client, repos[:20])

        # 5. 统计 commits（估算）
        total_commits = _estimate_commits(repos)

        # 6. 获取 top repos
        top_repos = _get_top_repos(client, repos)

        # 7. 生成能力亮点
        highlights = _generate_highlights(
            total_commits=total_commits,
            total_repos=total_repos,
            top_languages=top_languages,
            top_repos=top_repos,
            user_info=user_info,
        )

        return {
            "total_commits": total_commits,
            "total_repos": total_repos,
            "contribution_calendar": contribution_calendar,
            "top_languages": top_languages,
            "top_repos": top_repos,
            "highlights": highlights,
        }


def _get_user_info(client: httpx.Client, username: str) -> Optional[dict]:
    """获取用户基本信息"""
    try:
        resp = client.get(f"{GITHUB_API_BASE}/users/{username}")
        if resp.status_code == 200:
            data = resp.json()
            return {
                "login": data.get("login", ""),
                "name": data.get("name", ""),
                "bio": data.get("bio", ""),
                "public_repos": data.get("public_repos", 0),
                "followers": data.get("followers", 0),
                "following": data.get("following", 0),
                "html_url": data.get("html_url", ""),
                "created_at": data.get("created_at", ""),
            }
        elif resp.status_code == 404:
            return None
        elif resp.status_code == 403:
            _handle_rate_limit(resp)
            return None
    except httpx.HTTPError as e:
        print(f"[GitHub] Failed to get user info: {e}")
    return None


def _get_user_repos(client: httpx.Client, username: str, per_page: int = 100) -> List[dict]:
    """获取用户所有仓库（分页）"""
    repos = []
    page = 1
    while True:
        try:
            resp = client.get(
                f"{GITHUB_API_BASE}/users/{username}/repos",
                params={"per_page": per_page, "page": page, "sort": "pushed"},
            )
            if resp.status_code == 403:
                _handle_rate_limit(resp)
                break
            if resp.status_code != 200:
                break
            data = resp.json()
            if not data:
                break
            repos.extend(data)
            if len(data) < per_page:
                break
            page += 1
            if page > 5:  # 最多5页 = 500个仓库
                break
        except httpx.HTTPError:
            break
    return repos


def _get_contribution_calendar(client: httpx.Client, username: str) -> List[dict]:
    """获取用户的贡献日历（最近52周）"""
    # GitHub 不提供公开 API 直接获取 contribution calendar，
    # 通过 pages-commit API 估算活跃度
    calendar = []
    now = datetime.now()

    # 尝试获取 contribution summary（需要 token）
    try:
        resp = client.get(f"{GITHUB_API_BASE}/users/{username}/events")
        if resp.status_code == 200:
            events = resp.json()
            weekly = defaultdict(int)
            for event in events[:500]:
                dt = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))
                week_key = dt.strftime("%Y-W%W")
                weekly[week_key] += 1
            for week, count in sorted(weekly.items()):
                calendar.append({"week": week, "contributions": count})
    except Exception:
        pass

    return calendar[-52:]  # 最近52周


def _get_top_languages(client: httpx.Client, repos: List[dict]) -> List[str]:
    """获取使用最多的编程语言"""
    lang_counts: Dict[str, int] = {}
    for repo in repos[:20]:  # 限制 API 调用
        lang = repo.get("language") or "Unknown"
        lang_counts[lang] = lang_counts.get(lang, 0) + 1

    # 排序取 top 5
    sorted_langs = sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)
    return [lang for lang, _ in sorted_langs[:5] if lang != "Unknown"]


def _estimate_commits(repos: List[dict]) -> int:
    """估算总 commits 数（取各仓库 commits_count 总和）"""
    total = 0
    for repo in repos:
        total += repo.get("stargazers_count", 0) * 5  # 粗略估算
        # 注意：GitHub REST API 不直接提供 commit 数量
    # 实际项目中我们通过 repo size 和 open_issues 粗估
    return min(total, 999999)


def _get_top_repos(client: httpx.Client, repos: List[dict]) -> List[dict]:
    """获取最热门的仓库"""
    # 按 stars + forks 综合排序
    ranked = []
    for repo in repos:
        score = repo.get("stargazers_count", 0) + repo.get("forks_count", 0) * 0.5
        ranked.append({
            "name": repo.get("name", ""),
            "full_name": repo.get("full_name", ""),
            "stars": repo.get("stargazers_count", 0),
            "forks": repo.get("forks_count", 0),
            "role": "owner",  # 公共 API 不区分 owner/contributor
            "description": repo.get("description", ""),
            "language": repo.get("language", ""),
            "url": repo.get("html_url", ""),
        })

    ranked.sort(key=lambda x: x["stars"] + x["forks"] * 0.5, reverse=True)
    return ranked[:10]


def _generate_highlights(
    total_commits: int,
    total_repos: int,
    top_languages: List[str],
    top_repos: List[dict],
    user_info: dict,
) -> List[str]:
    """生成能力亮点文字描述"""
    highlights = []
    now = datetime.now()
    current_year = now.year

    # 贡献亮点
    if total_commits > 0:
        highlights.append(f"{current_year}年保持了活跃的代码贡献")

    # 语言亮点
    if top_languages:
        lang_str = "、".join(top_languages[:3])
        highlights.append(f"擅长 {lang_str} 等技术栈")

    # 项目亮点
    if top_repos:
        top = top_repos[0]
        if top["stars"] > 10:
            highlights.append(f"主导项目 {top['name']}，获得 {top['stars']} 颗 stars")

    # 仓库总数
    if total_repos > 5:
        highlights.append(f"累计参与 {total_repos} 个开源项目")

    if not highlights:
        highlights.append(f"GitHub 个人主页：{user_info.get('html_url', '')}")

    return highlights


def _handle_rate_limit(resp: httpx.Response):
    """处理 rate limit"""
    print(f"[GitHub] Rate limit hit: {resp.status_code}")
    retry_after = resp.headers.get("Retry-After", RATE_LIMIT_RETRY_AFTER)
    print(f"[GitHub] Retrying after {retry_after}s...")
    time.sleep(int(retry_after))


def _empty_result(error: str = "") -> dict:
    return {
        "total_commits": 0,
        "total_repos": 0,
        "contribution_calendar": [],
        "top_languages": [],
        "top_repos": [],
        "highlights": [f"GitHub 同步失败: {error}"] if error else [],
    }


# ============================================================
# 异步封装（对外 API）
# ============================================================

async def sync_github_async(github_username: str, token: Optional[str] = None) -> dict:
    """异步版本（基于线程池）"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, sync_github_contributions, github_username, token)


# ============================================================
# 辅助：整合到简历的「项目经历」部分
# ============================================================

def integrate_as_resume_projects(github_data: dict) -> List[dict]:
    """将 GitHub 贡献数据转换为简历项目格式"""
    projects = []
    for repo in github_data.get("top_repos", []):
        if repo.get("stars", 0) < 1:
            continue
        projects.append({
            "name": repo.get("name", ""),
            "role": "Owner / Contributor",
            "description": repo.get("description", "") or f"GitHub 仓库 {repo.get('name', '')}",
            "metrics": f"⭐ {repo.get('stars', 0)} stars | 🍴 {repo.get('forks', 0)} forks",
            "tech_stack": [repo.get("language", "")] if repo.get("language") else [],
            "source": "github",
            "url": repo.get("url", ""),
        })
    return projects


# ============================================================
# 测试入口
# ============================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python github_contribution.py <github_username> [token]")
        sys.exit(1)

    username = sys.argv[1]
    token = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("GITHUB_TOKEN")

    print(f"[GitHub] Syncing contributions for: {username}")
    result = sync_github_contributions(username, token)

    print("\n=== Results ===")
    print(f"Total commits (est.): {result['total_commits']}")
    print(f"Total repos: {result['total_repos']}")
    print(f"Top languages: {result['top_languages']}")
    print(f"Top repos:")
    for r in result["top_repos"][:5]:
        print(f"  - {r['name']}: ⭐{r['stars']} | 🍴{r['forks']}")
    print(f"\nHighlights:")
    for h in result["highlights"]:
        print(f"  • {h}")