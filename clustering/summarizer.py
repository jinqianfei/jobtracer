"""
clustering/summarizer.py
NEW-4: 生成项目摘要

对每个项目的文件内容，生成4段式摘要：
- background - 项目背景
- deliverables - 项目产出
- results - 项目成果
- solutions - 技术方案

优先用 docs/*.md 文件；无 LLM 时用规则方法提取关键信息。
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

PROJECTS_DIR = Path("~/.jobtracer/footprint/projects").expanduser()

# LLM 客户端（可选）
_LLM_CLIENT = None


def set_llm_client(client):
    """设置 LLM 客户端"""
    global _LLM_CLIENT
    _LLM_CLIENT = client


def _extract_title(content: str) -> str:
    """提取标题"""
    lines = content.split('\n')
    for line in lines[:10]:
        line = line.strip()
        if line.startswith('# '):
            return line[2:].strip()
        if line.startswith('## '):
            return line[3:].strip()
    # 取第一行非空
    for line in lines[:5]:
        line = line.strip()
        if line and not line.startswith('#'):
            return line[:80]
    return ""


def _extract_keywords(content: str, top_n: int = 10) -> List[str]:
    """提取关键词"""
    # 高频词（停用词过滤）
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
        'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
        'this', 'that', 'these', 'those', 'it', 'its', 'they', 'them', 'their',
        'we', 'you', 'i', '我', '你', '他', '她', '它', '的', '是', '在', '了', '和', '与',
        '及', '或', '等', '于', '对', '从', '到', '把', '被', '让', '给', '向', '向',
        '以下', '以上', '其中', '以及', '并且', '然后', '因此', '所以', '因为',
        '如果', '虽然', '但', '却', '又', '也', '还', '只', '都', '很', '更', '最',
        'function', 'class', 'def', 'import', 'export', 'return', 'var', 'let', 'const',
        'async', 'await', 'try', 'catch', 'throw', 'new', 'self', 'this', 'if', 'else',
        'for', 'while', 'switch', 'case', 'break', 'continue', 'default',
    }
    words = re.findall(r'[a-zA-Z_][a-zA-Z0-9_\-]{2,}', content.lower())
    freq = {}
    for w in words:
        if w not in stop_words and len(w) > 2:
            freq[w] = freq.get(w, 0) + 1
    sorted_words = sorted(freq.items(), key=lambda x: -x[1])
    return [w for w, _ in sorted_words[:top_n]]


def _extract_first_paragraph(content: str, max_chars: int = 500) -> str:
    """提取第一段"""
    para_pattern = re.compile(r'(.+?)(\n\n|\r\n\r\n|$)', re.DOTALL)
    for match in para_pattern.finditer(content):
        para = match.group(1).strip()
        if len(para) > 50:
            return para[:max_chars]
    return content[:max_chars]


def _rule_based_summary(project_dir: Path) -> Dict[str, str]:
    """
    规则方法生成摘要

    策略：
    1. 从 docs/*.md 提取标题、首段落、关键词
    2. 从 code_snippets 提取语言/框架信息
    3. 从目录名和项目描述提取背景
    """
    summary = {
        'background': '',
        'deliverables': '',
        'results': '',
        'solutions': ''
    }

    # 1. 收集 docs 内容
    docs_dir = project_dir / 'docs'
    md_files = list(docs_dir.glob('*.md')) if docs_dir.exists() else []
    all_doc_content = []

    for md_file in md_files[:5]:  # 最多5个md
        try:
            content = md_file.read_text(encoding='utf-8', errors='ignore')
            all_doc_content.append(content)
        except Exception:
            pass

    combined_doc = '\n'.join(all_doc_content)

    # 2. 收集 code_snippets 扩展名
    code_dir = project_dir / 'code_snippets'
    code_files = list(code_dir.glob('*')) if code_dir.exists() else []
    code_files = [f for f in code_files if not f.name.endswith('.path')]
    exts = set(f.suffix.lower() for f in code_files if f.suffix)

    # 3. 生成 background
    metadata_path = project_dir / 'metadata.json'
    if metadata_path.exists():
        try:
            meta = json.loads(metadata_path.read_text(encoding='utf-8'))
            desc = meta.get('description', '')
            name = meta.get('project_name', '')
            tags = meta.get('tags', [])

            if desc:
                # 从路径提取关键信息
                # desc 格式: "Files from ~/path"
                if 'Files from' in desc:
                    path_info = desc.replace('Files from ', '')
                    summary['background'] = f"项目位于 {path_info}，包含 {meta.get('file_count', 0)} 个文件"
                    if tags:
                        summary['background'] += f"，主要涉及 {', '.join(tags)} 相关技术"
        except Exception:
            pass

    # 4. 生成 deliverables
    if combined_doc:
        # 提取标题
        title = _extract_title(combined_doc)
        first_para = _extract_first_paragraph(combined_doc)
        if title and title != _extract_title(first_para):
            summary['deliverables'] = f"文档标题：{title}"
        elif first_para:
            summary['deliverables'] = first_para[:200]
        else:
            summary['deliverables'] = f"包含 {len(md_files)} 个文档文件"
    else:
        summary['deliverables'] = f"包含 {len(code_files)} 个代码文件"

    # 5. 生成 results
    if code_files:
        ext_summary = ', '.join(sorted(exts)) if exts else 'unknown'
        summary['results'] = f"产出 {len(code_files)} 个代码文件（{ext_summary}）"
    if combined_doc:
        keywords = _extract_keywords(combined_doc, 5)
        if keywords:
            if summary['results']:
                summary['results'] += f"，关键词：{', '.join(keywords)}"
            else:
                summary['results'] = f"涉及主题：{', '.join(keywords)}"

    # 6. 生成 solutions
    tech_keywords = {
        'python': ['python', 'flask', 'django', 'fastapi', 'pytorch', 'tensorflow'],
        'javascript': ['javascript', 'nodejs', 'react', 'vue', 'angular', 'express'],
        'typescript': ['typescript', 'ts', 'nestjs', 'nextjs'],
        'java': ['java', 'spring', 'maven', 'gradle'],
        'go': ['go', 'golang'],
        'database': ['sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch'],
        'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'k8s'],
        'ai': ['ai', 'llm', 'openai', 'claude', 'gemini', 'agent', 'gpt'],
    }

    all_content = combined_doc
    for cf in code_files[:20]:
        try:
            all_content += '\n' + cf.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            pass

    all_content_lower = all_content.lower()
    detected_tech = []
    for category, terms in tech_keywords.items():
        for term in terms:
            if term in all_content_lower:
                detected_tech.append(term)
                break

    if detected_tech:
        summary['solutions'] = f"使用技术栈：{', '.join(detected_tech[:8])}"
    elif exts:
        ext_map = {
            '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript',
            '.go': 'Go', '.java': 'Java', '.md': 'Markdown',
            '.json': 'JSON', '.yaml': 'YAML', '.yml': 'YAML',
        }
        tech_names = [ext_map.get(e, e[1:].upper()) for e in exts if e in ext_map]
        if tech_names:
            summary['solutions'] = f"主要语言/格式：{', '.join(tech_names)}"

    return summary


def generate_summary(project_id: str, llm_client=None) -> Dict[str, str]:
    """生成单个项目的摘要"""
    project_dir = PROJECTS_DIR / project_id
    if not project_dir.exists():
        return {}

    # 尝试 LLM 方法
    if llm_client or _LLM_CLIENT:
        client = llm_client or _LLM_CLIENT
        try:
            summary = _llm_summary(project_dir, client)
            if summary and any(summary.values()):
                return summary
        except Exception as e:
            print(f"[summarizer] LLM failed for {project_id}: {e}")

    # 回退到规则方法
    return _rule_based_summary(project_dir)


def _llm_summary(project_dir: Path, client) -> Dict[str, str]:
    """使用 LLM 生成摘要"""
    docs_dir = project_dir / 'docs'
    md_files = list(docs_dir.glob('*.md'))[:3] if docs_dir.exists() else []
    code_files = list((project_dir / 'code_snippets').glob('*'))[:10] if (project_dir / 'code_snippets').exists() else []
    code_files = [f for f in code_files if not f.name.endswith('.path')]

    combined = []
    for f in md_files:
        try:
            combined.append(f"# File: {f.name}\n{f.read_text(encoding='utf-8', errors='ignore')[:3000]}")
        except Exception:
            pass
    for f in code_files[:5]:
        try:
            combined.append(f"# File: {f.name}\n{f.read_text(encoding='utf-8', errors='ignore')[:1000]}")
        except Exception:
            pass

    content = '\n\n---\n\n'.join(combined)

    prompt = f"""为以下项目内容生成四段式摘要：

## 项目背景 (background)
简述这个项目是什么、做什么的

## 项目产出 (deliverables)
列出主要交付物（文件、文档、代码模块）

## 项目成果 (results)
描述取得了什么结果或进展

## 技术方案 (solutions)
使用了哪些技术栈或解决方案

---

项目内容：
{content[:8000]}

输出 JSON 格式：
{{
    "background": "...",
    "deliverables": "...",
    "results": "...",
    "solutions": "..."
}}
"""

    import asyncio
    response = asyncio.get_event_loop().run_until_complete(
        client.generate(prompt, schema='json')
    )
    result = json.loads(response)
    return {k: str(v) for k, v in result.items()}


def update_project_index(project_id: str, summary: Dict[str, str]) -> bool:
    """更新项目的 _index.md 和 metadata.json"""
    project_dir = PROJECTS_DIR / project_id
    if not project_dir.exists():
        return False

    # 1. 更新 _index.md，追加 Summary 部分
    index_path = project_dir / '_index.md'
    if index_path.exists():
        content = index_path.read_text(encoding='utf-8')
        if '## Summary' not in content:
            summary_section = f"""

## Summary

**Background:** {summary.get('background', 'N/A')}
**Deliverables:** {summary.get('deliverables', 'N/A')}
**Results:** {summary.get('results', 'N/A')}
**Solutions:** {summary.get('solutions', 'N/A')}
"""
            index_path.write_text(content + summary_section, encoding='utf-8')

    # 2. 更新 metadata.json
    metadata_path = project_dir / 'metadata.json'
    if metadata_path.exists():
        try:
            meta = json.loads(metadata_path.read_text(encoding='utf-8'))
            meta.update({
                'background': summary.get('background', ''),
                'deliverables': summary.get('deliverables', ''),
                'results': summary.get('results', ''),
                'solutions': summary.get('solutions', ''),
                'summary_updated_at': datetime.now().isoformat()
            })
            metadata_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception as e:
            print(f"[summarizer] Failed to update metadata for {project_id}: {e}")
            return False

    return True


def run_all(llm_client=None) -> Dict:
    """对所有项目生成摘要"""
    results = {}
    project_dirs = sorted(PROJECTS_DIR.iterdir())
    total = len(project_dirs)

    print(f"[summarizer] Found {total} projects to summarize")

    for i, project_dir in enumerate(project_dirs):
        if not project_dir.is_dir():
            continue
        project_id = project_dir.name

        if (i + 1) % 50 == 0 or i == 0:
            print(f"[summarizer] Processing [{i+1}/{total}]: {project_id}")

        try:
            summary = generate_summary(project_id, llm_client=llm_client)
            if summary and any(summary.values()):
                update_project_index(project_id, summary)
                results[project_id] = summary
        except Exception as e:
            results[project_id] = {'error': str(e)}

    print(f"\n=== Summary ===")
    print(f"Projects summarized: {len(results)}")
    print(f"Projects with errors: {sum(1 for v in results.values() if 'error' in v)}")

    # 保存全局结果
    output_path = PROJECTS_DIR.parent / "summaries.json"
    output_path.write_text(
        json.dumps({'results': results, 'timestamp': datetime.now().isoformat()}, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    print(f"Results saved to {output_path}")

    return results


if __name__ == '__main__':
    import sys
    print("Running summarizer...")
    results = run_all()