"""
reporting/resume_reporter.py
求职复盘报告生成器 - 每次求职周期结束自动生成复盘总结
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('jobtracer.reporting')


# ============================================================
# 报告生成器
# ============================================================

class ResumeReporter:
    """
    求职复盘报告生成器
    从 job-tracker.json 和 feedback.json 提取数据生成复盘报告
    """

    def __init__(self, storage_dir: str = "~/.jobtracer"):
        """
        初始化报告生成器

        Args:
            storage_dir: ~/.jobtracer 目录路径
        """
        self.storage_dir = Path(storage_dir).expanduser()
        self.reports_dir = self.storage_dir / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        self.tracker_file = self.storage_dir / "job-tracker.json"
        self.feedback_file = self.storage_dir / "feedback.json"

        logger.info(f"ResumeReporter initialized at {self.storage_dir}")

    # --------------------------------------------------------
    # 主接口
    # --------------------------------------------------------

    def generate_referral_report(self, period: str = "last_30_days") -> dict:
        """
        生成求职复盘报告（符合指定接口）

        Args:
            period: 统计周期 "last_week"|"last_30_days"|"last_90_days"

        Returns:
            dict: {
                "applied_count": N,
                "interview_count": N,
                "offer_count": N,
                "conversion_rate": "X%",
                "insights": ["insight1", "insight2"],
                "improvement_suggestions": [...]
            }
        """
        # 计算日期范围
        end_date = datetime.now()
        if period == "last_week":
            start_date = end_date - timedelta(days=7)
        elif period == "last_30_days":
            start_date = end_date - timedelta(days=30)
        elif period == "last_90_days":
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=30)

        # 加载数据
        jobs = self._load_jobs()
        feedbacks = self._load_feedbacks()

        # 过滤指定周期的数据
        period_jobs = self._filter_by_date(jobs, start_date, end_date)
        period_feedbacks = self._filter_by_date(feedbacks, start_date, end_date)

        # 统计各项指标
        applied_count = len(period_jobs)

        # 面试数：收到面试邀请的职位
        interview_count = sum(
            1 for j in period_jobs
            if j.get("status") in ("interview", "interviewing", "video_interview", "onsite")
        )

        # offer 数
        offer_count = sum(
            1 for j in period_jobs
            if j.get("status") in ("offer", "offer_received", "accepted")
        )

        # 计算转化率
        if applied_count > 0:
            interview_rate = interview_count / applied_count * 100
            offer_rate = offer_count / applied_count * 100
        else:
            interview_rate = 0.0
            offer_rate = 0.0

        conversion_rate = f"{interview_rate:.1f}% 面试率 / {offer_rate:.1f}% Offer率"

        # 生成洞察
        insights = self._generate_insights(period_jobs, period_feedbacks, applied_count, interview_count, offer_count)

        # 生成改进建议
        suggestions = self._generate_suggestions(period_jobs, period_feedbacks, applied_count, interview_count, offer_count)

        # 统计薪资信息
        salary_stats = self._extract_salary_stats(period_jobs)

        # 生成报告
        report = {
            "period": period,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "generated_at": datetime.now().isoformat(),
            "applied_count": applied_count,
            "interview_count": interview_count,
            "offer_count": offer_count,
            "conversion_rate": conversion_rate,
            "insights": insights,
            "improvement_suggestions": suggestions,
            "salary_stats": salary_stats,
            "status_breakdown": self._status_breakdown(period_jobs),
            "company_type_breakdown": self._company_type_breakdown(period_jobs),
        }

        # 保存报告
        self._save_report(report, period)

        logger.info(f"Generated referral report for {period}: {applied_count} applied, {interview_count} interviews, {offer_count} offers")
        return report

    # --------------------------------------------------------
    # 数据加载
    # --------------------------------------------------------

    def _load_jobs(self) -> List[Dict[str, Any]]:
        """加载所有职位数据"""
        if not self.tracker_file.exists():
            return []
        try:
            with open(self.tracker_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get("jobs", [])
        except Exception as e:
            logger.error(f"Failed to load jobs: {e}")
            return []

    def _load_feedbacks(self) -> List[Dict[str, Any]]:
        """加载所有反馈数据"""
        if not self.feedback_file.exists():
            return []
        try:
            with open(self.feedback_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get("feedbacks", [])
        except Exception as e:
            logger.error(f"Failed to load feedbacks: {e}")
            return []

    def _filter_by_date(
        self,
        records: List[Dict[str, Any]],
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """过滤指定日期范围内的记录"""
        result = []
        for record in records:
            # 尝试从多个字段获取日期
            date_str = (
                record.get("applied_at")
                or record.get("created_at")
                or record.get("date")
                or record.get("last_updated")
            )
            if not date_str:
                continue
            try:
                # 支持多种日期格式
                if "T" in date_str:
                    record_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                else:
                    record_date = datetime.strptime(date_str, "%Y-%m-%d")
                if start_date <= record_date <= end_date:
                    result.append(record)
            except Exception:
                continue
        return result

    # --------------------------------------------------------
    # 统计与分析
    # --------------------------------------------------------

    def _status_breakdown(self, jobs: List[Dict[str, Any]]) -> Dict[str, int]:
        """各状态数量统计"""
        breakdown: Dict[str, int] = {}
        for job in jobs:
            status = job.get("status", "unknown")
            breakdown[status] = breakdown.get(status, 0) + 1
        return breakdown

    def _company_type_breakdown(self, jobs: List[Dict[str, Any]]) -> Dict[str, int]:
        """公司类型分布"""
        breakdown: Dict[str, int] = {}
        for job in jobs:
            company_type = job.get("company_type", job.get("company_size", "unknown"))
            breakdown[company_type] = breakdown.get(company_type, 0) + 1
        return breakdown

    def _extract_salary_stats(self, jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """提取薪资统计"""
        salaries = []
        for job in jobs:
            salary = job.get("salary") or job.get("salary_range") or job.get("offer_salary")
            if salary:
                # 尝试解析薪资范围
                import re
                nums = re.findall(r"[\d]+", str(salary))
                if nums:
                    try:
                        salaries.append(int(nums[0]))
                    except ValueError:
                        pass

        if salaries:
            return {
                "count": len(salaries),
                "min": min(salaries),
                "max": max(salaries),
                "avg": sum(salaries) // len(salaries),
            }
        return {"count": 0, "min": None, "max": None, "avg": None}

    def _generate_insights(
        self,
        jobs: List[Dict[str, Any]],
        feedbacks: List[Dict[str, Any]],
        applied_count: int,
        interview_count: int,
        offer_count: int,
    ) -> List[str]:
        """生成洞察列表"""
        insights = []

        if applied_count == 0:
            insights.append("本期暂无投递记录，建议保持每日投递节奏")
            return insights

        # 转化率分析
        if applied_count > 0:
            interview_rate = interview_count / applied_count
            if interview_rate < 0.1:
                insights.append("面试邀请率较低（<10%），建议优化简历关键词和投递策略")
            elif interview_rate < 0.2:
                insights.append("面试邀请率一般（10-20%），简历匹配度有提升空间")
            else:
                insights.append(f"面试邀请率良好（{interview_rate:.1%}），简历和求职方向匹配度较高")

        # Offer 转化分析
        if interview_count > 0:
            offer_rate = offer_count / interview_count
            if offer_rate > 0.5:
                insights.append("面试通过率较高，说明技术能力得到认可")
            elif offer_rate > 0.25:
                insights.append("面试通过率一般，建议加强面试前系统复习")
            else:
                insights.append("面试通过率偏低，建议回顾面试中的高频失分点，针对性提升")

        # 反馈分析
        rejection_keywords = ["不太匹配", "不符合", "不太合适", "没有hc", "已招到"]
        feedback_rejections = [
            f for f in feedbacks
            if any(kw in f.get("feedback_text", "") for kw in rejection_keywords)
        ]
        if feedback_rejections:
            insights.append(f"本期收到 {len(feedback_rejections)} 条婉拒反馈，建议针对性提升相关技能")

        # 公司类型分析
        company_types = [j.get("company_type", "未知") for j in jobs]
        if "未知" not in company_types or len(set(company_types)) > 3:
            insights.append("投递公司类型多样，建议聚焦目标公司类型提升命中率")

        # 薪资分析
        salary_stats = self._extract_salary_stats(jobs)
        if salary_stats.get("count", 0) > 0:
            avg = salary_stats["avg"]
            insights.append(f"本期收到 {salary_stats['count']} 条薪资信息，平均值 {avg}K")

        if len(insights) == 0:
            insights.append("数据不足，无法生成深度洞察，建议持续记录求职数据")

        return insights

    def _generate_suggestions(
        self,
        jobs: List[Dict[str, Any]],
        feedbacks: List[Dict[str, Any]],
        applied_count: int,
        interview_count: int,
        offer_count: int,
    ) -> List[str]:
        """生成改进建议"""
        suggestions = []

        # 投递量建议
        if applied_count < 10:
            suggestions.append("建议每日投递量提升至 5-10 个岗位，保持招聘平台的活跃度")
        elif applied_count < 20:
            suggestions.append("投递量适中，建议注重投递质量和岗位匹配度")
        else:
            suggestions.append("投递量充足，建议定期复盘投递转化率，优化简历针对性")

        # 面试准备建议
        if interview_count == 0 and applied_count > 5:
            suggestions.append("投递量足够但无面试邀请，建议检查简历中的关键词是否与 JD 匹配")
            suggestions.append("可尝试使用技术版/管理版等不同简历版本针对不同岗位")

        if interview_count > 0 and offer_count == 0:
            suggestions.append("有面试但未获 offer，建议系统复习核心技术点并练习STAR法则描述项目")
            suggestions.append("可回顾面试中反复出现的知识点，进行针对性提升")

        # 简历版本建议
        suggestions.append("建议根据不同公司类型使用不同简历版本：技术版投递互联网，管理版投递外企，国央企版投递国企")

        # 技能提升建议
        if feedbacks:
            skill_mentions = {}
            for fb in feedbacks:
                text = fb.get("feedback_text", "")
                # 简单关键词提取
                skills = ["Python", "Go", "Java", "系统设计", "算法", "项目管理", "团队协作"]
                for skill in skills:
                    if skill.lower() in text.lower():
                        skill_mentions[skill] = skill_mentions.get(skill, 0) + 1
            if skill_mentions:
                top_skills = sorted(skill_mentions.items(), key=lambda x: x[1], reverse=True)[:3]
                suggestions.append(f"近期反馈中高频提到的技能：{', '.join([s[0] for s in top_skills])}，建议重点提升")

        # 数据记录建议
        suggestions.append("建议使用 JobTracer 记录每一次面试反馈，形成自己的面试问答库")

        return suggestions

    # --------------------------------------------------------
    # 报告保存与加载
    # --------------------------------------------------------

    def _save_report(self, report: dict, period: str) -> None:
        """保存报告到文件"""
        filename = f"referral_report_{period}_{datetime.now().strftime('%Y%m%d')}.json"
        report_path = self.reports_dir / filename
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            logger.info(f"Report saved to {report_path}")
        except Exception as e:
            logger.error(f"Failed to save report: {e}")

    def list_reports(self, period: str = None) -> List[Dict[str, Any]]:
        """
        列出已生成的报告

        Args:
            period: 可选，筛选特定周期的报告

        Returns:
            List[dict]: 报告列表
        """
        reports = []
        for f in self.reports_dir.glob("referral_report_*.json"):
            try:
                with open(f, 'r', encoding='utf-8') as fp:
                    data = json.load(fp)
                reports.append({
                    "filename": f.name,
                    "period": data.get("period"),
                    "start_date": data.get("start_date"),
                    "end_date": data.get("end_date"),
                    "applied_count": data.get("applied_count"),
                    "generated_at": data.get("generated_at"),
                })
            except Exception as e:
                logger.error(f"Failed to load report {f}: {e}")
        reports.sort(key=lambda x: x.get("generated_at", ""), reverse=True)
        if period:
            reports = [r for r in reports if r.get("period") == period]
        return reports

    def get_latest_report(self, period: str = None) -> Optional[dict]:
        """获取最新报告"""
        reports = self.list_reports(period)
        if reports:
            filename = self.reports_dir / reports[0]["filename"]
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    # --------------------------------------------------------
    # 格式化输出
    # --------------------------------------------------------

    def format_report_markdown(self, report: dict) -> str:
        """将报告格式化为 Markdown"""
        lines = [
            f"# 📋 求职复盘报告",
            f"",
            f"**统计周期**: {report['start_date']} ~ {report['end_date']}",
            f"",
            f"## 📊 核心指标",
            f"",
            f"| 指标 | 数值 |",
            f"|------|------|",
            f"| 投递数 | {report['applied_count']} |",
            f"| 面试邀请数 | {report['interview_count']} |",
            f"| Offer 数 | {report['offer_count']} |",
            f"| 转化率 | {report['conversion_rate']} |",
            f"",
        ]

        if report.get("salary_stats", {}).get("count", 0) > 0:
            ss = report["salary_stats"]
            lines.extend([
                f"**薪资统计**: 共 {ss['count']} 条，平均 {ss['avg']}K（{ss['min']}-{ss['max']}K）",
                f"",
            ])

        if report.get("status_breakdown"):
            lines.extend([
                f"## 📈 状态分布",
                f"",
            ])
            for status, count in report["status_breakdown"].items():
                lines.append(f"- {status}: {count}")
            lines.append("")

        if report.get("insights"):
            lines.extend([
                f"## 💡 洞察",
                f"",
            ])
            for insight in report["insights"]:
                lines.append(f"- {insight}")
            lines.append("")

        if report.get("improvement_suggestions"):
            lines.extend([
                f"## 🎯 改进建议",
                f"",
            ])
            for suggestion in report["improvement_suggestions"]:
                lines.append(f"- {suggestion}")
            lines.append("")

        return "\n".join(lines)


# ============================================================
# 便捷函数
# ============================================================

_default_reporter: Optional[ResumeReporter] = None


def get_reporter() -> ResumeReporter:
    """获取默认报告生成器"""
    global _default_reporter
    if _default_reporter is None:
        _default_reporter = ResumeReporter()
    return _default_reporter


def generate_referral_report(period: str = "last_30_days") -> dict:
    """便捷函数：生成复盘报告"""
    return get_reporter().generate_referral_report(period)


# ============================================================
# 测试入口
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("求职复盘报告生成器测试")
    print("=" * 60)

    reporter = ResumeReporter()

    # 测试生成报告
    for period in ["last_week", "last_30_days", "last_90_days"]:
        report = reporter.generate_referral_report(period)
        print(f"\n[{period}]")
        print(f"  投递数: {report['applied_count']}")
        print(f"  面试数: {report['interview_count']}")
        print(f"  Offer数: {report['offer_count']}")
        print(f"  转化率: {report['conversion_rate']}")
        print(f"  洞察数: {len(report['insights'])}")
        print(f"  建议数: {len(report['improvement_suggestions'])}")

    print()
    print("-" * 60)

    # 格式化输出示例
    report = reporter.generate_referral_report("last_30_days")
    md = reporter.format_report_markdown(report)
    print("\nMarkdown 格式报告预览：")
    print(md)

    print()
    print("=" * 60)
    print("测试完成")
    print("=" * 60)