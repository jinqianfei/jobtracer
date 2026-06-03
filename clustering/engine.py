"""
JobTracer Clustering Module
项目聚类引擎 - 基于数字足迹扫描结果进行项目聚类

实现说明：
- 支持基于规则的聚类（目录层级、文件类型、修改时间、相似文件名）
- 支持 LLM 聚类（当 llm_client 可用时）
- 生成 footprint/projects/{id}/ 结构
"""

import json
import hashlib
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from collections import defaultdict


class ProjectClusteringEngine:
    """
    项目聚类引擎
    将扫描文件聚类为项目，生成结构化的项目目录
    """

    def __init__(self, projects_dir: str = "~/.jobtracer/footprint/projects", llm_client=None):
        self.projects_dir = Path(projects_dir).expanduser()
        self.llm = llm_client

    async def cluster(self, scan_results: dict) -> List[dict]:
        """
        将扫描文件聚类为项目

        输入：scan_results（scan_all 的输出）
            {
                'local': {'files': [...]},
                'feishu': {'docs': [...]},
                'github': {'items': [...]},
                'openclaw': {'files': [...]}
            }

        输出：项目列表，每个项目包含 files/name/tags/summary
            [{
                'project_id': str,
                'project_name': str,
                'description': str,
                'files': [...],
                'tags': [...],
                'summary': str,
                'confidence': float
            }]
        """
        all_items = []

        # scan_all() 返回格式：
        # {
        #   'sources': {'local': {'files': 2295, ...}, 'openclaw': {...}},  <- files是数量
        #   'files': [...]  <- 这是完整文件列表
        # }
        # 直接从 result['files'] 读取，然后用 result['sources'] 获取各 source 的元数据
        all_files = scan_results.get('files', [])
        sources = scan_results.get('sources', {})
        
        # 构建 source 映射：path -> source_name
        path_to_source = {}
        for source_name, source_data in sources.items():
            # source_data 中的 files 可能是数量或列表，取决于扫描器实现
            # 文件列表已经在顶层 all_files 中，这里只需要记录 source 名称
            pass
        
        # 按 source 分组处理
        for f in all_files:
            source = f.get('source', 'unknown')
            item = {
                'id': f.get('path', ''),
                'name': f.get('name', ''),
                'path': f.get('path', ''),
                'content_preview': f.get('content_preview', ''),
                'source': source,
                'ext': f.get('ext', ''),
                'modified': f.get('modified', '')
            }
            all_items.append(item)

        if not all_items:
            return []

        # 优先使用 LLM 聚类，否则使用规则聚类
        if self.llm:
            return await self._llm_cluster(all_items)
        else:
            return self._rule_based_cluster(all_items)

    def _process_local(self, data: dict) -> List[dict]:
        """处理本地文件扫描结果"""
        items = []
        for f in data.get('files', []):
            items.append({
                'id': f.get('path', ''),
                'name': f.get('name', ''),
                'path': f.get('path', ''),
                'content_preview': f.get('content_preview', ''),
                'source': 'local',
                'ext': f.get('ext', ''),
                'modified': f.get('modified', '')
            })
        return items

    def _process_feishu(self, data: dict) -> List[dict]:
        """处理飞书文档扫描结果"""
        items = []
        for doc in data.get('docs', []):
            items.append({
                'id': doc.get('doc_id', ''),
                'name': doc.get('title', ''),
                'path': f"feishu:{doc.get('doc_id', '')}",
                'content_preview': (doc.get('content', '')[:200] if doc.get('content') else ''),
                'source': 'feishu',
                'ext': '.feishu',
                'modified': data.get('scan_time', '')
            })
        return items

    def _process_github(self, data: dict) -> List[dict]:
        """处理 GitHub 扫描结果"""
        items = []
        for item in data.get('items', []):
            item_id = f"{item.get('repo', '')}_{item.get('type', 'file')}_{item.get('title', '')}"
            items.append({
                'id': item_id,
                'name': item.get('title', item.get('name', '')),
                'path': f"github:{item.get('repo', '')}",
                'content_preview': (item.get('body', item.get('content', ''))[:200] if item.get('body') or item.get('content') else ''),
                'source': 'github',
                'repo': item.get('repo', ''),
                'item_type': item.get('type', 'file'),
                'ext': '.github',
                'modified': ''
            })
        return items

    def _process_openclaw(self, data: dict) -> List[dict]:
        """处理 OpenClaw 记忆扫描结果"""
        items = []
        for f in data.get('files', []):
            items.append({
                'id': f.get('path', ''),
                'name': Path(f.get('path', '')).name,
                'path': f.get('path', ''),
                'content_preview': (f.get('content', '')[:200] if f.get('content') else ''),
                'source': 'openclaw',
                'ext': Path(f.get('path', '')).suffix,
                'modified': ''
            })
        return items

    async def _llm_cluster(self, items: List[dict]) -> List[dict]:
        """基于 LLM 的智能聚类"""
        items_summary = [
            {
                'id': item.get('id', idx),
                'name': item.get('name', ''),
                'content_preview': item.get('content_preview', '')[:200],
                'source': item.get('source', '')
            }
            for idx, item in enumerate(items)
        ]

        prompt = """You are a project clustering assistant. Group files by project.

Rules:
1. Related content topics -> same project
2. Same GitHub repo -> same project
3. Same Feishu space -> same project
4. Files with similar names (e.g., a_test.py and a.py) -> same project
5. Files in same directory hierarchy -> same project

Output JSON array of projects:
[{
    "project_name": "Project Name",
    "project_description": "Brief description",
    "items": ["item_id1", "item_id2"],
    "confidence": 0.95
}]

Files to classify:
""" + json.dumps(items_summary, ensure_ascii=False, indent=2)

        try:
            response = await self.llm.generate(prompt, schema='json')
            clusters = json.loads(response)
        except Exception as e:
            # LLM 调用失败，降级为规则聚类
            print(f"LLM clustering failed: {e}, falling back to rule-based")
            return self._rule_based_cluster(items)

        # 将聚类结果转换为项目列表
        projects = []
        for cluster in clusters:
            project_items = [item for item in items if item.get('id') in cluster.get('items', [])]
            project_id = hashlib.md5(cluster.get('project_name', str(hash(str(items)))).encode()).hexdigest()[:8]

            projects.append({
                'project_id': project_id,
                'project_name': cluster.get('project_name', 'Unknown Project'),
                'description': cluster.get('project_description', ''),
                'files': project_items,
                'tags': self._extract_tags(project_items),
                'summary': cluster.get('project_description', ''),
                'confidence': cluster.get('confidence', 0.8)
            })

        return projects

    def _rule_based_cluster(self, items: List[dict]) -> List[dict]:
        """
        基于规则的聚类（当 LLM 不可用时）

        聚类策略：
        1. 按目录层级聚类
        2. 按文件类型聚类
        3. 按修改时间聚类（同一时间段修改的文件归为同一项目）
        4. 相似文件名聚类（a_test.py 和 a.py 归为同一项目）
        """
        # 策略1: 按目录层级 + GitHub repo 聚类
        clusters_by_location = defaultdict(list)
        clusters_by_repo = defaultdict(list)
        clusters_by_time = defaultdict(list)
        clusters_by_name_pattern = defaultdict(list)

        for item in items:
            source = item.get('source', 'unknown')

            # 按来源分组
            if source == 'github':
                repo = item.get('repo', 'unknown')
                clusters_by_repo[repo].append(item)
            else:
                # 按路径目录聚类
                path = item.get('path', '')
                if source == 'feishu':
                    path = f"feishu:{item.get('id', '')}"
                elif source == 'openclaw':
                    path = str(Path(path).parent)

                dir_key = self._normalize_path(path)
                clusters_by_location[dir_key].append(item)

            # 按修改时间聚类 (30天内的文件归为一组)
            modified = item.get('modified', '')
            if modified:
                try:
                    dt = datetime.fromisoformat(modified.replace('Z', '+00:00'))
                    time_key = dt.strftime('%Y-%m')
                    clusters_by_time[time_key].append(item)
                except:
                    pass

            # 相似文件名聚类
            name = item.get('name', '')
            pattern_key = self._extract_name_pattern(name)
            if pattern_key:
                clusters_by_name_pattern[pattern_key].append(item)

        # 合并聚类结果
        merged_clusters = []

        # 优先保留 GitHub repo 聚类
        for repo, repo_items in clusters_by_repo.items():
            if len(repo_items) >= 1:
                merged_clusters.append({
                    'project_id': hashlib.md5(repo.encode()).hexdigest()[:8],
                    'project_name': f"GitHub/{repo}",
                    'description': f"GitHub repository: {repo}",
                    'files': repo_items,
                    'tags': ['github', 'repository'],
                    'summary': f"Project from GitHub repository {repo}",
                    'confidence': 0.9,
                    'source': 'github'
                })

        # 合并路径聚类 (排除已被 GitHub 聚类包含的文件)
        github_item_ids = {item.get('id') for items in clusters_by_repo.values() for item in items}

        for dir_key, dir_items in clusters_by_location.items():
            filtered_items = [item for item in dir_items if item.get('id') not in github_item_ids]

            if not filtered_items:
                continue

            # 尝试从路径提取项目名称
            project_name = self._extract_project_name_from_path(dir_key)

            # 计算置信度
            confidence = min(0.5 + len(filtered_items) * 0.1, 0.85)

            merged_clusters.append({
                'project_id': hashlib.md5(dir_key.encode()).hexdigest()[:8],
                'project_name': project_name,
                'description': f"Files from {dir_key}",
                'files': filtered_items,
                'tags': self._extract_tags(filtered_items),
                'summary': f"Project {project_name} with {len(filtered_items)} files",
                'confidence': confidence,
                'source': filtered_items[0].get('source', 'unknown') if filtered_items else 'unknown'
            })

        # 合并时间聚类（作为补充）
        time_clusters = []
        for time_key, time_items in clusters_by_time.items():
            # 排除已被其他聚类包含的文件
            existing_ids = {item.get('id') for cluster in merged_clusters for item in cluster.get('files', [])}
            remaining_items = [item for item in time_items if item.get('id') not in existing_ids]

            if len(remaining_items) >= 3:
                time_clusters.append({
                    'project_id': hashlib.md5(time_key.encode()).hexdigest()[:8],
                    'project_name': f"Project ({time_key})",
                    'description': f"Files modified in {time_key}",
                    'files': remaining_items,
                    'tags': ['time-based'],
                    'summary': f"Files from {time_key}",
                    'confidence': 0.4,  # 时间聚类置信度较低
                    'source': 'time'
                })

        merged_clusters.extend(time_clusters)

        return merged_clusters

    def _normalize_path(self, path: str) -> str:
        """标准化路径"""
        if not path:
            return 'unknown'

        # 移除扩展名得到目录
        if '.' in path and not path.endswith('/'):
            path = str(Path(path).parent)

        # 简化 home 目录
        path = path.replace('/Users/jinqianfei', '~')
        path = path.replace('/home/user', '~')

        return path

    def _extract_name_pattern(self, name: str) -> Optional[str]:
        """提取文件名模式用于相似匹配"""
        if not name:
            return None

        # 移除测试后缀和扩展名
        pattern = re.sub(r'(_test|_tests|_spec|_specs)$', '', name)
        pattern = re.sub(r'\.(py|js|ts|java|cpp|c|h|md|txt|json|yaml|yml)$', '', pattern)

        # 移除数字后缀
        pattern = re.sub(r'\d+$', '', pattern)

        return pattern if pattern != name else None

    def _extract_project_name_from_path(self, path: str) -> str:
        """从路径提取项目名称"""
        if not path or path == 'unknown':
            return 'Unknown Project'

        # 取最后一层目录名
        parts = path.strip('/').split('/')
        last_dir = parts[-1] if parts else 'Unknown'

        # 清理名称
        last_dir = re.sub(r'[_\-]*(test|tests|spec|specs)[_\-]*', '', last_dir, flags=re.IGNORECASE)
        last_dir = re.sub(r'[_\-]+', '_', last_dir)
        last_dir = last_dir.strip('_')

        return last_dir if last_dir else 'Unknown Project'

    def _extract_tags(self, items: List[dict]) -> List[str]:
        """从文件列表提取标签"""
        tags = set()
        ext_tags = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.md': 'documentation',
            '.txt': 'text',
            '.json': 'data',
            '.yaml': 'config',
            '.yml': 'config',
            '.sql': 'database',
            '.sh': 'shell',
        }

        for item in items:
            source = item.get('source', '')
            if source:
                tags.add(source)

            ext = item.get('ext', '')
            if ext and ext in ext_tags:
                tags.add(ext_tags[ext])

        return list(tags)[:10]  # 最多10个标签

    def save_projects(self, projects: List[dict]) -> bool:
        """
        保存项目到 footprint/projects/

        目录结构：
        footprint/projects/
        ├── project_001/
        │   ├── _index.md
        │   ├── metadata.json
        │   ├── docs/
        │   ├── code_snippets/
        │   └── data/
        └── project_002/
        """
        try:
            # 创建根目录
            self.projects_dir.mkdir(parents=True, exist_ok=True)

            for project in projects:
                project_id = project.get('project_id', hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:8])
                project_dir = self.projects_dir / project_id

                # 创建项目目录
                project_dir.mkdir(exist_ok=True)
                (project_dir / 'docs').mkdir(exist_ok=True)
                (project_dir / 'code_snippets').mkdir(exist_ok=True)
                (project_dir / 'data').mkdir(exist_ok=True)

                # 生成 _index.md
                index_content = self.generate_project_index(project)
                (project_dir / '_index.md').write_text(index_content, encoding='utf-8')

                # 生成 metadata.json
                metadata = {
                    'project_id': project_id,
                    'project_name': project.get('project_name', 'Unknown'),
                    'description': project.get('description', ''),
                    'tags': project.get('tags', []),
                    'confidence': project.get('confidence', 0.8),
                    'source': project.get('source', 'unknown'),
                    'file_count': len(project.get('files', [])),
                    'created_at': datetime.now().isoformat()
                }
                (project_dir / 'metadata.json').write_text(
                    json.dumps(metadata, ensure_ascii=False, indent=2),
                    encoding='utf-8'
                )

                # 保存文件内容片段
                for idx, file_item in enumerate(project.get('files', [])[:20]):  # 最多保存20个文件
                    file_name = file_item.get('name', f'file_{idx}')
                    content = file_item.get('content_preview', '')

                    if not content:
                        continue

                    # 根据来源决定保存位置
                    source = file_item.get('source', 'unknown')
                    ext = file_item.get('ext', '')

                    if ext in ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.sh', '.sql']:
                        save_dir = project_dir / 'code_snippets'
                        save_name = file_name
                    elif ext in ['.md', '.txt', '.doc', '.docx']:
                        save_dir = project_dir / 'docs'
                        save_name = file_name
                    else:
                        save_dir = project_dir / 'data'
                        save_name = file_name

                    # 保存内容片段
                    file_hash = hashlib.md5(file_item.get('id', file_name).encode()).hexdigest()[:8]
                    save_path = save_dir / f"{file_hash}_{save_name}"
                    save_path.write_text(content[:5000], encoding='utf-8')  # 限制大小

            return True

        except Exception as e:
            print(f"Failed to save projects: {e}")
            return False

    def generate_project_index(self, project: dict) -> str:
        """
        生成项目的 _index.md 内容

        格式：
        # Project Name

        ## Project Description
        ...

        ## Metadata
        - project_id: xxx
        - confidence: 0.95
        - created: 2026-06-03
        - source: local/github/feishu/openclaw
        - file_count: 5

        ## Tags
        - python
        - documentation

        ## Files
        - file1.py
        - file2.md
        """
        lines = [
            f"# {project.get('project_name', 'Unknown Project')}",
            "",
            "## Project Description",
            project.get('description', 'No description available'),
            "",
            "## Metadata",
            f"- **project_id:** {project.get('project_id', 'unknown')}",
            f"- **confidence:** {project.get('confidence', 0.8):.2f}",
            f"- **source:** {project.get('source', 'unknown')}",
            f"- **created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- **file_count:** {len(project.get('files', []))}",
            "",
        ]

        # Tags
        tags = project.get('tags', [])
        if tags:
            lines.append("## Tags")
            for tag in tags:
                lines.append(f"- {tag}")
            lines.append("")

        # Files
        files = project.get('files', [])
        if files:
            lines.append("## Files")
            for f in files:
                name = f.get('name', 'unknown')
                path = f.get('path', '')
                source = f.get('source', '')
                lines.append(f"- **{name}** ({source}) - `{path}`")
            lines.append("")

        return "\n".join(lines)

    def load_projects(self) -> List[dict]:
        """从文件系统加载已保存的项目"""
        projects = []

        if not self.projects_dir.exists():
            return projects

        for project_dir in self.projects_dir.iterdir():
            if not project_dir.is_dir():
                continue

            metadata_file = project_dir / 'metadata.json'
            if not metadata_file.exists():
                continue

            try:
                metadata = json.loads(metadata_file.read_text(encoding='utf-8'))

                # 加载文件列表
                files = []
                for subdir in ['docs', 'code_snippets', 'data']:
                    subdir_path = project_dir / subdir
                    if subdir_path.exists():
                        for f in subdir_path.iterdir():
                            if f.is_file():
                                files.append({
                                    'name': f.name,
                                    'path': str(f),
                                    'source': subdir
                                })

                metadata['files'] = files
                projects.append(metadata)

            except Exception as e:
                print(f"Failed to load project from {project_dir}: {e}")
                continue

        return projects

    def generate_cluster_summary(self, projects: List[dict]) -> str:
        """生成聚类总览 JSON"""
        summary = {
            'total_projects': len(projects),
            'projects': [
                {
                    'project_id': p.get('project_id'),
                    'project_name': p.get('project_name'),
                    'confidence': p.get('confidence'),
                    'file_count': len(p.get('files', []))
                }
                for p in projects
            ],
            'generated_at': datetime.now().isoformat()
        }

        return json.dumps(summary, ensure_ascii=False, indent=2)