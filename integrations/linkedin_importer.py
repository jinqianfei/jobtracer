# integrations/linkedin_importer.py
# LinkedIn 简历导入 - 读取 LinkedIn 个人主页信息填充简历
import json
import re
import httpx
from typing import Optional, List, Dict, Any

# ============================================================
# 常量
# ============================================================

LINKEDIN_BASE_URL = "https://www.linkedin.com"
DEFAULT_TIMEOUT = 15.0


# ============================================================
# 核心导入函数
# ============================================================

def import_linkedin_profile(cookie: Optional[str] = None) -> dict:
    """
    导入 LinkedIn 个人资料。

    ⚠️ LinkedIn 需要登录 Cookie，公共 API 非常有限。
    无 Cookie 时返回 graceful degradation 结果（空的/示例数据）。

    Args:
        cookie: LinkedIn 登录 Cookie（li_at 或类似）

    Returns:
        {
            "name": "...",
            "headline": "...",
            "experience": [
                {
                    "company": "...",
                    "title": "...",
                    "start_date": "YYYY-MM",
                    "end_date": "YYYY-MM or null",
                    "description": "...",
                    "duration": "X years Y months"
                }
            ],
            "education": [
                {
                    "school": "...",
                    "degree": "...",
                    "major": "...",
                    "start_date": "YYYY",
                    "end_date": "YYYY"
                }
            ],
            "skills": ["..."],
            "certifications": ["..."]
        }
    """
    if not cookie:
        return _graceful_degradation("LinkedIn Cookie 未提供，跳过导入")

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/vnd.linkedin.v2.dplus+json",
        "Cookie": cookie,
        "Csrf-Token": _extract_csrf_token(cookie) or "",
    }

    profile = {}

    with httpx.Client(timeout=DEFAULT_TIMEOUT, headers=headers) as client:
        # 1. 获取基础资料
        profile = _fetch_basic_profile(client, headers)
        if not profile:
            return _graceful_degradation("无法获取 LinkedIn 资料，请检查 Cookie 是否有效")

        # 2. 获取工作经历
        profile["experience"] = _fetch_experience(client, headers)

        # 3. 获取教育经历
        profile["education"] = _fetch_education(client, headers)

        # 4. 获取技能
        profile["skills"] = _fetch_skills(client, headers)

        # 5. 获取认证
        profile["certifications"] = _fetch_certifications(client, headers)

    return profile


def _fetch_basic_profile(client: httpx.Client, headers: dict) -> dict:
    """获取基础个人信息"""
    try:
        resp = client.get(
            f"{LINKEDIN_BASE_URL}/voyager/api/me",
            headers=headers,
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "name": data.get("formattedName", ""),
                "headline": data.get("headline", ""),
                "location": data.get("locationName", ""),
                "profile_url": data.get("publicProfileUrl", ""),
            }
        elif resp.status_code == 401:
            return {}
    except httpx.HTTPError as e:
        print(f"[LinkedIn] Failed to fetch basic profile: {e}")
    return {}


def _fetch_experience(client: httpx.Client, headers: dict) -> List[dict]:
    """获取工作经历"""
    experience = []
    try:
        # LinkedIn Voyager API for positions
        resp = client.get(
            f"{LINKEDIN_BASE_URL}/voyager/api/profile/positions",
            headers=headers,
            params={"count": 20, "start": 0},
        )
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("elements", []):
                experience.append({
                    "company": item.get("companyName", ""),
                    "title": item.get("title", ""),
                    "start_date": _format_date(item.get("startDate")),
                    "end_date": _format_date(item.get("endDate")) if item.get("endDate") else None,
                    "description": item.get("description", ""),
                    "location": item.get("locationName", ""),
                })
    except httpx.HTTPError as e:
        print(f"[LinkedIn] Failed to fetch experience: {e}")
    return experience


def _fetch_education(client: httpx.Client, headers: dict) -> List[dict]:
    """获取教育经历"""
    education = []
    try:
        resp = client.get(
            f"{LINKEDIN_BASE_URL}/voyager/api/profile/education",
            headers=headers,
            params={"count": 10, "start": 0},
        )
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("elements", []):
                education.append({
                    "school": item.get("schoolName", ""),
                    "degree": item.get("degreeName", ""),
                    "major": item.get("fieldOfStudy", ""),
                    "start_date": str(item.get("startDate", {}).get("year", "")),
                    "end_date": str(item.get("endDate", {}).get("year", "")),
                })
    except httpx.HTTPError as e:
        print(f"[LinkedIn] Failed to fetch education: {e}")
    return education


