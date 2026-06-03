# resume/generator.py
# 简历生成器 - 支持 LLM + 基于规则两种模式
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List

DEFAULT_PROJECTS_DIR = Path("~/.jobtracer/footprint/projects").expanduser()
DEFAULT_RESUME_PATH = Path("~/.jobtracer/memory/resume.json").expanduser()

# ─────────────────────────────────────────────────────────────
# 技能 -> 编程语言映射（用于从文件类型推断技能）
# ─────────────────────────────────────────────────────────────
FILE_TYPE_SKILLS = {
    '.py': 'Python', '.pyw': 'Python',
    '.js': 'JavaScript', '.jsx': 'React', '.ts': 'TypeScript', '.tsx': 'React',
    '.go': 'Go', '.rs': 'Rust', '.java': 'Java', '.kt': 'Kotlin',
    '.c': 'C', '.cpp': 'C++', '.cc': 'C++', '.cxx': 'C++',
    '.cs': 'C#', '.rb': 'Ruby', '.php': 'PHP', '.swift': 'Swift',
    '.vue': 'Vue.js', '.svelte': 'Svelte',
    '.sh': 'Shell', '.bash': 'Bash', '.zsh': 'Zsh',
    '.sql': 'SQL', '.prql': 'PRQL',
    '.r': 'R', '.R': 'R',
    '.m': 'MATLAB', '.matlab': 'MATLAB',
    '.ipynb': 'Jupyter', '.nb': 'Jupyter',
    '.md': 'Markdown', '.rst': 'reStructuredText',
    '.yaml': 'YAML', '.yml': 'YAML',
    '.json': 'JSON', '.toml': 'TOML', '.xml': 'XML', '.csv': 'CSV',
    '.tf': 'Terraform', '.dockerfile': 'Docker', '.dockerignore': 'Docker',
    '.gitignore': 'Git', '.env': 'Environment Config',
    '.css': 'CSS', '.scss': 'SCSS', '.less': 'Less',
    '.html': 'HTML', '.htm': 'HTML',
    '.txt': 'Text Processing',
    '.pdf': 'PDF', '.doc': 'Word', '.docx': 'Word',
    '.xlsx': 'Excel', '.xls': 'Excel',
    '.png': 'Image Processing', '.jpg': 'JPEG', '.jpeg': 'JPEG',
    '.svg': 'SVG',
    '.proto': 'Protocol Buffers', '.grpc': 'gRPC',
    '.md': 'Documentation', '.rst': 'Documentation',
    '.pem': 'TLS/SSL', '.crt': 'TLS/SSL', '.key': 'TLS/SSL',
}


def infer_skills_from_files(root: Path) -> set:
    """遍历目录，收集所有文件的扩展名，映射为技能标签"""
    skills = set()
    if not root.exists():
        return skills
    for f in root.rglob('*'):
        if f.is_file() and not f.name.startswith('.'):
            ext = f.suffix.lower()
            if ext in FILE_TYPE_SKILLS:
                skills.add(FILE_TYPE_SKILLS[ext])
            # 特殊文件名推断
            if f.name in ('Makefile', 'makefile'):
                skills.add('Make')
            if f.name.startswith('Dockerfile'):
                skills.add('Docker')
    return skills


def extract_name_from_path(projects_dir: Path) -> str:
    """从项目目录结构推断姓名（取第一级目录名）"""
    try:
        parent = projects_dir.parent
        return parent.name if parent.name else "Your Name"
    except Exception:
        return "Your Name"


def parse_index_markdown(text: str) -> dict:
    """从 _index.md 解析项目描述"""
    result = {
        'name': '',
        'role': '',
        'description': '',
        'metrics': '',
        'tech': [],
    }
    lines = text.split('\n')

    # 尝试提取标题（# 项目名）
    for line in lines:
        line = line.strip()
        if line.startswith('# ') and not result['name']:
            result['name'] = line[2:].strip()
        # 角色：去掉 ** 或 Role: 前缀
    role_text = re.sub(r'\*\*', '', line).strip()
    role_text = re.sub(r'^Role:\s*', '', role_text, flags=re.IGNORECASE)
    if role_text and not result['role']:
        result['role'] = role_text

    # 合并所有内容作为描述
    result['description'] = text.strip()
    return result


