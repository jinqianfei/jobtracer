#!/usr/bin/env python3
"""
JobTracer 主入口
CLI 工具，支持 scan/search/resume/status/notify/daily 等命令
"""

import os
import sys
import json
import argparse
import asyncio
from datetime import datetime
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from storage.manager import StorageManager
from utils.feishu_bot import FeishuBot

# ============================================================
# 配置路径
# ============================================================

COOKIE_DIR = Path("~/.jobtracer/cookies").expanduser()
COOKIE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_COOKIE_PATH = COOKIE_DIR / "boss_cookies.json"

# ============================================================
# 辅助函数
# ============================================================

def print_step(step: str, msg: str):
    """打印带步骤标记的消息"""
    print(f"\n[Step {step}] {msg}")


def print_success(msg: str):
    print(f"  ✅ {msg}")


def print_error(msg: str):
    print(f"  ❌ {msg}")


def print_info(msg: str):
    print(f"  ℹ️  {msg}")


def load_webhook():
    """加载飞书 Webhook 配置"""
    webhook_path = Path("~/.jobtracer/feishu_webhook.json").expanduser()
    if not webhook_path.exists():
        return None
    try:
        with open(webhook_path, "r", encoding="utf-8") as f:
            return json.load(f).get("webhook_url")
    except Exception:
        return None


# ============================================================
# 命令: scan - 扫描数字足迹
# ============================================================

async def cmd_scan(args):
    """扫描数字足迹"""
    print_step(1, "扫描数字足迹...")

    from scanner.footprint_scanner import scan_all

    scan_result = await scan_all(
        user_id=args.user_id or "default",
        github_token=os.environ.get("GITHUB_TOKEN"),
    )

    print_success(f"扫描完成，共 {scan_result['total_files']} 个文件（去重后）")
    print_info(f"扫描耗时: {scan_result['duration_seconds']:.2f}s")
    print_info(f"各数据源: {scan_result['source_stats']}")

    return scan_result


# ============================================================
# 命令: search - 搜索职位
# ============================================================

async def cmd_search(args):
    """搜索职位"""
    print_step(1, "搜索职位...")

    keywords = args.keywords.split(",") if args.keywords else ["Python", "后端"]
    city = args.city or "上海"

    from boss.search import BOSSSearcher

    searcher = BOSSSearcher()
    result = await searcher.search_jobs(
        keywords=keywords,
        city=city,
        experience=args.experience or "不限",
        degree=args.degree or "不限",
        salary=args.salary or "不限",
        page=args.page or 1,
        page_size=args.page_size or 20,
    )

    if result.get("success"):
        jobs = result.get("jobs", [])
        print_success(f"找到 {len(jobs)} 个职位")
        for i, job in enumerate(jobs[: args.limit or 10], 1):
            salary = job.get("salary", "面议")
            location = job.get("location", "未知")
            print(f"  [{i}] {job.get('title', '未知职位')} @ {job.get('company', '未知公司')}")
            print(f"      💰 {salary} | 📍 {location}")
        return result
    else:
        print_error(f"搜索失败: {result.get('error')}")
        return None


# ============================================================
# 命令: cluster - 聚类项目
# ============================================================

async def cmd_cluster(args, scan_result=None):
    """聚类数字足迹项目"""
    print_step(1, "聚类项目...")

    if scan_result is None:
        # 先扫描
        from scanner.footprint_scanner import scan_all

        scan_result = await scan_all(user_id=args.user_id or "default")

    from clustering.engine import ProjectClusteringEngine

    engine = ProjectClusteringEngine()
    projects = await engine.cluster(scan_result)

    print_success(f"聚类出 {len(projects)} 个项目")

    for i, proj in enumerate(projects[:10], 1):
        name = proj.get("project_name", "Unknown")
        file_count = len(proj.get("files", []))
        confidence = proj.get("confidence", 0)
        tags = ", ".join(proj.get("tags", [])[:5])
        print(f"  [{i}] {name} (文件:{file_count}, 置信度:{confidence:.0%})")
        if tags:
            print(f"      🏷️ {tags}")

    # 保存项目
    if args.save:
        saved = engine.save_projects(projects)
        if saved:
            print_success("项目已保存到 footprint/projects/")
        else:
            print_error("项目保存失败")

    return projects


