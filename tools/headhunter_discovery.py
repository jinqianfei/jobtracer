"""
JobTracer 猎头/内推发现工具
识别可内推的机会，扫描 LinkedIn 和 GitHub 人脉
"""

import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ReferralOpportunity:
    """内推机会"""
    person: str          # 联系人姓名
    role: str           # 联系人职位
    company: str        # 公司名称
    connection_degree: int   # 连接度（1=一度，2=二度）
    referral_likelihood: str  # 内推可能性（high/medium/low）
    last_interaction: str     # 上次互动时间
    message: str        # 建议发送的消息


class HeadhunterDiscovery:
    """猎头/内推发现器"""

    def __init__(self):
        self.cache_file = "~/.jobtracer/referral_cache.json"

    def discover_referral_opportunities(
        self,
        linkedin_connections: List[dict] = None,
        github_orgs: List[dict] = None,
        saved_jobs: List[dict] = None
    ) -> List[dict]:
        """
        扫描 LinkedIn 人脉和 GitHub 组织，发现有内推资源的联系人
        
        Args:
            linkedin_connections: LinkedIn 连接列表，每项包含 name, title, company, connection_degree
            github_orgs: GitHub 组织列表，每项包含 org_name, role, contributions
            saved_jobs: 已保存的职位列表（用于匹配内推机会）
        
        Returns:
            内推机会列表
        """
        opportunities = []
        
        # 扫描 LinkedIn 连接
        if linkedin_connections:
            for conn in linkedin_connections:
                opp = self._analyze_linkedin_connection(conn, saved_jobs)
                if opp:
                    opportunities.append(opp)
        
        # 扫描 GitHub 组织成员
        if github_orgs:
            for org in github_orgs:
                opps = self._analyze_github_org(org, saved_jobs)
                opportunities.extend(opps)
        
        # 按内推可能性排序
        priority_map = {"high": 0, "medium": 1, "low": 2}
        opportunities.sort(key=lambda x: priority_map.get(x["referral_likelihood"], 2))
        
        return opportunities

    def _analyze_linkedin_connection(self, connection: dict, saved_jobs: List[dict] = None) -> Optional[dict]:
        """分析 LinkedIn 连接的内推可能性"""
        company = connection.get("company", "")
        title = connection.get("title", "")
        name = connection.get("name", "Unknown")
        degree = connection.get("connection_degree", 3)
        
        # 判断内推可能性
        likelihood = "low"
        
        # 一度连接（同事/朋友）内推可能性高
        if degree == 1:
            likelihood = "high"
        # 二度连接（朋友的朋友）
        elif degree == 2:
            # 如果是 HR/招聘/技术经理，提高可能性
            keywords = ["hr", "recruiter", "hiring", "manager", "tech lead", "director", "vp", "founder"]
            if any(k in title.lower() for k in keywords):
                likelihood = "high"
            else:
                likelihood = "medium"
        else:
            likelihood = "low"
        
        # 优先推荐知名公司
        priority_companies = [
            "google", "meta", "apple", "amazon", "microsoft", "netflix",
            "字节跳动", "阿里巴巴", "腾讯", "百度", "华为", "美团", "拼多多",
            "bytedance", "alibaba", "tencent", "baidu", "huawei", "meituan", "pinduoduo"
        ]
        
        company_lower = company.lower()
        is_priority = any(p in company_lower for p in priority_companies)
        
        # 生成建议消息
        message = self._generate_referral_message(name, company, title)
        
        return {
            "person": name,
            "role": title,
            "company": company,
            "connection_degree": degree,
            "referral_likelihood": likelihood,
            "last_interaction": connection.get("last_interaction", ""),
            "platform": "linkedin",
            "is_priority_company": is_priority,
            "suggested_message": message,
            "discovered_at": datetime.now().isoformat()
        }

    def _analyze_github_org(self, org: dict, saved_jobs: List[dict] = None) -> List[dict]:
        """分析 GitHub 组织成员"""
        opportunities = []
        org_name = org.get("org_name", "")
        members = org.get("members", [])
        
        # 查找在知名公司工作的成员
        for member in members:
            likelihood = "medium"
            
            # 核心贡献者或 Maintainer 内推可能性高
            if member.get("role") in ["maintainer", "core-contributor"]:
                likelihood = "high"
            
            opp = {
                "person": member.get("name", "Unknown"),
                "role": member.get("role", "Contributor"),
                "company": org_name,
                "connection_degree": 2,  # GitHub 通常是二度连接
                "referral_likelihood": likelihood,
                "last_interaction": member.get("last_contribution", ""),
                "platform": "github",
                "is_priority_company": True,
                "suggested_message": self._generate_referral_message(
                    member.get("name", ""), org_name, member.get("role", "")
                ),
                "discovered_at": datetime.now().isoformat()
            }
            opportunities.append(opp)
        
        return opportunities

    def _generate_referral_message(self, name: str, company: str, role: str) -> str:
        """生成内推建议消息"""
        return f"Hi {name}，我在关注 {company} 的 {role} 职位，请问是否可以帮忙内推？"

    def filter_by_company(self, opportunities: List[dict], target_companies: List[str]) -> List[dict]:
        """按公司筛选内推机会"""
        return [
            opp for opp in opportunities
            if any(c.lower() in opp["company"].lower() for c in target_companies)
        ]

    def filter_by_likelihood(self, opportunities: List[dict], min_likelihood: str = "medium") -> List[dict]:
        """按内推可能性筛选"""
        priority_map = {"high": 0, "medium": 1, "low": 2}
        min_priority = priority_map.get(min_likelihood, 1)
        return [
            opp for opp in opportunities
            if priority_map.get(opp["referral_likelihood"], 2) <= min_priority
        ]

    def save_opportunities(self, opportunities: List[dict]):
        """保存内推机会到缓存"""
        cache_path = self._get_cache_path()
        data = {
            "opportunities": opportunities,
            "updated_at": datetime.now().isoformat()
        }
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_opportunities(self) -> List[dict]:
        """从缓存加载内推机会"""
        cache_path = self._get_cache_path()
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("opportunities", [])
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _get_cache_path(self) -> str:
        """获取缓存文件路径"""
        from pathlib import Path
        cache_dir = Path("~/.jobtracer").expanduser()
        cache_dir.mkdir(parents=True, exist_ok=True)
        return str(cache_dir / "referral_cache.json")


