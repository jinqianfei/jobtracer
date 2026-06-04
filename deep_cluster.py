#!/usr/bin/env python3
"""
Deep Clustering for JobTracer Projects
升级聚类：从「路径分组」到「内容理解级项目聚类」
"""

import json
import os
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import re

PROJECTS_DIR = Path("~/.jobtracer/footprint/projects").expanduser()

# LLM Client
def get_llm_client():
    """Create LLM client from openclaw config"""
    config_path = Path("~/.openclaw/openclaw.json").expanduser()
    with open(config_path) as f:
        config = json.load(f)
    
    providers = config.get("models", {}).get("providers", {})
    
    # Try minimax first (uses anthropic messages API)
    if "minimax-portal" in providers:
        return {"provider": "minimax", "config": providers["minimax-portal"]}
    
    # Fallback to deepseek
    if "deepseek" in providers:
        p = providers["deepseek"]
        return {"provider": "deepseek", "api_key": p.get("apiKey", ""), "model": "deepseek-chat"}
    
    # Fallback to qwen
    if "qwen-portal" in providers:
        p = providers["qwen-portal"]
        return {"provider": "qwen", "api_key": p.get("apiKey", ""), "model": "coder-model", "base_url": "https://portal.qwen.ai/v1"}
    
    return None

def call_llm(client, prompt, max_tokens=400):
    """Call LLM with prompt"""
    try:
        if client["provider"] == "deepseek":
            import openai
            client_obj = openai.OpenAI(api_key=client["api_key"], base_url="https://api.deepseek.com")
            response = client_obj.chat.completions.create(
                model=client["model"],
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.3
            )
            return response.choices[0].message.content
            
        elif client["provider"] == "qwen":
            import openai
            client_obj = openai.OpenAI(api_key=client["api_key"], base_url=client.get("base_url", "https://portal.qwen.ai/v1"))
            response = client_obj.chat.completions.create(
                model=client["model"],
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.3
            )
            return response.choices[0].message.content
            
        elif client["provider"] == "minimax":
            # Use minimax portal - need to check auth method
            import urllib.request
            import urllib.parse
            
            # Try using the portal's chat API directly
            cfg = client["config"]
            api_key = cfg.get("apiKey", "")
            base_url = cfg.get("baseUrl", "https://api.minimax.chat/v1")
            
            # Use openai compatible client if possible
            try:
                import openai as _openai
                # Check if it's oauth or direct key
                if api_key and not api_key.startswith("minimax-oauth"):
                    client_obj = _openai.OpenAI(api_key=api_key, base_url=base_url)
                    response = client_obj.chat.completions.create(
                        model="MiniMax-M2.7",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=max_tokens,
                        temperature=0.3
                    )
                    return response.choices[0].message.content
            except Exception as e:
                pass
            
            return f"[Minimax API not directly accessible: {str(e)[:50]}]. Using rule-based summary."
        
        return "No LLM available"
        
    except Exception as e:
        return f"LLM Error: {str(e)[:100]}"

