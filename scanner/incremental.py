"""增量扫描模块
基于文件 hash 的增量更新，只扫描变更文件
"""
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

HASH_CACHE = Path("~/.jobtracer/cache/file_hashes.json")


@dataclass
class FileHashCache:
    """文件 hash 缓存"""
    path: str
    mtime: float
    content_hash: str


class IncrementalScanner:
    """增量扫描器 - 基于文件 hash 的变更检测"""

    def __init__(self, cache_path: str = "~/.jobtracer/cache/file_hashes.json"):
        self.cache_path: Path = Path(cache_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache: Dict[str, dict] = self._load_cache()

    def _load_cache(self) -> Dict[str, dict]:
        """加载缓存"""
        if self.cache_path.exists():
            with open(self.cache_path) as f:
                return json.load(f)
        return {}

    def _save_cache(self) -> None:
        """保存缓存"""
        with open(self.cache_path, 'w') as f:
            json.dump(self.cache, f, indent=2)

    def _compute_hash(self, file_path: Path) -> str:
        """计算文件 MD5 hash（只读前 1MB）"""
        h = hashlib.md5()
        with open(file_path, 'rb') as f:
            h.update(f.read(1024 * 1024))
        return h.hexdigest()

    def get_changed_files(self, file_list: List[Path]) -> List[Path]:
        """返回自上次扫描以来有变化的文件"""
        changed: List[Path] = []
        for fp in file_list:
            key = str(fp)
            try:
                mtime = fp.stat().st_mtime
                if key not in self.cache:
                    changed.append(fp)
                elif mtime > self.cache[key].get("mtime", 0):
                    # 文件修改时间变了，检查 hash
                    current_hash = self._compute_hash(fp)
                    if current_hash != self.cache[key].get("hash"):
                        changed.append(fp)
            except OSError:
                continue
        return changed

    def update_cache(self, file_list: List[Path]) -> None:
        """更新缓存"""
        for fp in file_list:
            key = str(fp)
            try:
                self.cache[key] = {
                    "mtime": fp.stat().st_mtime,
                    "hash": self._compute_hash(fp)
                }
            except OSError:
                continue
        self._save_cache()

    def scan_incremental(
        self,
        root: Path,
        extensions: set,
        exclude_dirs: set
    ) -> List[Path]:
        """增量扫描：只返回有变化的文件

        Args:
            root: 扫描根目录
            extensions: 要扫描的文件扩展名集合，如 {'.py', '.json'}
            exclude_dirs: 要排除的目录名集合，如 {'__pycache__', '.git'}

        Returns:
            有变化的文件路径列表
        """
        all_files = [
            f for f in root.rglob("*")
            if f.is_file()
            and f.suffix.lower() in extensions
            and not any(ex in f.parts for ex in exclude_dirs)
        ]

        changed = self.get_changed_files(all_files)
        self.update_cache(changed)
        return changed
