# scanner/github_scanner.py
# GitHub扫描器 - 扫描用户个人仓库（README/Issues）

import os
import base64
import requests
from datetime import datetime
from typing import Optional

GITHUB_API = "https://api.github.com"

# 默认请求头（无Token）
DEFAULT_HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "JobTracer/1.0"
}


def scan_github(user_id: str, github_token: str = None) -> dict:
    """
    扫描用户GitHub仓库信息。

    Args:
        user_id: 用户ID（用于返回结构）
        github_token: GitHub Personal Access Token（从环境变量GITHUB_TOKEN读取）

    Returns:
        dict: {
            "source": "github",
            "user": {...},
            "repositories": [...],
            "scanned_at": "...",
            "error": None or "..."
        }
    """
    token = github_token or os.environ.get("GITHUB_TOKEN")

    # 如果没有Token，返回友好的空结果+提示
    if not token:
        return {
            "source": "github",
            "user": None,
            "repositories": [],
            "scanned_at": datetime.now().isoformat(),
            "error": "GITHUB_TOKEN not found. Please set the GITHUB_TOKEN environment variable."
        }

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "JobTracer/1.0"
    }

    try:
        # 1. 获取用户个人资料
        user = _fetch_user_info(headers)
        if user.get("error"):
            return {
                "source": "github",
                "user": None,
                "repositories": [],
                "scanned_at": datetime.now().isoformat(),
                "error": user["error"]
            }

        # 2. 获取仓库列表
        repos = _fetch_repos(headers)
        if repos.get("error"):
            return {
                "source": "github",
                "user": user,
                "repositories": [],
                "scanned_at": datetime.now().isoformat(),
                "error": repos["error"]
            }

        # 3. 扫描每个仓库的详情
        repositories = _scan_repos_details(headers, repos["repos"])

        return {
            "source": "github",
            "user": user,
            "repositories": repositories,
            "scanned_at": datetime.now().isoformat(),
            "error": None
        }

    except requests.exceptions.Timeout:
        return {
            "source": "github",
            "user": None,
            "repositories": [],
            "scanned_at": datetime.now().isoformat(),
            "error": "GitHub API request timeout. Please try again later."
        }
    except requests.exceptions.ConnectionError:
        return {
            "source": "github",
            "user": None,
            "repositories": [],
            "scanned_at": datetime.now().isoformat(),
            "error": "Failed to connect to GitHub. Please check your network connection."
        }
    except Exception as e:
        return {
            "source": "github",
            "user": None,
            "repositories": [],
            "scanned_at": datetime.now().isoformat(),
            "error": f"Unexpected error: {str(e)}"
        }


def _fetch_user_info(headers: dict) -> dict:
    """获取GitHub用户个人资料"""
    try:
        resp = requests.get(f"{GITHUB_API}/user", headers=headers, timeout=30)
        if resp.status_code == 401:
            return {"error": "Invalid GITHUB_TOKEN. Please check your token."}
        if resp.status_code == 403:
            return {"error": "GitHub API rate limit exceeded or access forbidden."}
        if resp.status_code != 200:
            return {"error": f"Failed to fetch user info: HTTP {resp.status_code}"}

        data = resp.json()
        return {
            "login": data.get("login", ""),
            "name": data.get("name", ""),
            "bio": data.get("bio", ""),
            "company": data.get("company", ""),
            "blog": data.get("blog", ""),
            "public_repos": data.get("public_repos", 0),
            "followers": data.get("followers", 0),
            "following": data.get("following", 0),
            "avatar_url": data.get("avatar_url", ""),
            "html_url": data.get("html_url", "")
        }
    except requests.exceptions.RequestException as e:
        return {"error": f"Request error: {str(e)}"}


def _fetch_repos(headers: dict, per_page: int = 20) -> dict:
    """获取用户最近更新的仓库列表"""
    try:
        resp = requests.get(
            f"{GITHUB_API}/user/repos",
            headers=headers,
            params={"sort": "updated", "per_page": per_page},
            timeout=30
        )
        if resp.status_code == 403:
            return {"error": "GitHub API rate limit exceeded.", "repos": []}
        if resp.status_code != 200:
            return {"error": f"Failed to fetch repositories: HTTP {resp.status_code}", "repos": []}

        repos = resp.json()
        return {"repos": repos, "error": None}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request error: {str(e)}", "repos": []}


def _scan_repos_details(headers: dict, repos: list) -> list:
    """
    扫描每个仓库的详情：README、描述、topics、最近10个Issues、主要语言
    """
    results = []

    for repo in repos:
        repo_name = repo.get("name", "")
        full_name = repo.get("full_name", "")

        repo_info = {
            "name": repo_name,
            "full_name": full_name,
            "description": repo.get("description", ""),
            "language": repo.get("language", ""),
            "topics": repo.get("topics", []),
            "updated_at": repo.get("updated_at", ""),
            "stargazers_count": repo.get("stargazers_count", 0),
            "forks_count": repo.get("forks_count", 0),
            "html_url": repo.get("html_url", ""),
            "readme_preview": "",
            "recent_issues": []
        }

        # 读取README（Base64解码）
        readme_preview = _fetch_readme(headers, full_name)
        if readme_preview:
            repo_info["readme_preview"] = readme_preview

        # 读取最近10个Issues
        issues = _fetch_recent_issues(headers, full_name, limit=10)
        if issues:
            repo_info["recent_issues"] = issues

        results.append(repo_info)

    return results


def _fetch_readme(headers: dict, full_name: str, max_chars: int = 500) -> str:
    """获取仓库README.md内容（Base64解码，截取前max_chars字符）"""
    try:
        resp = requests.get(
            f"{GITHUB_API}/repos/{full_name}/readme",
            headers=headers,
            timeout=15
        )
        if resp.status_code != 200:
            return ""

        data = resp.json()
        content_b64 = data.get("content", "")
        if not content_b64:
            return ""

        # Base64解码
        # 移除可能的换行符
        content_b64 = content_b64.replace("\n", "").replace("\r", "")
        try:
            content = base64.b64decode(content_b64).decode("utf-8")
        except Exception:
            return ""

        # 截取前max_chars字符
        return content[:max_chars]

    except requests.exceptions.RequestException:
        return ""
    except Exception:
        return ""


def _fetch_recent_issues(headers: dict, full_name: str, limit: int = 10) -> list:
    """获取仓库最近limit个Issues（标题和状态）"""
    try:
        resp = requests.get(
            f"{GITHUB_API}/repos/{full_name}/issues",
            headers=headers,
            params={"state": "all", "per_page": limit},
            timeout=15
        )
        if resp.status_code != 200:
            return []

        issues_raw = resp.json()
        issues = []
        for issue in issues_raw:
            # 排除Pull Request（它们也在issues里）
            if "pull_request" in issue:
                continue
            issues.append({
                "title": issue.get("title", ""),
                "state": issue.get("state", ""),
                "labels": [label["name"] for label in issue.get("labels", [])]
            })

        return issues

    except requests.exceptions.RequestException:
        return []
    except Exception:
        return []


# 异步版本（预留，供footprint_scanner编排器调用）
def scan_github_async(user_id: str, github_token: str = None):
    """
    异步入口（兼容asyncio编排器）
    返回一个可await的对象/协程。
    这里直接调用同步版本作为简化实现。
    """
    import asyncio
    return asyncio.to_thread(scan_github, user_id, github_token)