def _fetch_skills(client: httpx.Client, headers: dict) -> List[str]:
    """获取技能列表"""
    skills = []
    try:
        resp = client.get(
            f"{LINKEDIN_BASE_URL}/voyager/api/profile/skills",
            headers=headers,
            params={"count": 50, "start": 0},
        )
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("elements", []):
                name = item.get("name", "")
                if name:
                    skills.append(name)
    except httpx.HTTPError:
        pass
    return skills


def _fetch_certifications(client: httpx.Client, headers: dict) -> List[str]:
    """获取认证"""
    certs = []
    try:
        resp = client.get(
            f"{LINKEDIN_BASE_URL}/voyager/api/profile/certifications",
            headers=headers,
            params={"count": 20, "start": 0},
        )
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("elements", []):
                name = item.get("name", "")
                if name:
                    certs.append(name)
    except httpx.HTTPError:
        pass
    return certs


def _format_date(date_obj: dict) -> Optional[str]:
    """格式化日期对象为 YYYY-MM"""
    if not date_obj:
        return None
    year = date_obj.get("year", "")
    month = date_obj.get("month", "")
    if year and month:
        return f"{year}-{str(month).zfill(2)}"
    elif year:
        return str(year)
    return None


def _extract_csrf_token(cookie: str) -> Optional[str]:
    """从 Cookie 中提取 CSRF token"""
    # 通常 CSRF token 叫 JSESSIONID 或类似
    match = re.search(r'csrfToken=([^;]+)', cookie)
    if match:
        return match.group(1)
    return None


def _graceful_degradation(reason: str) -> dict:
    """
    Graceful degradation - LinkedIn 无 Cookie/API 受限时返回空结构，
    不抛出异常，不中断流程。
    """
    return {
        "name": "",
        "headline": "",
        "experience": [],
        "education": [],
        "skills": [],
        "certifications": [],
        "_import_note": reason,
    }


# ============================================================
# 异步封装
# ============================================================

async def import_linkedin_async(cookie: Optional[str] = None) -> dict:
    """异步版本"""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, import_linkedin_profile, cookie)


# ============================================================
# 辅助：转换为简历 experience 格式
# ============================================================

def convert_to_resume_experience(linkedin_data: dict) -> List[dict]:
    """将 LinkedIn 工作经历转换为简历格式"""
    resume_exp = []
    for exp in linkedin_data.get("experience", []):
        duration = ""
        start = exp.get("start_date", "")
        end = exp.get("end_date", "") or "至今"
        if start and end:
            duration = f"{start} ~ {end}"

        resume_exp.append({
            "company": exp.get("company", ""),
            "title": exp.get("title", ""),
            "duration": duration,
            "description": exp.get("description", ""),
        })
    return resume_exp


def convert_to_resume_education(linkedin_data: dict) -> List[dict]:
    """将 LinkedIn 教育经历转换为简历格式"""
    resume_edu = []
    for edu in linkedin_data.get("education", []):
        resume_edu.append({
            "school": edu.get("school", ""),
            "degree": edu.get("degree", ""),
            "major": edu.get("major", ""),
            "graduation": edu.get("end_date", ""),
        })
    return resume_edu


# ============================================================
# 测试入口
# ============================================================

if __name__ == "__main__":
    import sys

    cookie = None
    if len(sys.argv) > 1:
        cookie = sys.argv[1]

    print("[LinkedIn] Importing profile...")
    result = import_linkedin_profile(cookie)

    if result.get("_import_note"):
        print(f"⚠️  {result['_import_note']}")
        sys.exit(0)

    print(f"\n=== {result.get('name', 'Unknown')} ===")
    print(f"Headline: {result.get('headline', '')}")
    print(f"\nExperience ({len(result.get('experience', []))} entries):")
    for e in result["experience"][:5]:
        print(f"  • {e['title']} @ {e['company']} ({e.get('start_date', '')} ~ {e.get('end_date', '至今')})")
    print(f"\nEducation ({len(result['education'])} entries):")
    for e in result["education"][:3]:
        print(f"  • {e['school']} | {e['degree']} {e.get('major', '')}")
    print(f"\nSkills: {', '.join(result['skills'][:10])}")
    if result.get("certifications"):
        print(f"Certifications: {', '.join(result['certifications'][:5])}")