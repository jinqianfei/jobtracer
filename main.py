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

    platforms = None
    if args.platforms:
        platforms = [p.strip() for p in args.platforms.split(",")]

    if platforms:
        # 多平台搜索
        from jobs.multi_platform_search import MultiPlatformSearcher
        searcher = MultiPlatformSearcher()
        result = await searcher.search_all(keywords=keywords, city=city, platforms=platforms)
        
        all_jobs = []
        for p in platforms:
            all_jobs.extend(result.get(p, []))
        
        jobs = searcher.dedup_jobs(all_jobs)
        print_success(f"找到 {len(jobs)} 个职位（{result['total']} 总计，去重后 {result['deduped']}，新职位 {len(result['new_jobs'])}）")
        for i, job in enumerate(jobs[:args.limit or 10], 1):
            salary = job.get("salary", "面议")
            location = job.get("location", "未知")
            platform = job.get("platform", "unknown")
            print(f"  [{i}][{platform}] {job.get('title', job.get('name', '未知职位'))} @ {job.get('company', '未知公司')}")
            print(f"      💰 {salary} | 📍 {location}")
        return result
    else:
        # 单平台搜索（BOSS）
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
            # 同步更新 projects_index.json
            from storage.manager import get_manager
            storage = get_manager()
            projects_index = []
            for p in projects:
                projects_index.append({
                    "project_id": p.get("project_id"),
                    "project_name": p.get("project_name", "Unknown"),
                    "description": p.get("description", ""),
                    "tags": p.get("tags", []),
                    "file_count": len(p.get("files", [])),
                    "confidence": p.get("confidence", 0),
                    "source": p.get("source", "local"),
                    "created_at": datetime.now().isoformat()
                })
            storage.set_footprint_projects(projects_index)
            print_success(f"projects_index.json 已更新 ({len(projects_index)} 条)")
        else:
            print_error("项目保存失败")

    return projects


# ============================================================
# 命令: resume - 生成简历
# ============================================================

