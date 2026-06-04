#!/usr/bin/env python3
"""
Enhanced Deep Clustering - Apply better summaries to top merged projects
"""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

PROJECTS_DIR = Path("~/.jobtracer/footprint/projects").expanduser()

# Enhanced summaries for major projects based on content analysis
MAJOR_PROJECT_SUMMARIES = {
    "deer-flow": {
        "project_name": "deer-flow",
        "background": "DeerFlow是一个开源的多Agent协作框架，基于LangGraph构建，支持多智能体工作流编排和外部工具扩展。",
        "deliverables": [
            "Backend API (FastAPI + LangGraph)",
            "Frontend (Next.js/React)",
            "Docker部署配置",
            "多Agent协调引擎",
            "文档 (中/英/日)"
        ],
        "results": "完整的开源多Agent框架，支持私有化部署，可对接多种LLM提供商（OpenAI、Claude、DeepSeek等）",
        "solutions": "LangGraph状态机 + FastAPI后端 + React前端，Docker容器化部署，支持extension扩展",
        "tags": ["multi-agent", "langgraph", "python", "fastapi", "react"],
        "significance": "high"
    },
    "mpktchioge2itirq": {
        "project_name": "mpktchioge2itirq",
        "background": "Agent Cowork是一个多Agent协作平台，支持A2A协议（Agent-to-Agent），实现外部智能体注册、任务分发和协作闭环。",
        "deliverables": [
            "API服务 (NestJS/TypeScript)",
            "Web前端 (Vue/TypeScript)",
            "A2A协议适配层",
            "外部Agent注册中心",
            "Smart Routing引擎",
            "E2E测试套件"
        ],
        "results": "实现了完整的Agent协作平台，支持外部Agent通过Adapter协议接入，支持多Agent任务编排和状态机管理",
        "solutions": "NestJS + TypeScript后端，Vue 3前端，A2A协议，Agent Gateway适配层，Smart Routing路由引擎",
        "tags": ["multi-agent", "a2a-protocol", "typescript", "nestjs", "vue"],
        "significance": "high"
    },
    "openclaw-workspace": {
        "project_name": "openclaw-workspace",
        "background": "OpenClaw工作区是用户的AI助手主工作空间，包含各种AI工具配置、技能、文档和工作日志。",
        "deliverables": [
            "AI工具配置 (skills/)",
            "工作日志 (memory/)",
            "AI报价助手相关文档",
            "仓配网络优化分析文件",
            "华鼎云仓产品方案"
        ],
        "results": "完整的AI助手工作环境，积累了丰富的供应链/物流/AI产品分析经验",
        "solutions": "OpenClaw平台 + 飞书集成 + 多源文档管理",
        "tags": ["ai-assistant", "openclaw", "supply-chain", "documentation"],
        "significance": "high"
    },
    "free-claude-code": {
        "project_name": "free-claude-code",
        "background": "Free Claude Code是一个开源代理项目，将Claude Code CLI等工具路由到免费的LLM提供商（NVIDIA NIM、OpenRouter、DeepSeek、LM Studio等），绕过Anthropic官方API限制。",
        "deliverables": [
            "API代理服务 (Python/FastAPI)",
            "Provider抽象层 (支持多家LLM)",
            "Anthropic协议兼容层",
            "测试套件 (smoke/tests)",
            "CLI工具",
            "Messaging模块"
        ],
        "results": "实现了免费使用Claude Code的方案，支持多种LLM后端，代码质量高（类型检查、测试覆盖、linting完备）",
        "solutions": "FastAPI + Python 3.14，OpenAI兼容接口，Anthropic消息转换层，多Provider动态路由",
        "tags": ["proxy", "anthropic", "openai-compatible", "python", "fastapi"],
        "significance": "high"
    },
    "other_数弈文档汇总": {
        "project_name": "shuyi-documents",
        "background": "数弈产品文档汇总，包含供应链优化相关的功能模块设计、领域模型、MRP算法等技术文档。",
        "deliverables": [
            "功能模块设计文档",
            "领域模型设计",
            "MRP算法说明",
            "产销协同计划文档",
            "生产排程计划文档"
        ],
        "results": "数弈供应链优化产品的完整技术文档体系，覆盖需求分析、功能设计、算法实现",
        "solutions": "MPS/MRP算法，产销协同优化，生产排程计划",
        "tags": ["supply-chain", "mrp", "planning", "documentation"],
        "significance": "high"
    },
    "other_蜀海": {
        "project_name": "shuhai-documents",
        "background": "蜀海供应链相关项目，包含库存计划优化、片区备货、发版评审等业务文档。",
        "deliverables": [
            "库存计划优化测试报告",
            "片区备货导入功能",
            "发版评审纪要",
            "BU2库存计划文档"
        ],
        "results": "蜀海B2B库存优化系统的发版文档和测试报告",
        "solutions": "库存优化算法，片区备货策略",
        "tags": ["inventory-optimization", "supply-chain", "documentation"],
        "significance": "high"
    },
    "openclaw-system": {
        "project_name": "openclaw-system",
        "background": "OpenClaw核心系统文件，包含系统配置、凭证管理、定时任务等基础设施。",
        "deliverables": [
            "系统配置文件",
            "凭证管理 (credentials/)",
            "定时任务脚本 (cron/)",
            "浏览器自动化",
            "Canvas渲染"
        ],
        "results": "OpenClaw AI助手平台的核心基础设施代码",
        "solutions": "OpenClaw平台核心模块，Python/JS混合架构",
        "tags": ["openclaw", "platform", "infrastructure"],
        "significance": "high"
    },
    "ai-kefu": {
        "project_name": "ai-customer-service",
        "background": "AI客服赋能项目，包含智能客服的技术方案、技能配置和工具集。",
        "deliverables": [
            "AI客服技术方案",
            "技能配置 (skills/)",
            "工具集 (tools/)"
        ],
        "results": "完整的AI客服赋能解决方案，支持多渠道接入",
        "solutions": "AI对话系统 + 知识库 + 工具调用",
        "tags": ["ai-customer-service", "chatbot", "knowledge-base"],
        "significance": "high"
    },
    "dingtalk-doc-plugin": {
        "project_name": "dingtalk-doc-plugin",
        "background": "钉钉文档插件，为OpenClaw提供钉钉文档读取和编辑能力。",
        "deliverables": [
            "钉钉API集成",
            "文档读取/编辑",
            "单元测试",
            "覆盖率报告"
        ],
        "results": "OpenClaw平台的钉钉文档插件，支持完整的文档操作",
        "solutions": "钉钉OpenAPI + MCP协议适配",
        "tags": ["dingtalk", "mcp", "plugin", "typescript"],
        "significance": "medium"
    },
    "playwright-automation": {
        "project_name": "playwright-automation",
        "background": "基于Playwright的自动化测试和爬虫项目，用于舜宇光学B2B系统的自动化操作。",
        "deliverables": [
            "登录探针 (login_probe.js)",
            "库存查询自动化",
            "菜单树抓取",
            "流程自动化脚本"
        ],
        "results": "实现了舜宇光学B2B系统的自动化操作，包括登录、库存查询、订单提交等",
        "solutions": "Playwright + Node.js，自动化登录和业务流程",
        "tags": ["playwright", "automation", "javascript", "b2b"],
        "significance": "medium"
    }
}

