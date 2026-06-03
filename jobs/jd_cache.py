"""
JobTracer JD缓存模块
对BOSS职位的JD详情进行缓存，避免重复调用 opencli boss search
"""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional


class JDCache:
    """BOSS职位JD详情缓存器"""

    def __init__(self, cache_dir: str = "~/.jobtracer/jobs/jd_cache"):
        self.cache_dir = Path(cache_dir).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = 24 * 60 * 60  # 24小时（秒）

    def _cache_path(self, security_id: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{security_id}.json"

    def is_expired(self, cache_file: Path) -> bool:
        """检查缓存是否过期（超过24小时）"""
        if not cache_file.exists():
            return True
        
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            
            # 检查 expires_at 字段
            if "expires_at" in cache_data:
                expires_at = datetime.fromisoformat(cache_data["expires_at"])
                now = datetime.now(timezone.utc)
                return now >= expires_at
            
            # 向后兼容：如果没有 expires_at，检查 fetched_at
            if "fetched_at" in cache_data:
                fetched_at = datetime.fromisoformat(cache_data["fetched_at"])
                now = datetime.now(timezone.utc)
                age_seconds = (now - fetched_at).total_seconds()
                return age_seconds >= self.ttl
            
            return True
            
        except (json.JSONDecodeError, KeyError, ValueError):
            # 损坏的缓存视为过期
            return True

    def get(self, security_id: str) -> Optional[dict]:
        """
        获取缓存的JD详情
        
        Args:
            security_id: BOSS职位的唯一标识
            
        Returns:
            缓存的JD数据字典，如果不存在或过期返回None
        """
        cache_file = self._cache_path(security_id)
        
        # 检查过期
        if self.is_expired(cache_file):
            return None
        
        # 读取缓存
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            
            return cache_data.get("data")
            
        except (json.JSONDecodeError, OSError) as e:
            return None

    def set(self, security_id: str, data: dict, ttl: int = None) -> bool:
        """
        写入JD缓存
        
        Args:
            security_id: BOSS职位的唯一标识
            data: JD详情数据
            ttl: 缓存有效期（秒），默认使用 self.ttl
            
        Returns:
            写入成功返回True，失败返回False
        """
        cache_file = self._cache_path(security_id)
        
        now = datetime.now(timezone.utc)
        effective_ttl = ttl if ttl is not None else self.ttl
        expires_at = now + timedelta(seconds=effective_ttl)
        
        cache_content = {
            "security_id": security_id,
            "fetched_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "data": data
        }
        
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_content, f, ensure_ascii=False, indent=2)
            return True
        except OSError as e:
            return False

    def clear_expired(self) -> int:
        """
        清理过期缓存
        
        Returns:
            清理的缓存文件数量
        """
        cleared_count = 0
        
        for cache_file in self.cache_dir.glob("*.json"):
            if self.is_expired(cache_file):
                try:
                    cache_file.unlink()
                    cleared_count += 1
                except OSError:
                    pass
        
        return cleared_count

    def clear_all(self) -> int:
        """
        清理所有缓存
        
        Returns:
            删除的缓存文件数量
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                count += 1
            except OSError:
                pass
        return count

    def get_stats(self) -> dict:
        """
        获取缓存统计信息
        
        Returns:
            包含缓存数量、过期数量、大小的字典
        """
        all_files = list(self.cache_dir.glob("*.json"))
        expired_count = sum(1 for f in all_files if self.is_expired(f))
        total_size = sum(f.stat().st_size for f in all_files)
        
        return {
            "total": len(all_files),
            "valid": len(all_files) - expired_count,
            "expired": expired_count,
            "size_bytes": total_size
        }