async def cmd_resume(args):
    """生成简历"""
    from resume.generator import ResumeGenerator
    from resume.customizer import ResumeCustomizer
    from matching.scorer import JDMatcher
    from storage.manager import StorageManager

    storage = StorageManager()

    # ── 定制简历预览/确认流程 ──
    if args.customize:
        print_step(1, f"定制简历: {args.customize}...")

        # 加载职位
        jobs = storage.get_jobs()
        job = None
        for j in jobs:
            key = f"{j.get('company', '')}|{j.get('title', '')}"
            if args.customize in key or args.customize in (j.get('job_id') or j.get('security_id') or ''):
                job = j
                break

        if not job:
            print_error(f"未找到职位: {args.customize}")
            return None

        print_info(f"职位: {job.get('title', '?')} @ {job.get('company', '?')}")

        # 加载 match_result（可选）
        match_result = None
        if args.match:
            try:
                import json
                match_result = json.loads(args.match)
            except json.JSONDecodeError:
                print_error("match JSON 格式错误")
                return None

        # 加载简历
        resume = storage.get_resume()
        if not resume:
            print_error("简历未生成，请先运行 resume 命令（不带 --customize）")
            return None

        customizer = ResumeCustomizer(base_resume=resume)

        # 预览模式（dry_run）
        if args.preview and not args.confirm:
            result = await customizer.generate_customized_resume(
                job=job,
                base_resume=resume,
                match_result=match_result,
                dry_run=True
            )
            if result.get('preview_markdown'):
                print()
                print(result['preview_markdown'])
            return result

        # 确认模式（实际保存）
        if args.confirm:
            result = await customizer.generate_customized_resume(
                job=job,
                base_resume=resume,
                match_result=match_result,
                dry_run=False
            )
            if result.get('confirmed'):
                print_success(f"定制简历已保存: {result.get('resume_path')}")
            else:
                print_error(f"保存失败: {result.get('error')}")
            return result

        # 只有 --customize 没有 --preview/--confirm：自动预览
        result = await customizer.generate_customized_resume(
            job=job,
            base_resume=resume,
            match_result=match_result,
            dry_run=True
        )
        if result.get('preview_markdown'):
            print()
            print(result['preview_markdown'])
            print_info("使用 --confirm 确认并保存，或重新生成后再次预览")
        return result

    # ── 普通简历生成流程 ──
    print_step(1, "生成简历...")

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
    storage = StorageManager()
    all_jobs = storage.get_jobs()

    if args.type == "test":
        result = await bot.send_daily_report(
            date=datetime.now().strftime("%Y-%m-%d"),
            saved_jobs=len(all_jobs),
            new_jobs=0,
            applied=0,
            interviewing=0,
            offer_count=0,
            use_v2=True,
        )
    elif args.type == "jobs":
        job_list = [
            {"title": j.get("title", ""), "company": j.get("company", "")}
            for j in all_jobs[:5]
        ]
        result = await bot.send_daily_report(
            date=datetime.now().strftime("%Y-%m-%d"),
            saved_jobs=len(all_jobs),
            new_jobs=0,
            applied=0,
            interviewing=0,
            offer_count=0,
            new_job_list=job_list,
            use_v2=True,
        )
    elif args.type == "scan":
        summary = storage.get_footprint_summary() or {}
        result = await bot.send_scan_complete(
            total_files=summary.get("total_files", 0),
            platform_distribution=summary.get("platform_distribution", {}),
            new_projects=summary.get("new_projects", 0),
            clusters=summary.get("clusters", 0),
            duration_seconds=summary.get("duration_seconds", 0),
            scanned_at=summary.get("scanned_at", datetime.now().isoformat()),
        )
    elif args.type == "daily":
        # 发送完整求职日报
        applied_count = sum(1 for j in all_jobs if j.get("status") in ("applied", "replied"))
        interviewing_count = sum(1 for j in all_jobs if j.get("status") in ("interview", "interviewing", "video_interview", "onsite"))
        offer_count = sum(1 for j in all_jobs if j.get("status") in ("offer", "offer_received", "accepted"))
        projects = storage.get_footprint_projects()
        job_list = [
            {"title": j.get("title", ""), "company": j.get("company", "")}
            for j in all_jobs[:3]
        ]
        result = await bot.send_daily_report(
            date=datetime.now().strftime("%Y-%m-%d"),
            saved_jobs=len(all_jobs),
            new_jobs=0,
            applied=applied_count,
            interviewing=interviewing_count,
            offer_count=offer_count,
            new_job_list=job_list,
            project_count=len(projects),
            use_v2=True,
        )
    elif args.type == "weekly":
        # 发送周报（更详细）
        from reporting.resume_reporter import ResumeReporter
        reporter = ResumeReporter()
        report = reporter.generate_referral_report("last_week")
        applied_count = report.get("applied_count", 0)
        interview_count = report.get("interview_count", 0)
        offer_count = report.get("offer_count", 0)

        # 构建周报卡片
        card_elements = [
            {"tag": "div", "text": {"tag": "lark_md", "content": f"**📊 本周求职周报 · {datetime.now().strftime('%Y-%m-%d')}**"}},
            {"tag": "hr"},
            {"tag": "div", "text": {"tag": "lark_md", "content": f"投递漏斗：{applied_count}投递 → {interview_count}面试 → {offer_count}Offer\n本周转化率：面试率 {report.get('conversion_rate', 'N/A')}"}},
            {"tag": "hr"},
        ]
        if report.get("insights"):
            card_elements.append({"tag": "div", "text": {"tag": "lark_md", "content": "**💡 洞察**"}})
            for insight in report["insights"][:3]:
                card_elements.append({"tag": "div", "text": {"tag": "lark_md", "content": f"• {insight}"}})
            card_elements.append({"tag": "hr"})
        if report.get("improvement_suggestions"):
            card_elements.append({"tag": "div", "text": {"tag": "lark_md", "content": "**🎯 改进建议**"}})
            for sug in report["improvement_suggestions"][:3]:
                card_elements.append({"tag": "div", "text": {"tag": "lark_md", "content": f"• {sug}"}})
        card_elements.append({"tag": "action", "actions": [
            {"tag": "button", "text": {"tag": "plain_text", "content": "查看完整报告"}, "type": "secondary", "value": "report"},
        ]})
        card = {
            "msg_type": "interactive",
            "card": {
                "header": {"title": {"tag": "plain_text", "content": f"📊 周报 · {datetime.now().strftime('%Y-%m-%d')}"}, "template": "blue"},
                "elements": card_elements,
            }
        }
        result = await bot.send_card(card)
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
            # 获取投递统计
            storage = StorageManager()
            all_jobs = storage.get_jobs()
            applied_count = sum(1 for j in all_jobs if j.get("status") in ("applied", "replied"))
            interviewing_count = sum(1 for j in all_jobs if j.get("status") in ("interview", "interviewing", "video_interview", "onsite"))
            offer_count = sum(1 for j in all_jobs if j.get("status") in ("offer", "offer_received", "accepted"))

            job_list = [
                {"title": j.get("title", ""), "company": j.get("company", "")}
                for j in results.get("jobs", [])[:3]
            ]
            bot = FeishuBot(verify_ssl=False)
            card_result = await bot.send_daily_report(
                date=datetime.now().strftime("%Y-%m-%d"),
                saved_jobs=len(all_jobs),
                new_jobs=len(results.get("jobs", [])),
                applied=applied_count,
                interviewing=interviewing_count,
                offer_count=offer_count,
                new_job_list=job_list,
                project_count=len(projects),
                project_new=0,
                use_v2=True,
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
    print(f"下次运行：明天 09:00")
    print("=" * 60)

    return results


# ============================================================
# 命令: match - JD 匹配
# ============================================================


# ============================================================
# 命令: import - LinkedIn 导入
# ============================================================

async def cmd_import(args):
    """从 LinkedIn 导入简历数据"""
    print_step(1, "导入 LinkedIn 数据...")

    from integrations.linkedin_importer import import_linkedin_profile, convert_to_resume_experience, convert_to_resume_education

    cookie = args.cookie
    if not cookie:
        cookie_path = Path("~/.jobtracer/cookies/linkedin_cookie.txt").expanduser()
        if cookie_path.exists():
            cookie = cookie_path.read_text().strip()

    profile = import_linkedin_profile(cookie)

    if profile.get("_import_note"):
        print_info(profile["_import_note"])
        return profile

    # 加载现有简历
    storage = StorageManager()
    current_resume = storage.get_resume() or {}

    # 合并策略
    strategy = args.prefer  # "linkedin" or "existing"

    if strategy == "prefer_linkedin":
        merged = dict(current_resume)
        if profile.get("name"):
            merged["name"] = profile["name"]
        merged["experience"] = convert_to_resume_experience(profile)
        merged["education"] = convert_to_resume_education(profile)
        # 合并技能
        existing_skills = {s.lower() for s in merged.get("skills", [])}
        new_skills = [s for s in profile.get("skills", []) if s.lower() not in existing_skills]
        if new_skills:
            merged["skills"] = merged.get("skills", []) + new_skills[:10]
    else:
        # existing 优先，只补充不冲突部分
        merged = dict(current_resume)
        existing_titles = {e.get("title", "") for e in current_resume.get("experience", [])}
        for exp in convert_to_resume_experience(profile):
            if exp.get("title") not in existing_titles:
                merged.setdefault("experience", []).append(exp)

    # 保存
    from resume.generator import ResumeGenerator
    gen = ResumeGenerator()
    gen.save_resume(merged)

    print_success(f"LinkedIn 数据已导入并合并到简历")
    print_info(f"姓名: {profile.get('name', 'N/A')}")
    print_info(f"工作经历: {len(profile.get('experience', []))} 条")
    print_info(f"教育经历: {len(profile.get('education', []))} 条")
    print_info(f"技能: {len(profile.get('skills', []))} 项")

    return profile


# ============================================================
# 命令: github-sync - GitHub 贡献同步
# ============================================================

async def cmd_github_sync(args):
    """同步 GitHub 贡献数据到简历"""
    print_step(1, f"同步 GitHub @{args.username} 贡献数据...")

    from integrations.github_contribution import sync_github_contributions, integrate_as_resume_projects

    token = args.token or os.environ.get("GITHUB_TOKEN")
    data = sync_github_contributions(args.username, token)

    if data.get("total_repos", 0) == 0 and not data.get("highlights"):
        print_error(f"无法获取 GitHub 用户 @{args.username} 的数据")
        return None

    print_success(f"GitHub 数据同步完成")
    print_info(f"总仓库数: {data.get('total_repos', 0)}")
    print_info(f"主要语言: {', '.join(data.get('top_languages', []))}")

    # 将 GitHub 项目整合到简历
    gh_projects = integrate_as_resume_projects(data)
    if gh_projects:
        storage = StorageManager()
        current_resume = storage.get_resume() or {}
        existing_names = {p.get("name", "").lower() for p in current_resume.get("projects", [])}
        for p in gh_projects:
            if p["name"].lower() not in existing_names:
                current_resume.setdefault("projects", []).append(p)

        from resume.generator import ResumeGenerator
        gen = ResumeGenerator()
        gen.save_resume(current_resume)
        print_success(f"已将 {len(gh_projects)} 个 GitHub 项目添加到简历")

    # 打印亮点
    print("\n📊 能力亮点:")
    for h in data.get("highlights", []):
        print(f"  • {h}")

    return data


# ============================================================
# 命令: fill - 智能填充简历
# ============================================================

async def cmd_fill(args):
    """智能填充简历空白内容"""
    print_step(1, "智能填充简历...")

    from resume.intelligent_filler import auto_fill_resume

    resume_path = args.resume_path
    result = auto_fill_resume(resume_path)

    added = result["added_projects"]
    if not added:
        print_info("简历已完整，未发现缺失项目")
        return result

    print_success(f"发现并填充 {len(added)} 个缺失项目:")
    for p in added:
        conf = result["confidence_scores"].get(p["name"], 0)
        print(f"  • {p['name']} (置信度: {conf:.0%})")
        if p.get("tech_stack"):
            print(f"    技术栈: {', '.join(p['tech_stack'][:5])}")

    # 保存填充后的简历
    from resume.generator import ResumeGenerator
    gen = ResumeGenerator()
    gen.save_resume(result["filled_resume"])
    print_success(f"简历已更新，共 {len(result['filled_resume']['projects'])} 个项目")

    return result


# ============================================================
# 命令: offer-compare - Offer 比较
# ============================================================

def cmd_offer_compare(args):
    """Offer 比较分析"""
    from tools.offer_comparator import compare_offers

    print_step(1, "Offer 比较分析...")

    # 示例 Offer 数据
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

    if args.offers:
        try:
            import json
            offer_list = json.loads(args.offers)
        except json.JSONDecodeError:
            print_error("Offer JSON 格式错误")
            return None
    else:
        print_info("使用示例 Offer 数据")
        offer_list = sample_offers

    result = compare_offers(offer_list)

    print_success(f"共 {len(result['ranking'])} 个 Offer")
    print("\n🏆 排名:")
    for i, item in enumerate(result["ranking"], 1):
        offer = item["offer"]
        score = item["total_score"]
        bar = "█" * int(score / 10) + "░" * (10 - int(score / 10))
        print(f"  #{i} {offer['company']} ({offer.get('title', '')}) {score:.1f}/100 [{bar}]")
        highlights = item.get("highlights", [])
        if highlights:
            print(f"      ✨ {', '.join(highlights[:3])}")

    if args.show_matrix:
        print("\n📊 对比矩阵:")
        matrix = result["comparison_matrix"]
        print(f"  公司: {', '.join(matrix['companies'])}")
        for dim in matrix["dimensions"]:
            scores = [str(s[dim]) for s in matrix["scores"]]
            print(f"  {dim:12s}: {', '.join(scores)}")

    print(f"\n💡 {result['recommendation']}")
    return result


# ============================================================
# 命令: team-dashboard - 团队看板
# ============================================================

def cmd_team_dashboard(args):
    """团队数据看板"""
    from teams.manager import TeamManager, TeamRole

    manager = TeamManager()

    if args.create:
        if not args.name:
            print_error("创建团队需要提供 --name 参数")
            return None

        print_step(1, "创建团队...")
        team = manager.create_team(
            name=args.name,
            owner_id=args.owner_id,
            description=args.description or ""
        )
        print_success(f"团队创建成功: {team['team_id']}")
        print_info(f"团队名: {team['name']}")
        return team

    if args.team_id:
        print_step(1, "加载团队看板...")
        dashboard = manager.get_team_dashboard(args.team_id)
        if not dashboard or "error" in dashboard:
            print_error(f"团队不存在: {args.team_id}")
            return None

        print_success(f"团队: {dashboard['name']}")
        print(f"\n📊 数据看板")
        print("=" * 50)

        stats = dashboard.get("stats", {})
        print(f"  职位总数: {stats.get('total_positions', 0)}")
        print(f"  候选人: {stats.get('total_candidates', 0)}")
        print(f"  面试安排: {stats.get('interviews_scheduled', 0)}")
        print(f"  Offer发放: {stats.get('offers_extended', 0)}")
        print(f"  成交: {stats.get('deals_closed', 0)}")

        members = dashboard.get("members", [])
        print(f"\n👥 成员 ({len(members)} 人)")
        for m in members:
            role = m.get("role", "unknown")
            joined = m.get("joined_at", "")[:10] if m.get("joined_at") else "未知"
            print(f"  - {m['user_id']} | {role} | 加入: {joined}")

        print("=" * 50)
        return dashboard
    else:
        print_step(1, "团队列表...")
        teams = manager.list_teams()
        if not teams:
            print_info("暂无团队，可使用 --create 创建")
            return []

        print_success(f"共 {len(teams)} 个团队")
        for team in teams:
            stats = team.get("stats", {})
            member_count = len(team.get("members", []))
            print(f"\n  [{team['team_id']}] {team['name']}")
            print(f"      成员: {member_count} | 职位: {stats.get('total_positions', 0)} | 成交: {stats.get('deals_closed', 0)}")

        return teams


# ============================================================
# 命令: api-server - API 服务器
# ============================================================

def cmd_api_server(args):
    """启动 API 服务器"""
    import uvicorn

    print_step(1, "启动 API 服务器...")
    print_info(f"监听: {args.host}:{args.port}")
    print_info("文档: http://localhost:8000/docs")
    print_info("按 Ctrl+C 停止")

    uvicorn.run(
        "api.server:app",
        host=args.host,
        port=args.port,
        reload=False,
        log_level="info"
    )


# ============================================================
# 命令: apply - 投递状态管理
# ============================================================

def cmd_apply(args):
    """投递状态管理"""
    from jobs.delivery_tracker import DeliveryTracker
    
    tracker = DeliveryTracker()
    
    # 统计模式
    if args.stats:
        stats = tracker.get_application_stats()
        # 同时显示原始状态分布
        all_jobs = tracker.storage.get_jobs()
        from collections import Counter
        raw_statuses = Counter(j.get('status', 'unknown') for j in all_jobs)
        
        print("📊 投递统计:")
        print(f"  已保存: {stats.get('saved', 0)} 个")
        print(f"  已投递: {stats.get('applied', 0)} 个")
        print(f"  面试中: {stats.get('interview', 0)} 个")
        print(f"  Offer: {stats.get('offer', 0)} 个")
        print(f"  ---原始状态分布---")
        for s, c in sorted(raw_statuses.items()):
            print(f"    [{s}]: {c} 个")
        return
    
    # 列表模式
    if args.list:
        status_map = {
            "saved": "saved",
            "applied": "applied",
            "interview": None,  # 包含所有面试状态
            "offer": "offer",
        }
        target = status_map.get(args.list)
        if args.list == "interview":
            jobs = []
            for s in ["screening", "interview_t1", "interview_t2", "interview_t3"]:
                jobs.extend(tracker.get_jobs_by_status(s))
        else:
            jobs = tracker.get_jobs_by_status(target) if target else []
        
        if not jobs:
            print_info(f"没有状态为 {args.list} 的职位")
            return
        
        print(f"📋 {args.list} 职位 ({len(jobs)} 个):")
        for j in jobs:
            title = j.get('title', j.get('name', '?'))
            company = j.get('company', '?')
            status = j.get('status', '?')
            print(f"  [{status}] {title} @ {company}")
        return
    
    # 更新状态模式
    if args.job_id:
        # 查找职位
        jobs = tracker.storage.get_jobs()
        job = next((j for j in jobs if j.get('job_id') == args.job_id), None)
        
        if not job:
            # 按 company+title 查找
            for j in jobs:
                key = f"{j.get('company','')}|{j.get('title', j.get('name',''))}"
                if args.job_id in key or args.job_id in j.get('job_id', ''):
                    job = j
                    break
        
        if not job:
            print_error(f"找不到职位: {args.job_id}")
            return
        
        # 更新状态
        new_status = args.status or "applied"
        note = args.note or ""
        result = tracker.storage.update_job_status(job['job_id'], new_status, note)
        
        if result.get('success'):
            print_success(f"状态更新成功: {job.get('title', job.get('name', '?'))} → {new_status}")
        else:
            print_error(f"更新失败: {result.get('error', '未知错误')}")
        return
    
    # 默认：列出所有职位及状态
    jobs = tracker.storage.get_jobs()
    if not jobs:
        print_info("暂无保存的职位")
        return
    
    print(f"📋 职位列表 ({len(jobs)} 个):")
    status_emoji = {
        "saved": "💾", "applied": "📨", "screening": "📝",
        "interview_t1": "🗣一面", "interview_t2": "🗣二面", "interview_t3": "🗣三面",
        "offer": "🎉Offer", "hired": "✅入职", "rejected": "❌拒绝",
    }
    for j in jobs:
        title = j.get('title', j.get('name', '?'))
        company = j.get('company', '?')
        status = j.get('status', 'saved')
        emoji = status_emoji.get(status, "📌")
        print(f"  {emoji} [{status}] {title} @ {company}")


# ============================================================
# 命令: career - 职业规划分析
# ============================================================

def cmd_career(args):
    """职业规划分析"""
    from career_planning.planner import CareerPlanner, analyze_background, suggest_career_paths
    from career_planning.roadmap_generator import generate_learning_roadmap, generate_markdown_report, generate_career_roadmap

    # 加载简历数据
    storage = StorageManager()
    resume = storage.get_resume() or {}
    if args.resume_json:
        import json
        resume = json.loads(args.resume_json)

    print_step(1, "职业背景分析...")
    planner = CareerPlanner(resume, [])
    background = planner.analyze_background()

    print_info(f"工作年限: {background['work_years']}年")
    print_info(f"当前级别: {background['level']}")
    print_info(f"优势: {', '.join(background['strengths'][:3])}")

    print_step(2, "生成职业路径建议...")
    paths = planner.suggest_career_paths(background)
    for i, p in enumerate(paths, 1):
        print(f"  {i}. {p['path_name']} ({p['match_score']}%匹配度)")
        print(f"     目标: {', '.join(p['target_roles'][:2])}")
        print(f"     成功率: {p['success_rate']}")

    if args.roadmap and paths:
        print_step(3, "生成学习路线图...")
        selected = None
        if args.path:
            selected = next((p for p in paths if args.path in p['path_key']), paths[0])
        else:
            selected = paths[0]
        roadmap = generate_learning_roadmap(selected, background['skills'])
        print_info(f"路径: {selected['path_name']}")
        for item in roadmap['learning_plan']:
            print(f"  Month {item['month']}: {item['focus']} → {item['deliverable']}")
        print()
        mermaid = generate_career_roadmap(selected, background['skills'])
        print(mermaid)

    elif args.report:
        print_step(3, "生成完整规划报告...")
        report = generate_markdown_report(paths, background)
        report_path = storage.data_dir / "career_report.md"
        Path(report_path).write_text(report, encoding="utf-8")
        print_success(f"报告已保存: {report_path}")
    else:
        print()
        print_info("使用 --roadmap 查看详细路线图")
        print_info("使用 --report 生成完整 Markdown 报告")

        print_info("使用 --path <路径key> 查看特定路径")


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
    p_search.add_argument("--platforms", "-p", help="搜索平台（逗号分隔，支持: boss,51job,zhilian，默认全部）")
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
    p_resume.add_argument("--customize", metavar="JOB_ID", help="针对目标职位生成定制简历")
    p_resume.add_argument("--match", metavar="MATCH_JSON", help="JD匹配结果 JSON（配合 --customize 使用）")
    p_resume.add_argument("--preview", action="store_true", help="预览定制简历（dry_run 模式，不保存）")
    p_resume.add_argument("--confirm", action="store_true", help="确认生成定制简历（实际保存文件）")

    # ---- status ----
    subparsers.add_parser("status", help="查看求职状态")

    # ---- notify ----
    p_notify = subparsers.add_parser("notify", help="发送飞书通知")
    p_notify.add_argument(
        "--type",
        "-t",
        choices=["test", "jobs", "scan", "daily", "weekly"],
        default="test",
        help="通知类型: test=测试, jobs=职位列表, scan=扫描报告, daily=求职日报, weekly=周报",
    )

    # ---- daily ----
    p_daily = subparsers.add_parser("daily", help="执行每日巡检")
    p_daily.add_argument("--user-id", default="default", help="用户ID")
    p_daily.add_argument("--keywords", help="搜索关键词（逗号分隔）")
    p_daily.add_argument("--city", default="上海", help="工作城市")
    p_daily.add_argument("--job-count", type=int, default=5, help="搜索职位数量")
    p_daily.add_argument("--no-search", action="store_true", help="跳过职位搜索")
    p_daily.add_argument("--no-notify", action="store_true", help="跳过飞书通知")
    p_daily.add_argument("--auto", action="store_true", help="自动模式（跳过确认提示）")
    p_daily.add_argument("--setup-cron", action="store_true", help="设置每日 09:00 cron 任务")
    p_daily.add_argument("--show-cron", action="store_true", help="查看当前 cron 配置")

    # ---- match ----
    p_match = subparsers.add_parser("match", help="JD 匹配评分")
    p_match.add_argument("--top", type=int, default=10, help="评分前N个职位")

    # ---- apply ----
    p_apply = subparsers.add_parser("apply", help="标记职位为已投递")
    p_apply.add_argument("job_id", nargs="?", help="职位ID（省略则列出待投递）")
    p_apply.add_argument("--status", help="更新状态（applied/screening/interview_t1/t2/t3/offer/rejected）")
    p_apply.add_argument("--note", help="状态备注")
    p_apply.add_argument("--stats", action="store_true", help="显示投递统计")
    p_apply.add_argument("--list", metavar="STATUS", help="按状态筛选职位（saved/applied/interview/offer）")

    # ---- import ----
    p_import = subparsers.add_parser("import", help="从 LinkedIn 导入简历数据")
    p_import.add_argument("--cookie", help="LinkedIn 登录 Cookie")
    p_import.add_argument("--prefer", choices=["linkedin", "existing"], default="linkedin",
                         help="数据合并策略（默认: linkedin）")

    # ---- github-sync ----
    p_github_sync = subparsers.add_parser("github-sync", help="同步 GitHub 贡献数据到简历")
    p_github_sync.add_argument("username", help="GitHub 用户名")
    p_github_sync.add_argument("--token", help="GitHub Personal Access Token")

    # ---- fill ----
    p_fill = subparsers.add_parser("fill", help="智能填充简历空白内容")
    p_fill.add_argument("--resume-path", help="简历文件路径")

    # ---- offer-compare ----
    p_offer = subparsers.add_parser("offer-compare", help="Offer 比较分析")
    p_offer.add_argument("--offers", "-o", help="JSON 格式的 Offer 列表")
    p_offer.add_argument("--show-matrix", action="store_true", help="显示对比矩阵")

    # ---- team-dashboard ----
    p_team = subparsers.add_parser("team-dashboard", help="团队数据看板")
    p_team.add_argument("--team-id", help="团队ID")
    p_team.add_argument("--create", action="store_true", help="创建新团队")
    p_team.add_argument("--name", help="团队名称")
    p_team.add_argument("--description", help="团队描述")
    p_team.add_argument("--owner-id", default="default", help="所有者ID")

    # ---- api-server ----
    p_api = subparsers.add_parser("api-server", help="启动 API 服务器")
    p_api.add_argument("--host", default="0.0.0.0", help="监听地址")
    p_api.add_argument("--port", type=int, default=8000, help="监听端口")
    # ---- career ----
    p_career = subparsers.add_parser("career", help="职业规划分析")
    p_career.add_argument("--path", help="查看指定路径详情")
    p_career.add_argument("--roadmap", action="store_true", help="生成学习路线图")
    p_career.add_argument("--report", action="store_true", help="输出完整规划报告")
    p_career.add_argument("--resume-json", help="简历 JSON 数据（可选）")


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
            # 处理 cron 管理命令（不在 asyncio 中执行）
            if args.setup_cron:
                import subprocess
                result = subprocess.run(
                    [sys.executable, str(Path(__file__).parent / "daily_cron.py"), "--setup-cron"],
                    capture_output=True, text=True
                )
                print(result.stdout)
                if result.stderr:
                    print(result.stderr, file=sys.stderr)
                return
            elif args.show_cron:
                import subprocess
                result = subprocess.run(
                    [sys.executable, str(Path(__file__).parent / "daily_cron.py"), "--show-cron"],
                    capture_output=True, text=True
                )
                print(result.stdout)
                if result.stderr:
                    print(result.stderr, file=sys.stderr)
                return
            loop.run_until_complete(cmd_daily(args))
        elif args.command == "match":
            loop.run_until_complete(cmd_match(args))
        elif args.command == "import":
            loop.run_until_complete(cmd_import(args))
        elif args.command == "github-sync":
            loop.run_until_complete(cmd_github_sync(args))
        elif args.command == "fill":
            loop.run_until_complete(cmd_fill(args))
        elif args.command == "offer-compare":
            cmd_offer_compare(args)
        elif args.command == "team-dashboard":
            cmd_team_dashboard(args)
        elif args.command == "api-server":
            cmd_api_server(args)
        elif args.command == "career":
            cmd_career(args)
        elif args.command == "apply":
            cmd_apply(args)
        else:
            parser.print_help()
    finally:
        loop.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())