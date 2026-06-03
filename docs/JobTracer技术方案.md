# JobTracer MVP 技术方案

> **产品名称：** JobTracer（求职足迹）
> **Version：** v1.0.3 | **状态：** 技术方案（基于 PRD v1.0.1 评审通过版）

---

## 文档信息

| 字段 | 内容 |
|------|------|
| **版本号** | v1.0.3 |
| **基于 PRD 版本** | v1.0.1 |
| **更新日期** | 2026-06-03 |
| **修改内容** | §7 开发计划精细化拆分：22 个任务卡（Sprint 1: 14个/Sprint 2: 10个/Sprint 3: 2个），合计 25.0 人天，P0/P1/P2 标注，附验收标准 | |

---

## 1. 技术架构

### 1.1 整体架构图

```
+------------------+  +------------------+  +------------------+
|  交互层(飞书Bot)   |  |  OpenClaw Agent  |  |  数据层           |
|  用户消息 -> 回复  |  |  JobTracer Skill |  |  ~/.jobtracer/    |
+------------------+  +------------------+  +------------------+
       |                      |                    |
       |              opencli boss                  |
       |              飞书MCP                        |
       |              GitHub API                     |
       |              本地文件                       |
       |              OpenClaw                       |
```

### 1.2 数据流设计

```
用户: 开始求职
        |
        v
+-------------------+
|  Step 1: 数字足迹扫描  |
|  (本地/飞书/GitHub/  |
|   OpenClaw)         |
+-------------------+
        |
        +-> footprint/projects/
        |
        v
+-------------------+     +--------------------+     +---------------------+
|  Step 2: 生成简历   | --> |  Step 3: BOSS搜索   | --> |  Step 4: 定制简历     |
|  resume.json       |     |  job-tracker.json  |     |  PDF + 发招呼        |
+-------------------+     +--------------------+     +---------------------+
```

### 1.3 工具层设计

| 工具 | 用途 | 认证方式 |
|------|------|---------|
| opencli boss | BOSS直聘搜索、发招呼 | Cookie（用户手动提供） |
| 飞书MCP | 读取飞书文档/知识库 | OAuth（飞书应用授权） |
| GitHub API | 读取项目内容 | Personal Access Token |
| 本地文件 | 扫描本地项目文档 | 无（本地路径访问） |
| OpenClaw | 读取MEMORY.md/workspace | 内置（直接读取文件） |

---

## 2. 核心模块详细设计

### 2.1 模块总览

| 模块 | 功能 | 优先级 | 对应 Step |
|------|------|--------|----------|
| a) 数字足迹扫描器 | 本地文件 + 飞书 + GitHub + OpenClaw | MVP P0 | Step 1 |
| b) 项目聚类引擎 | 基于ProjectTrace的Clustering Engine | MVP P0 | Step 1 |
| c) 简历生成器 | LLM + HTML模板 + PDF | MVP P0 | Step 2 |
| d) BOSS搜索模块 | opencli boss search | MVP P0 | Step 3 |
| e) JD匹配评分模块 | 关键词匹配 + 语义评分 | MVP P0 | Step 3 |
| f) 定制简历生成器 | 针对BOSS JD定制简历 | MVP P0 | Step 4 |
| g) BOSS发招呼模块 | opencli boss greet | MVP P1 | Step 4 |
| h) HR沟通引擎 | 意图分类 + 按意图分级回复 | Phase 2 | Step 5 |
| i) 面题库生成器 | JD + 简历生成面题 | Phase 2 | Step 7 |
| j) 数据存储模块 | ~/.jobtracer/ + SQLite | MVP P0 | 全局 |

---

### 2.2 模块 a) 数字足迹扫描器

#### 输入
- 用户触发信号（"开始求职"）
- 已授权的数据源列表

#### 输出
- `~/.jobtracer/footprint/summary.md` — 数字足迹摘要
- `~/.jobtracer/footprint/projects/` — 结构化项目文件夹
- `~/.jobtracer/footprint/skills_vector.json` — 技能向量

#### B1 冷启动/数字足迹为空处理（同步自 PRD v1.0.1 评审决策）

**冷启动最小路径（Resume Upload → LLM Parse → Structured Resume）：**

```
用户上传简历文档（PDF/DOCX）
        ↓
LLM 自动解析简历内容（PyMuPDF 提取文本 → LLM 结构化）
        ↓
生成结构化 resume.json
```

**增强选项（用户在简历上传后选择性触发）：**

| 增强项 | 触发时机 | 说明 |
|--------|---------|------|
| GitHub 扫描 | 简历上传后 | 读取 GitHub README/Issues 作为项目补充 |
| 飞书文档扫描 | 简历上传后 | 读取用户飞书工作区文档 |
| 本地文件扫描 | 简历上传后 | 扫描用户本地项目代码/文档 |
| OpenClaw MEMORY 扫描 | 简历上传后 | 读取 MEMORY.md 中的项目记录 |

> **决策说明：** 数字足迹扫描（GitHub/飞书/本地）作为增强选项，不在冷启动路径上；冷启动路径为简历上传 → LLM解析。

#### 实现方案

**1. 本地文件扫描**

```python
# scanner/local_scanner.py
import os, json
from pathlib import Path
from datetime import datetime

SUPPORTED_EXTENSIONS = {'.md', '.txt', '.doc', '.docx', '.pdf', '.xlsx', '.pptx'}
EXCLUDE_DIRS = {'node_modules', '.git', '__pycache__', '.venv', 'venv', '.idea'}

def scan_local_projects(root_path: str, user_id: str) -> dict:
    results = []
    root = Path(root_path).expanduser()
    
    for file_path in root.rglob('*'):
        if any(excluded in file_path.parts for excluded in EXCLUDE_DIRS):
            continue
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        if is_sensitive_file(file_path):
            continue
        
        content = read_file_content(file_path)
        if content:
            results.append({
                'path': str(file_path),
                'name': file_path.name,
                'ext': file_path.suffix,
                'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                'size': file_path.stat().st_size,
                'content_preview': content[:500],
                'content_hash': hash_content(content)
            })
    
    return {
        'user_id': user_id,
        'scan_time': datetime.now().isoformat(),
        'total_files': len(results),
        'files': results
    }

def is_sensitive_file(path: Path) -> bool:
    sensitive_names = {'password', 'secret', 'key', 'token', '.env', 'config'}
    name_lower = path.name.lower()
    return any(s in name_lower for s in sensitive_names)
```

**2. 飞书文档扫描（飞书MCP）**

```python
# scanner/feishu_scanner.py
async def scan_feishu_docs(user_id: str) -> dict:
    results = []
    
    docs = await feishu_doc_list(folder_token=None)
    for doc in docs:
        content = await feishu_doc_read(doc['token'])
        results.append({
            'source': 'feishu',
            'doc_id': doc['token'],
            'title': doc['title'],
            'type': doc['obj_type'],
            'content': content,
            'url': f"https://feishu.cn/docx/{doc['token']}"
        })
    
    wikis = await feishu_wiki_spaces()
    for space in wikis:
        nodes = await feishu_wiki_nodes(space['space_id'])
        for node in nodes:
            content = await feishu_wiki_get(node['node_token'])
            results.append({
                'source': 'feishu_wiki',
                'space_id': space['space_id'],
                'node_token': node['node_token'],
                'title': node['title'],
                'content': content,
                'url': f"https://feishu.cn/wiki/{node['node_token']}"
            })
    
    return {
        'user_id': user_id,
        'scan_time': datetime.now().isoformat(),
        'total_docs': len(results),
        'docs': results
    }
```

**3. GitHub扫描**

```python
# scanner/github_scanner.py
import httpx

GITHUB_API = "https://api.github.com"

async def scan_github(user_id: str, token: str) -> dict:
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    results = []
    
    async with httpx.AsyncClient() as client:
        repos_resp = await client.get(
            f"{GITHUB_API}/user/repos",
            headers=headers,
            params={"per_page": 30}
        )
        repos = repos_resp.json()
        
        for repo in repos:
            repo_name = repo['name']
            
            readme_resp = await client.get(
                f"{GITHUB_API}/repos/{repo_name}/readme",
                headers=headers
            )
            if readme_resp.status_code == 200:
                results.append({
                    'source': 'github',
                    'repo': repo_name,
                    'type': 'readme',
                    'content': decode_base64(readme_resp.json()['content'])
                })
            
            issues_resp = await client.get(
                f"{GITHUB_API}/repos/{repo_name}/issues",
                headers=headers,
                params={"state": "all", "per_page": 20}
            )
            if issues_resp.status_code == 200:
                for issue in issues_resp.json():
                    if 'pull_request' not in issue:
                        results.append({
                            'source': 'github',
                            'repo': repo_name,
                            'type': 'issue',
                            'title': issue['title'],
                            'body': issue['body'] or '',
                            'labels': [l['name'] for l in issue['labels']]
                        })
    
    return {
        'user_id': user_id,
        'scan_time': datetime.now().isoformat(),
        'total_items': len(results),
        'items': results
    }
```

**4. OpenClaw记忆扫描**

```python
# scanner/openclaw_scanner.py
import os

OPENCLAW_MEMORY_PATHS = [
    '~/.openclaw/workspace/MEMORY.md',
    '~/.openclaw/workspace/memory/',
    '~/.openclaw/workspace/',
]

def scan_openclaw(user_id: str) -> dict:
    results = []
    
    for path in OPENCLAW_MEMORY_PATHS:
        full_path = os.path.expanduser(path)
        if not os.path.exists(full_path):
            continue
        
        if os.path.isfile(full_path):
            content = read_file_content(full_path)
            results.append({
                'source': 'openclaw',
                'type': 'file',
                'path': path,
                'content': content
            })
        elif os.path.isdir(full_path):
            for root, dirs, files in os.walk(full_path):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for f in files:
                    if f.endswith(('.md', '.txt', '.json')):
                        file_path = os.path.join(root, f)
                        content = read_file_content(file_path)
                        results.append({
                            'source': 'openclaw',
                            'type': 'file',
                            'path': file_path,
                            'content': content
                        })
    
    return {
        'user_id': user_id,
        'scan_time': datetime.now().isoformat(),
        'total_files': len(results),
        'files': results
    }
```

**5. 扫描编排器（统一入口）**

```python
# scanner/footprint_scanner.py
import asyncio

class FootprintScanner:
    def __init__(self, config: dict):
        self.config = config
    
    async def scan_all(self, timeout_seconds: int = 300) -> dict:
        async with asyncio.timeout(timeout_seconds):
            tasks = []
            if self.config.get('local_enabled'):
                tasks.append(self._scan_local())
            if self.config.get('feishu_enabled'):
                tasks.append(self._scan_feishu())
            if self.config.get('github_enabled'):
                tasks.append(self._scan_github())
            if self.config.get('openclaw_enabled'):
                tasks.append(self._scan_openclaw())
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            merged = {'local': None, 'feishu': None, 'github': None, 'openclaw': None}
            for i, result in enumerate(results):
                key = list(merged.keys())[i]
                if isinstance(result, Exception):
                    merged[key] = {'error': str(result)}
                else:
                    merged[key] = result
            return merged
    
    async def _scan_local(self):
        from scanner.local_scanner import scan_local_projects
        root = self.config.get('local_root', '~')
        return scan_local_projects(root, self.config.get('user_id', ''))
    
    async def _scan_feishu(self):
        from scanner.feishu_scanner import scan_feishu_docs
        return await scan_feishu_docs(self.config.get('user_id', ''))
    
    async def _scan_github(self):
        from scanner.github_scanner import scan_github
        token = self.config.get('github_token', '')
        return await scan_github(self.config.get('user_id', ''), token)
    
    async def _scan_openclaw(self):
        from scanner.openclaw_scanner import scan_openclaw
        return scan_openclaw(self.config.get('user_id', ''))
```

