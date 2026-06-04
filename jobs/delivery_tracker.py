"""投递状态追踪器
管理职位的投递进度：已保存 → 已投递 → 面试 → Offer → 入职
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import json
import logging

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from storage.manager import StorageManager

logger = logging.getLogger('jobtracer.jobs.delivery')


class DeliveryTracker:
    """投递状态追踪器"""
    
    def __init__(self):
        self.storage = StorageManager()
    
    def mark_applied(self, job_id: str, note: str = "") -> dict:
        """标记为已投递"""
        return self.storage.update_job_status(job_id, "applied", note or "已投递")
    
    def advance_status(self, job_id: str, note: str = "") -> dict:
        """推进到下一状态"""
        job = self._get_job(job_id)
        if not job:
            return {"success": False, "error": "职位不存在"}
        
        current = job.get("status", "saved")
        next_status = self._get_next_status(current)
        
        if next_status is None:
            return {"success": False, "error": f"已是终态（{current}），无法推进"}
        
        return self.storage.update_job_status(job_id, next_status, note or f"从 {current} 推进到 {next_status}")
    
    def reject(self, job_id: str, reason: str = "") -> dict:
        """标记为拒绝"""
        return self.storage.update_job_status(job_id, "rejected", reason or "主动拒绝")
    
    def withdraw(self, job_id: str, reason: str = "") -> dict:
        """撤回投递"""
        return self.storage.update_job_status(job_id, "withdrawn", reason or "主动撤回")
    
    def get_next_action(self, job_id: str) -> str:
        """获取下一步建议"""
        job = self._get_job(job_id)
        if not job:
            return "职位不存在"
        
        status = job.get("status", "saved")
        suggestions = {
            "saved": "确认投递，调用 apply 命令标记为已投递",
            "applied": "等待HR回复，3天后未读可考虑跟进",
            "screening": "准备笔试，查看相关笔经",
            "interview_t1": "准备一面，复习技术基础和项目经历",
            "interview_t2": "准备二面，深入项目细节和技术深度",
            "interview_t3": "准备终面，了解团队文化和技术栈",
            "offer": "进行薪资谈判，使用 career 命令获取建议",
            "rejected": "复盘面试，准备其他机会",
            "withdrawn": "继续其他求职流程",
            "hired": "🎉 恭喜入职！",
            "expired": "职位已失效，查看其他机会",
        }
        return suggestions.get(status, "未知状态")
    
    def get_application_stats(self) -> Dict[str, int]:
        """获取投递统计"""
        return self.storage.get_application_stats()
    
    def get_jobs_by_status(self, status: str) -> List[dict]:
        """按状态筛选职位"""
        return self.storage.get_jobs_by_status(status)
    
    def list_pending_deliveries(self) -> List[dict]:
        """列出所有进行中的投递（已定制简历但未发送）"""
        pending_dir = Path.home() / ".jobtracer" / "pending_deliveries"
        if not pending_dir.exists():
            return []
        
        pending = []
        for f in pending_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                # 只返回7天内的
                saved_at = datetime.fromisoformat(data.get("saved_at", "2020-01-01"))
                if (datetime.now() - saved_at).days <= 7:
                    pending.append(data)
            except Exception:
                continue
        return pending
    
    def save_pending_delivery(self, job_id: str, customized_resume_path: str, job_info: dict):
        """保存进行中的投递（简历已定制但未发送）"""
        pending_dir = Path.home() / ".jobtracer" / "pending_deliveries"
        pending_dir.mkdir(exist_ok=True)
        
        data = {
            "job_id": job_id,
            "job_info": job_info,
            "customized_resume_path": customized_resume_path,
            "saved_at": datetime.now().isoformat(),
        }
        
        path = pending_dir / f"{job_id}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        logger.info(f"保存待投递: {job_id}")
    
    def restore_pending_delivery(self, job_id: str) -> dict:
        """恢复投递"""
        pending_dir = Path.home() / ".jobtracer" / "pending_deliveries"
        path = pending_dir / f"{job_id}.json"
        
        if not path.exists():
            return {"success": False, "error": "投递已失效或不存在"}
        
        data = json.loads(path.read_text())
        path.unlink()  # 删除pending文件
        logger.info(f"恢复投递: {job_id}")
        return {"success": True, "data": data}
    
    def _get_job(self, job_id: str) -> Optional[dict]:
        """获取职位信息"""
        jobs = self.storage.get_jobs()
        for j in jobs:
            if j.get("job_id") == job_id:
                return j
        return None
    
    def _get_next_status(self, current: str) -> Optional[str]:
        """获取下一状态"""
        progression = [
            "saved", "applied", "screening",
            "interview_t1", "interview_t2", "interview_t3",
            "offer", "hired"
        ]
        if current in progression:
            idx = progression.index(current)
            if idx + 1 < len(progression):
                return progression[idx + 1]
        return None  # 终态


# 快捷函数
def get_stats() -> Dict[str, int]:
    """获取投递统计（对外接口）"""
    tracker = DeliveryTracker()
    return tracker.get_application_stats()


if __name__ == "__main__":
    tracker = DeliveryTracker()
    stats = tracker.get_application_stats()
    print(f"📊 投递统计:")
    print(f"  已保存: {stats.get('saved', 0)}")
    print(f"  已投递: {stats.get('applied', 0)}")
    print(f"  面试中: {stats.get('interview', 0)}")
    print(f"  Offer: {stats.get('offer', 0)}")
    
    pending = tracker.list_pending_deliveries()
    if pending:
        print(f"\n📋 待恢复投递: {len(pending)}个")