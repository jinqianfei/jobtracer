# JobTracer API 文档

## 扫描模块 (scanner)

### scan_all(user_id, scan_paths=None)

扫描所有数字足迹来源。

**参数：**
- `user_id` (str): 用户 ID
- `scan_paths` (list, optional): 自定义扫描路径，默认扫描所有来源

**返回：**
```json
{
  "scan_id": "scan_20240101_001",
  "total_files": 42,
  "sources": ["local", "openclaw", "github"],
  "files": [
    {"path": "/path/to/file.py", "type": "python", "source": "local"},
    ...
  ],
  "timestamp": "2024-01-01T10:00:00Z"
}
```

---

### scan_local(paths)

扫描本地文件系统。

**参数：**
- `paths` (list): 要扫描的目录路径

**返回：** 文件列表

---

### scan_openclaw()

扫描 OpenClaw 工作区文件。

**返回：** OpenClaw 中的项目文件列表

---

### scan_github(token=None)

扫描 GitHub 仓库。

**参数：**
- `token` (str, optional): GitHub API Token

**返回：** GitHub 仓库中的代码文件列表

---

## 聚类模块 (clustering)

### cluster(scan_results)

将扫描结果智能聚类为项目。

**参数：**
- `scan_results` (dict): `scan_all()` 返回的结果

**返回：**
```json
[
  {
    "name": "电商推荐系统",
    "description": "基于协同过滤的个性化推荐引擎",
    "files": ["/path/to/recommender.py", ...],
    "tech_stack": ["Python", "TensorFlow", "Redis"],
    "confidence": 0.92
  },
  ...
]
```

---

### suggest_project_names(projects)

为聚类结果生成项目名称建议。

**参数：**
- `projects` (list): 聚类后的项目列表

**返回：** 带名称建议的项目列表

---

## 简历模块 (resume)

### generate_from_projects(project_names, target_role, user_info=None)

从项目列表生成简历。

**参数：**
- `project_names` (list): 项目名称列表
- `target_role` (str): 目标职位
- `user_info` (dict, optional): 用户基本信息

**返回：**
```json
{
  "personal_info": {...},
  "summary": "资深后端工程师，擅长...",
  "experience": [...],
  "projects": [...],
  "skills": {...},
  "generated_at": "2024-01-01T10:00:00Z"
}
```

---

### enhance_resume(resume, job_description)

根据 JD 增强简历关键词。

**参数：**
- `resume` (dict): 简历数据
- `job_description` (str): 职位描述

**返回：** 增强后的简历

---

## BOSS 模块 (boss)

### search_jobs(keyword, city=None, experience=None, salary=None)

搜索 BOSS 直聘职位。

**参数：**
- `keyword` (str): 搜索关键词
- `city` (str, optional): 城市
- `experience` (str, optional): 经验要求
- `salary` (str, optional): 薪资范围

**返回：**
```json
{
  "jobs": [
    {
      "job_id": "ABC123",
      "title": "Python 后端工程师",
      "company": "某科技有限公司",
      "salary": "25-40K",
      "city": "北京",
      "experience": "3-5年",
      "tags": ["五险一金", "弹性工作"],
      "jd": "岗位职责...",
      "url": "https://www.zhipin.com/job/ABC123.html"
    },
    ...
  ],
  "total": 100,
  "page": 1
}
```

---

### get_job_detail(job_id)

获取职位详情。

**参数：**
- `job_id` (str): 职位 ID

**返回：** 职位详细信息

---

## 匹配模块 (matching)

### match(job, resume)

对 JD 和简历进行匹配评分。

**参数：**
- `job` (dict): 职位信息
- `resume` (dict): 简历信息

**返回：**
```json
{
  "total_score": 85,
  "breakdown": {
    "skills_match": 90,
    "experience_match": 80,
    "education_match": 85,
    "overall_match": 85
  },
  "matching_skills": ["Python", "Redis", "微服务"],
  "missing_skills": ["Java", "Kubernetes"],
  "suggestions": ["建议补充 K8s 相关经验"]
}
```

---

### rank_jobs(jobs, resume)

对职位列表按匹配度排序。

**参数：**
- `jobs` (list): 职位列表
- `resume` (dict): 简历信息

**返回：** 按匹配度排序的职位列表

---

## HR 模块 (hr)

### generate_greeting(job, resume)

生成定制招呼语。

**参数：**
- `job` (dict): 职位信息
- `resume` (dict): 简历信息

**返回：**
```json
{
  "greeting": "您好，看了贵司的招聘信息，我对 Python 后端工程师一职很感兴趣...",
  "highlights": ["5年 Python 经验", "主导过电商系统"],
  "copy_button": "一键复制"
}
```

---

### track_application(job_id, status)

跟踪投递状态。

**参数：**
- `job_id` (str): 职位 ID
- `status` (str): 状态 (applied, viewed, replied, rejected)

---

## 通知模块 (feishu)

### send_resume_ready(user_id, resume)

发送简历生成完成通知。

---

### send_job_alert(user_id, job)

发送新职位发现通知。

---

### send_daily_report(user_id, stats)

发送每日求职日报。

---

## 使用示例

```python
from jobtracer.scanner import scan_all
from jobtracer.clustering import cluster
from jobtracer.resume import generate_from_projects
from jobtracer.boss import search_jobs
from jobtracer.matching import match

# 1. 扫描
scan_results = scan_all("user_001")

# 2. 聚类
projects = cluster(scan_results)

# 3. 生成简历
resume = generate_from_projects(
    [p["name"] for p in projects],
    target_role="Python 后端工程师"
)

# 4. 搜索职位
jobs = search_jobs("Python 后端", city="北京")

# 5. 匹配
top_match = match(jobs[0], resume)
```