#### 关键技术选型

| 技术 | 选型 | 说明 |
|------|------|------|
| 文件扫描 | Python pathlib | 跨平台，递归扫描 |
| PDF读取 | PyMuPDF (fitz) | 支持文本提取，不依赖外部服务 |
| Excel读取 | openpyxl | 轻量级Excel解析 |
| 飞书MCP | 官方MCP Server | 通过MCP协议访问 |
| GitHub API | httpx + 官方REST API | 异步HTTP客户端 |
| 并行扫描 | asyncio + asyncio.timeout | 多数据源并行扫描，超时控制 |

#### 2.2.1 数字足迹扫描顺序（MVP Phase 1）


**MVP 阶段扫描优先级（冷启动路径 → 增强路径）：**

| 优先级 | 数据源 | 说明 | 冷启动可用 |
|--------|--------|------|-----------|
| P0 | **简历上传（PDF/DOCX）** | 用户上传简历 → LLM自动解析 → resume.json | ✅ |
| P1 | OpenClaw MEMORY | 扫描 ~/.openclaw/workspace/MEMORY.md 和 memory/ | ✅（自动） |
| P2 | GitHub | 扫描用户个人仓库（README/Issues/代码） | ✅（需Token） |
| P3 | 本地文件 | 扫描用户本地项目代码/文档（默认 ~，可配置） | ❌（耗时长） |
| P4 | 飞书文档 | 扫描飞书工作区文档/知识库 | ❌（需OAuth） |

**扫描失败降级路径：**


| 场景 | 降级处理 |
|------|---------|
| 某平台 Token 无效 | 跳过该平台，继续扫描下一优先级；通知用户「XX平台连接失败」 |
| 本地文件扫描超时（>60s） | 返回已扫描结果，提示用户「本地扫描超时，可手动指定目录」 |
| GitHub API 限流 | 降级为只读 README，其他内容延迟扫描 |
| 飞书 OAuth 过期 | 跳过飞书扫描，提示用户重新授权 |

**扫描结果组织结构：**


```
~/.jobtracer/footprint/
├── summary.md                  # 数字足迹摘要（供用户预览）
├── skills_vector.json         # 技能向量
└── projects/                   # 按项目组织的文件夹
    ├── {project_id}/          # 项目Hash ID
    │   ├── _index.md         # 项目索引（含描述、文件列表）
    │   ├── metadata.json      # 项目元数据（来源、置信度、创建时间）
    │   ├── docs/              # 文档片段
    │   │   └── {file_hash}.md
    │   └── code_snippets/     # 代码片段（若有）
    │       └── {file_hash}.txt
    └── _cluster_summary.json  # 聚类总览（各项目名称 + 置信度）
```


---



### 2.3 模块 b) 项目聚类引擎

#### 输入
- 数字足迹扫描原始数据（来自模块 a）

#### 输出
- `~/.jobtracer/footprint/projects/` — 按项目组织的结构化文件夹
- 每个项目包含：`_index.md`, `docs/`, `code_snippets/`, `metadata.json`

#### 实现方案

```python
# clustering/engine.py
import json, hashlib
from pathlib import Path
from datetime import datetime

class ProjectClusteringEngine:
    def __init__(self, llm_client):
        self.llm = llm_client
    
    def cluster(self, scan_results: dict) -> list:
        all_items = []
        for source, data in scan_results.items():
            if data is None or (isinstance(data, dict) and 'error' in data):
                continue
            if source == 'local':
                all_items.extend(self._process_local(data))
            elif source == 'feishu':
                all_items.extend(self._process_feishu(data))
            elif source == 'github':
                all_items.extend(self._process_github(data))
            elif source == 'openclaw':
                all_items.extend(self._process_openclaw(data))
        
        return self._llm_cluster(all_items)
    
    def _llm_cluster(self, items: list) -> list:
        items_summary = [
            {
                'id': item.get('id', idx),
                'name': item.get('name') or item.get('title', ''),
                'content_preview': (item.get('content_preview') or item.get('content', ''))[:200],
                'source': item.get('source', '')
            }
            for idx, item in enumerate(items)
        ]
        
        prompt = "You are a project clustering assistant. Group files by project.

"
        prompt += "Rules:
"
        prompt += "1. Related content topics -> same project
"
        prompt += "2. Same GitHub repo -> same project
"
        prompt += "3. Same Feishu space -> same project

"
        prompt += "Output JSON array: [project_name, project_description, items[], confidence]

"
        prompt += "Files to classify:
" + json.dumps(items_summary, ensure_ascii=False, indent=2)
        
        response = self.llm.generate(prompt, schema='json')
        return json.loads(response)
    
    def _process_local(self, data: dict) -> list:
        return [{'id': f['path'], 'name': f['name'],
                 'content_preview': f.get('content_preview', ''), 'source': 'local'}
                for f in data.get('files', [])]
    
    def _process_feishu(self, data: dict) -> list:
        return [{'id': doc['doc_id'], 'name': doc['title'],
                 'content_preview': doc.get('content', '')[:200], 'source': 'feishu'}
                for doc in data.get('docs', [])]
    
    def _process_github(self, data: dict) -> list:
        return [{'id': item['repo'] + '_' + item.get('type','file') + '_' + item.get('title',''),
                 'name': item.get('title') or item.get('name', ''),
                 'content_preview': item.get('body', item.get('content', ''))[:200],
                 'source': 'github'}
                for item in data.get('items', [])]
    
    def _process_openclaw(self, data: dict) -> list:
        return [{'id': f['path'], 'name': Path(f['path']).name,
                 'content_preview': f.get('content', '')[:200], 'source': 'openclaw'}
                for f in data.get('files', [])]
    
    def generate_project_structure(self, clusters: list) -> list:
        root = Path('~/.jobtracer/footprint/projects').expanduser()
        root.mkdir(parents=True, exist_ok=True)
        
        output = []
        for cluster in clusters:
            project_id = hashlib.md5(cluster['project_name'].encode()).hexdigest()[:8]
            project_dir = root / project_id
            project_dir.mkdir(exist_ok=True)
            
            index_lines = ['# ' + cluster['project_name'], '', '## Project Description',
                           cluster['project_description'], '', '## Metadata',
                           '- project_id: ' + project_id,
                           '- confidence: ' + str(cluster['confidence']),
                           '- created: ' + datetime.now().isoformat(), '', '## Files', '']
            for item_id in cluster.get('items', []):
                index_lines.append('- ' + item_id)
            
            (project_dir / '_index.md').write_text('
'.join(index_lines))
            (project_dir / 'docs').mkdir(exist_ok=True)
            (project_dir / 'code_snippets').mkdir(exist_ok=True)
            
            metadata = {
                'project_id': project_id,
                'project_name': cluster['project_name'],
                'description': cluster['project_description'],
                'confidence': cluster['confidence'],
                'items': cluster.get('items', []),
                'created_at': datetime.now().isoformat()
            }
            (project_dir / 'metadata.json').write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2)
            )
            
            output.append({
                'project_id': project_id,
                'project_name': cluster['project_name'],
                'path': str(project_dir)
            })
        
        return output
```


### 2.4 模块 c) 简历生成器

#### 输入
- `~/.jobtracer/footprint/projects/` — 结构化项目数据
- `~/.jobtracer/memory/preferences.json` — 用户偏好（可选）

#### 输出
- `~/.jobtracer/memory/resume.json` — 结构化简历
- 用户可预览的简历 HTML

#### 实现方案

```python
# resume/generator.py
import json
from pathlib import Path
from datetime import datetime

class ResumeGenerator:
    def __init__(self, llm_client):
        self.llm = llm_client
    
    def generate(self, projects: list, user_profile: dict = None) -> dict:
        project_contents = []
        for proj in projects:
            index_md = Path(proj['path']) / '_index.md'
            metadata_json = Path(proj['path']) / 'metadata.json'
            
            if index_md.exists():
                project_contents.append({
                    'name': proj['project_name'],
                    'index': index_md.read_text(),
                    'metadata': json.loads(metadata_json.read_text()) if metadata_json.exists() else {}
                })
        
        prompt = "You are a professional resume writer. Generate a technical resume.

"
        prompt += "Requirements:
"
        prompt += "1. Extract key contributions and quantified results
"
        prompt += "2. Use STAR format for project descriptions
"
        prompt += "3. Highlight technical highlights and business value
"
        prompt += "4. Use action verbs, be concise and professional

"
        prompt += "Project Experience:
" + json.dumps(project_contents, ensure_ascii=False, indent=2) + "

"
        prompt += "User Profile:
" + json.dumps(user_profile or {}, ensure_ascii=False, indent=2) + "

"
        prompt += "Output JSON with: version, name, contact:{phone,email,location}, "
        prompt += "summary, skills:{technical:[],soft:[]}, "
        prompt += "experience:[{company,title,duration,highlights}], "
        prompt += "projects:[{name,role,description,metrics}], "
        prompt += "education:{school,degree,major,graduation_year}, "
        prompt += "meta:{generated_from,user_confirmed,generated_at}
"
        prompt += "Fill all fields."
        
        response = self.llm.generate(prompt, schema='json')
        resume = json.loads(response)
        resume['meta'] = {
            'generated_from': 'digital_footprint',
            'user_confirmed': False,
            'generated_at': datetime.now().isoformat()
        }
        return resume
    
    def save(self, resume: dict, path: str = '~/.jobtracer/memory/resume.json'):
        path = Path(path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(resume, ensure_ascii=False, indent=2))
    
    def generate_html(self, resume: dict) -> str:
        skills_html = ' '.join([
            '<span>' + s + '</span>' for s in resume.get('skills', {}).get('technical', [])
        ])
        
        projects_html = ''
        for proj in resume.get('projects', []):
            metrics_html = ''
            if proj.get('metrics'):
                metrics_html = '<p class="metrics">Result: ' + proj['metrics'] + '</p>'
            projects_html += '<div class="project"><h3>' + proj.get('name', '') + ' '
            projects_html += '<small style="color:#666">| ' + proj.get('role', 'Member') + '</small></h3>'
            projects_html += '<p>' + proj.get('description', '') + '</p>' + metrics_html + '</div>'
        
        contact_parts = [
            resume.get('contact', {}).get('phone', ''),
            resume.get('contact', {}).get('email', ''),
            resume.get('contact', {}).get('location', '')
        ]
        contact_html = ' | '.join([c for c in contact_parts if c])
        
        edu = resume.get('education', {})
        education_html = ''
        if edu:
            education_html = edu.get('school', '') + ' | ' + edu.get('degree', '') + ' | ' + edu.get('major', '')
        
        html = '<!DOCTYPE html><html><head><meta charset="UTF-8">'
        html += '<style>body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;max-width:800px;margin:40px auto;padding:20px;line-height:1.6}'
        html += 'h1{border-bottom:2px solid #333;padding-bottom:10px}h2{color:#2563eb;margin-top:30px}'
        html += '.contact{color:#666;font-size:14px;margin-bottom:20px}'
        html += '.skills span{background:#e5e7eb;padding:4px 12px;border-radius:16px;margin:4px;display:inline-block;font-size:14px}'
        html += '.project{margin-bottom:20px;padding:15px;background:#f9fafb;border-radius:8px}'
        html += '.project h3{margin:0 0 8px 0}.metrics{color:#059669;font-weight:600}</style>'
        html += '</head><body>'
        html += '<h1>' + resume.get('name', 'Name') + '</h1>'
        html += '<div class="contact">' + contact_html + '</div>'
        html += '<h2>Summary</h2><p>' + resume.get('summary', '') + '</p>'
        html += '<h2>Technical Skills</h2><div class="skills">' + skills_html + '</div>'
        html += '<h2>Project Experience</h2>' + projects_html
        html += '<h2>Education</h2><p>' + education_html + '</p></body></html>'
        return html
```