def infer_contact_from_index(text: str) -> dict:
    """从 index.md 文本中提取联系方式"""
    contact = {}
    email_pattern = r'[\w.+-]+@[\w-]+\.[\w.-]+'
    phone_pattern = r'1[3-9]\d{9}|\+86\s?\d{10,11}'
    location_pattern = r'(北京|上海|深圳|广州|杭州|南京|苏州|成都|武汉|西安|厦门|天津)'

    emails = re.findall(email_pattern, text)
    phones = re.findall(phone_pattern, text)
    locations = re.findall(location_pattern, text)

    if emails:
        contact['email'] = emails[0]
    if phones:
        contact['phone'] = phones[0]
    if locations:
        contact['location'] = locations[0]
    return contact


# ─────────────────────────────────────────────────────────────
# ResumeGenerator 主类
# ─────────────────────────────────────────────────────────────
class ResumeGenerator:
    """
    从数字化足迹（projects/）生成结构化简历 JSON。

    使用方式：
        gen = ResumeGenerator()
        resume = await gen.generate_from_projects(['proj_a', 'proj_b'])
        gen.save_resume(resume)
    """

    def __init__(
        self,
        projects_dir: str = None,
        llm_client=None,          # 可选：LLM 客户端（有则用 LLM 生成，否则基于规则）
        llm_model: str = "gpt-4o"
    ):
        self.projects_dir = Path(projects_dir or str(DEFAULT_PROJECTS_DIR))
        self.llm = llm_client
        self.llm_model = llm_model

    # ── 非异步 API（兼容旧代码）────────────────────────────────

    def load_projects(self) -> List[dict]:
        """加载所有已扫描的项目，返回 [{project_name, path, metadata}]"""
        projects = []
        if not self.projects_dir.exists():
            return projects
        for d in self.projects_dir.iterdir():
            if not d.is_dir() or d.name.startswith('.'):
                continue
            meta_path = d / 'metadata.json'
            index_path = d / '_index.md'
            entry = {
                'project_name': d.name,
                'path': str(d),
                'metadata': {},
                'index_content': '',
            }
            if meta_path.exists():
                try:
                    entry['metadata'] = json.loads(meta_path.read_text())
                except Exception:
                    pass
            if index_path.exists():
                entry['index_content'] = index_path.read_text()
            projects.append(entry)
        return projects

    def _extract_projects_data(self, project_list: List[dict]) -> List[dict]:
        """从项目列表提取可用于简历的数据"""
        result = []
        for p in project_list:
            parsed = parse_index_markdown(p.get('index_content', ''))
            # 从 metadata 获取额外信息
            meta = p.get('metadata', {})
            tech = meta.get('tech_stack', [])
            if isinstance(meta.get('tags'), list):
                tech.extend(meta['tags'])
            result.append({
                'name': p['project_name'].replace('-', ' ').replace('_', ' ').title(),
                'role': parsed.get('role') or meta.get('role', 'Developer'),
                'description': parsed.get('description', '')[:500],
                'metrics': parsed.get('metrics') or meta.get('metrics', ''),
                'tech_stack': list(set(tech)),
            })
        return result

    def _build_rule_resume(self, projects: List[dict], target_role: str = None) -> dict:
        """基于规则生成简历（无 LLM 时 fallback）"""
        projects_data = self._extract_projects_data(projects)

        # 收集所有技能
        all_skills = set()
        for p in projects:
            skills = infer_skills_from_files(Path(p['path']))
            all_skills.update(skills)

        # 推断联系人信息
        contact = {}
        for p in projects:
            c = infer_contact_from_index(p.get('index_content', ''))
            contact.update(c)

        resume = {
            "name": extract_name_from_path(self.projects_dir),
            "contact": {
                "phone": contact.get('phone', ''),
                "email": contact.get('email', ''),
                "location": contact.get('location', ''),
            },
            "skills": sorted(list(all_skills)),
            "experience": [],       # 基于规则时从项目推断
            "projects": [
                {
                    "name": p['name'],
                    "role": p['role'],
                    "description": p['description'][:300] if p['description'] else '',
                    "metrics": p.get('metrics', ''),
                    "tech_stack": p.get('tech_stack', []),
                }
                for p in projects_data
            ],
            "education": [],         # 教育经历需要用户提供
            "target_role": target_role or '',
            "summary": self._generate_summary(projects_data, target_role),
        }
        return resume

    def _generate_summary(self, projects: List[dict], target_role: str = None) -> str:
        """生成个人总结"""
        if not projects:
            return "具有多年项目开发经验的技术人员。"
        techs = []
        for p in projects:
            techs.extend(p.get('tech_stack', []))
        unique_techs = list(set(techs))[:8]
        tech_str = ', '.join(unique_techs) if unique_techs else '软件开发'
        role_str = target_role or '技术开发'
        return f"资深{role_str}，熟悉 {tech_str} 等技术栈，具有丰富的项目架构与开发经验。"

    # ── 主要生成接口 ──────────────────────────────────────────

    async def generate_from_projects(
        self,
        project_names: List[str] = None,
        target_role: str = None
    ) -> dict:
        """
        从项目列表生成简历。

        Args:
            project_names: 项目名列表（None 表示全部项目）
            target_role: 目标职位

        Returns:
            结构化 resume.json dict
        """
        all_projects = self.load_projects()

        if project_names:
            selected = [p for p in all_projects if p['project_name'] in project_names]
        else:
            selected = all_projects

        if not selected:
            # 返回空白模板
            return self._empty_resume(target_role)

        # 优先使用 LLM（有 llm_client 时）
        if self.llm is not None:
            return await self._generate_with_llm(selected, target_role)
        else:
            return self._build_rule_resume(selected, target_role)

    async def generate_from_scan(self, scan_results: dict, target_role: str = None) -> dict:
        """
        从扫描结果直接生成简历（1.6 scan_all 的输出格式）

        scan_results 预期格式：
            {'projects': [{'name': '...', 'files': [...], 'index': '...'}]}
        """
        projects = scan_results.get('projects', [])
        if self.llm is not None:
            return await self._generate_with_llm(projects, target_role)
        else:
            return self._build_rule_resume(projects, target_role)

    async def _generate_with_llm(self, projects: List[dict], target_role: str = None) -> dict:
        """使用 LLM 生成简历（需要 llm_client）"""
        prompt = self._build_llm_prompt(projects, target_role)
        try:
            response = await self.llm.generate(prompt, schema='json')
            resume = json.loads(response) if isinstance(response, str) else response
        except Exception as e:
            # LLM 调用失败时回退到规则
            print(f"[ResumeGenerator] LLM failed: {e}, falling back to rule-based")
            return self._build_rule_resume(projects, target_role)

        resume['meta'] = {
            'generated_from': 'digital_footprint',
            'user_confirmed': False,
            'generated_at': datetime.now().isoformat(),
            'projects_count': len(projects),
        }
        return resume

    def _build_llm_prompt(self, projects: List[dict], target_role: str = None) -> str:
        """构建 LLM prompt"""
        projects_data = self._extract_projects_data(projects)
        prompt = """You are a professional resume writer. Generate a concise technical resume in JSON.

Requirements:
1. Extract key contributions and quantifiable results
2. Use STAR format for project descriptions
3. Highlight technical highlights and business value
4. Use action verbs, be concise and professional
5. Fill ALL fields with plausible content based on the provided data

Input projects:
""" + json.dumps(projects_data, ensure_ascii=False, indent=2)

        if target_role:
            prompt += f"\nTarget role: {target_role}"

        prompt += """
Output JSON with exactly these fields:
- name (string)
- contact: {phone, email, location} (all strings)
- skills: [list of technical skills]
- experience: [{company, title, duration, description}]
- projects: [{name, role, description, metrics}]
- education: [{school, degree, major, graduation}]
- target_role: (string)
- summary: (string)
- meta: {generated_from, user_confirmed, generated_at}

Fill all fields. Return only valid JSON."""
        return prompt

    # ── 保存 / 读取 ───────────────────────────────────────────

    def save_resume(self, resume: dict, path: str = None) -> bool:
        """保存简历到 resume.json"""
        dest = Path(path or str(DEFAULT_RESUME_PATH)).expanduser()
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            dest.write_text(json.dumps(resume, ensure_ascii=False, indent=2))
            return True
        except Exception as e:
            print(f"[ResumeGenerator] save failed: {e}")
            return False

    def load_resume(self, path: str = None) -> Optional[dict]:
        """读取已有简历"""
        src = Path(path or str(DEFAULT_RESUME_PATH)).expanduser()
        if not src.exists():
            return None
        try:
            return json.loads(src.read_text())
        except Exception:
            return None

    def _empty_resume(self, target_role: str = None) -> dict:
        return {
            "name": "Your Name",
            "contact": {"phone": "", "email": "", "location": ""},
            "skills": [],
            "experience": [],
            "projects": [],
            "education": [],
            "target_role": target_role or "",
            "summary": "",
            "meta": {
                "generated_from": "digital_footprint",
                "user_confirmed": False,
                "generated_at": datetime.now().isoformat(),
                "projects_count": 0,
            }
        }

    # ── HTML 预览 ─────────────────────────────────────────────

    def generate_html(self, resume: dict = None) -> str:
        """生成简历 HTML 预览"""
        r = resume or self.load_resume()
        if not r:
            return "<p>No resume found. Generate one first.</p>"
        return self._render_html(r)

    def _render_html(self, r: dict) -> str:
        skills_html = ' '.join(
            f'<span class="skill-tag">{s}</span>' for s in r.get('skills', [])
        )
        projects_html = ''
        for proj in r.get('projects', []):
            metrics_html = ''
            if proj.get('metrics'):
                metrics_html = f'<p class="metrics">Result: {proj["metrics"]}</p>'
            tech_html = ''
            if proj.get('tech_stack'):
                tech_html = ' | '.join(proj['tech_stack'])
            projects_html += f'''
        <div class="project">
            <h3>{proj.get("name","")} <small>| {proj.get("role","Member")}</small></h3>
            {"<p class='tech'>" + tech_html + "</p>" if tech_html else ""}
            <p>{proj.get("description","")}</p>
            {metrics_html}
        </div>'''

        exp_html = ''
        for exp in r.get('experience', []):
            exp_html += f'''
        <div class="experience">
            <h3>{exp.get("company","")} — {exp.get("title","")}</h3>
            <p class="duration">{exp.get("duration","")}</p>
            <p>{exp.get("description","")}</p>
        </div>'''

        contact = r.get('contact', {})
        contact_parts = [contact.get('phone',''), contact.get('email',''),
                         contact.get('location','')]
        contact_str = ' | '.join(p for p in contact_parts if p)

        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>{r.get('name','')} - Resume</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:800px;margin:40px auto;padding:0 20px;color:#333}}
