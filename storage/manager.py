"""
storage/manager.py
JobTracer 数据存储管理器
统一管理 ~/.jobtracer/ 下所有 JSON 文件的读写
"""

import json
import shutil
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('jobtracer.storage')


class StorageManager:
    """
    统一管理 ~/.jobtracer/ 下所有 JSON 文件的读写
    提供类型安全的读取和写入接口
    """
    
    # 管理的文件列表
    MANAGED_FILES = [
        'state.json',
        'preferences.json',
        'resume.json',
        'job-tracker.json',
        'feedback.json',
        'digital_footprint_summary.json',
        'projects_index.json',
    ]
    
    # 目录结构
    SUBDIRS = [
        'memory',
        'footprint/projects',
        'jobs/jd_cache',
        'customized_resumes',
        'interview_prep',
        'cookies',
        'logs',
        'reports',
    ]
    
    def __init__(self, base_path: str = "~/.jobtracer"):
        """
        初始化存储管理器
        
        Args:
            base_path: 存储根目录路径，默认为 ~/.jobtracer
        """
        self.base_path = Path(base_path).expanduser()
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # 首次加载时初始化目录结构
        self._init_directories()
        
        logger.info(f"StorageManager initialized at {self.base_path}")
        logger.info(f"Subdirectories: {list(self.base_path.iterdir())}")
    
    def _init_directories(self) -> None:
        """初始化所有必要的目录结构"""
        for subdir in self.SUBDIRS:
            dir_path = self.base_path / subdir
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化空 JSON 文件（如果不存在）
        for filename in self.MANAGED_FILES:
            file_path = self.base_path / filename
            if not file_path.exists():
                # 根据文件类型初始化空数据结构
                if filename == 'job-tracker.json':
                    file_path.write_text(json.dumps({"jobs": [], "last_updated": datetime.now().isoformat()}, ensure_ascii=False, indent=2))
                elif filename == 'feedback.json':
                    file_path.write_text(json.dumps({"feedbacks": [], "last_updated": datetime.now().isoformat()}, ensure_ascii=False, indent=2))
                elif filename == 'projects_index.json':
                    file_path.write_text(json.dumps({"projects": [], "last_updated": datetime.now().isoformat()}, ensure_ascii=False, indent=2))
                elif filename == 'digital_footprint_summary.json':
                    file_path.write_text(json.dumps({"summary": "", "skills_vector": [], "last_updated": datetime.now().isoformat()}, ensure_ascii=False, indent=2))
                elif filename == 'state.json':
                    file_path.write_text(json.dumps({"current_step": 0, "user_id": None, "last_active": datetime.now().isoformat()}, ensure_ascii=False, indent=2))
                elif filename == 'preferences.json':
                    file_path.write_text(json.dumps({"user_id": None, "notification_time": "09:00", "language": "zh-CN", "timezone": "Asia/Shanghai"}, ensure_ascii=False, indent=2))
                elif filename == 'resume.json':
                    file_path.write_text(json.dumps({"meta": {"generated_from": "", "user_confirmed": False, "generated_at": datetime.now().isoformat()}}, ensure_ascii=False, indent=2))
                else:
                    file_path.write_text(json.dumps({}, ensure_ascii=False, indent=2))
                logger.info(f"Initialized empty file: {filename}")
    
    def read(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        读取 JSON 文件
        
        Args:
            filename: 文件名（如 'state.json'）
            
        Returns:
            文件内容（字典），不存在返回 None
        """
        file_path = self.base_path / filename
        
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.debug(f"Read {filename}: {len(str(data))} chars")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from {filename}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to read {filename}: {e}")
            return None
    
    def write(self, filename: str, data: Dict[str, Any]) -> bool:
        """
        写入 JSON 文件
        
        Args:
            filename: 文件名（如 'state.json'）
            data: 要写入的数据
            
        Returns:
            写入成功返回 True，失败返回 False
        """
        file_path = self.base_path / filename
        
        try:
            # 确保父目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入前先备份
            self.backup(filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Written {filename}: {len(str(data))} chars")
            return True
        except Exception as e:
            logger.error(f"Failed to write {filename}: {e}")
            return False
    
    def update(self, filename: str, updates: Dict[str, Any]) -> bool:
        """
        部分更新 JSON 文件（merge）
        
        Args:
            filename: 文件名
            updates: 要更新的字段（字典）
            
        Returns:
            更新成功返回 True，失败返回 False
        """
        current = self.read(filename)
        
        if current is None:
            current = {}
        
        # 深合并
        self._deep_merge(current, updates)
        
        return self.write(filename, current)
    
    def _deep_merge(self, base: Dict[str, Any], updates: Dict[str, Any]) -> None:
        """深合并两个字典"""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def backup(self, filename: str) -> bool:
        """
        备份文件为 filename.bak
        
        Args:
            filename: 要备份的文件名
            
        Returns:
            备份成功返回 True，失败返回 False
        """
        file_path = self.base_path / filename
        backup_path = file_path.with_suffix(file_path.suffix + '.bak')
        
        if not file_path.exists():
            logger.debug(f"No file to backup: {filename}")
            return False
        
        try:
            shutil.copy2(file_path, backup_path)
            logger.debug(f"Backed up {filename} -> {backup_path.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to backup {filename}: {e}")
            return False
    
    def restore(self, filename: str) -> bool:
        """
        从备份恢复文件
        
        Args:
            filename: 要恢复的文件名
            
        Returns:
            恢复成功返回 True，失败返回 False
        """
        file_path = self.base_path / filename
        backup_path = file_path.with_suffix(file_path.suffix + '.bak')
        
        if not backup_path.exists():
            logger.warning(f"No backup file found for {filename}")
            return False
        
        try:
            shutil.copy2(backup_path, file_path)
            logger.info(f"Restored {filename} from backup")
            return True
        except Exception as e:
            logger.error(f"Failed to restore {filename}: {e}")
            return False
    
    def exists(self, filename: str) -> bool:
        """检查文件是否存在"""
        return (self.base_path / filename).exists()
    
    def delete(self, filename: str) -> bool:
        """删除文件"""
        file_path = self.base_path / filename
        if not file_path.exists():
            return True
        
        try:
            file_path.unlink()
            logger.info(f"Deleted {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {filename}: {e}")
            return False
    
    def list_files(self, pattern: str = "*.json") -> List[Path]:
        """列出所有 JSON 文件"""
        return list(self.base_path.glob(pattern))
    
    def get_file_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """获取文件信息"""
        file_path = self.base_path / filename
        
        if not file_path.exists():
            return None
        
        stat = file_path.stat()
        return {
            'name': filename,
            'path': str(file_path),
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'has_backup': file_path.with_suffix(file_path.suffix + '.bak').exists()
        }
    
    def ensure_subdir(self, subdir: str) -> Path:
        """确保子目录存在"""
        dir_path = self.base_path / subdir
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
    
    # ========== 便捷方法 ==========
    
    def get_state(self) -> Optional[Dict[str, Any]]:
        """获取求职状态"""
        return self.read('state.json')
    
    def set_state(self, state: Dict[str, Any]) -> bool:
        """设置求职状态"""
        return self.write('state.json', state)
    
    def get_preferences(self) -> Optional[Dict[str, Any]]:
        """获取用户偏好"""
        return self.read('preferences.json')
    
    def set_preferences(self, preferences: Dict[str, Any]) -> bool:
        """设置用户偏好"""
        return self.write('preferences.json', preferences)
    
    def get_resume(self) -> Optional[Dict[str, Any]]:
        """获取简历数据"""
        return self.read('resume.json')
    
    def set_resume(self, resume: Dict[str, Any]) -> bool:
        """设置简历数据"""
        return self.write('resume.json', resume)
    
    def get_jobs(self) -> List[Dict[str, Any]]:
        """获取所有职位"""
        data = self.read('job-tracker.json')
        return data.get('jobs', []) if data else []
    
    def add_job(self, job: Dict[str, Any]) -> bool:
        """添加一个职位"""
        data = self.read('job-tracker.json') or {'jobs': [], 'last_updated': datetime.now().isoformat()}
        data['jobs'].append(job)
        data['last_updated'] = datetime.now().isoformat()
        return self.write('job-tracker.json', data)
    
    def update_job(self, job_id: str, updates: Dict[str, Any]) -> bool:
        """更新职位信息"""
        data = self.read('job-tracker.json') or {'jobs': [], 'last_updated': datetime.now().isoformat()}
        for i, job in enumerate(data['jobs']):
            if job.get('job_id') == job_id:
                data['jobs'][i].update(updates)
                data['last_updated'] = datetime.now().isoformat()
                return self.write('job-tracker.json', data)
        return False
    
    def get_feedbacks(self) -> List[Dict[str, Any]]:
        """获取所有反馈"""
        data = self.read('feedback.json')
        return data.get('feedbacks', []) if data else []
    
    def add_feedback(self, feedback: Dict[str, Any]) -> bool:
        """添加反馈"""
        data = self.read('feedback.json') or {'feedbacks': [], 'last_updated': datetime.now().isoformat()}
        data['feedbacks'].append(feedback)
        data['last_updated'] = datetime.now().isoformat()
        return self.write('feedback.json', data)
    
    def get_footprint_projects(self) -> List[Dict[str, Any]]:
        """获取数字足迹项目索引"""
        data = self.read('projects_index.json')
        return data.get('projects', []) if data else []
    
    def add_footprint_project(self, project: Dict[str, Any]) -> bool:
        """添加数字足迹项目"""
        data = self.read('projects_index.json') or {'projects': [], 'last_updated': datetime.now().isoformat()}
        data['projects'].append(project)
        data['last_updated'] = datetime.now().isoformat()
        return self.write('projects_index.json', data)

    def set_footprint_projects(self, projects: List[Dict[str, Any]]) -> bool:
        """批量设置数字足迹项目（替换整个列表）"""
        data = {
            'projects': projects,
            'last_updated': datetime.now().isoformat()
        }
        return self.write('projects_index.json', data)
    
    def get_footprint_summary(self) -> Optional[Dict[str, Any]]:
        """获取数字足迹摘要"""
        return self.read('digital_footprint_summary.json')
    
    def set_footprint_summary(self, summary: Dict[str, Any]) -> bool:
        """设置数字足迹摘要"""
        return self.write('digital_footprint_summary.json', summary)

    # ========== 投递状态追踪方法 ==========

    def get_job_by_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        """根据 job_id 获取职位"""
        jobs = self.get_jobs()
        for job in jobs:
            if job.get('job_id') == job_id:
                return job
        return None

    def update_job_status(self, job_id: str, new_status: str, note: str = "") -> bool:
        """
        更新职位投递状态，自动记录状态历史

        Args:
            job_id: 职位ID
            new_status: 新状态（DeliveryStatus 值）
            note: 状态变更备注

        Returns:
            更新成功返回 True，失败返回 False
        """
        from datetime import datetime

        data = self.read('job-tracker.json') or {'jobs': [], 'last_updated': datetime.now().isoformat()}
        for i, job in enumerate(data['jobs']):
            if job.get('job_id') == job_id:
                now = datetime.now().isoformat()
                
                # 初始化状态字段（向后兼容）
                if 'status' not in job:
                    job['status'] = 'saved'
                if 'status_history' not in job:
                    job['status_history'] = []
                if 'applied_at' not in job:
                    job['applied_at'] = None
                if 'interview_count' not in job:
                    job['interview_count'] = 0
                if 'next_action' not in job:
                    job['next_action'] = ''
                if 'salary_offered' not in job:
                    job['salary_offered'] = None
                if 'feedback' not in job:
                    job['feedback'] = ''

                # 记录状态历史
                history_entry = {
                    'status': new_status,
                    'timestamp': now,
                    'note': note
                }
                job['status_history'].append(history_entry)

                # 更新当前状态
                old_status = job.get('status')
                job['status'] = new_status

                # 如果是从 saved 变为 applied，记录 applied_at
                if old_status == 'saved' and new_status == 'applied':
                    job['applied_at'] = now

                # 更新 next_action
                from jobs.job_status import get_next_action
                job['next_action'] = get_next_action(new_status)

                # 统计面试次数
                interview_statuses = {'screening', 'interview_t1', 'interview_t2', 'interview_t3', 'offer'}
                job['interview_count'] = sum(
                    1 for h in job['status_history']
                    if h.get('status') in interview_statuses
                )

                data['last_updated'] = now
                return self.write('job-tracker.json', data)
        return False

    def get_jobs_by_status(self, status: str) -> List[Dict[str, Any]]:
        """
        按投递状态筛选职位

        Args:
            status: DeliveryStatus 值

        Returns:
            符合状态的职位列表
        """
        jobs = self.get_jobs()
        # 'new' 状态归入 'saved'
        if status == 'saved':
            return [job for job in jobs if job.get('status') in ('saved', 'new')]
        return [job for job in jobs if job.get('status') == status]

    def get_application_stats(self) -> Dict[str, int]:
        """
        获取投递统计数据

        Returns:
            各状态的职位数量统计
        """
        jobs = self.get_jobs()
        stats = {
            'saved': 0,
            'applied': 0,
            'interview': 0,  # 包含 screening + 各轮面试
            'offer': 0,
            'hired': 0,
            'rejected': 0,
            'total': len(jobs)
        }

        interview_statuses = {'screening', 'interview_t1', 'interview_t2', 'interview_t3'}

        for job in jobs:
            status = job.get('status', 'saved')
            # 'new' 状态归入 'saved'
            if status == 'new':
                status = 'saved'
            if status in stats:
                stats[status] += 1
            elif status not in ['saved', 'applied', 'interview', 'offer', 'hired', 'rejected']:
                # 未知状态归入 saved
                stats['saved'] += 1
            if status in interview_statuses or status == 'offer':
                stats['interview'] += 1

        return stats

    def migrate_jobs_status_field(self) -> int:
        """
        迁移旧职位数据：为没有 status 字段的职位添加默认状态
        用于向后兼容

        Returns:
            迁移的职位数量
        """
        from datetime import datetime

        data = self.read('job-tracker.json')
        if not data:
            return 0

        migrated = 0
        for job in data.get('jobs', []):
            if 'status' not in job:
                job['status'] = 'saved'
                job['status_history'] = [{
                    'status': 'saved',
                    'timestamp': job.get('created_at', datetime.now().isoformat()),
                    'note': '系统自动迁移初始化'
                }]
                job['applied_at'] = None
                job['interview_count'] = 0
                job['next_action'] = '投递职位，记录求职意向'
                job['salary_offered'] = None
                job['feedback'] = ''
                migrated += 1

        if migrated > 0:
            data['last_updated'] = datetime.now().isoformat()
            self.write('job-tracker.json', data)

        return migrated


# 模块级别实例，方便直接导入使用
_default_manager: Optional[StorageManager] = None

def get_manager() -> StorageManager:
    """获取默认的存储管理器实例（单例）"""
    global _default_manager
    if _default_manager is None:
        _default_manager = StorageManager()
    return _default_manager


if __name__ == '__main__':
    # 测试代码
    print("=" * 60)
    print("StorageManager 初始化测试")
    print("=" * 60)
    
    manager = StorageManager()
    
    print(f"\n存储根目录: {manager.base_path}")
    print(f"\n目录结构:")
    for item in manager.base_path.iterdir():
        print(f"  - {item.name}/")
    
    print(f"\n管理的文件:")
    for filename in StorageManager.MANAGED_FILES:
        info = manager.get_file_info(filename)
        if info:
            print(f"  - {filename} ({info['size']} bytes, backup={'是' if info['has_backup'] else '否'})")
        else:
            print(f"  - {filename} (不存在)")
    
    # 测试读写
    print(f"\n测试写入 state.json...")
    test_state = {
        "current_step": 1,
        "user_id": "test_user",
        "last_active": datetime.now().isoformat(),
        "test_data": "Hello from StorageManager!"
    }
    result = manager.write('state.json', test_state)
    print(f"写入结果: {'成功' if result else '失败'}")
    
    print(f"\n测试读取 state.json...")
    data = manager.read('state.json')
    print(f"读取结果: {data}")
    
    print(f"\n测试更新 state.json...")
    result = manager.update('state.json', {"current_step": 2, "new_field": "new_value"})
    print(f"更新结果: {'成功' if result else '失败'}")
    data = manager.read('state.json')
    print(f"更新后数据: {data}")
    
    print(f"\n测试备份...")
    result = manager.backup('state.json')
    print(f"备份结果: {'成功' if result else '失败'}")
    
    print(f"\n测试恢复...")
    result = manager.restore('state.json')
    print(f"恢复结果: {'成功' if result else '失败'}")
    data = manager.read('state.json')
    print(f"恢复后数据: {data}")
    
    print("\n" + "=" * 60)
    print("StorageManager 测试完成")
    print("=" * 60)