### 2.5 模块 d) BOSS搜索模块

#### 输入
- `resume.json` 中的技能关键词 + 项目关键词
- 用户偏好（城市、薪资、经验等）

#### 输出
- `~/.jobtracer/jobs/jd_cache/` — JD详情缓存
- `~/.jobtracer/jobs/job-tracker.json` — 职位列表

#### 实现方案

```python
# boss/search.py
import subprocess, json, re, os
from pathlib import Path
from datetime import datetime

class BOSSSearcher:
    def __init__(self, cookie: str = None):
        self.cookie = cookie or os.environ.get('BOSS_COOKIE', '')
        self.cache_dir = Path('~/.jobtracer/jobs/jd_cache').expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def search(self, keywords: list, city: str = 'Beijing', 
               experience: str = '', salary: str = '',
               page: int = 1, limit: int = 15) -> list:
        query = ' '.join(keywords[:3])
        
        cmd = [
            'opencli', 'boss', 'search', query,
            '--city', city,
            '--page', str(page),
            '--limit', str(limit),
            '-f', 'json'
        ]
        
        if experience:
            cmd.extend(['--experience', experience])
        if salary:
            cmd.extend(['--salary', salary])
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            raise Exception('BOSS search failed: ' + result.stderr)
        
        jobs = json.loads(result.stdout)
        normalized_jobs = []
        
        for job in jobs:
            job_id = 'boss_' + job.get('security_id', '')
            normalized = {
                'job_id': job_id,
                'platform': 'boss',
                'title': job.get('name', ''),
                'company': job.get('company', ''),
                'location': job.get('area', ''),
                'salary': self._parse_salary(job.get('salary', '')),
                'experience': job.get('experience', ''),
                'degree': job.get('degree', ''),
                'skills': job.get('skills', []),
                'boss_name': job.get('boss', ''),
                'boss_online': job.get('bossOnline', False),
                'security_id': job.get('security_id', ''),
                'url': job.get('url', ''),
                'created_at': datetime.now().isoformat(),
                'status': 'new'
            }
            normalized_jobs.append(normalized)
            self._cache_job(job_id, job)
        
        return normalized_jobs
    
    def get_job_detail(self, security_id: str) -> dict:
        cache_file = self.cache_dir / (security_id + '.json')
        if cache_file.exists():
            return json.loads(cache_file.read_text())
        
        cmd = ['opencli', 'boss', 'detail', security_id, '-f', 'json']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            raise Exception('BOSS detail failed: ' + result.stderr)
        
        return json.loads(result.stdout)
    
    def _cache_job(self, job_id: str, job_data: dict):
        cache_file = self.cache_dir / (job_id + '.json')
        cache_file.write_text(json.dumps(job_data, ensure_ascii=False))
    
    def _parse_salary(self, salary_text: str) -> dict:
        match = re.search(r'(\d+)-(\d+)(K|k|wan)', salary_text)
        if match:
            min_sal, max_sal, unit = match.groups()
            multiplier = 1000 if unit.lower() in ('k',) else 10000
            return {
                'min': int(min_sal) * multiplier,
                'max': int(max_sal) * multiplier,
                'raw': salary_text
            }
        return {'min': 0, 'max': 0, 'raw': salary_text}
```


### 2.6 模块 e) JD匹配评分模块

#### 输入
- `resume.json` — 用户简历
- 职位 JD 内容

#### 输出
- 每个职位的匹配度评分（0-100）
- 关联项目列表

#### 实现方案

```python
# matching/scorer.py
import json, re

class JDMatcher:
    def __init__(self, llm_client=None):
        self.llm = llm_client
    
    def score(self, resume: dict, job: dict) -> dict:
        scores = {}
        details = {}
        
        skill_score, skill_details = self._score_skills(resume, job)
        scores['skill'] = skill_score
        details['skill'] = skill_details
        
        project_score, project_details = self._score_projects(resume, job)
        scores['project'] = project_score
        details['project'] = project_details
        
        exp_score, exp_details = self._score_experience(resume, job)
        scores['experience'] = exp_score
        details['experience'] = exp_details
        
        salary_score, salary_details = self._score_salary(resume, job)
        scores['salary'] = salary_score
        details['salary'] = salary_details
        
        total_score = scores['skill'] * 0.4 + scores['project'] * 0.2 + scores['experience'] * 0.2 + scores['salary'] * 0.2
        
        related_projects = self._find_related_projects(resume, job)
        
        return {
            'total_score': round(total_score, 1),
            'breakdown': scores,
            'details': details,
            'related_projects': related_projects
        }
    
    def _score_skills(self, resume: dict, job: dict) -> tuple:
        resume_skills = set([s.lower() for s in resume.get('skills', {}).get('technical', [])])
        job_skills = set([s.lower() for s in job.get('skills', [])])
        
        if not job_skills:
            return 50, {'reason': 'No skill requirements in JD'}
        
        matched = resume_skills & job_skills
        score = (len(matched) / len(job_skills)) * 100
        
        return round(score, 1), {'matched': list(matched), 'job_required': list(job_skills)}
    
    def _score_projects(self, resume: dict, job: dict) -> tuple:
        project_keywords = self._extract_project_keywords(resume)
        job_domain = self._extract_job_domain(job)
        
        overlap = project_keywords & job_domain
        score = (len(overlap) / max(len(job_domain), 1)) * 100
        
        return round(score, 1), {'overlap': list(overlap), 'job_domain': list(job_domain)}
    
    def _extract_project_keywords(self, resume: dict) -> set:
        keywords = set()
        for proj in resume.get('projects', []):
            text = proj.get('description', '') + ' ' + proj.get('name', '')
            words = re.findall(r'[\u4e00-\u9fa5a-zA-Z]{2,}', text)
            keywords.update([w.lower() for w in words if len(w) > 1])
        return keywords
    
    def _extract_job_domain(self, job: dict) -> set:
        text = job.get('title', '') + ' ' + job.get('jd_summary', '') + ' ' + ' '.join(job.get('skills', []))
        words = re.findall(r'[\u4e00-\u9fa5a-zA-Z]{2,}', text)
        return set([w.lower() for w in words if len(w) > 1])
    
    def _score_experience(self, resume: dict, job: dict) -> tuple:
        exp_text = job.get('experience', '')
        
        exp_map = {
            'student': 0, 'fresh': 0, 'any': 0,
            'less_than_1': 1, '1-3': 2, '3-5': 4, '5-10': 7, 'above_10': 10
        }
        
        exp_map_cn = {
            '在校生': 0, '应届生': 0, '经验不限': 0,
            '1年以内': 1, '1-3年': 2, '3-5年': 4, '5-10年': 7, '10年以上': 10
        }
        
        required_years = exp_map_cn.get(exp_text, 3)
        resume_years = self._estimate_resume_years(resume)
        
        if resume_years >= required_years:
            score = 100
        else:
            score = (resume_years / required_years) * 100 if required_years > 0 else 100
        
        return round(score, 1), {'required': exp_text, 'required_years': required_years, 'resume_years': resume_years}
    
    def _estimate_resume_years(self, resume: dict) -> int:
        return len(resume.get('experience', [])) * 2 + len(resume.get('projects', []))
    
    def _score_salary(self, resume: dict, job: dict) -> tuple:
        job_salary = job.get('salary', {})
        pref_salary = resume.get('preferences', {}).get('expected_salary', {})
        
        if not job_salary.get('min') or not pref_salary.get('min'):
            return 50, {'reason': 'Missing salary data'}
        
        if job_salary['min'] <= pref_salary['max']:
            return 100, {}
        else:
            overlap = (pref_salary['max'] - job_salary['min']) / job_salary['min']
            return max(0, round(overlap * 100, 1)), {}
    
    def _find_related_projects(self, resume: dict, job: dict) -> list:
        job_skills = set([s.lower() for s in job.get('skills', [])])
        job_domain = self._extract_job_domain(job)
        
        related = []
        for proj in resume.get('projects', []):
            proj_text = (proj.get('description', '') + ' ' + proj.get('name', '')).lower()
            proj_words = set(re.findall(r'[\u4e00-\u9fa5a-zA-Z]{2,}', proj_text))
            
            skill_overlap = len(proj_words & job_skills)
            domain_overlap = len(proj_words & job_domain)
            
            if skill_overlap >= 1 or domain_overlap >= 2:
                related.append({
                    'name': proj.get('name', ''),
                    'role': proj.get('role', ''),
                    'match_score': skill_overlap * 10 + domain_overlap * 5
                })
        
        related.sort(key=lambda x: x['match_score'], reverse=True)
        return related[:3]
```


### 2.7 模块 f) 定制简历生成器

#### 输入
- `resume.json` — 基础简历
- 目标 JD 内容
- 关联项目列表

#### 输出
- `~/.jobtracer/customized_resumes/{jd_id}/customized.pdf` — 定制简历 PDF
- `~/.jobtracer/customized_resumes/{jd_id}/customized.html` — HTML版本

#### 实现方案

