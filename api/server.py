"""
JobTracer FastAPI 服务
提供 REST API 供其他 Agent 调用
"""

import sys
from pathlib import Path
from typing import Optional, List
from contextlib import asynccontextmanager

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# ============================================================
# 数据模型
# ============================================================

class JobSearchQuery(BaseModel):
    """职位搜索查询"""
    keywords: List[str] = ["Python", "后端"]
    city: str = "上海"
    experience: str = "不限"
    degree: str = "不限"
    salary: str = "不限"
    page: int = 1
    page_size: int = 20


class JDMatchRequest(BaseModel):
    """JD匹配请求"""
    job_id: str
    resume_data: Optional[dict] = None


class ResumeUpdateRequest(BaseModel):
    """简历更新请求"""
    name: Optional[str] = None
    target_role: Optional[str] = None
    skills: Optional[List[str]] = None
    projects: Optional[List[dict]] = None


# ============================================================
# FastAPI App
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    yield
    # 关闭时
    pass


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title="JobTracer API",
        description="智能求职追踪助手 API - 供其他 Agent 调用",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 存储管理器
    storage = StorageManager()
    
    # ============================================================
    # API 路由
    # ============================================================
    
    @app.get("/")
    async def root():
        """API 根路径"""
        return {
            "name": "JobTracer API",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs"
        }
    
    @app.get("/health")
    async def health():
        """健康检查"""
        return {"status": "healthy", "service": "jobtracer"}
    
    # ---- 项目索引 ----
    
    @app.get("/projects")
    async def get_projects(
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0)
    ):
        """获取项目索引"""
        projects = storage.get_footprint_projects()
        return {
            "total": len(projects),
            "projects": projects[offset:offset + limit]
        }
    
    @app.get("/projects/{project_id}")
    async def get_project(project_id: str):
        """获取指定项目详情"""
        projects = storage.get_footprint_projects()
        project = next((p for p in projects if p.get("project_id") == project_id), None)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project
    
    # ---- 简历 ----
    
    @app.get("/resume")
    async def get_resume():
        """获取简历"""
        resume = storage.get_resume()
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found, please generate first")
        return resume
    
    @app.post("/resume")
    async def update_resume(data: ResumeUpdateRequest):
        """更新简历"""
        resume = storage.get_resume() or {}
        
        if data.name is not None:
            resume["name"] = data.name
        if data.target_role is not None:
            resume["target_role"] = data.target_role
        if data.skills is not None:
            resume["skills"] = data.skills
        if data.projects is not None:
            resume["projects"] = data.projects
        
        storage.save_resume(resume)
        return {"success": True, "resume": resume}
    
    # ---- 职位 ----
    
    @app.get("/jobs")
    async def get_jobs(
        status: Optional[str] = None,
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0)
    ):
        """获取职位列表"""
        jobs = storage.get_jobs()
        
        if status:
            jobs = [j for j in jobs if j.get("status") == status]
        
        return {
            "total": len(jobs),
            "jobs": jobs[offset:offset + limit]
        }
    
    @app.post("/jobs/search")
    async def search_jobs(query: JobSearchQuery):
        """搜索职位（通过 BOSS 直聘）"""
        try:
            from boss.search import BOSSSearcher
            
            searcher = BOSSSearcher()
            result = await searcher.search_jobs(
                keywords=query.keywords,
                city=query.city,
                experience=query.experience,
                degree=query.degree,
                salary=query.salary,
                page=query.page,
                page_size=query.page_size
            )
            
            if result.get("success"):
                return {
                    "success": True,
                    "total": len(result.get("jobs", [])),
                    "jobs": result.get("jobs", [])
                }
            else:
                raise HTTPException(status_code=500, detail=result.get("error", "Search failed"))
        except ImportError:
            raise HTTPException(status_code=500, detail="BOSS search not available")
    
    @app.get("/jobs/{job_id}")
    async def get_job(job_id: str):
        """获取指定职位详情"""
        jobs = storage.get_jobs()
        job = next((j for j in jobs if j.get("job_id") == job_id or j.get("id") == job_id), None)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job
    
    @app.post("/jobs/{job_id}/save")
    async def save_job(job_id: str):
        """保存职位"""
        jobs = storage.get_jobs()
        job = next((j for j in jobs if j.get("job_id") == job_id or j.get("id") == job_id), None)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job["status"] = "saved"
        storage.add_job(job)
        return {"success": True, "job": job}
    
    # ---- JD 匹配 ----
    
    @app.get("/match/{job_id}")
    async def match_job(job_id: str):
        """对职位进行 JD 匹配评分"""
        # 获取职位
        jobs = storage.get_jobs()
        job = next((j for j in jobs if j.get("job_id") == job_id or j.get("id") == job_id), None)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # 获取简历
        resume = storage.get_resume()
        if not resume:
            raise HTTPException(status_code=400, detail="Resume not found")
        
        # 匹配评分
        matcher = JDMatcher()
        score = await matcher.score_job(job, resume)
        
        return {
            "job_id": job_id,
            "score": score,
            "resume_name": resume.get("name", ""),
            "job_title": job.get("title", ""),
            "company": job.get("company", "")
        }
    
    @app.post("/match")
    async def match_jobs(job_ids: List[str]):
        """批量匹配职位"""
        results = []
        
        for job_id in job_ids:
            try:
                result = await match_job(job_id)
                results.append(result)
            except Exception as e:
                results.append({"job_id": job_id, "error": str(e)})
        
        return {"results": results}
    
    # ---- 状态 ----
    
    @app.get("/status")
    async def get_status():
        """获取 JobTracer 状态"""
        state = storage.get_state() or {}
        resume = storage.get_resume() or {}
        jobs = storage.get_jobs()
        projects = storage.get_footprint_projects()
        
        return {
            "last_active": state.get("last_active", "unknown"),
            "resume": {
                "name": resume.get("name", "未设置"),
                "target_role": resume.get("target_role", "未设置"),
                "skills_count": len(resume.get("skills", [])),
                "projects_count": len(resume.get("projects", []))
            },
            "jobs": {
                "total": len(jobs),
                "new": len([j for j in jobs if j.get("status") == "new"]),
                "applied": len([j for j in jobs if j.get("status") == "applied"])
            },
            "projects": {
                "total": len(projects)
            }
        }
    
    # ---- Offer 比较 ----
    
    @app.post("/offer/compare")
    async def compare_offers_api(offer_list: List[dict]):
        """比较多个 Offer"""
        from tools.offer_comparator import compare_offers
        
        if not offer_list:
            raise HTTPException(status_code=400, detail="No offers provided")
        
        result = compare_offers(offer_list)
        return result
    
    # ---- 团队 ----
    
    @app.get("/teams")
    async def list_teams():
        """列出团队"""
        from teams.manager import TeamManager
        
        manager = TeamManager()
        teams = manager.list_teams()
        return {"teams": teams}
    
    @app.post("/teams")
    async def create_team(name: str, owner_id: str, description: str = ""):
        """创建团队"""
        from teams.manager import TeamManager
        
        manager = TeamManager()
        team = manager.create_team(name=name, owner_id=owner_id, description=description)
        return {"success": True, "team": team}
    
    @app.get("/teams/{team_id}/dashboard")
    async def get_team_dashboard(team_id: str):
        """获取团队看板"""
        from teams.manager import TeamManager
        
        manager = TeamManager()
        dashboard = manager.get_team_dashboard(team_id)
        if not dashboard:
            raise HTTPException(status_code=404, detail="Team not found")
        return dashboard
    
    return app


# 创建默认 app 实例（延迟创建避免版本兼容问题）
_app = None

def get_app() -> FastAPI:
    global _app
    if _app is None:
        _app = create_app()
    return _app

@app.get("/")
async def root():
    return {
        "name": "JobTracer API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

# 懒加载 app 属性
class _LazyApp:
    def __getattr__(self, name):
        return getattr(get_app(), name)

app = _LazyApp()  # type: ignore


# ============================================================
# 独立运行入口
# ============================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🚀 JobTracer API Server")
    print("=" * 60)
    print("📚 API 文档: http://localhost:8000/docs")
    print("📖 Redoc: http://localhost:8000/redoc")
    print("=" * 60)
    
    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )