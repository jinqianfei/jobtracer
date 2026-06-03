"""JSON → SQLite 迁移脚本
Phase 1: JSON 文件存储
Phase 2: SQLite 单机数据库（支持 10万+ 记录）
Phase 3: PostgreSQL 云端扩展
"""
import sqlite3
import json
import os
from pathlib import Path
from typing import Any, Dict, List

SCHEMA_SQL = """
-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT UNIQUE NOT NULL,
    name TEXT,
    contact_json TEXT,
    preferences_json TEXT,
    boss_cookie TEXT,
    feishu_token TEXT,
    github_token TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 职位表
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT UNIQUE NOT NULL,
    platform TEXT NOT NULL,
    company TEXT,
    position TEXT,
    salary_min INTEGER,
    salary_max INTEGER,
    city TEXT,
    jd_text TEXT,
    match_score REAL,
    status TEXT DEFAULT 'new',
    applied_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 简历表
CREATE TABLE IF NOT EXISTS resumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resume_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    resume_json TEXT,
    file_path TEXT,
    target_role TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 活动记录表
CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    activity_type TEXT NOT NULL,
    platform TEXT,
    target_id TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_jobs_platform ON jobs(platform);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_activities_user ON activities(user_id);
"""


class Migrator:
    """SQLite 迁移器"""

    def __init__(self, db_path: str = "~/.jobtracer/jobtracer.db"):
        self.db_path: Path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def init_db(self) -> None:
        """初始化数据库和表结构"""
        conn = sqlite3.connect(self.db_path)
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        conn.close()

    def migrate_json_to_sqlite(self, json_dir: str = "~/.jobtracer") -> Dict[str, Any]:
        """将现有 JSON 文件迁移到 SQLite"""
        json_dir = Path(json_dir).expanduser()
        stats: Dict[str, Any] = {
            "jobs": 0,
            "resumes": 0,
            "activities": 0,
            "errors": []
        }

        conn = sqlite3.connect(self.db_path)

        # 迁移 job-tracker.json
        job_file = json_dir / "job-tracker.json"
        if job_file.exists():
            try:
                with open(job_file) as f:
                    data = json.load(f)
                    jobs = data if isinstance(data, list) else data.get("jobs", [])
                    for job in jobs:
                        conn.execute("""
                            INSERT OR REPLACE INTO jobs
                            (job_id, platform, company, position, salary_min, salary_max, city, match_score, status)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            job.get("id"),
                            job.get("platform"),
                            job.get("company"),
                            job.get("position"),
                            job.get("salary_min"),
                            job.get("salary_max"),
                            job.get("city"),
                            job.get("match_score"),
                            job.get("status", "new")
                        ))
                    stats["jobs"] = len(jobs)
            except Exception as e:
                stats["errors"].append(f"job-tracker.json: {str(e)}")

        conn.commit()
        conn.close()
        return stats

    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)


def main() -> None:
    """命令行入口"""
    import argparse
    parser = argparse.ArgumentParser(description="JobTracer JSON → SQLite 迁移")
    parser.add_argument("--db", default="~/.jobtracer/jobtracer.db", help="数据库路径")
    parser.add_argument("--json-dir", default="~/.jobtracer", help="JSON 文件目录")
    args = parser.parse_args()

    migrator = Migrator(args.db)
    migrator.init_db()
    print("数据库初始化完成")

    stats = migrator.migrate_json_to_sqlite(args.json_dir)
    print(f"迁移完成: {stats}")


if __name__ == "__main__":
    main()