```python
# resume/customizer.py
import json
from pathlib import Path
from datetime import datetime

class ResumeCustomizer:
    def __init__(self, llm_client):
        self.llm = llm_client
    
    def customize(self, resume: dict, job: dict, related_projects: list) -> dict:
        job_skills = set(job.get('skills', []))
        
        prompt = "You are a resume customization specialist.

"
        prompt += "Given a base resume and a target job description, "
        prompt += "customize the resume to highlight relevant experience.

"
        prompt += "Rules:
"
        prompt += "1. Prioritize projects/skills that match the JD
"
        prompt += "2. De-emphasize irrelevant experience
"
        prompt += "3. Use keywords from the JD in descriptions
"
        prompt += "4. Keep all information truthful, do not fabricate

"
        prompt += "Base Resume:
" + json.dumps(resume, ensure_ascii=False, indent=2) + "

"
        prompt += "Target JD:
" + json.dumps(job, ensure_ascii=False, indent=2) + "

"
        prompt += "Related Projects:
" + json.dumps(related_projects, ensure_ascii=False, indent=2) + "

"
        prompt += "Output customized resume JSON (same schema as base resume)."
        
        customized = json.loads(self.llm.generate(prompt, schema='json'))
        return customized
    
    def save(self, customized: dict, jd_id: str) -> Path:
        output_dir = Path('~/.jobtracer/customized_resumes').expanduser() / jd_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        html_path = output_dir / 'customized.html'
        html_path.write_text(self._generate_html(customized))
        
        return output_dir
    
    def _generate_html(self, resume: dict) -> str:
        skills_html = ' '.join(['<span>' + s + '</span>' for s in resume.get('skills', {}).get('technical', [])])
        
        projects_html = ''
        for proj in resume.get('projects', []):
            metrics_html = ''
            if proj.get('metrics'):
                metrics_html = '<p class="metrics">Result: ' + proj['metrics'] + '</p>'
            projects_html += '<div class="project"><h3>' + proj.get('name', '') + ' '
            projects_html += '<small style="color:#666">| ' + proj.get('role', '') + '</small></h3>'
            projects_html += '<p>' + proj.get('description', '') + '</p>' + metrics_html + '</div>'
        
        contact_parts = [resume.get('contact', {}).get('phone', ''),
                          resume.get('contact', {}).get('email', ''),
                          resume.get('contact', {}).get('location', '')]
        contact_html = ' | '.join([c for c in contact_parts if c])
        
        edu = resume.get('education', {})
        education_html = ''
        if edu:
            education_html = edu.get('school', '') + ' | ' + edu.get('degree', '') + ' | ' + edu.get('major', '')
        
        html = '<!DOCTYPE html><html><head><meta charset="UTF-8">'
        html += '<style>body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;max-width:800px;margin:40px auto;padding:20px;line-height:1.6}'
        html += 'h1{border-bottom:2px solid #333;padding-bottom:10px}h2{color:#2563eb;margin-top:30px}'
        html += '.contact{color:#666;font-size:14px;margin-bottom:20px}'
        html += '.skills span{background:#e5e7eb;padding:4px 12px;border-radius:16px;margin:4px;display:inline-block;font-size:14px}'
        html += '.project{margin-bottom:20px;padding:15px;background:#f9fafb;border-radius:8px}'
        html += '.project h3{margin:0 0 8px 0}.metrics{color:#059669;font-weight:600}</style>'
        html += '</head><body>'
        html += '<h1>' + resume.get('name', 'Name') + '</h1>'
        html += '<div class="contact">' + contact_html + '</div>'
        html += '<h2>Summary</h2><p>' + resume.get('summary', '') + '</p>'
        html += '<h2>Technical Skills</h2><div class="skills">' + skills_html + '</div>'
        html += '<h2>Project Experience</h2>' + projects_html
        html += '<h2>Education</h2><p>' + education_html + '</p></body></html>'
        return html
    
    def to_pdf(self, html_path: Path, output_path: Path = None):
        try:
            import weasyprint
            if output_path is None:
                output_path = html_path.with_suffix('.pdf')
            weasyprint.HTML(filename=str(html_path)).write_pdf(str(output_path))
            return output_path
        except ImportError:
            raise Exception('WeasyPrint not installed, please run: pip install weasyprint')
```


### 2.8 模块 g) BOSS发招呼模块

#### 输入
- 目标候选人 UID
- 定制招呼语
- 职位 ID

#### 输出
- 发招呼结果（成功/失败）
- 飞书通知用户

#### 实现方案

```python
# boss/greet.py
import subprocess
import json
from datetime import datetime

class BOSSGreeting:
    def __init__(self, cookie: str = None):
        self.cookie = cookie
    
    def greet(self, uid: str, security_id: str = None, 
              job_id: str = None, text: str = None) -> dict:
        cmd = ['opencli', 'boss', 'greet', uid]
        
        if security_id:
            cmd.extend(['--security-id', security_id])
        if job_id:
            cmd.extend(['--job-id', job_id])
        if text:
            cmd.extend(['--text', text])
        
        cmd.extend(['-f', 'json'])
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        response_time = datetime.now().isoformat()
        
        if result.returncode != 0:
            return {
                'success': False,
                'uid': uid,
                'error': result.stderr,
                'response_time': response_time
            }
        
        try:
            output = json.loads(result.stdout)
            return {
                'success': True,
                'uid': uid,
                'output': output,
                'response_time': response_time
            }
        except json.JSONDecodeError:
            return {
                'success': False,
                'uid': uid,
                'error': 'Failed to parse response',
                'raw_output': result.stdout,
                'response_time': response_time
            }
    
    def greet_batch(self, candidates: list, greeting_template: str = None) -> list:
        results = []
        for candidate in candidates:
            uid = candidate.get('uid')
            security_id = candidate.get('security_id')
            job_id = candidate.get('job_id')
            
            text = greeting_template
            if text is None and candidate.get('name'):
                text = 'Hello ' + candidate.get('name') + ', I am interested in this position.'
            
            result = self.greet(uid, security_id, job_id, text)
            results.append(result)
        
        return results
    
    def generate_greeting_text(self, resume: dict, job: dict) -> str:
        prompt = "Generate a brief, professional greeting message for BOSS zhipin.

"
        prompt += "My resume highlights:
"
        prompt += "- Skills: " + ', '.join(resume.get('skills', {}).get('technical', [])[:5]) + "
"
        prompt += "- Experience years: " + str(len(resume.get('experience', []))) + "

"
        prompt += "Job title: " + job.get('title', '') + "
"
        prompt += "Job company: " + job.get('company', '') + "
"
        prompt += "Job skills: " + ', '.join(job.get('skills', [])[:5]) + "

"
        prompt += "Generate a 2-3 sentence greeting in Chinese that:
"
        prompt += "1. Briefly mentions relevant experience
"
        prompt += "2. Shows genuine interest in the position
"
        prompt += "3. Is under 100 characters"
        
        return self.llm.generate(prompt)
```

#### BOSS直聘集成方案（opencli）

| 功能 | 命令 | 参数 |
|------|------|------|
| 搜索职位 | `opencli boss search <query>` | `--city`, `--experience`, `--salary`, `--page`, `--limit` |
| 职位详情 | `opencli boss detail <security_id>` | 无额外参数 |
| 发招呼 | `opencli boss greet <uid>` | `--security-id`, `--job-id`, `--text` |
| 查看聊天 | `opencli boss chatlist` | 无参数 |
| 发消息 | `opencli boss send <uid>` | `--text` |

**Cookie 管理：**
- Cookie 存储在 `~/.jobtracer/cookies/boss.json`
- 用户首次使用时需提供 Cookie
- Cookie 有效期通常为 30 天，过期后需重新提供

#### A1 平台登录失效处理（同步自 PRD v1.0.1 评审决策）

| 场景 | 处理策略 |
|------|---------|
| Cookie 过期或无效 | **等待用户手动重新授权**，而非自动降级切换平台 |
| 单平台失效 | **不影响其他平台**继续工作（如 BOSS 失效，飞书/GitHub 扫描仍正常） |
| opencli 不可用 | 提示用户提供新 Cookie；降级为「生成招呼语 + 手动复制」模式 |

> **决策说明：** PRD v1.0.1 评审明确——不实现自动降级切换平台；单平台失效由用户手动授权恢复。

#### C2 投递过程中断处理（同步自 PRD v1.0.1 评审决策）

BOSS 发招呼失败时，按以下顺序处理：

1. **重试**（指数退避，最多 3 次，间隔 2s → 4s → 8s）
2. **记录失败原因**到 `~/.jobtracer/logs/greet_failures.log`
3. **提供手动补救入口**：
   - 飞书卡片显示「重新发送」按钮（点击触发重试）
   - 同时提供「复制招呼语」按钮，用户可手动粘贴到 BOSS App

**手动补救飞书卡片示例：**
```
标题：发招呼失败 - {公司名}
内容：
- 失败原因：{error_message}
- 招呼语：{greeting_text}
按钮：
[重新发送] [复制招呼语]
```

> **决策说明：** PRD v1.0.1 评审明确——C2 场景需包含「重新发送」按钮 + 手动复制入口。



### 2.9 模块 h) HR沟通引擎

#### 输入
- HR 消息内容
- 用户简历和求职状态

#### 输出
- 回复建议列表（按意图分级）
- 自动发送或待确认

#### 实现方案

```python
# hr/engine.py
import json

class HREngine:
    pass  # See detailed implementation below
```

**意图分类Prompt：**

```
Classify the intent of this HR message.

Intents:
- initial_contact: First time HR reaches out
- project_inquiry: Asking about project experience
- skill_inquiry: Asking about technical stack
- city_inquiry: Asking about preferred city
- contact_inquiry: Asking for contact info
- salary_inquiry: Asking about salary expectations
- interview_invite: Inviting to interview
- offer_extended: Offering a position
- rejection: Rejecting application
- follow_up: Following up
- availability: Asking about availability
- other: Does not fit above

Message: {message}

Output: {"intent": "name", "confidence": 0.95}
```

**意图分级处理策略：**

| 意图 | 处理方式 | 确认？ |
|------|---------|--------|
| initial_contact | 自动生成 + 发送 | No |
| availability | 自动发送 | No |
| contact_inquiry | 自动发送 | No |
| project_inquiry | 自动发送 | No |
| skill_inquiry | 自动发送 | No |
| city_inquiry | 自动发送 | No |
| interview_invite | 生成 + 确认时间 | Yes |
| salary_inquiry | 生成 + 确认数字 | Yes |
| offer_extended | 生成 + 确认条款 | Yes |
| rejection | 生成 + 确认决定 | Yes |
| other | 自动发送 | No |


### 2.10 模块 i) 面题库生成器

#### 输入
- 目标职位 JD
- 用户简历

#### 输出
- `interview_prep.json` — 面题库
- 飞书文档格式

#### 实现方案

面题库生成Prompt模板：

```
Generate personalized interview questions based on resume and job description.

Resume:
{resume_json}

Job Description:
{job_json}

Generate JSON with categories:
- basic_knowledge: Fundamental questions based on job type
- technical: Technical questions based on required skills
- behavioral: STAR-format questions based on project experience
- reverse: Good questions to ask the interviewer

Each question: question, answer_direction, related_skill
```

输出JSON格式：

```json
{
  "job_id": "boss_xxx",
  "basic_knowledge": [
    {"question": "...", "answer_direction": "...", "related_skill": "..."}
  ],
  "technical": [
    {"question": "...", "answer_direction": "...", "related_skill": "..."}
  ],
  "behavioral": [
    {"question": "...", "situation": "...", "task": "...", "action": "...", "result": "..."}
  ],
  "reverse": ["...", "..."],
  "status": "generated",
  "created_at": "2026-06-02T12:00:00Z"
}
```


### 2.11 模块 j) 数据存储模块

#### 输入
- 各模块产生的数据
- 用户操作产生的状态变更

#### 输出
- 持久化的 JSON 文件
- SQLite 数据库（大数据量场景）

#### 目录结构