def get_project_name_from_id(project_id: str) -> str:
    """Extract clean project name from merged ID"""
    if project_id.startswith("merged_"):
        return project_id.replace("merged_", "")
    return project_id

def update_projects_index():
    """Update projects_index.json with enhanced summaries"""
    index_file = PROJECTS_DIR / "projects_index.json"
    
    with open(index_file) as f:
        index_data = json.load(f)
    
    updated_count = 0
    
    for project in index_data["projects"]:
        project_name = get_project_name_from_id(project["project_id"])
        
        if project_name in MAJOR_PROJECT_SUMMARIES:
            summary = MAJOR_PROJECT_SUMMARIES[project_name]
            project["project_name"] = summary["project_name"]
            project["background"] = summary["background"]
            project["deliverables"] = summary["deliverables"]
            project["results"] = summary["results"]
            project["solutions"] = summary["solutions"]
            project["tags"] = summary["tags"]
            project["significance"] = summary["significance"]
            project["summary_source"] = "enhanced-rule-based"
            updated_count += 1
        else:
            # Enhance with path-based inference
            if project.get("file_count", 0) > 20:
                path = project.get("source", "")
                tags = project.get("tags", [])
                
                # Clean up tags
                tags = [t for t in tags if t not in ["local", "text"]]
                project["tags"] = tags[:8]
                
                # Infer better background
                if project.get("is_merged"):
                    project["background"] = f"合并的项目集合，包含 {project.get('file_count', 0)} 个文件"
    
    index_data["generated_at"] = datetime.now().isoformat()
    index_data["summary_method"] = "enhanced-rule-based"
    index_data["updated_projects"] = updated_count
    
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Updated {updated_count} projects with enhanced summaries")
    return index_data