def load_project_index(proj_dir: Path) -> dict:
    """Load a project's _index.md and metadata.json"""
    result = {
        "project_id": proj_dir.name,
        "project_name": "",
        "description": "",
        "files": [],
        "tags": [],
        "source": "local",
        "file_count": 0,
        "content_snippets": [],
        "original_path": ""
    }
    
    index_file = proj_dir / "_index.md"
    meta_file = proj_dir / "metadata.json"
    
    if meta_file.exists():
        try:
            with open(meta_file) as f:
                meta = json.load(f)
                result.update(meta)
        except:
            pass
    
    if index_file.exists():
        content = index_file.read_text(encoding="utf-8")
        
        # Extract description
        for line in content.split("\n"):
            if line.startswith("## Project Description"):
                continue
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and not stripped.startswith("##") and not stripped.startswith("- **"):
                result["description"] = stripped
                break
        
        # Extract files list
        in_files = False
        for line in content.split("\n"):
            if "## Files" in line:
                in_files = True
                continue
            if in_files and line.startswith("- **"):
                match = re.search(r'\*\*([^*]+)\*\*.*?`([^`]+)`', line)
                if match:
                    result["files"].append({"name": match.group(1), "path": match.group(2)})
            elif in_files and (line.startswith("##") or line.startswith("#")):
                break
    
    # Load content from code_snippets and docs
    snippets = []
    for cs_dir in ["code_snippets", "docs"]:
        cs_path = proj_dir / cs_dir
        if cs_path.exists():
            for f in list(cs_path.iterdir())[:10]:  # Max 10 files per dir
                if f.is_file():
                    try:
                        content = f.read_text(encoding="utf-8", errors="ignore")[:500]
                        if content.strip():
                            snippets.append({
                                "file": f.name,
                                "type": cs_dir,
                                "content": content
                            })
                    except:
                        pass
    
    result["content_snippets"] = snippets
    
    # Extract original path
    if index_file.exists():
        idx_content = index_file.read_text(encoding="utf-8")
        if "Files from " in idx_content:
            result["original_path"] = idx_content.split("Files from ")[-1].split("\n")[0]
    
    return result

def build_summary_prompt(project: dict) -> str:
    """Build LLM prompt for project summarization"""
    name = project.get("project_name", "Unknown")
    desc = project.get("description", "")
    files = project.get("files", [])[:8]
    snippets = project.get("content_snippets", [])[:4]
    
    files_text = "\n".join([f"  - {fi['name']}" for fi in files])
    
    snippets_text = ""
    for s in snippets:
        snippets_text += f"\n=== {s['file']} ===\n{s['content'][:200]}\n"
    
    prompt = f"""分析项目，生成JSON摘要：

项目: {name}
路径: {project.get('original_path', '')[:80]}
描述: {desc}

文件:
{files_text}

内容:
{snippets_text}

输出JSON（必须包含所有字段）：
{{
    "project_name": "英文名",
    "background": "1-2句背景",
    "deliverables": ["产出的文件或功能"],
    "results": "成果/价值",
    "solutions": "技术方案",
    "tags": ["标签"],
    "significance": "high/medium/low"
}}
"""
    return prompt

def rule_based_summary(project: dict) -> dict:
    """Generate summary without LLM using rules"""
    name = project.get("project_name", "")
    path = project.get("original_path", "")
    files = project.get("files", [])
    desc = project.get("description", "")
    
    # Determine significance
    significance = "medium"
    if len(files) >= 10:
        significance = "high"
    elif len(files) <= 2:
        significance = "low"
    
    # Extract tags from path and files
    tags = []
    for f in files:
        name_lower = f.get("name", "").lower()
        if ".py" in name_lower:
            tags.append("python")
        elif ".ts" in name_lower:
            tags.append("typescript")
        elif ".js" in name_lower:
            tags.append("javascript")
        elif ".md" in name_lower:
            tags.append("documentation")
    
    # Special projects
    if "jobtracer" in path.lower():
        significance = "high"
        tags.append("jobtracer")
    elif "ai-kefu" in path:
        significance = "high"
        tags.append("ai-customer-service")
    
    return {
        "background": desc or f"Project from {path.split('/')[-1]}",
        "deliverables": [f.get("name", "") for f in files[:5]],
        "results": f"{len(files)} files in project",
        "solutions": "",
        "tags": list(set(tags))[:5],
        "significance": significance,
        "confidence": 0.6
    }

