"""LLM-based keyword extraction for JobTracer daily search

Uses LLM to analyze user's projects and resume, generates precise search keywords.
Falls back to regex method if LLM fails.
"""
import json
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger('jobtracer.daily_cron.llm_keywords')


def _get_llm_client() -> Optional[dict]:
    """Get LLM client from openclaw config"""
    try:
        config_path = Path("~/.openclaw/openclaw.json").expanduser()
        with open(config_path) as f:
            config = json.load(f)
        
        providers = config.get("models", {}).get("providers", {})
        
        # Try minimax first (default in openclaw)
        if "minimax-portal" in providers:
            cfg = providers["minimax-portal"]
            return {
                "provider": "minimax",
                "api_key": cfg.get("apiKey", ""),
                "base_url": cfg.get("baseUrl", "https://api.minimax.chat/v1"),
                "model": cfg.get("model", "MiniMax-M2.7-32K")
            }
        
        # Fallback to deepseek
        if "deepseek" in providers:
            p = providers["deepseek"]
            return {
                "provider": "deepseek",
                "api_key": p.get("apiKey", ""),
                "base_url": "https://api.deepseek.com",
                "model": "deepseek-chat"
            }
        
        # Fallback to qwen
        if "qwen-portal" in providers:
            p = providers["qwen-portal"]
            return {
                "provider": "qwen",
                "api_key": p.get("apiKey", ""),
                "base_url": "https://portal.qwen.ai/v1",
                "model": "qwen-coder"
            }
        
        return None
    except Exception as e:
        logger.debug(f"Failed to get LLM client: {e}")
        return None


def _call_llm(client: dict, prompt: str, max_tokens: int = 400) -> Optional[str]:
    """Call LLM with prompt, return text response"""
    try:
        import openai
        
        client_obj = openai.OpenAI(
            api_key=client["api_key"],
            base_url=client.get("base_url", "https://api.deepseek.com")
        )
        
        response = client_obj.chat.completions.create(
            model=client.get("model", "deepseek-chat"),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.debug(f"LLM call failed: {e}")
        return None


def _build_keyword_prompt(projects: List[dict], resume: dict) -> str:
    """Build prompt for keyword extraction"""
    
    # Build projects summary
    project_summaries = []
    for i, p in enumerate(projects[:20]):  # max 20 projects
        name = p.get('project_name', 'Unknown')
        tags = p.get('tags', [])
        solutions = p.get('solutions', '')
        desc = p.get('description', '')
        
        summary = f"{i+1}. {name}"
        if tags:
            summary += f" [标签: {', '.join(tags[:5])}]"
        if solutions:
            summary += f" | 技术: {solutions[:100]}"
        project_summaries.append(summary)
    
    # Build resume summary
    resume_summary = []
    if resume.get('name'):
        resume_summary.append(f"姓名: {resume['name']}")
    if resume.get('work_years'):
        resume_summary.append(f"工作年限: {resume['work_years']}年")
    if resume.get('skills'):
        resume_summary.append(f"技能: {', '.join(resume['skills'][:15])}")
    if resume.get('projects'):
        proj_names = [p.get('name', '') for p in resume['projects'][:5]]
        resume_summary.append(f"项目: {', '.join(proj_names)}")
    
    prompt = f"""你是求职助手。用户有以下背景：

简历信息：
{chr(10).join(resume_summary) if resume_summary else "(简历为空)"}

项目经历（来自数字足迹）：
{chr(10).join(project_summaries)}

请生成 8-12 个搜索关键词，用于在 BOSS直聘/51job 上搜索职位。

要求：
1. 关键词要体现用户的核心技能和经验
2. 包含技术栈（如 Python, Django, FastAPI, Kubernetes）
3. 包含职位方向（如 后端工程师, 产品经理, 算法工程师）
4. 包含行业领域（如 供应链, 电商, SaaS）
5. 包含具体方向（如 运筹优化, 智能调度, 数据分析）

请直接输出关键词，用逗号分隔，不要解释。例如：
Python后端, Django, FastAPI, 产品经理, 供应链, 运筹优化, 后端工程师, 数据分析"""
    
    return prompt


def _parse_llm_response(response: str) -> List[str]:
    """Parse LLM response, extract keywords"""
    if not response:
        return []
    
    # Split by comma, newline, or other delimiters
    import re
    keywords = re.split(r'[,，\n\r]+', response.strip())
    
    result = []
    for kw in keywords:
        kw = kw.strip()
        # Filter out empty, too short, or too long
        if len(kw) >= 2 and len(kw) <= 20 and not kw.startswith('#'):
            result.append(kw)
    
    return result


async def _extract_keywords_by_llm(projects: List[dict], resume: dict) -> List[str]:
    """
    用 LLM 理解用户背景，生成精准搜索关键词
    
    Args:
        projects: 项目列表（来自 projects_index.json）
        resume: 简历 dict
    
    Returns:
        关键词列表，如果 LLM 失败返回空列表
    """
    # Get LLM client
    client = _get_llm_client()
    if not client:
        logger.debug("No LLM client available for keyword extraction")
        return []
    
    logger.info(f"Using LLM ({client['provider']}) for keyword extraction")
    
    # Build prompt
    prompt = _build_keyword_prompt(projects, resume)
    
    # Call LLM
    response = _call_llm(client, prompt)
    if not response:
        logger.warning("LLM keyword extraction failed")
        return []
    
    # Parse response
    keywords = _parse_llm_response(response)
    
    if keywords:
        logger.info(f"LLM extracted {len(keywords)} keywords: {keywords[:5]}...")
    else:
        logger.warning(f"LLM returned empty keywords. Response: {response[:100]}")
    
    return keywords


# Sync wrapper for non-async context
def extract_keywords_by_llm_sync(projects: List[dict], resume: dict) -> List[str]:
    """Synchronous wrapper for _extract_keywords_by_llm"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Create new loop if current is already running
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _extract_keywords_by_llm(projects, resume))
                return future.result(timeout=30)
        else:
            return asyncio.run(_extract_keywords_by_llm(projects, resume))
    except Exception as e:
        logger.debug(f"LLM extraction failed: {e}")
        return []