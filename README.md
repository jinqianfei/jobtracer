# JobTracer - 智能求职工作流

## 功能

- 📂 **数字足迹扫描** - 本地文件 / OpenClaw / GitHub 全面搜索项目经历
- 🔬 **项目聚类** - 智能识别并归类你的项目成果
- 📄 **简历生成** - 基于项目自动生成专业简历
- 🎯 **BOSS直聘搜索** - 自动搜索目标职位并匹配 JD
- ✉️ **定制招呼** - 一键生成针对职位定制的招呼语
- 📱 **飞书通知** - 重要节点实时推送飞书 Bot

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 BOSS Cookie
# 打开 ~/.jobtracer/cookies/boss.json 填入你的 BOSS 登录 Cookie

# 3. 首次扫描
python -m jobtracer scan

# 4. 查看生成的简历
cat ~/.jobtracer/resume.json
```

## 目录结构

```
jobtracer/
├── scanner/          # 数字足迹扫描器（本地文件/OpenClaw/GitHub）
├── clustering/        # 项目聚类引擎
├── resume/            # 简历生成模块
├── boss/              # BOSS直聘 API 集成
├── matching/          # JD 智能匹配
├── hr/                # HR 沟通助手
├── interview/         # 面试题库
├── jobs/              # 职位数据管理
├── utils/             # 工具函数
├── config.py          # 配置文件
├── main.py            # 主入口
└── storage/           # 本地存储
```

## 常用命令

```bash
# 扫描数字足迹
python -m jobtracer scan

# 搜索职位
python -m jobtracer search "Python 后端"

# 生成简历
python -m jobtracer resume

# 查看状态
python -m jobtracer status
```

## 配置说明

- Cookie 路径：`~/.jobtracer/cookies/boss.json`
- 简历输出：`~/.jobtracer/resume.json`
- 日志目录：`~/.jobtracer/logs/`

## 依赖

- Python 3.10+
- 见 requirements.txt