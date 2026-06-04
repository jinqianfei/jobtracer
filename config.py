# config.py
# JobTracer 全局配置

import os
from pathlib import Path

# ============================================================
# 基础路径
# ============================================================

BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = Path("~/.jobtracer").expanduser()

# 数据子目录
MEMORY_DIR = DATA_DIR / "memory"
FOOTPRINT_DIR = DATA_DIR / "footprint"
JOBS_DIR = DATA_DIR / "jobs"
COOKIES_DIR = DATA_DIR / "cookies"
RESUME_DIR = DATA_DIR / "customized_resumes"
INTERVIEW_DIR = DATA_DIR / "interview_prep"
REPORTS_DIR = DATA_DIR / "reports"
LOGS_DIR = DATA_DIR / "logs"

# 确保目录存在
for _dir in [DATA_DIR, MEMORY_DIR, FOOTPRINT_DIR, JOBS_DIR, COOKIES_DIR,
             RESUME_DIR, INTERVIEW_DIR, REPORTS_DIR, LOGS_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)

# 项目目录（聚类结果）
PROJECTS_DIR = FOOTPRINT_DIR / "projects"
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

# JD缓存
JD_CACHE_DIR = JOBS_DIR / "jd_cache"
JD_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# 存储文件
# ============================================================

STATE_FILE = DATA_DIR / "state.json"
PREFERENCES_FILE = DATA_DIR / "preferences.json"
RESUME_FILE = MEMORY_DIR / "resume.json"
JOB_TRACKER_FILE = DATA_DIR / "job-tracker.json"
FEEDBACK_FILE = DATA_DIR / "feedback.json"
FOOTPRINT_SUMMARY_FILE = DATA_DIR / "digital_footprint_summary.json"
PROJECTS_INDEX_FILE = DATA_DIR / "projects_index.json"

# 飞书 Webhook 配置
FEISHU_WEBHOOK_FILE = DATA_DIR / "feishu_webhook.json"

# Cookie 文件
BOSS_COOKIE_FILE = COOKIES_DIR / "boss_cookies.json"

# ============================================================
# 扫描配置
# ============================================================

SCANNER_GLOBAL_TIMEOUT = 300  # 全局超时（秒）
SCANNER_CONFIGS = {
    "openclaw": {"timeout": 60.0},
    "github": {"timeout": 90.0},
    "local": {"timeout": 120.0},
    "agent": {"timeout": 60.0},
    "openclaw_sessions": {"timeout": 30.0},
}
MAX_CONCURRENT_SCANS = 4

# GitHub Token
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# ============================================================
# BOSS 搜索配置
# ============================================================

BOSS_SEARCH_DEFAULTS = {
    "keywords": ["Python", "后端"],
    "city": "上海",
    "experience": "不限",
    "degree": "不限",
    "salary": "不限",
    "page": 1,
    "page_size": 20,
}
BOSS_SEARCH_TIMEOUT = 60  # 秒
BOSS_MAX_RETRIES = 1

# ============================================================
# 简历配置
# ============================================================

RESUME_OUTPUT_PATH = MEMORY_DIR / "resume.json"
RESUME_MD_PATH = MEMORY_DIR / "resume.md"
RESUME_HTML_PATH = MEMORY_DIR / "resume_preview.html"

# ============================================================
# 飞书通知配置
# ============================================================

def load_feishu_webhook() -> str:
    """加载飞书 Webhook URL"""
    path = FEISHU_WEBHOOK_FILE
    if path.exists():
        try:
            import json
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f).get("webhook_url", "")
        except Exception:
            pass
    return os.environ.get("FEISHU_WEBHOOK", "")

FEISHU_WEBHOOK = load_feishu_webhook()

# ============================================================
# 匹配评分权重
# ============================================================

MATCH_WEIGHTS = {
    "skill": 0.4,
    "project": 0.2,
    "experience": 0.2,
    "salary": 0.2,
}

# ============================================================
# 日志配置
# ============================================================

import logging

LOG_LEVEL = os.environ.get("JOBTRACER_LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

def setup_logging():
    logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO), format=LOG_FORMAT)

setup_logging()

# ============================================================
# 便捷访问函数
# ============================================================

def get_storage_path(name: str) -> Path:
    """获取存储文件路径"""
    mapping = {
        "state": STATE_FILE,
        "preferences": PREFERENCES_FILE,
        "resume": RESUME_FILE,
        "job_tracker": JOB_TRACKER_FILE,
        "feedback": FEEDBACK_FILE,
        "footprint_summary": FOOTPRINT_SUMMARY_FILE,
        "projects_index": PROJECTS_INDEX_FILE,
        "feishu_webhook": FEISHU_WEBHOOK_FILE,
    }
    return mapping.get(name, DATA_DIR / name)