# ============================================================
# 命令: resume - 生成简历
# ============================================================

async def cmd_resume(args):
    """生成简历"""
    print_step(1, "生成简历...")

    from resume.generator import ResumeGenerator

    gen = ResumeGenerator()

    if args.project_names:
        project_names = [p.strip() for p in args.project_names.split(",")]
        resume = await gen.generate_from_projects(project_names=project_names)
    else:
        resume = await gen.generate_from_projects()

    # 保存简历
    saved = gen.save_resume(resume)
    if saved:
        print_success("简历已保存")
    else:
        print_error("简历保存失败")

    # 显示摘要
    name = resume.get("name", "未知")
    skills_count = len(resume.get("skills", []))
    projects_count = len(resume.get("projects", []))
    print_info(f"姓名: {name}")
    print_info(f"技能: {skills_count} 项")
    print_info(f"项目: {projects_count} 个")

    if args.export:
        export_path = gen.export_markdown(resume)
        print_success(f"Markdown 导出: {export_path}")

    if args.preview:
        html_path = gen.generate_html_file(resume)
        print_success(f"HTML 预览: {html_path}")

    # 验证
    validation = gen.validate_resume(resume)
    if validation["valid"]:
        print_success("简历校验通过")
    else:
        for err in validation["errors"]:
            print_error(f"错误: {err}")
        for warn in validation["warnings"]:
            print_info(f"警告: {warn}")

    return resume


# ============================================================
# 命令: status - 查看状态
# ============================================================

def cmd_status(args):
    """查看求职状态"""
    storage = StorageManager()

    print("\n📊 JobTracer 状态概览")
    print("=" * 50)

    # 读取各数据文件
    state = storage.get_state() or {}
    resume = storage.get_resume() or {}
    jobs = storage.get_jobs()
    feedbacks = storage.get_feedbacks()
    projects = storage.get_footprint_projects()

    print(f"\n👤 简历信息:")
    name = resume.get("name", "未设置")
    print(f"   姓名: {name}")
    target_role = resume.get("target_role", "未设置")
    print(f"   目标职位: {target_role}")
    skills = resume.get("skills", [])
    print(f"   技能: {len(skills)} 项 - {', '.join(skills[:8])}{'...' if len(skills) > 8 else ''}")

    print(f"\n💼 职位追踪:")
    print(f"   已保存职位: {len(jobs)} 个")
    new_jobs = [j for j in jobs if j.get("status") == "new"]
    applied_jobs = [j for j in jobs if j.get("status") == "applied"]
    print(f"   新职位: {len(new_jobs)} | 已投递: {len(applied_jobs)}")

    print(f"\n📁 数字足迹:")
    print(f"   项目数: {len(projects)}")
    footprint_summary = storage.get_footprint_summary()
    if footprint_summary:
        total_files = footprint_summary.get("total_files", "未知")
        print(f"   文件总数: {total_files}")

    print(f"\n💬 HR 反馈:")
    print(f"   反馈数: {len(feedbacks)}")

    # 最后更新
    state_last = state.get("last_active", "未知")
    print(f"\n🕐 最后活跃: {state_last}")

    print("\n" + "=" * 50)
    return state


# ============================================================
# 命令: notify - 发送飞书通知
# ============================================================