def update_index_md_files():
    """Update _index.md files for top projects with enhanced summaries"""
    index_file = PROJECTS_DIR / "projects_index.json"
    
    with open(index_file) as f:
        index_data = json.load(f)
    
    updated = 0
    
    for project in index_data["projects"]:
        if project.get("significance") != "high":
            continue
        
        project_name = get_project_name_from_id(project["project_id"])
        
        # Only update if we have an enhanced summary
        if project_name not in MAJOR_PROJECT_SUMMARIES:
            continue
        
        summary = MAJOR_PROJECT_SUMMARIES[project_name]
        
        # Find first sub-project to update (the merged project ID points to... well, we need to find the actual project dirs)
        # For merged projects, there isn't a single dir to update - the info is in projects_index.json
        # For non-merged projects, update their _index.md
        
        if not project.get("is_merged"):
            proj_dir = PROJECTS_DIR / project["project_id"]
            if proj_dir.exists():
                new_content = f"# {summary['project_name']}\n\n"
                new_content += f"## Project Description\n{summary['background']}\n\n"
                new_content += "## Metadata\n"
                new_content += f"- **project_id:** {project['project_id']}\n"
                new_content += f"- **confidence:** {project.get('confidence', 0.8):.2f}\n"
                new_content += f"- **source:** {project.get('source', 'local')}\n"
                new_content += f"- **significance:** {summary['significance']}\n"
                new_content += f"- **file_count:** {project.get('file_count', 0)}\n\n"
                new_content += "## AI Summary\n"
                new_content += f"**Deliverables:** {', '.join(summary['deliverables'][:5])}\n"
                new_content += f"**Results:** {summary['results']}\n"
                if summary['solutions']:
                    new_content += f"**Solutions:** {summary['solutions']}\n"
                new_content += "\n## Tags\n"
                for tag in summary['tags'][:10]:
                    new_content += f"- {tag}\n"
                new_content += "\n"
                
                index_file_md = proj_dir / "_index.md"
                if index_file_md.exists():
                    try:
                        index_file_md.write_text(new_content, encoding="utf-8")
                        updated += 1
                    except:
                        pass
    
    print(f"✅ Updated {updated} _index.md files")
    return updated

if __name__ == "__main__":
    print("🚀 Applying enhanced summaries...")
    data = update_projects_index()
    update_index_md_files()
    
    print(f"\n📊 Final Results:")
    print(f"  Total projects: {data['total_projects']}")
    print(f"  High-value: {data['high_value_count']}")
    print(f"  Merged: {data['merged_count']}")
    print(f"  Updated with enhanced summaries: {data.get('updated_projects', 0)}")
    
    print(f"\n📋 Top Projects:")
    for p in sorted(data['projects'], key=lambda x: -x.get('file_count', 0))[:15]:
        sig = p.get('significance', '?')
        name = p.get('project_name', '?')
        fc = p.get('file_count', 0)
        tags = p.get('tags', [])[:3]
        print(f"  [{sig}] {name} ({fc} files) tags={tags}")