"""
JobTracer 智能Offer比较工具
多Offer对比分析，辅助求职决策
"""

import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class OfferScore:
    """Offer评分结果"""
    offer: dict
    total_score: float
    breakdown: dict
    highlights: List[str]
    concerns: List[str]
    recommendation: str


class OfferComparator:
    """Offer比较器"""

    # 评分维度及权重
    WEIGHTS = {
        "salary": 0.40,      # 薪资
        "stock": 0.20,       # 股票/期权
        "growth": 0.20,      # 成长空间
        "balance": 0.10,     # Work-Life Balance
        "stability": 0.10    # 公司稳定性
    }

    def __init__(self):
        self.offers = []

    def compare_offers(self, offer_list: List[dict]) -> dict:
        """
        比较多个Offer并生成分析报告
        
        Args:
            offer_list: Offer列表，每个Offer包含:
                - company: 公司名
                - title: 职位名称
                - salary: 年薪（含税，单位：万）
                - stock: 股票/期权价值（4年总计，单位：万）
                - bonus: 年终奖（单位：月）
                - remote: 是否支持远程 (bool)
                - growth: 成长空间评分 (1-10)
                - balance: 工作生活平衡评分 (1-10)
                - stability: 公司稳定性评分 (1-10)
                - benefits: 其他福利列表
        
        Returns:
            {
                "ranking": [...],
                "comparison_matrix": {...},
                "recommendation": "..."
            }
        """
        if not offer_list:
            return {"error": "No offers provided"}
        
        self.offers = offer_list
        
        # 计算每个Offer的评分
        scored = []
        for offer in offer_list:
            score_result = self._score_offer(offer)
            scored.append(score_result)
        
        # 按总分排序
        scored.sort(key=lambda x: x["total_score"], reverse=True)
        
        # 生成对比矩阵
        matrix = self._generate_matrix(offer_list)
        
        # 生成推荐
        recommendation = self._generate_recommendation(scored)
        
        return {
            "ranking": scored,
            "comparison_matrix": matrix,
            "recommendation": recommendation,
            "summary": self._generate_summary(scored)
        }

    def _score_offer(self, offer: dict) -> dict:
        """计算单个Offer的评分"""
        breakdown = {}
        highlights = []
        concerns = []
        
        # 1. 薪资评分 (0-100)
        salary = offer.get("salary", 0)
        salary_score = min(salary / 80 * 100, 100)  # 80万年薪为满分基准
        breakdown["salary"] = {
            "score": round(salary_score, 1),
            "weight": self.WEIGHTS["salary"],
            "weighted": round(salary_score * self.WEIGHTS["salary"], 2),
            "raw": salary
        }
        
        # 2. 股票/期权评分 (0-100)
        stock = offer.get("stock", 0)
        stock_score = min(stock / 100 * 100, 100)  # 100万股票为满分
        breakdown["stock"] = {
            "score": round(stock_score, 1),
            "weight": self.WEIGHTS["stock"],
            "weighted": round(stock_score * self.WEIGHTS["stock"], 2),
            "raw": stock
        }
        
        # 3. 成长空间 (0-100)
        growth = offer.get("growth", 5)
        growth_score = growth * 10
        breakdown["growth"] = {
            "score": round(growth_score, 1),
            "weight": self.WEIGHTS["growth"],
            "weighted": round(growth_score * self.WEIGHTS["growth"], 2),
            "raw": growth
        }
        
        # 4. Work-Life Balance (0-100)
        balance = offer.get("balance", 5)
        balance_score = balance * 10
        breakdown["balance"] = {
            "score": round(balance_score, 1),
            "weight": self.WEIGHTS["balance"],
            "weighted": round(balance_score * self.WEIGHTS["balance"], 2),
            "raw": balance
        }
        
        # 5. 公司稳定性 (0-100)
        stability = offer.get("stability", 5)
        stability_score = stability * 10
        breakdown["stability"] = {
            "score": round(stability_score, 1),
            "weight": self.WEIGHTS["stability"],
            "weighted": round(stability_score * self.WEIGHTS["stability"], 2),
            "raw": stability
        }
        
        # 计算总分
        total_score = sum(item["weighted"] for item in breakdown.values())
        
        # 生成亮点和顾虑
        if salary >= 50:
            highlights.append(f"高薪：{salary}万/年")
        if stock >= 50:
            highlights.append(f"丰厚股票：{stock}万")
        if growth >= 8:
            highlights.append("成长空间优秀")
        if balance >= 8:
            highlights.append("工作生活平衡好")
        if stability >= 8:
            highlights.append("公司稳定可靠")
            
        if salary < 30:
            concerns.append("薪资偏低")
        if stock < 20:
            concerns.append("股票期权少")
        if growth < 5:
            concerns.append("成长空间有限")
        if balance < 5:
            concerns.append("可能加班严重")
        if stability < 5:
            concerns.append("公司风险较高")
        
        # 远程工作加成
        if offer.get("remote"):
            breakdown["balance"]["score"] += 10
            breakdown["balance"]["weighted"] = round(breakdown["balance"]["score"] * self.WEIGHTS["balance"], 2)
            highlights.append("支持远程办公")
        
        # 重新计算总分
        total_score = sum(item["weighted"] for item in breakdown.values())
        
        return {
            "offer": offer,
            "total_score": round(total_score, 1),
            "breakdown": breakdown,
            "highlights": highlights,
            "concerns": concerns
        }

    def _generate_matrix(self, offers: List[dict]) -> dict:
        """生成对比矩阵"""
        companies = [o.get("company", f"Offer-{i+1}") for i, o in enumerate(offers)]
        
        matrix = {
            "companies": companies,
            "dimensions": list(self.WEIGHTS.keys()),
            "scores": [],
            "raw_data": []
        }
        
        for offer in offers:
            company = offer.get("company", "Unknown")
            score_entry = {"company": company}
            raw_entry = {"company": company}
            
            for dim in self.WEIGHTS.keys():
                score_entry[dim] = round(self._score_offer(offer)["breakdown"][dim]["score"], 1)
                raw_entry[dim] = offer.get(dim, offer.get(dim.replace("_", ""), 0))
            
            matrix["scores"].append(score_entry)
            matrix["raw_data"].append(raw_entry)
        
        return matrix

    def _generate_recommendation(self, scored: List[dict]) -> str:
        """生成推荐建议"""
        if not scored:
            return "没有足够的Offer进行比较"
        
        best = scored[0]
        company = best["offer"].get("company", "Unknown")
        title = best["offer"].get("title", "")
        score = best["total_score"]
        
        reasons = best.get("highlights", [])[:3]
        reasons_str = "、".join(reasons) if reasons else "综合评分最优"
        
        return f"推荐 {company}（{title}），综合得分{score}分，{reasons_str}。"

    def _generate_summary(self, scored: List[dict]) -> dict:
        """生成汇总信息"""
        if not scored:
            return {}
        
        best = scored[0]
        worst = scored[-1]
        
        return {
            "total_offers": len(scored),
            "best_offer": best["offer"].get("company", ""),
            "best_score": best["total_score"],
            "worst_offer": worst["offer"].get("company", ""),
            "worst_score": worst["total_score"],
            "score_range": round(best["total_score"] - worst["total_score"], 1),
            "avg_salary": round(sum(o["offer"].get("salary", 0) for o in scored) / len(scored), 1)
        }