~/.jobtracer/
  memory/
    state.json              # 求职状态
    resume.json             # 结构化简历
    preferences.json        # 用户偏好
    hr_conversations.json   # HR沟通记录
    job-tracker.json        # 职位追踪
  footprint/
    summary.md              # 数字足迹摘要
    skills_vector.json      # 技能向量
    projects/               # 按项目组织的文档
      {project_id}/
        _index.md
        metadata.json
        docs/
        code_snippets/
  jobs/
    job-tracker.json        # 职位列表（JSON备份）
    jd_cache/               # JD详情缓存
  customized_resumes/
    {jd_id}/
      customized.html
      customized.pdf
  interview_prep/
    {job_id}/
      prep.json
      prep.md
  cookies/
    boss.json               # BOSS登录Cookie
  reports/
    career_review_*.md      # 求职复盘报告
  logs/
    scan_*.log              # 扫描日志

#### SQLite Schema（Phase 2）

-- jobs表
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    title TEXT,
    company TEXT,
    location TEXT,
    salary_min INTEGER,
    salary_max INTEGER,
    match_score REAL,
    jd_summary TEXT,
    status TEXT DEFAULT 'new',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    applied_at TIMESTAMP,
    related_projects TEXT
);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_platform ON jobs(platform);
CREATE INDEX idx_jobs_match_score ON jobs(match_score);

