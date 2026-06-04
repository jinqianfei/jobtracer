"""
tools/salary_negotiator.py
薪资谈判辅助工具 - 基于市场数据给谈判建议
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('jobtracer.tools.salary_negotiator')


# ============================================================
# 薪资谈判辅助器
# ============================================================

class SalaryNegotiator:
    """
    薪资谈判辅助工具
    基于市场数据、候选人背景、offer 信息给出谈判建议
    """

    # 默认市场薪资范围（2024年参考，单位 K/月）
    DEFAULT_MARKET_RANGES = {
        "后端工程师": {"low": 20, "mid": 30, "high": 45},
        "前端工程师": {"low": 18, "mid": 28, "high": 40},
        "全栈工程师": {"low": 20, "mid": 30, "high": 42},
        "算法工程师": {"low": 25, "mid": 35, "high": 55},
        "数据工程师": {"low": 20, "mid": 30, "high": 45},
        "架构师": {"low": 35, "mid": 50, "high": 70},
        "技术经理": {"low": 40, "mid": 55, "high": 80},
        "产品经理": {"low": 20, "mid": 30, "high": 45},
        "设计师": {"low": 18, "mid": 28, "high": 40},
        "测试工程师": {"low": 15, "mid": 25, "high": 35},
        "运维工程师": {"low": 18, "mid": 28, "high": 40},
        "DBA": {"low": 22, "mid": 32, "high": 45},
        "安全工程师": {"low": 25, "mid": 38, "high": 55},
        "DevOps工程师": {"low": 20, "mid": 30, "high": 42},
        "通用": {"low": 20, "mid": 30, "high": 45},
    }

    def __init__(self, market_data_file: str = None):
        """
        初始化谈判辅助器

        Args:
            market_data_file: 市场数据文件路径（可选）
        """
        self.market_data: Dict[str, Dict[str, float]] = {}
        if market_data_file:
            self._load_market_data(market_data_file)
        else:
            self.market_data = self.DEFAULT_MARKET_RANGES.copy()

        logger.info(f"SalaryNegotiator initialized with {len(self.market_data)} position ranges")

    def _load_market_data(self, file_path: str) -> None:
        """从 JSON 文件加载市场薪资数据"""
        path = Path(file_path).expanduser()
        if not path.exists():
            logger.warning(f"Market data file not found: {path}, using defaults")
            self.market_data = self.DEFAULT_MARKET_RANGES.copy()
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.market_data = data
        except Exception as e:
            logger.error(f"Failed to load market data: {e}")
            self.market_data = self.DEFAULT_MARKET_RANGES.copy()

    # --------------------------------------------------------
    # 主接口
    # --------------------------------------------------------

    def get_salary_advice(
        self,
        position: str,
        offered_salary: float,
        market_data: dict = None,
    ) -> dict:
        """
        获取薪资谈判建议（符合指定接口）

        Args:
            position: 职位名称
            offered_salary: 对方给到的薪资（K/月）
            market_data: 可选，覆盖市场数据（dict，如 {"low": 20, "mid": 30, "high": 40}）

        Returns:
            dict: {
                "market_range": "25-30K",
                "counter_offer": 28,
                "key_points": ["优势1", "优势2"],
                "negotiation_script": "..."
            }
        """
        # 合并市场数据
        if market_data:
            range_data = market_data
        else:
            range_data = self.market_data.get(position, self.market_data.get("通用"))

        low = range_data.get("low", 20)
        mid = range_data.get("mid", 30)
        high = range_data.get("high", 45)

        market_range = f"{low}-{high}K"

        # 计算还价金额
        counter_offer = self._calculate_counter_offer(offered_salary, low, mid, high)

        # 生成谈判要点
        key_points = self._generate_key_points(position, offered_salary, low, mid, high)

        # 生成谈判话术
        negotiation_script = self._generate_script(position, offered_salary, counter_offer, low, mid, high)

        return {
            "market_range": market_range,
            "counter_offer": counter_offer,
            "key_points": key_points,
            "negotiation_script": negotiation_script,
        }

    # --------------------------------------------------------
    # 核心计算逻辑
    # --------------------------------------------------------

    def _calculate_counter_offer(
        self,
        offered: float,
        low: float,
        mid: float,
        high: float,
    ) -> int:
        """
        计算还价建议

        策略：
        - 如果 offer 低于市场 low：还价到 mid 或 low~mid 之间
        - 如果 offer 在市场中位附近：还价到 mid~high 之间
        - 如果 offer 接近或高于 high：象征性争取或接受
        """
        if offered < low:
            # 低于市场下限，还价到 mid
            counter = int(mid)
        elif offered < mid:
            # 低于中位，还价到 mid~high 之间
            counter = int((mid + high) / 2)
        elif offered < high:
            # 接近或略低于高端，还价到 high 或略高
            counter = int(high)
        else:
            # 已高于市场高位，象征性争取
            counter = int(offered * 1.05)
            if counter > high * 1.15:
                counter = int(high * 1.1)

        return counter

    def _generate_key_points(
        self,
        position: str,
        offered: float,
        low: float,
        mid: float,
        high: float,
    ) -> List[str]:
        """生成谈判要点"""
        points = []

        # 优势 1：市场竞争价值
        if offered < mid:
            points.append(f"你的市场价值在 {position} 领域处于中上水平，当前 offer 低于市场平均值")
        else:
            points.append(f"你的专业能力在 {position} 领域具有竞争力，市场认可度高")

        # 优势 2：稀缺技能
        points.append("具备核心技术栈和项目实战经验，是团队需要的关键能力")

        # 优势 3：行业趋势
        points.append("当前市场需求旺盛，同类职位薪资持续上涨，招聘方有预算空间")

        # Offer 分析
        if offered < low:
            points.append(f"当前 offer {offered}K 低于市场最低值 {low}K，建议明确表达期望")
        elif offered < mid:
            points.append(f"当前 offer {offered}K 低于市场中位 {mid}K，有明确谈判空间")
        elif offered < high:
            points.append(f"当前 offer {offered}K 接近市场高位，但仍有争取余地")

        # 附加价值
        points.append("可强调除基本工资外的其他福利、年终奖、股票期权等综合收益")

        return points

    def _generate_script(
        self,
        position: str,
        offered: float,
        counter: float,
        low: float,
        mid: float,
        high: float,
    ) -> str:
        """生成薪资谈判话术"""
        diff = counter - offered
        diff_pct = (diff / offered * 100) if offered > 0 else 0

        if diff <= 2:
            # 差距较小，温和谈判
            script = f"""感谢您发来 offer。我对贵司的{position}岗位确实很感兴趣，也非常期待加入。

