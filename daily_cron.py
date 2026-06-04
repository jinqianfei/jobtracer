#!/usr/bin/env python3
"""
daily_cron.py
每日定时任务 - 每天 09:00 自动执行
自动搜索新职位 + 发飞书通知
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# 路径设置（支持直接运行和包内导入）
# ---------------------------------------------------------------------------
FILE_PATH = Path(__file__).resolve()
PROJECT_ROOT = FILE_PATH.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(PROJECT_ROOT / "logs" / "daily_cron.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("jobtracer.daily_cron")


# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

TRACKER_FILE = Path("~/.jobtracer/job-tracker.json").expanduser()
PREFERENCES_FILE = Path("~/.jobtracer/preferences.json").expanduser()
CRON_MARKER = "# JobTracer daily_cron.py"
LOG_FILE = PROJECT_ROOT / "logs" / "daily_cron.log"


# ---------------------------------------------------------------------------
# 核心逻辑
# ---------------------------------------------------------------------------

def load_preferences() -> dict:
    """加载用户偏好配置，自动从简历和项目中提取关键词"""
    if not PREFERENCES_FILE.exists():
        logger.warning(f"偏好配置文件不存在，使用默认值: {PREFERENCES_FILE}")
        return _build_default_preferences()
    try:
        with open(PREFERENCES_FILE, encoding="utf-8") as f:
            data = json.load(f)
        keywords = data.get("keywords")
        if not keywords:
            # 无关键词，从简历和项目自动提取
            logger.info("未配置搜索关键词，从简历和项目中自动提取")
            extracted = _extract_keywords_from_profile()
            if extracted:
                keywords = extracted
            else:
                keywords = ["Python", "后端"]
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(",")]
        return {
            "keywords": keywords,
            "city": data.get("city", "上海"),
            "platforms": data.get("platforms", ["boss", "51job"]),
        }
    except Exception as e:
        logger.error(f"加载偏好配置失败: {e}，使用默认值")
        return _build_default_preferences()


def _build_default_preferences() -> dict:
    """构建默认偏好配置，尝试从简历和项目提取"""
    extracted = _extract_keywords_from_profile()
    return {
        "keywords": extracted if extracted else ["Python", "后端"],
        "city": "上海",
        "platforms": ["boss", "51job"],
    }


def _extract_keywords_from_profile() -> list:
    """从简历和数字足迹项目中提取搜索关键词"""
    import re
    from collections import Counter
    
    keywords = set()
    
    # 1. 从简历提取技能
    try:
        resume_path = Path.home() / ".jobtracer" / "resume.json"
        if resume_path.exists():
            with open(resume_path, encoding="utf-8") as f:
                resume = json.load(f)
            # 技能
            for skill in resume.get("skills", []):
                if skill and len(skill) > 1:
                    keywords.add(skill.strip())
            # 项目名
            for proj in resume.get("projects", []):
                name = proj.get("name", "")
                if name:
                    # 提取有意义的词
                    words = re.findall(r'[A-Za-z]{2,}[+#]*|[\u4e00-\9fff]{2,}', name)
                    for w in words:
                        if len(w) > 1:
                            keywords.add(w.strip())
    except Exception as e:
        logger.debug(f"简历读取失败: {e}")
    
    # 2. 从 projects_index 提取技术栈和项目标签
    try:
        projects_path = Path.home() / ".jobtracer" / "projects_index.json"
        if projects_path.exists():
            with open(projects_path, encoding="utf-8") as f:
                data = json.load(f)
            projects = data.get("projects", data.get("data", []))
            
            # 从 tags 提取
            all_tags = []
            for p in projects:
                all_tags.extend(p.get("tags", []))
            tag_counter = Counter(all_tags)
            
            # 过滤掉通用标签，保留技术栈
            stop_tags = {"local", "documentation", "source", "files", "config", 
                        "test", "api", "src", "tool", "doc", "资料", "文档", "笔记",
                        "workspace", "openclaw", "agent", "skill"}
            
            for tag, count in tag_counter.most_common(100):
                if count >= 3 and tag.lower() not in stop_tags and len(tag) > 1:
                    keywords.add(tag.strip())
            
            # 从 solutions/background 提取技术栈
            tech_pattern = re.compile(r'[A-Za-z][a-z]+(?:[A-Z][a-z]+)*(?:\+[a-z]+)?')
            for p in projects:
                for field in ["solutions", "background", "description"]:
                    text = p.get(field, "")
                    matches = tech_pattern.findall(text)
                    for m in matches:
                        if len(m) > 2 and m.lower() not in stop_tags:
                            keywords.add(m.strip())
    except Exception as e:
        logger.debug(f"项目索引读取失败: {e}")
    
    # 3. 过滤和精简
    final_keywords = []
    for kw in keywords:
        kw = kw.strip()
        if len(kw) >= 2 and len(kw) <= 20 and not kw.startswith("~"):
            final_keywords.append(kw)
    
    # 取前10个最有价值的
    priority_map = {
        "Python": 10, "Java": 9, "Go": 9, "Rust": 8, "TypeScript": 8,
        "产品经理": 10, "后端": 7, "前端": 6, "全栈": 7,
        "算法": 7, "机器学习": 8, "深度学习": 8, "NLP": 8,
        "供应链": 10, "物流": 7, "仓储": 6, "电商": 7,
        "Django": 8, "FastAPI": 8, "Flask": 7, "React": 7,
        "MySQL": 8, "PostgreSQL": 8, "MongoDB": 7, "Redis": 7,
        "Docker": 7, "Kubernetes": 8, "云": 5,
    }
    final_keywords.sort(key=lambda x: priority_map.get(x, 5), reverse=True)
    
    result = final_keywords[:10]
    if result:
        logger.info(f"自动提取搜索关键词: {result}")
    return result


def get_saved_job_keys() -> set:
    """
    读取 job-tracker.json，返回所有已保存职位的去重 key 集合
    key = company + "|" + title
    """
    keys = set()
    if not TRACKER_FILE.exists():
        return keys
    try:
        with open(TRACKER_FILE, encoding="utf-8") as f:
            data = json.load(f)
        for job in data.get("jobs", []):
            company = job.get("company", "").strip()
            title = job.get("title", "").strip()
            if company and title:
                keys.add(f"{company}|{title}")
        logger.info(f"已保存 {len(keys)} 个唯一职位")
    except Exception as e:
        logger.error(f"读取 job-tracker.json 失败: {e}")
    return keys


def save_new_jobs(new_jobs: list) -> int:
    """保存新职位到 job-tracker.json，返回实际新增数量"""
    if not new_jobs:
        return 0
    data = {"jobs": [], "last_updated": datetime.now().isoformat()}
    if TRACKER_FILE.exists():
        try:
            with open(TRACKER_FILE, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass

    existing_keys = set()
    for job in data.get("jobs", []):
        c = job.get("company", "").strip()
        t = job.get("title", "").strip()
        if c and t:
            existing_keys.add(f"{c}|{t}")

    added = 0
    for job in new_jobs:
        company = job.get("company", "").strip()
        title = job.get("title", "").strip()
        key = f"{company}|{title}"
        if key not in existing_keys:
            data["jobs"].append(job)
            existing_keys.add(key)
            added += 1

    if added > 0:
        data["last_updated"] = datetime.now().isoformat()
        TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TRACKER_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"新增 {added} 个职位，已保存到 {TRACKER_FILE}")
    return added


async def daily_auto_search() -> list:
    """
    每日自动搜索新职位
    - 加载关键词和城市配置
    - 搜索职位并与已保存职位去重
    - 保存新职位
    - 发飞书通知
    返回新职位列表
    """
    prefs = load_preferences()
    keywords = prefs["keywords"]
    city = prefs["city"]
    platforms = prefs.get("platforms", ["boss", "51job"])

    logger.info(f"开始每日自动搜索 | 关键词: {keywords} | 城市: {city} | 平台: {platforms}")

    # 1. 多平台搜索
    try:
        from jobs.multi_platform_search import MultiPlatformSearcher
        searcher = MultiPlatformSearcher()
        result = await searcher.search_all(keywords=keywords, city=city, platforms=platforms)
        new_jobs = result.get("new_jobs", [])
        logger.info(f"共搜索到 {result['total']} 个职位，新增 {len(new_jobs)} 个")
    except Exception as e:
        logger.error(f"多平台搜索失败: {e}")
        new_jobs = []

    # 2. 保存新职位
    if new_jobs:
        from storage.manager import StorageManager
        sm = StorageManager()
        for job in new_jobs:
            sm.add_job(job)
        logger.info(f"已保存 {len(new_jobs)} 个新职位")

    # 3. 发飞书通知
    if new_jobs:
        await send_feishu_notification(new_jobs)

    return new_jobs


async def send_feishu_notification(jobs: list) -> bool:
    """发送飞书通知卡片"""
    try:
        from utils.feishu_bot import FeishuBot

        bot = FeishuBot()
        today = datetime.now().strftime("%Y-%m-%d")

        # 构造发送给卡片的 jobs 数据（加 match_score）
        enriched = []
        for j in jobs:
            enriched.append({
                "title": j.get("title", ""),
                "company": j.get("company", ""),
                "city": j.get("city", ""),
                "salary": j.get("salary", ""),
                "match_score": j.get("match_score", 0),
                "url": j.get("url", j.get("job_url", "")),
            })

        result = await bot.send_new_jobs_card(jobs=enriched, date=today)
        if result.get("success"):
            logger.info("飞书通知发送成功")
            return True
        else:
            logger.warning(f"飞书通知发送失败: {result.get('error')}")
            return False
    except Exception as e:
        logger.error(f"发送飞书通知异常: {e}")
        return False


# ---------------------------------------------------------------------------
# Cron 管理
# ---------------------------------------------------------------------------

def get_cron_lines() -> list:
    """获取当前 crontab 中与 JobTracer 相关的行"""
    try:
        result = subprocess.run(
            ["crontab", "-l"], capture_output=True, text=True
        )
        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
        return [l for l in lines if CRON_MARKER not in l]
    except Exception as e:
        logger.error(f"读取 crontab 失败: {e}")
        return []


def setup_cron():
    """设置每日 cron 任务（每天 09:00）"""
    # 确保 logs 目录存在
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    cron_cmd = (
        f"0 9 * * * "
        f"cd {PROJECT_ROOT} && "
        f"{sys.executable} daily_cron.py >> {LOG_FILE} 2>&1 "
        f"{CRON_MARKER}"
    )

    existing_lines = get_cron_lines()
    existing_lines.append(cron_cmd)

    new_crontab = "\n".join(existing_lines) + "\n"

    try:
        proc = subprocess.Popen(
            ["crontab", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = proc.communicate(input=new_crontab.encode("utf-8"))
        if proc.returncode == 0:
            logger.info("Cron 任务设置成功")
            print("✅ Cron 任务已设置：每天 09:00 自动搜索新职位")
            print(f"   日志文件：{LOG_FILE}")
        else:
            err = stderr.decode("utf-8") if stderr else ""
            logger.error(f"Cron 设置失败: {err}")
            print(f"❌ Cron 设置失败: {err}")
    except Exception as e:
        logger.error(f"Cron 设置异常: {e}")
        print(f"❌ Cron 设置异常: {e}")


def remove_cron():
    """移除 JobTracer cron 任务"""
    existing_lines = get_cron_lines()
    new_crontab = "\n".join(existing_lines) + "\n" if existing_lines else "\n"

    try:
        proc = subprocess.Popen(
            ["crontab", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = proc.communicate(input=new_crontab.encode("utf-8"))
        if proc.returncode == 0:
            logger.info("Cron 任务已移除")
            print("✅ Cron 任务已移除")
        else:
            err = stderr.decode("utf-8") if stderr else ""
            logger.error(f"Cron 移除失败: {err}")
            print(f"❌ Cron 移除失败: {err}")
    except Exception as e:
        logger.error(f"Cron 移除异常: {e}")
        print(f"❌ Cron 移除异常: {e}")


def show_cron():
    """显示当前 JobTracer cron 配置"""
    try:
        result = subprocess.run(
            ["crontab", "-l"], capture_output=True, text=True
        )
        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
        jt_lines = [l for l in lines if CRON_MARKER in l]
        if jt_lines:
            print("📋 当前 JobTracer Cron 任务：")
            for line in jt_lines:
                print(f"   {line}")
            print(f"\n📄 日志文件：{LOG_FILE}")
        else:
            print("❌ 未找到 JobTracer Cron 任务（未设置）")
            print("   运行 `python3 daily_cron.py --setup-cron` 可设置")
    except Exception as e:
        logger.error(f"读取 crontab 失败: {e}")
        print(f"❌ 读取 crontab 失败: {e}")


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="JobTracer 每日定时任务")
    parser.add_argument(
        "--setup-cron", action="store_true",
        help="设置每天 09:00 的 cron 任务"
    )
    parser.add_argument(
        "--show-cron", action="store_true",
        help="显示当前 cron 配置"
    )
    parser.add_argument(
        "--remove-cron", action="store_true",
        help="移除 cron 任务"
    )
    args = parser.parse_args()

    if args.setup_cron:
        setup_cron()
    elif args.show_cron:
        show_cron()
    elif args.remove_cron:
        remove_cron()
    else:
        # 执行每日自动搜索
        print("=" * 60)
        print(f"JobTracer 每日自动搜索 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("=" * 60)

        new_jobs = asyncio.run(daily_auto_search())

        print()
        if new_jobs:
            print(f"✅ 发现 {len(new_jobs)} 个新职位，已保存并发送通知")
        else:
            print("📭 今日暂无新增职位")
        print(f"下次运行：明天 09:00")