def compare_offers(offer_list: List[dict]) -> dict:
    """
    快捷函数：比较多个Offer
    
    Args:
        offer_list: Offer列表
    
    Returns:
        比较结果字典
    """
    comparator = OfferComparator()
    return comparator.compare_offers(offer_list)


# ============================================================
# 测试入口
# ============================================================

if __name__ == "__main__":
    # 示例Offer数据
    sample_offers = [
        {
            "company": "字节跳动",
            "title": "高级后端工程师",
            "salary": 65,
            "stock": 80,
            "bonus": 3,
            "remote": True,
            "growth": 9,
            "balance": 6,
            "stability": 7,
            "benefits": ["免费三餐", "健身房"]
        },
        {
            "company": "阿里巴巴",
            "title": "技术专家",
            "salary": 70,
            "stock": 120,
            "bonus": 4,
            "remote": False,
            "growth": 8,
            "balance": 5,
            "stability": 8,
            "benefits": ["期权", "股票"]
        },
        {
            "company": "创业公司A",
            "title": "技术负责人",
            "salary": 45,
            "stock": 200,
            "bonus": 0,
            "remote": True,
            "growth": 10,
            "balance": 9,
            "stability": 4,
            "benefits": ["股权激励", "弹性工作"]
        },
        {
            "company": "腾讯",
            "title": "高级工程师",
            "salary": 55,
            "stock": 60,
            "bonus": 3,
            "remote": False,
            "growth": 7,
            "balance": 7,
            "stability": 9,
            "benefits": ["年终奖高", "福利好"]
        }
    ]
    
    print("=" * 60)
    print("📊 Offer 比较分析")
    print("=" * 60)
    
    result = compare_offers(sample_offers)
    
    # 排名
    print("\n🏆 排名:")
    for i, item in enumerate(result["ranking"], 1):
        offer = item["offer"]
        score = item["total_score"]
        print(f"  #{i} {offer['company']} - {score}分")
        print(f"      亮点: {', '.join(item['highlights'][:3]) or '无'}")
    
    # 汇总
    summary = result["summary"]
    print(f"\n📈 汇总:")
    print(f"  参与比较: {summary['total_offers']} 个Offer")
    print(f"  最高分: {summary['best_offer']} ({summary['best_score']}分)")
    print(f"  最低分: {summary['worst_offer']} ({summary['worst_score']}分)")
    print(f"  最高薪资: {summary['avg_salary']}万（平均）")
    
    # 推荐
    print(f"\n💡 {result['recommendation']}")