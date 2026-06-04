# JobTracer - 智能求职自动化工作流

基于数字足迹的智能化求职辅助工具，自动化职位搜索、简历定制、面试准备的完整闭环。

## ✨ 核心功能

- **数字足迹扫描** — 聚合 GitHub、项目文档、工作记录为可求职素材
- **多平台职位搜索** — BOSS直聘 + 51job + 智联聚合搜索，自动去重
- **JD智能匹配** — 简历与职位描述的语义匹配评分
- **定制简历生成** — 针对不同职位定制化调整简历
- **HR沟通辅助** — 自动识别意图，生成回复话术
- **模拟面试** — 基于简历和JD生成面题库 + AI模拟面试
- **投递状态跟踪** — 全流程状态管理（已保存→投递→面试→Offer）
- **职业规划** — 基于背景的路径建议 + 学习路线图
- **定时自动搜索** — 每日09:00自动搜索新职位推送飞书

## 🛠️ 快速开始

```bash
# 克隆项目
git clone https://github.com/jinqianfei/jobtracer.git
cd jobtracer

# 安装依赖
pip install -r requirements.txt

# 初始化
python3 main.py init

# 扫描数字足迹生成简历
python3 main.py scan
python3 main.py cluster
python3 main.py resume

# 搜索职位
python3 main.py search --keywords "Python后端" --city 上海 --platforms boss,51job

# 投递状态管理
python3 main.py apply --stats
python3 main.py apply <job-id> --status applied

# 定时自动搜索（设置cron）
python3 daily_cron.py --setup-cron

# 职业规划
python3 main.py career --roadmap

# API服务
python3 main.py api-server
```

## 📋 CLI 命令

| 命令 | 说明 |
|------|------|
| `scan` | 扫描数字足迹 |
| `search` | 搜索职位 |
| `cluster` | 聚类项目 |
| `resume` | 生成简历 |
| `match` | JD匹配评分 |
| `apply` | 投递状态管理 |
| `career` | 职业规划 |
| `daily` | 执行每日巡检 |
| `notify` | 发送飞书通知 |
| `fill` | 智能填充简历 |
| `offer-compare` | Offer比较 |
| `api-server` | 启动API服务 |

## 📁 项目结构

```
jobtracer/
├── boss/           # BOSS直聘搜索和发招呼
├── jobs/           # 职位管理和投递跟踪
├── resume/        # 简历生成和定制
├── matching/      # JD匹配评分
├── hr/            # HR沟通辅助
├── interview/     # 面题库和模拟面试
├── career_planning/ # 职业规划
├── platforms/     # 多平台搜索抽象
├── reporting/    # 报告生成
├── scanner/       # 数字足迹扫描
├── clustering/   # 项目聚类
├── storage/        # 本地存储管理
├── daily_cron.py  # 定时自动搜索
└── main.py        # CLI主入口
```

## 📄 文档

- [PRD文档](./docs/JobTracer%20PRD.md)
- [技术方案](./docs/JobTracer技术方案.md)
- [工作流方案](./docs/JobTracer智能求职工作流方案.md)
- [用户指南](./docs/USER_GUIDE.md)

## 📜 License

MIT License - see [LICENSE](./LICENSE)