async def cmd_notify(args):
    """发送飞书通知"""
    webhook_url = load_webhook()

    if not webhook_url:
        print_error("飞书 Webhook 未配置，请先配置 ~/.jobtracer/feishu_webhook.json")
        return None

    print_step(1, f"发送飞书通知 [{args.type}]...")

    bot = FeishuBot(verify_ssl=False)

    if args.type == "test":
        result = await bot.send_daily_report(
            date=datetime.now().strftime("%Y-%m-%d"),
            new_jobs=0,
            status_changes=0,
            pending=0,
            new_job_list=[],
        )
    elif args.type == "jobs":
        # 发送新职位通知
        storage = StorageManager()
        jobs = storage.get_jobs()[:5]
        job_list = [
            {"title": j.get("title", ""), "company": j.get("company", "")}
            for j in jobs
        ]
        result = await bot.send_daily_report(
            date=datetime.now().strftime("%Y-%m-%d"),
            new_jobs=len(job_list),
            status_changes=0,
            pending=0,
            new_job_list=job_list,
        )
    elif args.type == "scan":
        # 发送扫描完成通知
        storage = StorageManager()
        summary = storage.get_footprint_summary() or {}
        result = await bot.send_scan_complete(
            total_files=summary.get("total_files", 0),
            platform_distribution=summary.get("platform_distribution", {}),
            new_projects=summary.get("new_projects", 0),
            clusters=summary.get("clusters", 0),
            duration_seconds=summary.get("duration_seconds", 0),
            scanned_at=summary.get("scanned_at", datetime.now().isoformat()),
        )
    else:
        print_error(f"未知通知类型: {args.type}")
        return None

    if result and result.get("success"):
        print_success("通知发送成功")
    else:
        error = result.get("error") if result else "未知错误"
        print_error(f"通知发送失败: {error}")

    return result


# ============================================================
# 命令: daily - 每日巡检
# ============================================================

async def cmd_daily(args):
    """每日巡检"""
    print(f"\n{'='*60}")
    print(f"JobTracer 每日巡检 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")

    # 1. 加载飞书配置
    webhook_url = load_webhook()
    if webhook_url:
        os.environ["FEISHU_WEBHOOK"] = webhook_url

    results = {}

    # 2. 扫描数字足迹
    print_step(1, "扫描数字足迹...")
    from scanner.footprint_scanner import scan_all

    scan_result = await scan_all(user_id=args.user_id or "default")
    print_success(f"扫描到 {scan_result['total_files']} 个文件")
    results["scan"] = scan_result

    # 3. 聚类项目
    print_step(2, "聚类项目...")
    from clustering.engine import ProjectClusteringEngine

    engine = ProjectClusteringEngine()
    projects = await engine.cluster(scan_result)
    print_success(f"聚类出 {len(projects)} 个项目")
    results["projects"] = projects

    # 保存项目
    engine.save_projects(projects)

    # 4. 生成/更新简历
    print_step(3, "生成简历...")
    from resume.generator import ResumeGenerator

    gen = ResumeGenerator()
    resume = await gen.generate_from_projects([p["project_name"] for p in projects])
    gen.save_resume(resume)
    print_success(f"简历已更新: {resume.get('name', 'unknown')}")
    results["resume"] = resume

    # 5. 搜索新职位（可选）
    if not args.no_search:
        print_step(4, "搜索新职位...")
        from boss.search import BOSSSearcher

        searcher = BOSSSearcher()
        keywords = args.keywords.split(",") if args.keywords else ["Python", "后端"]
        jobs_result = await searcher.search_jobs(
            keywords=keywords,
            city=args.city or "上海",
            page=1,
            page_size=args.job_count or 5,
        )
        new_jobs = jobs_result.get("jobs", []) if jobs_result.get("success") else []
        print_success(f"发现 {len(new_jobs)} 个新职位")
        results["jobs"] = new_jobs

        # 6. 保存新职位
        for job in new_jobs:
            storage = StorageManager()
            storage.add_job(job)
    else:
        results["jobs"] = []

    # 7. 发送飞书日报
    if not args.no_notify:
        print_step(5, "发送飞书日报...")

        webhook_config_path = Path("~/.jobtracer/feishu_webhook.json").expanduser()
        if webhook_config_path.exists():
            bot = FeishuBot(verify_ssl=False)
            job_list = [
                {"title": j.get("title", ""), "company": j.get("company", "")}
                for j in results.get("jobs", [])[:3]
            ]
            card_result = await bot.send_daily_report(
                date=datetime.now().strftime("%Y-%m-%d"),
                new_jobs=len(results.get("jobs", [])),
                status_changes=0,
                pending=len(projects),
                new_job_list=job_list,
            )
            if card_result.get("success"):
                print_success("日报发送成功")
                results["feishu"] = True
            else:
                print_error(f"日报发送失败: {card_result.get('error')}")
                results["feishu"] = False
        else:
            print_info("飞书未配置，跳过日报发送")
            results["feishu"] = None
    else:
        results["feishu"] = None

    # 汇总
    print("\n" + "=" * 60)
    print("📋 巡检汇总")
    print("=" * 60)
    print(f"  扫描文件: {scan_result['total_files']}")
    print(f"  聚类项目: {len(projects)}")
    print(f"  简历更新: ✅")
    print(f"  新职位数: {len(results.get('jobs', []))}")
    if results.get("feishu") is True:
        print(f"  飞书日报: ✅")
    elif results.get("feishu") is False:
        print(f"  飞书日报: ❌")
    else:
        print(f"  飞书日报: ⏭️ 跳过")
    print("=" * 60)

    return results


