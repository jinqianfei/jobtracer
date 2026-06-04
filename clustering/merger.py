"""
clustering/merger.py
NEW-5: 合并相关项目

542个路径分组 → 合并为 50~100 个有意义的大项目

合并策略（从粗到细）：
1. 顶级目录不同 → 不合并
2. 顶级相同但二级不同 → 不合并
3. 前2级相同，前3级相同：
   - 该组 < 10 个项目 → 合并成1个大项目
   - 该组 >= 10 个项目 → 只合并前4级相同的（避免把所有子目录合并成一个大项目）
4. 前4级相同 → 合并

被合并的文件夹 → 移到 projects/merged/ 子目录，加 _merged_ 前缀
"""

import json
import re
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Tuple

PROJECTS_DIR = Path("~/.jobtracer/footprint/projects").expanduser()
PROJECTS_INDEX = Path("~/.jobtracer/projects_index.json").expanduser()

LARGE_GROUP_THRESHOLD = 10


def load_projects() -> List[Dict]:
    if not PROJECTS_INDEX.exists():
        return []
    data = json.loads(PROJECTS_INDEX.read_text(encoding='utf-8'))
    return data.get('projects', [])


def parse_path_depth(path: str) -> Tuple[str, List[str]]:
    m = re.search(r'~/([^/]+)(?:/(.+))?', path)
    if m:
        top = m.group(1)
        rest = m.group(2) or ""
        parts = [p for p in rest.split('/') if p]
        return top, parts
    return path, []


def group_projects_by_depth(projects: List[Dict], depth: int) -> Dict[Tuple, List[int]]:
    groups: Dict[Tuple, List[int]] = {}
    for i, p in enumerate(projects):
        _, parts = parse_path_depth(p.get('description', ''))
        key = tuple(parts[:depth]) if len(parts) >= depth else tuple(parts)
        if key not in groups:
            groups[key] = []
        groups[key].append(i)
    return groups


def merge_projects_by_path(projects: List[Dict]) -> Tuple[List[Dict], List[str]]:
    n = len(projects)

    # 第一步：按前3级分组，检查每组大小
    groups_3 = group_projects_by_depth(projects, 3)

    merge_at: Dict[int, int] = {}
    for key, indices in groups_3.items():
        if len(indices) >= LARGE_GROUP_THRESHOLD:
            # 大组：只合并前4级相同的
            sub_projects = [projects[i] for i in indices]
            groups_4 = group_projects_by_depth(sub_projects, 4)
            for k4, i4 in groups_4.items():
                for idx in i4:
                    merge_at[indices[idx]] = 4
        else:
            for idx in indices:
                merge_at[idx] = 3

    # 第二步：并查集合并
    parent = list(range(n))

    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for i in range(n):
        level_i = merge_at.get(i, 0)
        if level_i == 0:
            continue
        for j in range(i + 1, n):
            level_j = merge_at.get(j, 0)
            if level_j != level_i:
                continue
            if level_i >= 3:
                _, parts_i = parse_path_depth(projects[i].get('description', ''))
                _, parts_j = parse_path_depth(projects[j].get('description', ''))
                if tuple(parts_i[:level_i]) == tuple(parts_j[:level_i]):
                    union(i, j)

    # 收集所有簇
    clusters: Dict[int, List[int]] = {}
    for i in range(n):
        root = find(i)
        if root not in clusters:
            clusters[root] = []
        clusters[root].append(i)

    merged = []
    deprecated: List[str] = []

    for root, members in clusters.items():
        if len(members) == 1:
            p = projects[members[0]]
            merged.append({
                'project_id': p['project_id'],
                'project_name': p['project_name'],
                'description': p['description'],
                'tags': p.get('tags', []),
                'file_count': p.get('file_count', 0),
                'confidence': p.get('confidence', 0.8),
                'source': p.get('source', 'local'),
                'created_at': p.get('created_at', ''),
                'merged_from': [],
            })
        else:
            sorted_members = sorted(members, key=lambda idx: projects[idx].get('file_count', 0), reverse=True)
            primary = projects[sorted_members[0]]
            merged_ids = [projects[idx]['project_id'] for idx in sorted_members]

            _, parts = parse_path_depth(primary.get('description', ''))
            level = merge_at.get(sorted_members[0], 3)
            if len(parts) >= level:
                merged_parts = parts[:level]
                merged_desc = "Files from ~/" + "/".join(merged_parts)
                merged_name = merged_parts[-1]
            else:
                merged_desc = primary['description']
                merged_name = primary['project_name']

            all_tags: Set[str] = set()
            for idx in sorted_members:
                all_tags.update(projects[idx].get('tags', []))
            total_files = sum(projects[idx].get('file_count', 0) for idx in sorted_members)
            avg_conf = sum(projects[idx].get('confidence', 0) for idx in sorted_members) / len(sorted_members)

            merged.append({
                'project_id': primary['project_id'],
                'project_name': merged_name,
                'description': merged_desc,
                'tags': list(all_tags)[:10],
                'file_count': total_files,
                'confidence': round(avg_conf, 2),
                'source': primary.get('source', 'local'),
                'created_at': primary.get('created_at', ''),
                'merged_from': merged_ids,
            })

            for idx in sorted_members[1:]:
                deprecated.append(projects[idx]['project_id'])

    return merged, deprecated


def move_deprecated_to_merged(deprecated_ids: List[str]) -> None:
    """将被合并项目移到 projects/merged/ 子目录"""
    merged_dir = PROJECTS_DIR / "merged"
    merged_dir.mkdir(exist_ok=True)

    for pid in deprecated_ids:
        project_dir = PROJECTS_DIR / pid
        if not project_dir.exists():
            # 已经被移动过了，跳过
            continue
        new_name = f"_merged_{pid}"
        new_path = merged_dir / new_name
        if new_path.exists():
            shutil.rmtree(new_path)
        try:
            project_dir.rename(new_path)
            print(f"[merger] Moved {pid} -> merged/{new_name}")
        except Exception as e:
            print(f"[merger] Failed to move {pid}: {e}")


def run() -> Dict:
    print("[merger] Loading projects...")
    projects = load_projects()
    print(f"[merger] Loaded {len(projects)} projects")

    print("[merger] Running merge by path hierarchy...")
    merged, deprecated = merge_projects_by_path(projects)

    print(f"[merger] Merged into {len(merged)} projects, {len(deprecated)} deprecated")

    if deprecated:
        print("[merger] Moving deprecated projects to merged/...")
        move_deprecated_to_merged(deprecated)

    return {
        'merged_projects': merged,
        'deprecated_count': len(deprecated),
        'original_count': len(projects),
    }


if __name__ == '__main__':
    result = run()
    print(json.dumps({
        'merged_count': len(result['merged_projects']),
        'deprecated_count': result['deprecated_count'],
        'original_count': result['original_count'],
        'timestamp': datetime.now().isoformat()
    }, ensure_ascii=False, indent=2))