def merge_projects(projects: list) -> list:
    """Merge related projects based on path patterns"""
    groups = defaultdict(list)
    
    for p in projects:
        path = p.get("original_path", "")
        
        # Key project groupings
        if "free-claude-code" in path:
            key = "free-claude-code"
        elif "mpktchioge2itirq" in path:
            key = "mpktchioge2itirq"
        elif "openclaw" in path and "workspace" in path:
            key = "openclaw-workspace"
        elif "openclaw" in path:
            key = "openclaw-system"
        elif "playwright" in path:
            key = "playwright-automation"
        elif "deer-flow" in path:
            key = "deer-flow"
        elif "jobtracer" in path.lower():
            key = "jobtracer"
        elif "ai-kefu" in path:
            key = "ai-kefu"
        elif "dingtalk" in path:
            key = "dingtalk-doc-plugin"
        elif "figma" in path:
            key = "figma-tools"
        else:
            key = f"other_{path.split('/')[-2][:20]}" if '/' in path else "other"
        
        groups[key].append(p)
    
    merged = []
    for group_name, group_projects in groups.items():
        if len(group_projects) > 1:
            # Merge into single project
            all_files = []
            all_snippets = []
            all_tags = set()
            
            for p in group_projects:
                all_files.extend(p.get("files", []))
                all_snippets.extend(p.get("content_snippets", []))
                all_tags.update(p.get("tags", []))
            
            merged.append({
                "project_id": f"merged_{group_name[:30]}",
                "project_name": group_name,
                "background": f"合并的项目集合 ({group_name})，包含 {len(group_projects)} 个子项目",
                "deliverables": [f"{len(group_projects)} 个子项目的文件集合"],
                "results": f"共 {len(all_files)} 个文件",
                "solutions": "",
                "tags": list(all_tags)[:10],
                "confidence": 0.7,
                "significance": "high" if len(group_projects) > 3 else "medium",
                "files": all_files[:100],
                "content_snippets": all_snippets[:20],
                "source": group_projects[0].get("source", "local"),
                "file_count": len(all_files),
                "is_merged": True,
                "sub_projects": [p.get("project_id") for p in group_projects]
            })
        else:
            p = group_projects[0]
            p["is_merged"] = False
            merged.append(p)
    
    return merged

def update_index_file(proj_dir: Path, project: dict):
    """Update project's _index.md with AI-generated summary"""
    index_file = proj_dir / "_index.md"
    if not index_file.exists():
        return
    
    # Read existing for file list
    existing = index_file.read_text(encoding="utf-8")
    
    new_content = f"# {project.get('project_name', 'Unknown')}\n\n"
    
    if project.get("background"):
        new_content += f"## Project Description\n{project['background']}\n\n"
    
    new_content += "## Metadata\n"
    new_content += f"- **project_id:** {project.get('project_id', proj_dir.name)}\n"
    new_content += f"- **confidence:** {project.get('confidence', 0.8):.2f}\n"
    new_content += f"- **source:** {project.get('source', 'local')}\n"
    new_content += f"- **significance:** {project.get('significance', 'medium')}\n"
    new_content += f"- **file_count:** {project.get('file_count', len(project.get('files', [])))}\n\n"
    
    if project.get("deliverables"):
        new_content += "## AI Summary\n"
        dels = project['deliverables']
        if isinstance(dels, list):
            new_content += f"**Deliverables:** {', '.join(str(d) for d in dels[:5])}\n"
        else:
            new_content += f"**Deliverables:** {dels}\n"
        if project.get("results"):
            new_content += f"**Results:** {project['results']}\n"
        if project.get("solutions"):
            new_content += f"**Solutions:** {project['solutions']}\n"
        new_content += "\n"
    
    tags = project.get("tags", [])
    if tags:
        new_content += "## Tags\n"
        for tag in tags[:10]:
            new_content += f"- {tag}\n"
        new_content += "\n"
    
    if project.get("is_merged"):
        new_content += f"**Merged from:** {len(project.get('sub_projects', []))} sub-projects\n\n"
    
    try:
        index_file.write_text(new_content, encoding="utf-8")
    except:
        pass