def discover_referral_opportunities(
    linkedin_connections: List[dict] = None,
    github_orgs: List[dict] = None,
    saved_jobs: List[dict] = None
) -> List[dict]:
    """
    快捷函数：发现内推机会
    
    Args:
        linkedin_connections: LinkedIn 连接列表
        github_orgs: GitHub 组织列表
        saved_jobs: 已保存的职位列表
    
    Returns:
        内推机会列表
    """
    discovery = HeadhunterDiscovery()
    return discovery.discover_referral_opportunities(linkedin_connections, github_orgs, saved_jobs)


# ============================================================
# 测试入口
# ============================================================

if __name__ == "__main__":
    # 模拟 LinkedIn 连接数据
    linkedin_connections = [
        {"name": "张明", "title": "HR招聘经理", "company": "字节跳动", "connection_degree": 1, "last_interaction": "2024-01-15"},
        {"name": "李华", "title": "技术总监", "company": "阿里巴巴", "connection_degree": 2, "last_interaction": "2024-02-01"},
        {"name": "王芳", "title": "前端工程师", "company": "美团", "connection_degree": 2, "last_interaction": "2024-01-20"},
        {"name": "刘强", "title": "CTO", "company": "创业公司X", "connection_degree": 3, "last_interaction": "2023-12-01"},
    ]
    
    # 模拟 GitHub 组织数据
    github_orgs = [
        {
            "org_name": "Microsoft",
            "members": [
                {"name": "陈伟", "role": "maintainer", "last_contribution": "2024-02-10"},
                {"name": "赵磊", "role": "contributor", "last_contribution": "2024-01-28"},
            ]
        }
    ]
    
    # 已保存的职位
    saved_jobs = [
        {"company": "字节跳动", "title": "后端工程师"},
        {"company": "阿里巴巴", "title": "技术专家"},
    ]
    
    print("=" * 60)
    print("🔍 猎头/内推发现")
    print("=" * 60)
    
    opportunities = discover_referral_opportunities(linkedin_connections, github_orgs, saved_jobs)
    
    print(f"\n📊 发现 {len(opportunities)} 个内推机会:\n")
    
    for i, opp in enumerate(opportunities, 1):
        likelihood_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(opp["referral_likelihood"], "⚪")
        platform_icon = {"linkedin": "💼", "github": "🐙"}.get(opp.get("platform", "unknown"), "📌")
        
        print(f"[{i}] {platform_icon} {opp['person']}")
        print(f"     职位: {opp['role']} @ {opp['company']}")
        print(f"     连接: {opp['connection_degree']}度 | 可能性: {likelihood_icon} {opp['referral_likelihood']}")
        print(f"     消息: {opp['suggested_message']}")
        print()
    
    # 按公司筛选
    print("\n🏢 字节跳动内推机会:")
    byte_opps = [o for o in opportunities if "字节" in o["company"]]
    for opp in byte_opps:
        print(f"  - {opp['person']} ({opp['role']})")
    
    # 按可能性筛选
    print("\n🎯 高可能性内推（可直接联系）:")
    high_opps = [o for o in opportunities if o["referral_likelihood"] == "high"]
    for opp in high_opps:
        print(f"  - {opp['person']} @ {opp['company']}")