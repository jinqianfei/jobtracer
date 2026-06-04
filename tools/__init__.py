"""
tools/ - 求职辅助工具模块
"""

from .salary_negotiator import SalaryNegotiator, get_salary_advice
from .offer_comparator import OfferComparator, compare_offers
from .headhunter_discovery import HeadhunterDiscovery, discover_referral_opportunities

__all__ = [
    "SalaryNegotiator",
    "get_salary_advice",
    "OfferComparator", 
    "compare_offers",
    "HeadhunterDiscovery", 
    "discover_referral_opportunities"
]