-- hr_conversations表
CREATE TABLE hr_conversations (
    id TEXT PRIMARY KEY,
    job_id TEXT REFERENCES jobs(id),
    direction TEXT,
    intent TEXT,
    message_preview TEXT,
    message_full TEXT,
    reply_sent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_conv_job ON hr_conversations(job_id);
CREATE INDEX idx_conv_intent ON hr_conversations(intent);

-- interview_prep表
CREATE TABLE interview_prep (
    id TEXT PRIMARY KEY,
    job_id TEXT REFERENCES jobs(id),
    questions TEXT,
    status TEXT DEFAULT 'generated',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_prep_job ON interview_prep(job_id);

#### 增量同步策略

| 数据类型 | 同步策略 |
|---------|---------|
| 数字足迹 | 全量首次，增量后续（基于文件hash） |
| 简历 | 每次编辑后自动保存 |
| 职位列表 | 每次搜索后合并更新 |
| HR对话 | 实时追加写入 |
| Cookie | 手动更新，不自动同步 |

---

## 3. BOSS直聘集成方案

### 3.1 opencli boss 命令使用方式

| 功能 | 命令 | 输出格式 |
|------|------|---------|
| 搜索职位 | opencli boss search query --city Beijing --page 1 --limit 15 -f json | JSON array |
| 职位详情 | opencli boss detail security_id -f json | JSON |
| 发招呼 | opencli boss greet uid --security-id id --job-id jid --text msg -f json | JSON |
| 查看聊天 | opencli boss chatlist -f json | JSON array |
| 发消息 | opencli boss send uid --text msg -f json | JSON |

### 3.2 Cookie登录态管理

BOSS requires cookie for authentication. Cookie management:

1. First time: User manually provides cookie string
2. Storage: ~/.jobtracer/cookies/boss.json
3. Format:
```json
{
  "cookie_string": "complete cookie string",
  "expires_at": "2026-07-01T00:00:00Z",
  "note": "Please update periodically"
}
```

4. How to get:
   - Login zhipin.com in browser
   - Open DevTools -> Network
   - Copy Cookie from request headers

### 3.3 搜索和发招呼完整流程

```
1. User: 开始求职
2. Agent calls BOSSSearcher.search(keywords=[Python, backend])
3. opencli boss search Python --city Beijing -f json
4. Parse results, save to job-tracker.json
5. User selects target jobs
6. Agent calls ResumeCustomizer.customize(resume, job)
7. Generate customized resume HTML
8. Agent calls BOSSGreeting.greet(uid, text=greeting)
9. opencli boss greet uid --text greeting -f json
10. Return result, update application status
```

### 3.4 异常处理（A1/B1/C2 同步自 PRD v1.0.1）

| 异常场景 | 代码 | 处理策略 |
|---------|------|---------|
| **A1：平台登录失效** | A1 | 等待用户手动重新授权，不自动降级切换平台；单平台失效不影响其他平台 |
| **B1：冷启动/数字足迹为空** | B1 | 简历上传（PDF/DOCX）→ LLM自动解析 → 结构化简历；数字足迹扫描作为增强选项 |
| **C2：投递过程中断** | C2 | 重试（指数退避）→ 记录失败原因 → 手动补救入口（重新发送 + 复制招呼语） |

#### A1 详细处理流程

```
1. 调用 opencli boss greet 时返回认证失败
2. 检测 Cookie 状态（读取 ~/.jobtracer/cookies/boss.json 的 expires_at）
3. 通知用户：「BOSS Cookie 已过期，请重新提供」
4. 用户通过飞书卡片重新粘贴 Cookie
5. 更新 boss.json，重试发招呼
6. 若用户拒绝提供 → 保持「待授权」状态，不阻塞其他流程
```

#### C2 详细处理流程（指数退避重试）

```python
def greet_with_retry(uid, text, max_retries=3):
    """指数退避重试策略：2s → 4s → 8s"""
    for attempt in range(max_retries):
        result = greet(uid, text)
        if result['success']:
            return result
        
        wait_time = 2 ** (attempt + 1)  # 2, 4, 8
        sleep(wait_time)
    
    # 所有重试失败 → 记录并提供手动补救入口
    log_failure(uid, result['error'])
    return {'success': False, 'manual_remedy': True, 'greeting_text': text}
```

#### 飞书卡片交互规范（同步自 PRD v1.0.1 交互设计）

- **消息卡片按钮数量限制**：最多 3 个按钮
- **Bitable 状态同步**：实时更新职位状态（new/applied/interview/offer/rejected）
- **关键节点飞书卡片：**
  - 简历确认卡片（Step 2 结束）
  - 职位匹配结果卡片（Step 3 结束）
  - 定制简历预览卡片（Step 4）
  - HR 回复建议卡片（Step 5）
  - 发招呼失败手动补救卡片（C2 场景）

---

---

## 4. 数据存储详细设计

### 4.1 目录结构

~/.jobtracer/
  memory/
    state.json              # 求职状态
    resume.json             # 结构化简历
    preferences.json        # 用户偏好
    hr_conversations.json   # HR沟通记录
  footprint/
    summary.md              # 数字足迹摘要
    skills_vector.json      # 技能向量
    projects/               # 按项目组织的文档
      {project_id}/
        _index.md
        metadata.json
        docs/
        code_snippets/
  jobs/
    job-tracker.json        # 职位追踪
    jd_cache/               # JD详情缓存
  customized_resumes/       # 定制简历
  interview_prep/           # 面题库
  cookies/                  # 登录态
  reports/                  # 复盘报告
  logs/                     # 日志

### 4.2 JSON文件格式（MVP Phase 1 完整字段列表）

#### 4.2.1 resume.json
```json
{
  "version": "v1.0",
  "name": "张三",
  "contact": {
    "phone": "138-xxxx-xxxx",
    "email": "zhangsan@example.com",
    "location": "北京",
    "linkedin": ""
  },
  "summary": "资深后端工程师，擅长Python/Go在高并发场景下的架构设计...",
  "skills": {
    "technical": ["Python", "Go", "PostgreSQL", "Redis", "Kubernetes"],
    "soft": ["跨团队协作", "技术文档写作", "代码评审"]
  },
  "experience": [
    {
      "company": "XX科技",
      "title": "高级后端工程师",
      "duration": "2022.03 - 至今",
      "highlights": [
        "设计并实现日均请求量超5000万的微服务架构",
        "主导数据库迁移项目，从MySQL迁移到PostgreSQL，QPS提升40%"
      ]
    }
  ],
  "projects": [
    {
      "name": "电商秒杀系统",
      "role": "技术负责人",
      "description": "基于Redis集群+消息队列实现10万并发秒杀",
      "metrics": "支撑双十一峰值QPS 8万，下单转化率提升15%",
      "source_project_id": "abc123"
    }
  ],
  "education": {
    "school": "北京理工大学",
    "degree": "本科",
    "major": "计算机科学与技术",
    "graduation_year": 2018
  },
  "meta": {
    "generated_from": "digital_footprint",
    "user_confirmed": false,
    "generated_at": "2026-06-03T10:00:00Z",
    "last_modified": "2026-06-03T10:00:00Z"
  }
}
```

#### 4.2.2 job-tracker.json
```json
{
  "jobs": [
    {
      "job_id": "boss_abc123",
      "platform": "boss",
      "title": "Python高级后端工程师",
      "company": "XX科技有限公司",
      "location": "北京-海淀区",
      "salary": {"min": 30000, "max": 50000, "raw": "30-50K"},
      "experience": "3-5年",
      "degree": "本科及以上",
      "skills": ["Python", "Go", "MySQL", "Redis"],
      "boss_name": "李经理",
      "boss_online": true,
      "security_id": "abc123",
      "url": "https://www.zhipin.com/job/abc123.html",
      "match_score": 85.5,
      "related_projects": ["abc123"],
      "status": "new",
      "created_at": "2026-06-03T10:00:00Z",
      "applied_at": null,
      "greet_attempts": 0,
      "last_error": null
    }
  ],
  "last_updated": "2026-06-03T10:00:00Z"
}
```

#### 4.2.3 state.json
```json
{
  "user_id": "ou_xxxxx",
  "current_step": 3,
  "resume_id": "v1.0_20260603",
  "platforms": {
    "boss": {
      "cookie_status": "valid",
      "cookie_expires_at": "2026-07-01T00:00:00Z"
    },
    "feishu": {
      "enabled": true,
      "last_sync": "2026-06-03T09:00:00Z"
    },
    "github": {
      "enabled": true,
      "token_status": "valid"
    }
  },
  "last_active": "2026-06-03T10:00:00Z"
}
```

#### 4.2.4 feedback.json
```json
{
  "feedback_id": "fb_001",
  "job_id": "boss_abc123",
  "hr_intent": "interview_invite",
  "agent_reply": "周三下午3点可以，请问是线上还是线下？",
  "user_edited": false,
  "final_reply": "周三下午3点可以，请问是线上还是线下？",
  "sent_at": null,
  "user_confirmed": true,
  "created_at": "2026-06-03T10:00:00Z"
}
```

#### 4.2.5 preferences.json
```json
{
  "target_cities": ["北京", "上海"],
  "target_roles": ["后端工程师", "高级后端工程师"],
  "expected_salary": {"min": 30000, "max": 50000, "currency": "CNY"},
  "experience_years": 5,
  "degree": "本科及以上",
  "boss_cookie": "...",
  "github_token": "...",
  "scan_config": {
    "local_enabled": true,
    "feishu_enabled": true,
    "github_enabled": true,
    "openclaw_enabled": true
  }
}
```

#### 4.2.6 目录结构（完整）

```
~/.jobtracer/
├── memory/
│   ├── state.json              # 求职状态（当前Step、平台状态）
│   ├── resume.json             # 结构化简历
│   ├── preferences.json       # 用户偏好（薪资/城市/平台/Cookie）
│   ├── hr_conversations.json   # HR沟通记录
│   └── job-tracker.json        # 职位追踪（JSON备份）
├── footprint/
│   ├── summary.md              # 数字足迹摘要
│   ├── skills_vector.json     # 技能向量
│   └── projects/              # 按项目组织的文档
│       └── {project_id}/
│           ├── _index.md
│           ├── metadata.json
│           ├── docs/
│           └── code_snippets/
├── jobs/
│   ├── job-tracker.json       # 职位追踪（主数据）
│   └── jd_cache/              # JD详情缓存
│       └── {security_id}.json
├── customized_resumes/
│   └── {jd_id}/
│       ├── customized.html
│       └── customized.pdf
├── interview_prep/
│   └── {job_id}/
│       └── prep.json
├── cookies/
│   └── boss.json              # BOSS登录Cookie（含expires_at）
├── logs/
│   ├── scan_20260603.log      # 扫描日志
│   ├── greet_failures.log    # 发招呼失败记录（C2场景）
│   └── errors.log            # 错误日志
└── reports/
    └── career_review_2026-06-03.md  # 求职复盘报告
```

### 4.3 Schema 设计（Phase 2 目标）

> **设计背景：** MVP Phase 1 使用 JSON 文件存储，提前设计关系型 Schema，确保 Phase 2 从 JSON 迁移到 SQLite（单机）再到 PostgreSQL（云端扩展）平滑演进。

#### 4.3.1 ER 图描述（文字版）

```
┌─────────────┐       ┌─────────────┐       ┌─────────────────────┐
│   users     │───1:1─│   resumes   │───1:N─┤   projects          │
│  用户表      │       │  简历表      │       │  项目经历表（数字足迹）│
└─────────────┘       └─────────────┘       └─────────────────────┘
                                                     │
                                                     │ 1:N
                                                     ▼
┌─────────────┐       ┌─────────────────────┐       ┌─────────────────────┐
│ job_status_ │◄─N:1─│   job_tracker       │─N:1─►│    feedback         │
│ history     │       │   职位追踪表         │       │    用户反馈记录      │
│ 状态变更历史│       └─────────────────────┘       └─────────────────────┘
└─────────────┘                  │
                                  │ 1:N
                                  ▼
                         ┌─────────────────────┐
                         │   interactions      │
                         │   HR沟通交互记录     │
                         └─────────────────────┘
                                  │
                                  │ 1:N
                                  ▼
                         ┌─────────────────────┐
                         │ digital_footprints  │
                         │   数字足迹聚合表     │
                         └─────────────────────┘
```

**表关系说明：**

| 关系 | 说明 |
|------|------|
| users ↔ resumes | 1:1（每个用户一份当前简历） |
| resumes ↔ projects | 1:N（每份简历包含多个项目经历） |
| projects ↔ digital_footprints | 1:N（每个项目包含多个数字足迹文档） |
| job_tracker ↔ job_status_history | 1:N（每个职位有多条状态变更记录） |
| job_tracker ↔ feedback | 1:N（每个职位有多条用户反馈） |
| job_tracker ↔ interactions | 1:N（每个职位有多条HR沟通记录） |

#### 4.3.2 表字段定义

##### 表 1：users（用户表）

| 字段 | 类型 | 主键 | 外键 | 索引 | 说明 |
|------|------|------|------|------|------|
| id | TEXT | ✅ | — | PK | 用户唯一标识（飞书 OpenID） |
| name | TEXT | — | — | — | 用户姓名 |
| phone | TEXT | — | — | — | 手机号 |
| email | TEXT | — | — | idx_email | 邮箱 |
| location | TEXT | — | — | — | 常住地 |
| linkedin | TEXT | — | — | — | LinkedIn URL |
| current_resume_id | TEXT | — | → resumes.id | idx_resume | 当前活跃简历ID |
| preferences_json | TEXT | — | — | — | 偏好JSON（薪资/城市/平台） |
| github_token | TEXT | — | — | — | GitHub Token（加密存储） |
| boss_cookie | TEXT | — | — | — | BOSS Cookie（加密存储） |
| feishu_token | TEXT | — | — | — | 飞书 OAuth Token（加密存储） |
| created_at | TIMESTAMP | — | — | — | 创建时间 |
| updated_at | TIMESTAMP | — | — | — | 更新时间 |

##### 表 2：resumes（简历表）

| 字段 | 类型 | 主键 | 外键 | 索引 | 说明 |
|------|------|------|------|------|------|
| id | TEXT | ✅ | — | PK | 简历ID（UUID） |
| user_id | TEXT | — | → users.id | idx_user | 所属用户 |
| version | TEXT | — | — | — | 版本号（如 v1.0） |
| name | TEXT | — | — | — | 姓名 |
| contact_json | TEXT | — | — | — | 联系方式JSON |
| summary | TEXT | — | — | FULLTEXT | 个人Summary |
| skills_json | TEXT | — | — | — | 技能JSON（technical/soft） |
| experience_json | TEXT | — | — | — | 工作经验JSON |
| education_json | TEXT | — | — | — | 教育背景JSON |
| user_confirmed | BOOLEAN | — | — | — | 用户是否已确认 |
| generated_from | TEXT | — | — | — | 生成来源（digital_footprint/upload） |
| generated_at | TIMESTAMP | — | — | — | 生成时间 |
| last_modified | TIMESTAMP | — | — | — | 最后修改时间 |

##### 表 3：projects（项目经历表）

| 字段 | 类型 | 主键 | 外键 | 索引 | 说明 |
|------|------|------|------|------|------|
| id | TEXT | ✅ | — | PK | 项目ID（UUID） |
| resume_id | TEXT | — | → resumes.id | idx_resume | 所属简历 |
| project_name | TEXT | — | — | idx_name | 项目名称 |
| role | TEXT | — | — | — | 角色 |
| description | TEXT | — | — | FULLTEXT | 项目描述 |
| metrics | TEXT | — | — | — | 量化成果 |
| source_project_id | TEXT | — | — | — | 数字足迹来源项目ID |
| created_at | TIMESTAMP | — | — | — | 创建时间 |

##### 表 4：job_tracker（职位追踪表）

| 字段 | 类型 | 主键 | 外键 | 索引 | 说明 |
|------|------|------|------|------|------|
| id | TEXT | ✅ | — | PK | 职位ID（如 boss_abc123） |
| user_id | TEXT | — | → users.id | idx_user | 所属用户 |
| platform | TEXT | — | — | idx_platform | 平台（boss/lagou/zhilian） |
| title | TEXT | — | — | idx_title | 职位名称 |
| company | TEXT | — | — | idx_company | 公司名称 |
| location | TEXT | — | — | — | 工作地点 |
| salary_min | INTEGER | — | — | idx_salary | 薪资下限（元/月） |
| salary_max | INTEGER | — | — | idx_salary | 薪资上限（元/月） |
| experience_required | TEXT | — | — | — | 经验要求 |
| degree_required | TEXT | — | — | — | 学历要求 |
| skills_json | TEXT | — | — | — | 技能要求JSON |
| jd_summary | TEXT | — | — | FULLTEXT | JD摘要 |
| boss_name | TEXT | — | — | — | HR姓名 |
| boss_uid | TEXT | — | — | — | HR UID |
| boss_online | BOOLEAN | — | — | — | HR是否在线 |
| security_id | TEXT | — | — | idx_security | 平台职位ID |
| url | TEXT | — | — | — | 职位链接 |
| match_score | REAL | — | — | idx_match | 匹配度评分 |
| status | TEXT | — | — | idx_status | 状态（new/applied/interview/offer/rejected） |
| related_projects_json | TEXT | — | — | — | 关联项目JSON |
| created_at | TIMESTAMP | — | — | — | 创建时间 |
| applied_at | TIMESTAMP | — | — | idx_applied | 投递时间 |
| greet_attempts | INTEGER | — | — | — | 发招呼次数 |
| last_error | TEXT | — | — | — | 最近错误信息 |


##### 表 5：job_status_history（职位状态变更历史）

| 字段 | 类型 | 主键 | 外键 | 索引 | 说明 |
|------|------|------|------|------|------|
| id | TEXT | ✅ | — | PK | 记录ID（UUID） |
| job_id | TEXT | — | → job_tracker.id | idx_job | 所属职位 |
| from_status | TEXT | — | — | — | 变更前状态 |
| to_status | TEXT | — | — | idx_to_status | 变更后状态 |
| reason | TEXT | — | — | — | 变更原因 |
| changed_at | TIMESTAMP | — | — | idx_changed | 变更时间 |

##### 表 6：interactions（HR沟通交互记录）

| 字段 | 类型 | 主键 | 外键 | 索引 | 说明 |
|------|------|------|------|------|------|
| id | TEXT | ✅ | — | PK | 交互ID（UUID） |
| job_id | TEXT | — | → job_tracker.id | idx_job | 所属职位 |
| direction | TEXT | — | — | idx_direction | 方向（inbound/outbound） |
| intent | TEXT | — | — | idx_intent | 意图分类 |
| message_preview | TEXT | — | — | — | 消息预览（截取前100字） |
| message_full | TEXT | — | — | FULLTEXT | 完整消息内容 |
| reply_suggested | TEXT | — | — | — | AI建议回复 |
| reply_sent | TEXT | — | — | — | 实际发送回复 |
| user_confirmed | BOOLEAN | — | — | — | 用户是否确认 |
| created_at | TIMESTAMP | — | — | idx_created | 创建时间 |
| sent_at | TIMESTAMP | — | — | — | 发送时间 |

##### 表 7：feedback（用户反馈记录）

| 字段 | 类型 | 主键 | 外键 | 索引 | 说明 |
|------|------|------|------|------|------|
| id | TEXT | ✅ | — | PK | 反馈ID（UUID） |
| job_id | TEXT | — | → job_tracker.id | idx_job | 所属职位 |
| feedback_type | TEXT | — | — | — | 反馈类型（rejected/interview/offer/salary_low/other） |
| hr_intent | TEXT | — | — | idx_intent | HR意图（如 interview_invite） |
| agent_reply | TEXT | — | — | — | Agent生成的回复 |
| user_edited | BOOLEAN | — | — | — | 用户是否编辑过 |
| final_reply | TEXT | — | — | — | 最终确认回复 |
| sent_at | TIMESTAMP | — | — | — | 发送时间 |
| user_confirmed | BOOLEAN | — | — | — | 用户是否确认 |
| created_at | TIMESTAMP | — | — | — | 创建时间 |

##### 表 8：digital_footprints（数字足迹聚合表）

| 字段 | 类型 | 主键 | 外键 | 索引 | 说明 |
|------|------|------|------|------|------|
| id | TEXT | ✅ | — | PK | 足迹ID（UUID） |
| project_id | TEXT | — | → projects.id | idx_project | 所属项目 |
| source | TEXT | — | — | idx_source | 来源（github/feishu/local/openclaw） |
| source_id | TEXT | — | — | — | 平台特定ID（如GitHub repo名） |
| title | TEXT | — | — | idx_title | 标题/文件名 |
| content | TEXT | — | — | FULLTEXT | 完整内容 |
| content_hash | TEXT | — | — | idx_hash | 内容哈希（去重用） |
| url | TEXT | — | — | — | 原始链接 |
| confidence | REAL | — | — | — | 来源置信度 |
| created_at | TIMESTAMP | — | — | — | 创建时间 |

#### 4.3.3 迁移策略说明（JSON → SQLite → PostgreSQL）

```
Phase 1 (MVP)          Phase 2 (Growth)         Phase 3 (Scale)
─────────────         ─────────────────         ─────────────────
JSON 文件存储    ───►   SQLite 本地      ───►   PostgreSQL 云端
~/.jobtracer/          单机数据库              分布式数据库
```

**迁移阶段说明：**

| 阶段 | 存储方案 | 数据量估算 | 迁移方式 |
|------|---------|-----------|---------|
| Phase 1 | JSON 文件 | < 1000 条记录 | 手工导入 |
| Phase 2 | SQLite | 1000 ~ 10万 条 | 脚本自动化迁移 + 增量同步 |
| Phase 3 | PostgreSQL | 10万+ 条 | 水平分库 + 读写分离 |

**JSON → SQLite 迁移脚本要点：**

1. **字段映射**：JSON 顶层字段 → 对应 SQL 表字段
2. **外键回填**：基于时间戳或关联字段建立外键关系
3. **冲突处理**：INSERT OR REPLACE（幂等迁移）
4. **迁移校验**：迁移前后数据行数一致 + 抽样校验

```python
# migration/json_to_sqlite.py
import json, sqlite3, os
from pathlib import Path

def migrate_all(json_root: str, db_path: str):
    """JSON → SQLite 全量迁移"""
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_SQL)  # 执行建表SQL
    
    migrate_users(json_root + '/memory/state.json', conn)
    migrate_resumes(json_root + '/memory/resume.json', conn)
    migrate_jobs(json_root + '/memory/job-tracker.json', conn)
    migrate_feedback(json_root + '/memory/feedback.json', conn)
    migrate_footprint(json_root + '/footprint/', conn)
    
    conn.commit()
    conn.close()
```

**SQLite → PostgreSQL 迁移脚本要点：**

1. 使用 `pgloader` 或自定义 ETL 脚本
2. 数据类型适配（TEXT → VARCHAR, BOOLEAN → BOOLEAN）
3. 全文检索适配（SQLite FTS → PostgreSQL pg_trgm）
4. 迁移窗口：选择低峰时段 + 灰度验证

#### 4.3.4 Phase 1 JSON ↔ Phase 2 Schema 映射关系表

| Phase 1 JSON 文件 | Phase 2 表 | 映射关系 |
|------------------|-----------|---------|
| `memory/state.json` | **users** | state.json.user_id → users.id；preferences_json → users.preferences_json；platforms.* → users.boss_cookie/feishu_token/github_token |
| `memory/resume.json` | **resumes** + **projects** | resume.json → resumes 表（顶层字段）；resume.json.projects[] → projects 表（resume_id 外键） |
| `memory/job-tracker.json` | **job_tracker** | job-tracker.json.jobs[] → job_tracker 表；job_id 直接映射 |
| `memory/job-tracker.json` | **job_status_history** | 通过 status 字段变更时 INSERT |
| `memory/hr_conversations.json` | **interactions** | hr_conversations[] → interactions 表 |
| `memory/feedback.json` | **feedback** | feedback.json → feedback 表 |
| `footprint/projects/{id}/` | **projects** + **digital_footprints** | 项目文件夹 → projects 表；docs/ 和 code_snippets/ → digital_footprints 表 |

**具体字段映射示例（resume.json → resumes + projects）：**

```sql
-- resume.json → resumes 表
INSERT INTO resumes (id, user_id, version, name, contact_json, summary,
                    skills_json, experience_json, education_json,
                    user_confirmed, generated_from, generated_at, last_modified)
SELECT 
    'resume_' || strftime('%Y%m%d%H%M%S', generated_at) || '_' || user_id,
    user_id,
    version,
    name,
    json_object('phone', phone, 'email', email, 'location', location),
    summary,
    json_object('technical', skills.technical, 'soft', skills.soft),
    json_object('experience', experience),
    json_object('education', education),
    user_confirmed,
    generated_from,
    generated_at,
    last_modified
FROM resume_json;

-- resume.json.projects[] → projects 表
INSERT INTO projects (id, resume_id, project_name, role, description, metrics)
SELECT 
    'proj_' || substr(md5(project_name), 1, 8),
    resume_id,
    project_name,
    role,
    description,
    metrics
FROM resume_json, json_each(resume_json.projects);
```

---

### 4.4 SQLite Schema

Phase 1 uses JSON files, Phase 2 migrates to SQLite:

```sql
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    title TEXT,
    company TEXT,
    location TEXT,
    salary_min INTEGER,
    salary_max INTEGER,
    match_score REAL,
    jd_summary TEXT,
    status TEXT DEFAULT 'new',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    applied_at TIMESTAMP,
    related_projects TEXT
);

CREATE TABLE hr_conversations (
    id TEXT PRIMARY KEY,
    job_id TEXT,
    direction TEXT,
    intent TEXT,
    message_preview TEXT,
    message_full TEXT,
    reply_sent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE interview_prep (
    id TEXT PRIMARY KEY,
    job_id TEXT,
    questions TEXT,
    status TEXT DEFAULT 'generated',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.5 增量同步策略

| Data Type | Sync Strategy |
|-----------|---------------|
| Digital Footprint | Full scan first time, incremental (hash-based change detection) |
| Resume | Auto-save on each user edit |
| Job List | Merge on each search (dedup) |
| HR Conversation | Real-time append |
| Cookie | Manual update, expiration reminder |

---

## 5. API/接口设计

### 5.1 Agent消息协议

User interacts with JobTracer via Feishu messages:

**User -> Agent:**
- Trigger: "开始求职", "帮我找工作", "生成简历"
- HR message forward: "帮我回复" + pasted HR message
- Status query: "现在投了哪些", "面试进度"

**Agent -> User:**
- Confirmation cards: Resume preview, customized resume preview, HR reply suggestions
- Status notifications: Application success, new HR reply, interview invite
- Action buttons: Confirm apply, confirm reply, edit content

### 5.2 模块间接口

```
JobTracer Skill
    |
    +-- scan_footprint() -> FootprintScanner -> projects[]
    +-- generate_resume(projects[]) -> ResumeGenerator -> resume.json
    +-- search_jobs(resume.json) -> BOSSSearcher -> jobs[]
    +-- match_jobs(resume.json, jobs[]) -> JDMatcher -> scored_jobs[]
    +-- customize_resume(resume.json, job, projects[]) -> ResumeCustomizer -> customized.html
    +-- greet_boss(uid, text) -> BOSSGreeting -> result
    +-- generate_interview_prep(resume.json, job) -> InterviewPrepGenerator -> prep.json
    +-- save_state() -> StorageManager -> JSON files
```

### 5.3 飞书通知格式

**Job Match Notification Card:**
```
Title: Found 5 matching jobs
---
[Job 1] Salary: 20-35K | Match: 85%
[Job 2] Salary: 25-40K | Match: 78%
...
[View All] [Apply All]
```

**HR Reply Notification Card:**
```
Title: New HR Reply - XX Tech
---
Intent: Interview Invite
Suggested Reply: Hello, 3PM Wednesday works, is that convenient?
[Confirm Send] [Edit Reply]
```

---

## 6. 技术选型

### 6.1 核心依赖

| Dependency | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Main development language |
| httpx | 0.27+ | Async HTTP client (GitHub API) |
| PyMuPDF | 1.24+ | PDF text extraction |
| openpyxl | 3.1+ | Excel file reading |
| weasyprint | 60+ | HTML to PDF (recommended) |
| playwright | 1.44+ | Fallback PDF generation |
| aiofiles | 24+ | Async file IO |
| sqlite3 | built-in | Database (Phase 2) |

### 6.2 LLM调用方案

| Phase | Solution | Note |
|-------|----------|------|
| Phase 1 | OpenAI GPT-4 / Claude 3.5 | Cloud API, high quality |
| Phase 2 | Local model (optional) | Cost reduction, private deployment |

### 6.3 PDF生成方案

**Recommended: WeasyPrint**
```bash
pip install weasyprint
```

Pros:
- Pure Python, no external dependencies
- CSS style support, high quality output
- Chinese support (font configuration required)

**Fallback: Playwright + Chrome**
```bash
pip install playwright
playwright install chromium
```

Use when WeasyPrint cannot handle complex CSS.

### 6.4 项目结构

```
jobtracer/
  scanner/
    __init__.py
    footprint_scanner.py   # Unified orchestrator
    local_scanner.py       # Local files
    feishu_scanner.py      # Feishu docs
    github_scanner.py      # GitHub
    openclaw_scanner.py    # OpenClaw
  clustering/
    __init__.py
    engine.py              # Project clustering
  resume/
    __init__.py
    generator.py           # Resume generation
    customizer.py          # Customized resume
  boss/
    __init__.py
    search.py              # BOSS search
    greet.py               # Send greeting
  matching/
    __init__.py
    scorer.py              # JD matching score
  hr/
    __init__.py
    engine.py              # HR communication engine
  interview/
    __init__.py
    prep.py                # Interview question generation
  storage/
    __init__.py
    manager.py             # Data storage manager
  utils/
    __init__.py
    file_utils.py          # File operations
    html_utils.py          # HTML generation
  config.py                 # Configuration
  main.py                   # Entry point
  requirements.txt           # Dependencies
```

---

## 7. 开发计划

### 7.1 Sprint 1 (2 weeks) Task Breakdown

**Sprint 1 目标：完成数字足迹扫描 + 基础简历生成 + BOSS搜索**

#### Week 1：基础框架 + 数字足迹扫描

| # | 任务 | 描述 | 依赖 | 验收标准（DOD） | 估算 | 优先级 |
|---|------|------|------|----------------|------|--------|
| 1.1 | 创建项目脚手架 | 创建 Python 项目结构、requirements.txt、__init__.py 文件 | 无 | 项目可 import；pip install -r requirements.txt 成功 | 0.5d | P0 |
| 1.2 | 初始化存储目录 | 创建 ~/.jobtracer/ 目录结构；初始化 state.json / preferences.json | 无 | 目录存在；JSON 文件格式正确 | 0.5d | P0 |
| 1.3 | 实现本地文件扫描器 | 实现 scanner/local_scanner.py；支持 .md/.txt/.pdf/.doc/.docx/.xlsx/.pptx；过滤敏感文件 | 1.1 | 扫描结果包含 path/name/ext/modified/size/content_preview；排除 node_modules/.git 等目录 | 1.0d | P0 |
| 1.4 | 实现 OpenClaw 记忆扫描器 | 实现 scanner/openclaw_scanner.py；扫描 ~/.openclaw/workspace/MEMORY.md 和 memory/ | 1.1 | 读取到 MEMORY.md 和 memory/*.md 文件；输出文件列表 | 0.5d | P0 |
| 1.5 | 实现 GitHub 扫描器 | 实现 scanner/github_scanner.py；调用 GitHub REST API 读取 README 和 Issues | 1.1 | 能读取仓库 README（Base64 解码）和 Issues；支持分页 | 1.0d | P1 |
| 1.6 | 实现扫描器编排器 | 实现 scanner/footprint_scanner.py；统一调度各扫描器 + asyncio 超时控制 + 异常捕获 | 1.3, 1.4, 1.5 | 300s 超时控制；单个平台失败不影响整体；返回 merged 结果 | 1.0d | P0 |
| 1.7 | 实现项目聚类引擎 | 实现 clustering/engine.py；调用 LLM 将扫描结果聚类；生成 footprint/projects/{id}/ 结构 | 1.6 | 输出 projects/ 目录；每个项目含 _index.md + metadata.json + docs/ + code_snippets/ | 1.5d | P0 |
| 1.8 | 实现数据存储层 | 实现 storage/manager.py；统一读写 ~/.jobtracer/ 下所有 JSON 文件 | 1.2 | resume.json / job-tracker.json / state.json 读写正常；路径自动创建 | 1.0d | P0 |

#### Week 2：简历生成 + BOSS搜索

| # | 任务 | 描述 | 依赖 | 验收标准（DOD） | 估算 | 优先级 |
|---|------|------|------|----------------|------|--------|
| 1.9 | 实现简历生成器 | 实现 resume/generator.py；从 footprint/projects/ 调用 LLM 生成结构化 resume.json | 1.7, 1.8 | resume.json 包含 name/contact/summary/skills/experience/projects/education/meta；JSON 格式正确 | 1.5d | P0 |
| 1.10 | 实现 HTML 简历模板 | 实现 resume/preview.html 渲染模板；支持 skills tag / project cards / contact | 1.9 | HTML 在浏览器中显示正常；中文无乱码；可复制文本 | 0.5d | P0 |
| 1.11 | 实现 BOSS 搜索模块 | 实现 boss/search.py；调用 opencli boss search；解析 JSON 输出 | 1.8 | 命令行 opencli boss search 能返回结果；解析后写入 job-tracker.json | 1.0d | P0 |
| 1.12 | 实现 JD 缓存机制 | 实现 jobs/jd_cache/ {security_id}.json 缓存；读取时优先读缓存 | 1.11 | 同一 security_id 不重复调用 opencli；缓存文件存在且可读 | 0.5d | P0 |
| 1.13 | 实现 JD 匹配评分模块 | 实现 matching/scorer.py；技能匹配40% + 项目匹配20% + 经验匹配20% + 薪资匹配20% | 1.9, 1.11 | 每个 job 有 total_score（0-100）和 breakdown；related_projects 至少返回3个 | 1.0d | P0 |
| 1.14 | 实现飞书通知卡片（Step 1-3） | 实现飞书消息卡片；关键节点：简历确认卡片、职位匹配结果卡片 | 1.9, 1.13 | 卡片显示 Job Title / Company / Match Score / [查看简历] 按钮 | 0.5d | P1 |

**Week 1 小计：8 个任务，6.5 人天 | Week 2 小计：6 个任务，5.0 人天 | Sprint 1 合计：14 个任务，11.5 人天**

### 7.2 Sprint 2 (2 weeks) Task Breakdown

**Sprint 2 目标：完成定制简历 + BOSS 发招呼 + 飞书通知 + 异常处理 + 稳定化**

#### Week 3：定制简历 + 发招呼

| # | 任务 | 描述 | 依赖 | 验收标准（DOD） | 估算 | 优先级 |
|---|------|------|------|----------------|------|--------|
| 2.1 | 实现定制简历生成器 | 实现 resume/customizer.py；针对目标 JD 定制 resume.json 内容（重排项目/强调技能） | 1.9, 1.13 | 针对 JD 的定制简历生成成功；保留原始信息不变形 | 1.0d | P0 |
| 2.2 | 实现 PDF 生成集成 | 实现 HTML → PDF 转换（WeasyPrint）；中文字体配置 | 2.1 | customized.pdf 生成成功；中文字体显示正常 | 1.0d | P1 |
| 2.3 | 实现 BOSS 发招呼模块 | 实现 boss/greet.py；调用 opencli boss greet；实现指数退避重试（2s→4s→8s） | 1.11 | 最多重试3次；失败时返回 manual_remedy=true + greeting_text；写入 greet_failures.log | 1.0d | P0 |
| 2.4 | 实现 Cookie 管理 | 实现 cookies/boss.json 读写；expires_at 过期检测；过期时提示用户重新授权 | 1.11 | Cookie 写入文件；启动时检测过期；过期后飞书卡片提示 | 0.5d | P1 |
| 2.5 | 实现飞书 Bot 交互集成 | 实现飞书消息收发；按钮卡片交互（[重新发送] / [复制招呼语]） | 2.3, 2.4 | C2 场景下用户可点击按钮重试或复制招呼语 | 1.5d | P1 |

#### Week 4：稳定化 + 交付

| # | 任务 | 描述 | 依赖 | 验收标准（DOD） | 估算 | 优先级 |
|---|------|------|------|----------------|------|--------|
| 2.6 | 实现异常处理（A1/B1/C2） | 实现扫描失败降级（A1 平台失效）、冷启动路径（B1 数字足迹为空）、发招呼中断（C2） | 1.3-1.8, 2.3 | 各异常场景有明确定义的处理路径；不崩溃 | 1.0d | P0 |
| 2.7 | 实现日志系统 | 实现 logs/scan_*.log / logs/greet_failures.log / logs/errors.log；统一日志格式 | 2.6 | 日志文件存在；每条日志含 timestamp/level/module/message | 0.5d | P1 |
| 2.8 | 端到端集成测试 | 完整流程测试：上传简历 → 数字足迹扫描 → 生成简历 → BOSS 搜索 → 发招呼 | 1.14, 2.5 | 全流程可跑通；各模块数据流正确；飞书卡片正常触达 | 1.5d | P0 |
| 2.9 | 性能优化 | 并发扫描优化（asyncio.gather）；扫描超时控制（60s 本地文件 / 300s 全局） | 1.6 | 并发扫描相比串行提效 ≥30%；超时场景优雅降级 | 0.5d | P2 |
| 2.10 | 文档 + 用户手册 | README + API 文档 + 使用手册（飞书 Bot 操作说明） | 2.8 | 文档覆盖全流程；用户可根据文档独立使用 | 0.5d | P1 |

**Week 3 小计：5 个任务，5.0 人天 | Week 4 小计：5 个任务，3.5 人天 | Sprint 2 合计：10 个任务，8.5 人天**

### 7.3 Sprint 3（如需要）— Phase 2 准备

| # | 任务 | 描述 | 依赖 | 验收标准（DOD） | 估算 | 优先级 |
|---|------|------|------|----------------|------|--------|
| 3.1 | SQLite Schema 迁移脚本 | 实现 JSON → SQLite 迁移脚本；执行 §4.3 建表 SQL；实现 INSERT OR REPLACE 幂等迁移 | Sprint 2 完成 | 迁移前后数据行数一致；抽样校验字段正确 | 2.0d | P2 |
| 3.2 | 其他招聘平台接入 | 接入 51job / 牛客 等平台（opencli 或 API）；扩展 boss/search.py 支持多平台 | Sprint 2 完成 | 多平台搜索返回统一格式的 job-tracker.json；平台差异化字段兼容 | 3.0d | P2 |

**Sprint 3 合计：2 个任务，5.0 人天**

### 7.4 MVP交付标准

| Feature | Delivery Criteria |
|---------|-------------------|
| Digital Footprint Scan | Scan local/OpenClaw/GitHub, generate structured projects |
| Resume Generation | Generate resume.json from projects, HTML preview available |
| BOSS Search | Search returns results with match scores displayed |
| Customized Resume | Generate customized HTML resume for JD |
| BOSS Greeting | Call opencli greet to send greeting successfully |
| Feishu Notification | Push Feishu messages at key nodes |
| Data Persistence | Save resume/job data to ~/.jobtracer/ |

---

## 8. 技术风险和应对

### 8.1 BOSS Cookie Expired

| Risk | BOSS cookie expires or invalid, causing search/greet failure |
|------|-----------------------------------------------------------|
| Likelihood | High (cookie usually expires in 30 days) |
| Impact | Cannot automate search and greeting |
| Mitigation | Prompt user to re-provide cookie, fallback to manual copy |

### 8.2 PDF Generation Failure

| Risk | WeasyPrint rendering fails or Chinese fonts missing |
|------|---------------------------------------------------|
| Likelihood | Medium |
| Impact | Customized resume cannot generate PDF |
| Mitigation | Fallback Playwright solution, prompt user to check fonts |

### 8.3 LLM Output Quality

| Risk | LLM generates inaccurate or malformed resume content |
|------|------------------------------------------------------|
| Likelihood | Medium |
| Impact | Resume quality low, requires extensive user edits |
| Mitigation | User confirmation checkpoint, iterative prompt optimization |

### 8.4 Data Consistency

| Risk | Multi-point writes cause data inconsistency |
|------|---------------------------------------------|
| Likelihood | Low |
| Impact | Job status display error |
| Mitigation | Transactional writes, JSON backup, SQLite migration plan |

### 8.5 Feishu MCP Unavailable

| Risk | Feishu MCP connection fails or token expires |
|------|---------------------------------------------|
| Likelihood | Low |
| Impact | Cannot read Feishu documents |
| Mitigation | Skip Feishu scan, prompt user to upload manually |

### 8.6 Risk Summary

| Risk | Likelihood | Impact | Mitigation Priority |
|------|------------|--------|---------------------|
| Cookie expired | High | Medium | P1 |
| PDF generation failed | Medium | Medium | P2 |
| LLM output quality | Medium | High | P1 |
| Data consistency | Low | Medium | P3 |
| Feishu MCP unavailable | Low | High | P2 |

---

## 9. PRD待验证项跟进

| # | Verification Item | Status | Result |
|---|-----------------|--------|--------|
| 1 | BOSS opencli boss greet available | Verified | opencli boss greet exists, params: uid, --security-id, --job-id, --text |
| 2 | BOSS search API feasibility | Verified | opencli boss search supported, outputs JSON |
| 3 | PDF generation (weasyprint/playwright) | Pending | WeasyPrint recommended, Playwright fallback |
| 4 | Feishu MCP availability | Pending | Needs actual connection test |

---

## 10. 附录

### A. 缩写说明

| Abbreviation | Full Name | Note |
|--------------|-----------|------|
| JD | Job Description | Job posting |
| BOSS | BOSS Zhipin | Recruitment platform |
| MCP | Model Context Protocol | Model context protocol |
| LLM | Large Language Model | Large language model |
| STAR | Situation, Task, Action, Result | Interview behavior method |

### B. 参考文档

| Document | Path |
|----------|------|
| JobTracer PRD | ~/openclaw-workspaces/product-solution/JobTracer PRD.md |
| ProjectTrace方案 | ~/openclaw-workspaces/product-solution/数字足迹聚合器方案.md |
| opencli boss help | opencli boss --help |

### C. 修改日志

| Version | Date | Changes |
|---------|------|---------|
| v1.0.3 | 2026-06-03 | §7 开发计划精细化拆分：22 个任务卡（Sprint 1: 14个11.5d / Sprint 2: 10个8.5d / Sprint 3: 2个5.0d），合计 25.0 人天，P0/P1/P2 标注，附验收标准 |
| v1.0.2 | 2026-06-03 | 新增 §4.3 Schema 设计章节（Phase 2 目标）：8 张关系型表定义、ER 图、迁移策略、JSON ↔ Schema 映射关系 |

---

*本文档由 ProductSolution Agent 基于 PRD v1.0.1 生成*
