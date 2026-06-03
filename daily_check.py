#!/usr/bin/env python3
"""
JobTracer 每日巡检脚本
- 扫描数字足迹
- 生成简历
- 搜索新职位
- 发送飞书日报
"""

import os
import sys
import json
import asyncio
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置工作目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

async def daily_check():
    print(f"=== JobTracer 每日巡检 {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
    
    # 1. 加载配置
    webhook_config_path = os.path.expanduser("~/.jobtracer/feishu_webhook.json")
    if os.path.exists(webhook_config_path):
        with open(webhook_config_path) as f:
            webhook_config = json.load(f)
        os.environ["FEISHU_WEBHOOK"] = webhook_config.get("webhook_url", "")
    
    # 2. 扫描数字足迹
    print("\n📂 扫描数字足迹...")
    from scanner.footprint_scanner import scan_all
    scan = await scan_all()
    print(f"   扫描到 {scan['total_files']} 文件")
    
    # 3. 聚类项目
    print("\n🔬 聚类项目...")
    from clustering.engine import ProjectClusteringEngine
    engine = ProjectClusteringEngine()
    projects = await engine.cluster(scan)
    print(f"   聚类出 {len(projects)} 个项目")
    
    # 4. 生成/更新简历
    print("\n📄 更新简历...")
    from resume.generator import ResumeGenerator
    gen = ResumeGenerator()
    resume = await gen.generate_from_projects([p['project_name'] for p in projects])
    gen.save_resume(resume)
    print(f"   简历已更新: {resume.get('name', 'unknown')}")
    
    # 5. 搜索新职位
    print("\n🎯 搜索职位...")
    from boss.search import BOSSSearcher
    from matching.scorer import JDMatcher
    
    searcher = BOSSSearcher()
    jobs_result = await searcher.search_jobs(keywords=["Python", "后端"], city="上海", page=1, page_size=5)
    
    new_jobs = jobs_result.get("jobs", []) if isinstance(jobs_result, dict) else []
    print(f"   发现 {len(new_jobs)} 个新职位")
    
    # 6. 发送飞书日报
    print("\n📱 发送飞书日报...")
    from utils.feishu_bot import FeishuBot
    
    bot = FeishuBot(verify_ssl=False)
    
    # 准备新职位列表
    new_job_list = []
    for job in new_jobs[:3]:
        new_job_list.append({
            "title": job.get("title", "未知职位"),
            "company": job.get("company", "未知公司")
        })
    
    card_result = await bot.send_daily_report(
        date=datetime.now().strftime("%Y-%m-%d"),
        new_jobs=len(new_jobs),
        status_changes=0,
        pending=len(projects),
        new_job_list=new_job_list
    )
    
    if card_result.get("success"):
        print("   ✅ 日报发送成功")
    else:
        print(f"   ❌ 日报发送失败: {card_result.get('error')}")
    
    print("\n=== 巡检完成 ===")
    return {
        "scan_files": scan['total_files'],
        "projects": len(projects),
        "new_jobs": len(new_jobs),
        "feishu_sent": card_result.get("success", False)
    }

if __name__ == "__main__":
    result = asyncio.run(daily_check())
    sys.exit(0 if result.get("feishu_sent") else 1)