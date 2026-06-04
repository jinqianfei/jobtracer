"""
clustering/copy_project_content.py
NEW-3: 将原始文件内容复制到项目目录

从 _index.md 解析文件路径，复制实际内容到 docs/code_snippets/data/attachments/
优先读取实际文件，失败时用 local_files.json 的 content_preview 回退。
"""

import json
import re
import os
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# 项目根目录
PROJECTS_DIR = Path("~/.jobtracer/footprint/projects").expanduser()
PROJECTS_PARENT = PROJECTS_DIR.parent
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB - 大文件只记录路径
ENCODING_OPTIONS = ['utf-8', 'gbk', 'gb2312', 'latin-1']

# 全局 content_preview 缓存（从 local_files.json 加载）
_CONTENT_PREVIEW_MAP: Optional[Dict[str, str]] = None


def _get_content_preview_map() -> Dict[str, str]:
    """懒加载 content_preview 映射表"""
    global _CONTENT_PREVIEW_MAP
    if _CONTENT_PREVIEW_MAP is not None:
        return _CONTENT_PREVIEW_MAP

    _CONTENT_PREVIEW_MAP = {}
    try:
        lf_path = PROJECTS_PARENT.parent / "openclaw-workspaces" / "product-solution" / "jobtracer" / "scanner" / "results" / "local_files.json"
        # also try workspace-relative path
        if not lf_path.exists():
            lf_path = Path("~/openclaw-workspaces/product-solution/jobtracer/scanner/results/local_files.json").expanduser()
        if lf_path.exists():
            with open(lf_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for f_item in data.get('files', []):
                cp = f_item.get('content_preview', '')
                if cp:
                    _CONTENT_PREVIEW_MAP[f_item['path']] = cp
            print(f"[copy_project_content] Loaded {len(_CONTENT_PREVIEW_MAP)} content_previews from local_files.json")
    except Exception as e:
        print(f"[copy_project_content] Could not load local_files.json: {e}")

    return _CONTENT_PREVIEW_MAP


def parse_index_paths(index_md_path: Path) -> List[Dict]:
    """从 _index.md 解析文件路径列表"""
    if not index_md_path.exists():
        return []

    content = index_md_path.read_text(encoding='utf-8')
    files = []

    # 匹配格式: - **filename** (source) - `path`
    pattern = r'- \*\*(.+?)\*\* \(.+?\) - `(.+?)`'
    for match in re.finditer(pattern, content):
        name = match.group(1)
        path = match.group(2)
        files.append({
            'name': name,
            'path': path
        })

    return files


def read_file_content(file_path: str) -> Tuple[Optional[str], str]:
    """
    读取文件内容，处理编码和大文件

    Returns:
        (content_or_None, status)
        status: 'copied', 'path_recorded', 'skipped', 'error'
    """
    if not file_path or file_path.startswith('feishu:') or file_path.startswith('github:'):
        return None, 'skipped'

    p = Path(file_path)
    if not p.exists():
        # 回退：用 content_preview
        cp_map = _get_content_preview_map()
        if file_path in cp_map:
            return cp_map[file_path][:50 * 1024], 'copied'
        return None, 'skipped'

    # 检查文件大小
    try:
        size = p.stat().st_size
        if size > MAX_FILE_SIZE:
            # 回退：用 content_preview
            cp_map = _get_content_preview_map()
            if file_path in cp_map:
                return cp_map[file_path][:50 * 1024], 'copied'
            return None, 'path_recorded'
    except Exception:
        pass

    ext = p.suffix.lower()
    # 二进制文件只记录路径
    BINARY_EXTS = {'.pdf', '.ppt', '.pptx', '.doc', '.docx', '.xls', '.xlsx',
                   '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico',
                   '.zip', '.tar', '.gz', '.rar', '.7z',
                   '.mp3', '.mp4', '.avi', '.mov', '.wav',
                   '.exe', '.dmg', '.pkg', '.bin'}
    if ext in BINARY_EXTS:
        return None, 'path_recorded'

    # 文本文件 - 读字节流解码，绕过 read_text 限制
    try:
        raw_data = p.read_bytes()
        # 检测空字节（二进制标志）
        if b'\x00' in raw_data[:1000]:
            return None, 'path_recorded'
        for enc in ENCODING_OPTIONS:
            try:
                content = raw_data.decode(enc, errors='ignore')
                return content[:50 * 1024], 'copied'
            except Exception:
                continue
    except Exception as e:
        # 可能是资源锁定（errno 11）等，回退：用 content_preview
        cp_map = _get_content_preview_map()
        if file_path in cp_map:
            return cp_map[file_path][:50 * 1024], 'copied'
        return None, 'path_recorded'

    # 回退
    cp_map = _get_content_preview_map()
    if file_path in cp_map:
        return cp_map[file_path][:50 * 1024], 'copied'

    return None, 'error'


def get_target_dir(ext: str) -> str:
    """根据扩展名确定目标子目录"""
    if ext in ['.py', '.js', '.ts', '.go', '.java', '.cpp', '.c', '.h', '.sh', '.sql', '.jsx', '.tsx']:
        return 'code_snippets'
    elif ext in ['.md', '.txt', '.rst', '.adoc']:
        return 'docs'
    elif ext in ['.json', '.yaml', '.yml', '.toml', '.ini', '.conf', '.config']:
        return 'data'
    elif ext in ['.pdf', '.doc', '.docx', '.xlsx', '.xls', '.pptx', '.ppt']:
        return 'attachments'
    else:
        return 'data'


def deduplicate_filename(target_dir: Path, base_name: str) -> str:
    """处理文件名冲突，加序号"""
    if not (target_dir / base_name).exists():
        return base_name

    name, ext = os.path.splitext(base_name)
    counter = 1
    while (target_dir / f"{name}_{counter}{ext}").exists():
        counter += 1

    return f"{name}_{counter}{ext}"


def copy_project_content(project_id: str, dry_run: bool = False) -> Dict:
    """
    复制单个项目的文件内容

    Returns:
        {
            'project_id': str,
            'copied': int,
            'path_recorded': int,
            'skipped': int,
            'errors': int,
            'details': [(filename, status), ...]
        }
    """
    project_dir = PROJECTS_DIR / project_id
    if not project_dir.exists():
        return {'project_id': project_id, 'error': 'project not found'}

    index_path = project_dir / '_index.md'
    if not index_path.exists():
        return {'project_id': project_id, 'error': 'no index file'}

    files = parse_index_paths(index_path)

    stats = {
        'copied': 0,
        'path_recorded': 0,
        'skipped': 0,
        'errors': 0,
        'details': []
    }

    # 确保子目录存在
    for subdir in ['docs', 'code_snippets', 'data', 'attachments']:
        (project_dir / subdir).mkdir(exist_ok=True)

    for f in files:
        path = f['path']
        name = f['name']
        ext = Path(path).suffix.lower()

        target_subdir = get_target_dir(ext)
        target_dir = project_dir / target_subdir

        # 去重文件名
        save_name = deduplicate_filename(target_dir, name)
        save_path = target_dir / save_name

        if dry_run:
            stats['details'].append((name, 'dry_run'))
            stats['copied'] += 1
            continue

        # 读取内容
        content, status = read_file_content(path)

        if status == 'copied' and content:
            save_path.write_text(content, encoding='utf-8')
            stats['copied'] += 1
        elif status == 'path_recorded':
            # 写一个 .path 文件记录路径
            path_file = save_path.with_suffix('.path')
            path_file.write_text(path, encoding='utf-8')
            stats['path_recorded'] += 1
        else:
            stats['skipped'] += 1

        stats['details'].append((name, status))

    return stats


def run_all(dry_run: bool = False) -> Dict:
    """对所有项目执行内容复制"""
    results = {}

    project_dirs = sorted(PROJECTS_DIR.iterdir())
    total = len(project_dirs)

    print(f"Found {total} projects to process")

    for i, project_dir in enumerate(project_dirs):
        if not project_dir.is_dir():
            continue

        project_id = project_dir.name

        if (i + 1) % 50 == 0 or i == 0:
            print(f"Processing [{i+1}/{total}]: {project_id}")

        try:
            stats = copy_project_content(project_id, dry_run=dry_run)
            results[project_id] = stats
        except Exception as e:
            results[project_id] = {'project_id': project_id, 'error': str(e)}

    # 汇总
    total_copied = sum(r.get('copied', 0) for r in results.values())
    total_path_recorded = sum(r.get('path_recorded', 0) for r in results.values())
    total_skipped = sum(r.get('skipped', 0) for r in results.values())
    total_errors = sum(r.get('errors', 0) for r in results.values())

    print(f"\n=== Summary ===")
    print(f"Total projects: {len(results)}")
    print(f"Files copied: {total_copied}")
    print(f"Paths recorded (large/binary files): {total_path_recorded}")
    print(f"Skipped: {total_skipped}")
    print(f"Errors: {total_errors}")

    return results


if __name__ == '__main__':
    import sys
    dry_run = '--dry-run' in sys.argv
    print(f"Running copy_project_content (dry_run={dry_run})...")
    results = run_all(dry_run=dry_run)

    # 保存结果
    output_path = PROJECTS_DIR.parent / "copy_results.json"
    output_path.write_text(
        json.dumps({'results': results, 'timestamp': datetime.now().isoformat()}, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    print(f"\nResults saved to {output_path}")