h1{{margin-bottom:4px}}h2{{margin-top:28px;border-bottom:2px solid #2563eb;padding-bottom:4px}}
.contact{{color:#666;margin-bottom:8px;font-size:14px}}
.skill-tag{{background:#dbeafe;color:#1e40af;padding:2px 10px;border-radius:12px;font-size:12px;margin:2px;display:inline-block}}
.project,.experience{{margin-bottom:20px;padding:12px;background:#f8fafc;border-radius:8px}}
.project h3,.experience h3{{margin:0 0 4px;color:#1e40af}}
.duration,.tech{{color:#666;font-size:13px;margin:2px 0 6px}}
.metrics{{color:#059669;font-weight:600}}
.summary{{background:#eff6ff;padding:16px;border-radius:8px;margin:16px 0}}
</style></head><body>
<h1>{r.get('name','')}</h1>
<p class="contact">{contact_str}</p>
<div class="summary"><strong>Summary</strong><p>{r.get('summary','')}</p></div>
<h2>Skills</h2><p>{skills_html}</p>
<h2>Experience</h2>{exp_html or '<p>Experience data will be filled in after confirmation.</p>'}
<h2>Projects</h2>{projects_html or '<p>No projects found.</p>'}
</body></html>"""

# ─────────────────────────────────────────────────────────────
# generate_html_file — 生成含内联数据的自包含 HTML
# ─────────────────────────────────────────────────────────────

    def generate_html_file(self, resume: dict = None, output_path: str = None) -> str:
        """
        生成含内联数据的自包含 HTML 文件（可独立打开，无跨域限制）。
        简历 JSON 作为 <script id="resume-data"> 注入，
        JS 优先读取内联数据，无需跨域 fetch。

        Args:
            resume: 简历 dict（None 时从默认路径加载）
            output_path: 输出文件路径（None 时写入 preview.html 同目录）

        Returns:
            HTML 文件路径
        """
        r = resume or self.load_resume()
        if not r:
            r = {
                "name": "未找到简历",
                "contact": {},
                "skills": [],
                "experience": [],
                "projects": [],
                "education": [],
                "summary": "请先生成简历数据",
            }

        resume_json = json.dumps(r, ensure_ascii=False)
        inline_data = f'<script id="resume-data" type="application/json">{resume_json}</script>'
        html_template = self._load_html_template()
        html = html_template.replace('</body>', inline_data + '\n</body>')

        dest = Path(output_path) if output_path else (Path(__file__).parent / 'preview.html')
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html, encoding='utf-8')
        return str(dest)

    def _load_html_template(self) -> str:
        """加载 HTML 模板文件"""
        tmpl_path = Path(__file__).parent / 'preview.html'
        if tmpl_path.exists():
            return tmpl_path.read_text(encoding='utf-8')
        return self._inline_html_template()

    def _inline_html_template(self) -> str:
        """内联 HTML 模板（fallback）"""
        return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>简历预览 - JobTracer</title>
  <style>
    :root{--primary:#2563eb;--primary-light:#dbeafe;--primary-dark:#1e40af;
          --bg:#f8fafc;--text:#333;--text-muted:#666;--success:#059669;--border:#e2e8f0}
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC',
         'Hiragino Sans GB','Microsoft YaHei',sans-serif;color:var(--text);
         line-height:1.6;background:#f1f5f9;min-height:100vh}
    .resume-wrapper{max-width:800px;margin:0 auto;padding:20px}
    .toolbar{display:flex;justify-content:flex-end;gap:10px;margin-bottom:16px}
    .btn{background:white;border:1px solid var(--border);border-radius:6px;
        padding:6px 14px;font-size:13px;cursor:pointer;color:var(--text-muted);
        transition:all .2s;text-decoration:none;display:inline-flex;align-items:center;gap:4px}
    .btn:hover{background:var(--primary-light);color:var(--primary-dark);border-color:var(--primary)}
    .resume{background:white;padding:40px;border-radius:12px;
            box-shadow:0 4px 24px rgba(0,0,0,.08);margin-bottom:40px}
    .resume-header{margin-bottom:20px}
    .name{font-size:28px;font-weight:700;color:var(--primary-dark);
           border-bottom:2px solid var(--primary);padding-bottom:10px;margin-bottom:8px}
    .contact{color:var(--text-muted);font-size:14px}
    .contact span{margin-right:12px}
    .section{margin-bottom:24px}
    .section h2{font-size:16px;font-weight:600;color:var(--primary);
               border-bottom:2px solid var(--primary-light);padding-bottom:4px;margin-bottom:12px}
    .summary-box{background:#eff6ff;padding:14px 16px;border-radius:8px;font-size:14px}
    .skills-cloud{display:flex;flex-wrap:wrap;gap:6px}
    .skill-tag{background:var(--primary-light);color:var(--primary-dark);
              padding:3px 11px;border-radius:14px;font-size:13px;font-weight:500}
    .project-card{margin-bottom:16px;padding:14px 16px;background:var(--bg);
                 border-radius:8px;border-left:3px solid var(--primary)}
    .project-card h3{font-size:15px;color:var(--primary-dark);margin-bottom:4px}
    .project-card h3 small{color:var(--text-muted);font-weight:400;font-size:13px}
    .project-tech{color:var(--text-muted);font-size:12px;margin-bottom:6px}
    .project-metrics{color:var(--success);font-weight:600;font-size:13px}
    .timeline{position:relative;padding-left:20px}
    .timeline::before{content:'';position:absolute;left:6px;top:4px;bottom:4px;
                      width:2px;background:var(--primary-light)}
    .timeline-item{position:relative;margin-bottom:16px}
    .timeline-item::before{content:'';position:absolute;left:-17px;top:6px;
                           width:10px;height:10px;border-radius:50%;background:var(--primary);
                           border:2px solid white}
    .timeline-item h3{font-size:15px;color:var(--primary-dark);margin-bottom:2px}
    .timeline-item .company-duration{color:var(--text-muted);font-size:13px;margin-bottom:4px}
    .edu-item{padding:8px 12px;background:var(--bg);border-radius:6px;font-size:14px}
    .empty-hint{color:var(--text-muted);font-size:13px;font-style:italic;padding:8px 0}
    @media print{body{background:white}.resume{box-shadow:none;padding:0;margin:0}
                 .toolbar{display:none}.resume{page-break-inside:avoid}
                 .project-card,.timeline-item{page-break-inside:avoid}}
    @media(max-width:600px){.resume{padding:20px}.name{font-size:22px}.resume-wrapper{padding:10px}}
  </style>
</head>
<body>
<div class="resume-wrapper">
  <div class="toolbar">
    <button class="btn" onclick="window.print()">🖨️ 打印/导出 PDF</button>
    <button class="btn" onclick="location.reload()">🔄 刷新</button>
  </div>
  <div class="resume" id="resume-root">
    <div class="resume-header">
      <h1 class="name" id="resume-name">加载中...</h1>
      <p class="contact" id="resume-contact"></p>
    </div>
    <div class="section" id="section-summary">
      <h2>个人总结</h2>
      <div class="summary-box" id="resume-summary"></div>
    </div>
    <div class="section" id="section-skills">
      <h2>技术技能</h2>
      <div class="skills-cloud" id="resume-skills"></div>
    </div>
    <div class="section" id="section-experience">
      <h2>工作经历</h2>
      <div class="timeline" id="resume-experience">
        <p class="empty-hint">工作经历数据待确认后填充</p>
      </div>
    </div>
    <div class="section" id="section-projects">
      <h2>项目经历</h2>
      <div id="resume-projects"><p class="empty-hint">暂无项目数据</p></div>
    </div>
    <div class="section" id="section-education">
      <h2>教育背景</h2>
      <div id="resume-education"><p class="empty-hint">教育背景数据待确认后填充</p></div>
    </div>
  </div>
</div>
<script>
(function(){
  function getInlineResume(){
    var el=document.getElementById('resume-data');
    if(el)try{return JSON.parse(el.textContent)}catch(e){}
    try{var s=localStorage.getItem('jobtracer_resume');if(s)return JSON.parse(s)}catch(e){}
    return null
  }
  function esc(s){if(!s)return'';return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
  function render(r){
    if(!r){document.getElementById('resume-name').textContent='⚠️ 简历未找到';return}
    document.getElementById('resume-name').textContent=r.name||'未填写姓名';
    var c=r.contact||{},
        parts=[c.phone?'📱 '+c.phone:'',c.email?'✉️ '+c.email:'',c.location?'📍 '+c.location:''].filter(Boolean);
    document.getElementById('resume-contact').innerHTML=parts.join(' <span>|</span> ');
    document.getElementById('resume-summary').textContent=r.summary||'暂无个人总结';
    var sk=document.getElementById('resume-skills');
    if((r.skills||[]).length)sk.innerHTML=r.skills.map(function(s){return'<span class="skill-tag">'+esc(s)+'</span>'}).join('');
    else sk.innerHTML='<span class="empty-hint">暂无技能数据</span>';
    var exp=document.getElementById('resume-experience');
    if((r.experience||[]).length)exp.innerHTML=r.experience.map(function(e){return'<div class="timeline-item"><h3>'+esc(e.company||'')+' — '+esc(e.title||'')+'</h3><p class="company-duration">'+esc(e.duration||'')+'</p><p>'+esc(e.description||'')+'</p></div>'}).join('');
    var proj=document.getElementById('resume-projects');
    if((r.projects||[]).length)proj.innerHTML=r.projects.map(function(p){
      var tech=(p.tech_stack||[]).join(' | ');
      return'<div class="project-card"><h3>'+esc(p.name||'')+' <small>| '+esc(p.role||'Member')+'</small></h3>'+
             (tech?'<p class="project-tech">'+esc(tech)+'</p>':'')+
             '<p>'+esc(p.description||'')+'</p>'+
             (p.metrics?'<p class="project-metrics">🏆 '+esc(p.metrics)+'</p>':'')+'</div>'
    }).join('');
    var edu=document.getElementById('resume-education');
    if((r.education||[]).length)edu.innerHTML=r.education.map(function(e){return'<div class="edu-item"><strong>'+esc(e.school||'')+'</strong> | '+esc(e.degree||'')+' '+esc(e.major||'')+' | '+esc(e.graduation||e.graduation_year||'')+'</div>'}).join('');
    if(r.meta&&r.meta.user_confirmed)document.querySelector('.resume').style.borderTop='4px solid #059669'
  }
  render(getInlineResume())
})()
</script>
</body>
</html>'''
