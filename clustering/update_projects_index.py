"""
update_projects_index.py
NEW-6: 更新 projects_index.json 完整字段

从 footprint/projects/ 目录读取当前项目状态，更新 projects_index.json
"""

import json
from pathlib import Path
from datetime import datetime

PROJECTS_DIR = Path("~/.jobtracer/footprint/projects").expanduser()
PROJECTS_INDEX = Path("~/.jobtracer/projects_index.json").expanduser()


def load_summaries() -> dict:
    """加载 summaries.json"""
    path = PROJECTS_DIR.parent / "summaries.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return {k: v for k, v in data.get('results', {}).items()
                if isinstance(v, dict) and 'error' not in v}
    except Exception as e:
        print(f"[update_index] Could not load summaries: {e}")
        return {}


def load_merged_ids() -> set:
    """获取已合并的项目ID"""
    merged_dir = PROJECTS_DIR / "merged"
    if not merged_dir.exists():
        return set()
    merged_ids = set()
    for d in merged_dir.iterdir():
        if d.is_dir():
            # _merged_85ac22f0 → 85ac22f0
            pid = d.name.replace("_merged_", "")
            merged_ids.add(pid)
    return merged_ids


def run():
    print("[update_index] Loading summaries...")
    summaries = load_summaries()
    print(f"[update_index] Loaded {len(summaries)} summaries")

    merged_ids = load_merged_ids()
    print(f"[update_index] Merged IDs: {len(merged_ids)}")

    print("[update_index] Scanning active projects...")
    active_projects = []
    merged_map = {}  # project_id -> {merged_from, ...}

    for project_dir in sorted(PROJECTS_DIR.iterdir()):
        if not project_dir.is_dir() or project_dir.name == 'merged':
            continue

        metadata_path = project_dir / 'metadata.json'
        if not metadata_path.exists():
            continue

        try:
            meta = json.loads(metadata_path.read_text(encoding='utf-8'))
        except Exception:
            continue

        pid = meta.get('project_id', project_dir.name)

        # Check for merged_from (may be in the merged projects' metadata)
        merged_from = meta.get('merged_from', [])

        # Summary fields from summaries.json
        summary = summaries.get(pid, {})

        project = {
            'project_id': pid,
            'project_name': meta.get('project_name', ''),
            'description': meta.get('description', ''),
            'background': meta.get('background', summary.get('background', '')),
            'deliverables': meta.get('deliverables', summary.get('deliverables', '')),
            'results': meta.get('results', summary.get('results', '')),
            'solutions': meta.get('solutions', summary.get('solutions', '')),
            'tags': meta.get('tags', []),
            'file_count': meta.get('file_count', 0),
            'confidence': meta.get('confidence', 0.8),
            'source': meta.get('source', 'local'),
            'created_at': meta.get('created_at', ''),
            'merged_from': merged_from,
        }

        # For projects that have merged_from, find the merged projects and add to merged_map
        if merged_from:
            merged_map[pid] = project

        active_projects.append(project)

    print(f"[update_index] Active projects: {len(active_projects)}")

    # Build complete projects list (active + merged)
    all_projects = active_projects + list(merged_map.values())

    # Write projects_index.json
    data = {
        'projects': all_projects,
        'last_updated': datetime.now().isoformat()
    }

    PROJECTS_INDEX.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    print(f"[update_index] Written {len(all_projects)} projects to {PROJECTS_INDEX}")

    # Verify field completeness
    required_fields = ['project_id', 'project_name', 'description', 'background',
                      'deliverables', 'results', 'solutions', 'tags', 'file_count',
                      'confidence', 'source', 'created_at', 'merged_from']
    missing = {}
    for p in all_projects:
        for f in required_fields:
            val = p.get(f)
            if val is None or val == '':
                missing[f] = missing.get(f, 0) + 1

    if missing:
        print(f"[update_index] Missing fields: {missing}")
    else:
        print(f"[update_index] All fields complete!")

    return all_projects


if __name__ == '__main__':
    results = run()
    print(json.dumps({
        'total_projects': len(results),
        'timestamp': datetime.now().isoformat()
    }, ensure_ascii=False, indent=2))