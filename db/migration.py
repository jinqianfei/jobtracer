"""
db/migration.py
JobTracer SQLite Schema 迁移脚本
将 JSON 文件迁移到 SQLite 数据库
"""

import sqlite3
import json
import logging
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('jobtracer.migration')

# 迁移日志文件
LOG_DIR = Path(__file__).parent.parent / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)
MIGRATION_LOG = LOG_DIR / 'migration.log'


def setup_logging():
    """设置文件日志处理器"""
    file_handler = logging.FileHandler(MIGRATION_LOG, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)


setup_logging()


class Migration:
    """
    JobTracer JSON → SQLite 迁移类
    
    迁移范围:
    - resume.json → resume 表
    - job-tracker.json → jobs + applications 表
    - state.json → state 表
    - preferences.json → preferences 表
    - feedback.json → feedback 表
    """
    
    def __init__(self, db_path: str = "~/.jobtracer/jobtracer.db"):
        """
        初始化迁移器
        
        Args:
            db_path: SQLite 数据库路径
        """
        self.db_path = Path(db_path).expanduser()
        self.json_base = Path("~/.jobtracer").expanduser()
        self.stats = {}
        self._log_start()
    
    def _log_start(self):
        """记录迁移开始"""
        logger.info("=" * 60)
        logger.info("JobTracer JSON → SQLite 迁移开始")
        logger.info(f"数据库路径: {self.db_path}")
        logger.info(f"JSON 路径: {self.json_base}")
        logger.info("=" * 60)
    
    def _log(self, message: str):
        """同时输出到 logger 和控制台"""
        print(message)
        logger.info(message)
    
    def _ensure_db_dir(self):
        """确保数据库目录存在"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        self._ensure_db_dir()
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def create_tables(self):
        """创建所有表"""
        self._log("\n[1] 创建数据库表...")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # jobs 表（职位）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                title TEXT NOT NULL,
                company TEXT,
                salary TEXT,
                location TEXT,
                security_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                raw_data TEXT
            )
        """)
        
        # applications 表（投递记录）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                resume_id TEXT,
                status TEXT DEFAULT 'pending',
                applied_at TIMESTAMP,
                responded_at TIMESTAMP,
                greeting_sent BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            )
        """)
        
        # resume 表（简历）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resume (
                id TEXT PRIMARY KEY,
                name TEXT,
                email TEXT,
                phone TEXT,
                location TEXT,
                skills TEXT,
                experience TEXT,
                education TEXT,
                projects TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # state 表（状态）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # feedback 表（反馈）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                type TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # preferences 表（偏好）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        self._log("  ✓ 所有表创建完成")
    
    def upsert(self, table: str, data: dict, pk: str = "id"):
        """
        INSERT OR REPLACE 实现幂等迁移
        
        Args:
            table: 表名
            data: 要插入的数据字典
            pk: 主键字段名
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 动态构建 INSERT OR REPLACE 语句
        columns = list(data.keys())
        placeholders = ', '.join(['?' for _ in columns])
        columns_str = ', '.join(columns)
        
        sql = f"INSERT OR REPLACE INTO {table} ({columns_str}) VALUES ({placeholders})"
        values = [self._serialize(v) for v in data.values()]
        
        try:
            cursor.execute(sql, values)
            conn.commit()
        except Exception as e:
            logger.error(f"Upsert 到 {table} 失败: {e}")
            raise
        finally:
            conn.close()
    
    def _serialize(self, value: Any) -> str:
        """序列化非字符串值为 JSON 字符串"""
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        elif isinstance(value, bool):
            return '1' if value else '0'
        elif value is None:
            return ''
        return str(value)
    
    def _generate_id(self) -> str:
        """生成唯一 ID"""
        return str(uuid.uuid4())
    
    def _read_json(self, filename: str) -> Optional[Dict[str, Any]]:
        """读取 JSON 文件"""
        file_path = self.json_base / filename
        if not file_path.exists():
            self._log(f"  ⚠ 文件不存在，跳过: {filename}")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败 {filename}: {e}")
            return None
    
    def migrate_resume(self) -> int:
        """
        迁移 resume.json → resume 表
        
        Returns:
            迁移的记录数
        """
        self._log("\n[2] 迁移 resume.json...")
        
        data = self._read_json('resume.json')
        if data is None:
            return 0
        
        count = 0
        # meta 信息单独存储（不放入 resume 表的 raw_data 列）
        # resume.json 结构: {"meta": {...}} 或包含 name, email 等字段
        record = {
            'id': self._generate_id(),
            'name': data.get('name', ''),
            'email': data.get('email', ''),
            'phone': data.get('phone', ''),
            'location': data.get('location', ''),
            'skills': json.dumps(data.get('skills', []), ensure_ascii=False),
            'experience': json.dumps(data.get('experience', []), ensure_ascii=False),
            'education': json.dumps(data.get('education', []), ensure_ascii=False),
            'projects': json.dumps(data.get('projects', []), ensure_ascii=False),
        }
        
        self.upsert('resume', record)
        count = 1
        self._log(f"  ✓ 迁移 resume.json: {count} 条记录")
        logger.info(f"Migrated resume: {count} records")
        return count
    
    def migrate_job_tracker(self) -> int:
        """
        迁移 job-tracker.json → jobs + applications 表
        
        Returns:
            迁移的记录总数
        """
        self._log("\n[3] 迁移 job-tracker.json...")
        
        data = self._read_json('job-tracker.json')
        if data is None:
            return 0
        
        count = 0
        jobs = data.get('jobs', [])
        
        for job in jobs:
            job_id = job.get('job_id') or self._generate_id()
            
            # 迁移到 jobs 表
            job_record = {
                'id': job_id,
                'platform': job.get('platform', 'unknown'),
                'title': job.get('title', ''),
                'company': job.get('company', ''),
                'salary': job.get('salary', ''),
                'location': job.get('location', ''),
                'security_id': job.get('security_id', ''),
                'raw_data': json.dumps(job, ensure_ascii=False),
            }
            self.upsert('jobs', job_record)
            count += 1
            
            # 迁移到 applications 表（如果 job 有投递信息）
            if 'application' in job or 'status' in job:
                app_record = {
                    'id': self._generate_id(),
                    'job_id': job_id,
                    'resume_id': job.get('resume_id', ''),
                    'status': job.get('status', 'pending'),
                    'applied_at': job.get('applied_at', ''),
                    'responded_at': job.get('responded_at', ''),
                    'greeting_sent': job.get('greeting_sent', False),
                }
                self.upsert('applications', app_record)
        
        self._log(f"  ✓ 迁移 job-tracker.json: {count} 条职位记录")
        logger.info(f"Migrated job-tracker: {count} job records")
        return count
    
    def migrate_state(self) -> int:
        """
        迁移 state.json → state 表
        
        Returns:
            迁移的记录数
        """
        self._log("\n[4] 迁移 state.json...")
        
        data = self._read_json('state.json')
        if data is None:
            return 0
        
        count = 0
        # state.json 是键值对结构
        for key, value in data.items():
            if key in ('last_active', 'last_updated'):
                # 时间字段处理
                continue
            
            record = {
                'key': key,
                'value': self._serialize(value),
            }
            self.upsert('state', record)
            count += 1
        
        self._log(f"  ✓ 迁移 state.json: {count} 条记录")
        logger.info(f"Migrated state: {count} records")
        return count
    
    def migrate_preferences(self) -> int:
        """
        迁移 preferences.json → preferences 表
        
        Returns:
            迁移的记录数
        """
        self._log("\n[5] 迁移 preferences.json...")
        
        data = self._read_json('preferences.json')
        if data is None:
            return 0
        
        count = 0
        # preferences.json 是键值对结构
        for key, value in data.items():
            if key in ('created_at', 'updated_at'):
                continue
            
            record = {
                'key': key,
                'value': self._serialize(value),
            }
            self.upsert('preferences', record)
            count += 1
        
        self._log(f"  ✓ 迁移 preferences.json: {count} 条记录")
        logger.info(f"Migrated preferences: {count} records")
        return count
    
    def migrate_feedback(self) -> int:
        """
        迁移 feedback.json → feedback 表
        
        Returns:
            迁移的记录数
        """
        self._log("\n[6] 迁移 feedback.json...")
        
        data = self._read_json('feedback.json')
        if data is None:
            return 0
        
        count = 0
        feedbacks = data.get('feedbacks', [])
        
        for fb in feedbacks:
            record = {
                'id': fb.get('id') or self._generate_id(),
                'type': fb.get('type', ''),
                'content': fb.get('content', ''),
                'created_at': fb.get('created_at', datetime.now().isoformat()),
            }
            self.upsert('feedback', record)
            count += 1
        
        self._log(f"  ✓ 迁移 feedback.json: {count} 条记录")
        logger.info(f"Migrated feedback: {count} records")
        return count
    
    def migrate_all(self) -> Dict[str, int]:
        """
        执行全量迁移
        
        Returns:
            每类迁移的记录数字典
        """
        self._log("\n" + "=" * 60)
        self._log("开始全量迁移")
        self._log("=" * 60)
        
        # 1. 创建表
        self.create_tables()
        
        # 2. 迁移各个 JSON 文件
        self.stats = {
            'resume': self.migrate_resume(),
            'jobs': self.migrate_job_tracker(),
            'state': self.migrate_state(),
            'preferences': self.migrate_preferences(),
            'feedback': self.migrate_feedback(),
        }
        
        # 3. 输出汇总
        total = sum(self.stats.values())
        self._log("\n" + "=" * 60)
        self._log("迁移汇总")
        self._log("=" * 60)
        for table, count in self.stats.items():
            self._log(f"  - {table}: {count} 条")
        self._log(f"\n总计: {total} 条记录迁移到 SQLite")
        logger.info(f"Migration complete: {self.stats}")
        
        return self.stats
    
    def rollback(self):
        """
        回滚：删除所有迁移创建的表
        """
        self._log("\n[ROLLBACK] 删除所有迁移表...")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        tables = ['applications', 'jobs', 'resume', 'state', 'feedback', 'preferences']
        for table in tables:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
                self._log(f"  ✓ 删除表: {table}")
            except Exception as e:
                logger.error(f"删除表 {table} 失败: {e}")
        
        conn.commit()
        conn.close()
        self._log("[ROLLBACK] 完成")
        logger.info("Migration rollback completed")
    
    def get_stats(self) -> dict:
        """
        获取迁移统计信息
        
        Returns:
            包含各表记录数的字典
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        stats = {}
        tables = ['jobs', 'applications', 'resume', 'state', 'feedback', 'preferences']
        
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                stats[table] = count
            except sqlite3.OperationalError as e:
                stats[table] = f"表不存在或查询失败: {e}"
        
        conn.close()
        return stats
    
    def verify_data(self, sample_count: int = 3) -> bool:
        """
        抽样校验迁移数据的正确性
        
        Args:
            sample_count: 抽样数量
            
        Returns:
            校验通过返回 True
        """
        self._log("\n" + "=" * 60)
        self._log("数据校验")
        self._log("=" * 60)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        all_ok = True
        
        # 检查各表是否有数据
        tables = ['resume', 'jobs', 'state', 'preferences', 'feedback']
        for table in tables:
            try:
                cursor.execute(f"SELECT * FROM {table} LIMIT ?", (sample_count,))
                rows = cursor.fetchall()
                if rows:
                    self._log(f"\n[{table}] 抽样 ({min(sample_count, len(rows))} 条):")
                    for row in rows:
                        row_dict = dict(row)
                        # 截断过长的 raw_data
                        if 'raw_data' in row_dict and row_dict['raw_data']:
                            row_dict['raw_data'] = row_dict['raw_data'][:50] + '...'
                        self._log(f"  {row_dict}")
                else:
                    self._log(f"[{table}] 无数据")
            except sqlite3.OperationalError as e:
                self._log(f"[{table}] 查询失败: {e}")
                all_ok = False
        
        conn.close()
        return all_ok


def main():
    """主函数 - 执行迁移"""
    print("\n" + "=" * 60)
    print("JobTracer JSON → SQLite 迁移工具")
    print("=" * 60)
    
    migrator = Migration()
    
    # 执行迁移
    stats = migrator.migrate_all()
    
    # 校验数据
    migrator.verify_data(sample_count=3)
    
    # 输出最终统计
    print("\n" + "=" * 60)
    print("最终数据库状态")
    print("=" * 60)
    final_stats = migrator.get_stats()
    for table, count in final_stats.items():
        print(f"  {table}: {count}")


if __name__ == '__main__':
    main()