关于薪资，我目前收到另一家的 offer 在 {counter}K 左右。考虑到我的项目经验和技术能力，以及{position}岗位的市场行情，我的期望薪资是 {counter}K。

当然，我更看重贵司的平台和发展机会，如果 {counter}K 有困难的话，{int(counter - 2)}K 也是可以接受的。请问能否再帮忙争取一下？"""
        elif diff <= 5:
            # 差距中等，中等力度
            script = f"""非常感谢您发来 offer！

我对贵司的{position}岗位非常感兴趣，也认真考虑过这个机会。不过关于薪资，我需要坦诚地说明：

结合我过往的项目经验、市场薪资水平以及同岗位的普遍薪资范围，我的期望薪资是 {counter}K。当前 offer {offered}K 与我的期望有一定差距。

我了解到贵司对这个岗位很重视，也相信公司有一定的薪酬灵活空间。能否帮忙再争取一下 {counter}K？如果综合福利或其他收益可以弥补这个差距，我也很愿意进一步讨论。"""
        else:
            # 差距较大，强力谈判
            script = f"""非常感谢您发来 offer！

关于薪资方面，我需要诚实地说：目前收到的 offer {offered}K 与我的期望差距较大。根据我的背景调查，{position}岗位在同类公司的市场薪资范围在 {low}-{high}K 之间，中位值约 {mid}K。

基于我的项目经验和技术深度，我期望的薪资是 {counter}K。这个期望基于市场数据和我过往的工作成果，并非无依据地抬高。