def main():
    print("🚀 Starting Deep Clustering...")
    
    # Get LLM client
    llm_client = get_llm_client()
    print(f"LLM Provider: {llm_client['provider'] if llm_client else 'None'}")
    
    # Load all projects
    all_project_dirs = sorted([d for d in PROJECTS_DIR.iterdir() if d.is_dir()])
    print(f"Total project dirs: {len(all_project_dirs)}")
    
    # Filter meaningful projects
    meaningful = []
    junk_patterns = ["Trash", "temp", "缓存", "Download", "__pycache__", ".pytest"]
    
    for proj_dir in all_project_dirs:
        index_file = proj_dir / "_index.md"
        if not index_file.exists():
            continue
        
        try:
            index_content = index_file.read_text(encoding="utf-8")
        except:
            continue
        
        if any(pat in index_content for pat in junk_patterns):
            continue
        
        file_count = index_content.count("\n- **")
        if file_count < 1:
            continue
        
        project = load_project_index(proj_dir)
        meaningful.append(project)
    
    print(f"Meaningful projects: {len(meaningful)}")
    
    # Process projects with LLM
    summarized = []
    high_value = []
    
    for i, project in enumerate(meaningful):
        if i % 50 == 0:
            print(f"Processing {i}/{len(meaningful)}...")
        
        has_content = len(project.get("content_snippets", [])) > 0
        has_many_files = project.get("file_count", 0) >= 5
        
        if has_content or has_many_files:
            if llm_client:
                prompt = build_summary_prompt(project)
                response = call_llm(llm_client, prompt)
                
                try:
                    summary = json.loads(response)
                    project.update(summary)
                except:
                    # Fallback to rule-based
                    rb = rule_based_summary(project)
                    project.update(rb)
                    project["llm_error"] = response[:50] if len(response) < 100 else "parse error"
            else:
                rb = rule_based_summary(project)
                project.update(rb)
            
            summarized.append(project)
            
            if project.get("significance") == "high" or project.get("file_count", 0) >= 10:
                high_value.append(project)
        else:
            project["significance"] = "low"
            project["background"] = project.get("description", "")
            summarized.append(project)
    
    print(f"Summarized: {len(summarized)}, High-value: {len(high_value)}")
    
    # Merge related projects
    merged = merge_projects(summarized)
    print(f"After merging: {len(merged)} projects")
    
    # Generate projects_index.json
    index_data = {
        "generated_at": datetime.now().isoformat(),
        "total_projects": len(merged),
        "high_value_count": len([p for p in merged if p.get("significance") == "high"]),
        "merged_count": len([p for p in merged if p.get("is_merged")]),
        "original_count": len(meaningful),
        "projects": []
    }
    
    for p in merged:
        index_entry = {
            "project_id": p["project_id"],
            "project_name": p["project_name"],
            "background": p.get("background", ""),
            "deliverables": p.get("deliverables", []),
            "results": p.get("results", ""),
            "solutions": p.get("solutions", ""),
            "tags": p.get("tags", []),
            "significance": p.get("significance", "low"),
            "file_count": p.get("file_count", len(p.get("files", []))),
            "source": p.get("source", "local"),
            "is_merged": p.get("is_merged", False),
            "confidence": p.get("confidence", 0.8)
        }
        index_data["projects"].append(index_entry)
        
        # Update first sub-project's _index.md with merged info
        if p.get("is_merged") and p.get("sub_projects"):
            first_id = p["sub_projects"][0]
            proj_dir = PROJECTS_DIR / first_id
            if proj_dir.exists():
                update_index_file(proj_dir, p)
    
    # Save projects_index.json
    index_file = PROJECTS_DIR / "projects_index.json"
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    print(f"✅ Saved projects_index.json")
    
    # Print top projects
    print(f"\n📊 Top Projects (by significance):")
    for p in sorted(merged, key=lambda x: (0 if x.get("significance")=="high" else 1 if x.get("significance")=="medium" else 2, -x.get("file_count", 0)))[:15]:
        print(f"  [{p.get('significance','?')}] {p.get('project_name','?')} ({p.get('file_count',0)} files)")
    
    return index_data

if __name__ == "__main__":
    main()