# ============================================================
# 命令: match - JD 匹配
# ============================================================

async def cmd_match(args):
    """对职位进行 JD 匹配评分"""
    print_step(1, "职位 JD 匹配...")

    from matching.scorer import JDMatcher

    # 加载简历
    storage = StorageManager()
    resume = storage.get_resume()
    if not resume:
        print_error("简历未生成，请先运行 resume 命令")
        return None

    # 加载职位
    jobs = storage.get_jobs()
    if not jobs:
        print_error("没有已保存的职位，请先运行 search 命令")
        return None

    # 选择前 N 个职位评分
    target_jobs = jobs[: args.top or 10]

    matcher = JDMatcher()
    matched = []

    for job in target_jobs:
        score = await matcher.score_job(job, resume)
        matched.append((job, score))

    # 按分数排序
    matched.sort(key=lambda x: x[1], reverse=True)

    print_success(f"匹配完成，共 {len(matched)} 个职位")
    print("\n📊 匹配结果:")
    for i, (job, score) in enumerate(matched, 1):
        bar = "█" * int(score / 10) + "░" * (10 - int(score / 10))
        print(f"  [{i:2d}] {score:3.0f}/100 [{bar}] {job.get('title', '')} @ {job.get('company', '')}")

    return matched


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        prog="jobtracer",
        description="JobTracer - 智能求职追踪助手",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m jobtracer scan              # 扫描数字足迹
  python -m jobtracer search "Python,后端" --city 上海  # 搜索职位
  python -m jobtracer resume             # 生成简历
  python -m jobtracer status             # 查看状态
  python -m jobtracer notify --type test # 发送测试飞书通知
  python -m jobtracer daily              # 执行每日巡检
  python -m jobtracer cluster            # 聚类项目
  python -m jobtracer match              # JD 匹配
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # ---- scan ----
    p_scan = subparsers.add_parser("scan", help="扫描数字足迹")
    p_scan.add_argument("--user-id", default="default", help="用户ID（默认: default）")

    # ---- search ----
    p_search = subparsers.add_parser("search", help="搜索职位")
    p_search.add_argument("--keywords", "-k", help="搜索关键词（逗号分隔）")
    p_search.add_argument("--city", "-c", default="上海", help="工作城市（默认: 上海）")
    p_search.add_argument("--experience", default="不限", help="经验要求")
    p_search.add_argument("--degree", default="不限", help="学历要求")
    p_search.add_argument("--salary", default="不限", help="薪资要求")
    p_search.add_argument("--page", type=int, default=1, help="页码")
    p_search.add_argument("--page-size", type=int, default=20, help="每页数量")
    p_search.add_argument("--limit", type=int, default=10, help="最多显示数量")

    # ---- cluster ----
    p_cluster = subparsers.add_parser("cluster", help="聚类数字足迹项目")
    p_cluster.add_argument("--user-id", default="default", help="用户ID")
    p_cluster.add_argument("--save", action="store_true", help="保存项目到文件")

    # ---- resume ----
    p_resume = subparsers.add_parser("resume", help="生成/更新简历")
    p_resume.add_argument("--project-names", help="指定项目名（逗号分隔）")
    p_resume.add_argument("--export", action="store_true", help="导出 Markdown")
    p_resume.add_argument("--preview", action="store_true", help="生成 HTML 预览")

    # ---- status ----
    subparsers.add_parser("status", help="查看求职状态")

    # ---- notify ----
    p_notify = subparsers.add_parser("notify", help="发送飞书通知")
    p_notify.add_argument(
        "--type",
        "-t",
        choices=["test", "jobs", "scan"],
        default="test",
        help="通知类型: test=测试, jobs=职位列表, scan=扫描报告",
    )

    # ---- daily ----
    p_daily = subparsers.add_parser("daily", help="执行每日巡检")
    p_daily.add_argument("--user-id", default="default", help="用户ID")
    p_daily.add_argument("--keywords", help="搜索关键词（逗号分隔）")
    p_daily.add_argument("--city", default="上海", help="工作城市")
    p_daily.add_argument("--job-count", type=int, default=5, help="搜索职位数量")
    p_daily.add_argument("--no-search", action="store_true", help="跳过职位搜索")
    p_daily.add_argument("--no-notify", action="store_true", help="跳过飞书通知")

    # ---- match ----
    p_match = subparsers.add_parser("match", help="JD 匹配评分")
    p_match.add_argument("--top", type=int, default=10, help="评分前N个职位")

    # ---- init ----
    p_init = subparsers.add_parser("init", help="初始化配置目录")

    args = parser.parse_args()

    # 无命令时显示帮助
    if not args.command:
        parser.print_help()
        return 0

    # init 命令：创建配置目录
    if args.command == "init":
        print_step(1, "初始化配置目录...")
        base = Path("~/.jobtracer").expanduser()
        base.mkdir(parents=True, exist_ok=True)
        (base / "memory").mkdir(exist_ok=True)
        (base / "cookies").mkdir(exist_ok=True)
        (base / "footprint/projects").mkdir(parents=True, exist_ok=True)
        (base / "jobs/jd_cache").mkdir(parents=True, exist_ok=True)

        # 创建默认配置文件
        state_path = base / "state.json"
        if not state_path.exists():
            state_path.write_text(
                json.dumps(
                    {"current_step": 0, "user_id": None, "last_active": datetime.now().isoformat()},
                    ensure_ascii=False,
                    indent=2,
                )
            )

        prefs_path = base / "preferences.json"
        if not prefs_path.exists():
            prefs_path.write_text(
                json.dumps(
                    {"notification_time": "09:00", "language": "zh-CN", "timezone": "Asia/Shanghai"},
                    ensure_ascii=False,
                    indent=2,
                )
            )

        print_success(f"配置目录已初始化: {base}")
        print_info("请配置 ~/.jobtracer/feishu_webhook.json（飞书 Webhook）")
        return 0

    # 异步命令执行
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        if args.command == "scan":
            loop.run_until_complete(cmd_scan(args))
        elif args.command == "search":
            loop.run_until_complete(cmd_search(args))
        elif args.command == "cluster":
            loop.run_until_complete(cmd_cluster(args))
        elif args.command == "resume":
            loop.run_until_complete(cmd_resume(args))
        elif args.command == "status":
            cmd_status(args)
        elif args.command == "notify":
            loop.run_until_complete(cmd_notify(args))
        elif args.command == "daily":
            loop.run_until_complete(cmd_daily(args))
        elif args.command == "match":
            loop.run_until_complete(cmd_match(args))
        else:
            parser.print_help()
    finally:
        loop.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())