我非常看重贵司的发展平台，也诚意满满地希望加入。如果{counter}K 在预算范围内有困难，我可以讨论其他方案，比如增加签字费、调整绩效考核方案等。期待您的回复！"""

        return script

    # --------------------------------------------------------
    # 批量分析与报告
    # --------------------------------------------------------

    def analyze_multiple_offers(self, offers: List[Dict[str, Any]]) -> List[dict]:
        """
        批量分析多个 offer

        Args:
            offers: offer 列表，每项包含 position, offered_salary, company

        Returns:
            List[dict]: 每个 offer 的分析结果
        """
        results = []
        for offer in offers:
            position = offer.get("position", "通用")
            salary = offer.get("offered_salary", offer.get("salary", 0))
            company = offer.get("company", "某公司")

            advice = self.get_salary_advice(position, salary)

            results.append({
                "company": company,
                "position": position,
                "offered_salary": salary,
                "market_range": advice["market_range"],
                "counter_offer": advice["counter_offer"],
                "recommendation": self._get_recommendation(salary, advice["market_range"]),
                "key_points": advice["key_points"],
            })

        return results

    def _get_recommendation(self, offered: float, market_range: str) -> str:
        """获取推荐建议"""
        try:
            parts = market_range.replace("K", "").split("-")
            low = float(parts[0])
            high = float(parts[1])
            mid = (low + high) / 2
        except Exception:
            return "评估中"

        if offered < low:
            return "⚠️ 偏低，建议还价"
        elif offered < mid:
            return "🔻 一般，建议争取"
        elif offered < high:
            return "✅ 合理，可接受"
        else:
            return "🌟 优秀，建议接受"

    # --------------------------------------------------------
    # 市场数据管理
    # --------------------------------------------------------

    def update_market_range(self, position: str, low: float, mid: float, high: float) -> None:
        """更新某个职位的市场薪资范围"""
        self.market_data[position] = {"low": low, "mid": mid, "high": high}
        logger.info(f"Updated market range for {position}: {low}-{high}K")

    def get_market_range(self, position: str) -> Optional[Dict[str, float]]:
        """获取某职位的市场薪资范围"""
        return self.market_data.get(position)

    def export_market_data(self, file_path: str) -> bool:
        """导出市场数据到文件"""
        try:
            with open(Path(file_path).expanduser(), 'w', encoding='utf-8') as f:
                json.dump(self.market_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Exported market data to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export market data: {e}")
            return False


# ============================================================
# 便捷函数
# ============================================================

_default_negotiator: Optional[SalaryNegotiator] = None


def get_negotiator(market_data_file: str = None) -> SalaryNegotiator:
    """获取默认谈判辅助器"""
    global _default_negotiator
    if _default_negotiator is None:
        _default_negotiator = SalaryNegotiator(market_data_file=market_data_file)
    return _default_negotiator


def get_salary_advice(position: str, offered_salary: float, market_data: dict = None) -> dict:
    """便捷函数：获取谈判建议"""
    return get_negotiator().get_salary_advice(position, offered_salary, market_data)


# ============================================================
# 测试入口
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("薪资谈判辅助工具测试")
    print("=" * 60)

    negotiator = SalaryNegotiator()

    # 测试不同场景
    test_cases = [
        ("后端工程师", 18, None),       # 偏低
        ("算法工程师", 28, None),       # 中等偏低
        ("架构师", 40, None),           # 接近中位
        ("技术经理", 55, None),         # 高位
        ("产品经理", 15, {"low": 18, "mid": 28, "high": 40}),  # 自定义数据
    ]

    for position, offered, custom_data in test_cases:
        print(f"\n[{position}] Offer: {offered}K")
        print("-" * 50)

        advice = negotiator.get_salary_advice(position, offered, custom_data)

        print(f"  市场范围: {advice['market_range']}")
        print(f"  还价建议: {advice['counter_offer']}K")
        print(f"  推荐话术:\n{advice['negotiation_script'][:100]}...")
        print(f"  关键要点: {advice['key_points'][:2]}")

    print()
    print("=" * 60)
    print("批量 offer 分析测试")
    print("=" * 60)

    offers = [
        {"position": "后端工程师", "offered_salary": 22, "company": "A公司"},
        {"position": "算法工程师", "offered_salary": 32, "company": "B公司"},
        {"position": "架构师", "offered_salary": 55, "company": "C公司"},
    ]

    analysis = negotiator.analyze_multiple_offers(offers)
    for a in analysis:
        print(f"\n{a['company']} - {a['position']}")
        print(f"  Offer: {a['offered_salary']}K | 市场: {a['market_range']}")
        print(f"  还价: {a['counter_offer']}K | 推荐: {a['recommendation']}")

    print()
    print("=" * 60)
    print("测试完成")
    print("=" * 60)