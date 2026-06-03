# JobTracer 智能求职工作流 PRD

> **产品名称：** JobTracer（求职足迹）
> **Slogan：** _"你的每一步足迹，都成为面试的底气。"_
> **Version：** v1.0.0
> **Status：** 评审通过（待技术方案）

---

## 文档信息

| 字段 | 内容 |
|------|------|
| **版本号** | v1.0.1 |
| **作者** | ProductSolution Agent |
| **创建日期** | 2026-06-02 |
| **更新日期** | 2026-06-02 |
| **评审日期** | 2026-06-02 |
| **评审结论** | 通过（有条件认可）- 需技术验证 |
| **状态** | 评审通过，待技术方案 |

---

## 1. 产品概述

### 1.1 产品定位

JobTracer 是一款 AI 驱动的智能求职工作流产品，定位为求职者的「第二大脑」。它将用户散落在各处的数字足迹（项目文档、技术积累、协作记录）自动聚合，生成结构化简历，匹配合适岗位，辅助 HR 沟通，最终帮助用户拿到 Offer。

**核心差异：** 现有竞品呈现"三段分裂"——A段（简历）、B段（投递）、C段（面试），没有任何产品真正打通全链路。JobTracer 是国内市场首款真正意义上的全链路整合产品。

### 1.2 目标用户

| 用户群体 | 特征 | 痛点 |
|---------|------|------|
| 中高级工程师 | 3-10年经验，技术积累丰富 | 项目经历难以系统化呈现，投递精准度低 |
| 转行者 | 有相关技能但缺乏系统简历 | 不知道如何包装过往经历 |
| 应届生 | 缺乏实战项目经历 | 简历内容空洞，难以匹配 JD |
| 海归/外语求职者 | 需要中英双语简历 | 国内外平台不互通，环境差异大 |

### 1.3 核心价值

| 价值点 | 说明 |
|--------|------|
| **数字足迹聚合** | 从本地文件、飞书、GitHub、AI Agent 平台自动提取项目资料，无需手动输入 |
| **AI 简历生成** | 基于真实项目数据生成结构化简历，内容可溯源 |
| **精准岗位匹配** | 多平台搜索 + JD 匹配度评分，投10个最合适的而非100个随意的 |
| **HR 沟通辅助** | AI 分析 HR 意图，生成回复建议，用户做最终决策 |
| **面试全流程准备** | 个性化面题库 + STAR 法则指导 + 模拟面试 |

### 1.4 与现有产品关系

| 组件 | 角色 | 说明 |
|------|------|------|
| **ProjectTrace** | 数字足迹聚合引擎 | 负责扫描本地文件/飞书/GitHub 等，构建项目知识库 |
| **job-hunter** | 求职状态管理层 | 负责 state.json / resume.json / job-tracker.json 管理 |
| **JobTracer** | 工作流编排层 | 整合两者，形成 Step 1-8 完整求职闭环 |

---

## 2. 用户旅程与功能需求

### 2.1 Step 1：数字足迹聚合

#### 触发条件
- 用户发送消息「开始求职」或「帮我找工作」

#### 执行内容
1. 调用 ProjectTrace 核心引擎，扫描以下数据源：
   - 本地项目文档（txt/md/doc/pdf/excel/ppt）
   - 飞书文档/知识库（Lark/Feishu MCP）
   - GitHub 项目（Issues/Wiki/Repo 内容）
   - OpenClaw MEMORY.md 及 workspace 文件
   - 企业文档平台：钉钉文档、企业微信文档
   - AI Agent 平台：Claude Code、Codex、Trae、Qoder、WorkBuddy 等
2. 调用 ProjectTrace Clustering Engine，将扫描结果按项目聚类
3. 提取简历相关特征：技能向量、量化成果、协作经历

#### 输出物
- `digital_footprint_summary.md` — 数字足迹摘要（供用户查看）
- `~/.jobtracer/footprint/projects/` — 结构化项目文件夹（含 `_index.md`、`docs/`、`code_snippets/`、`metadata.json`）
- `skills_vector.json` — 用户技能向量

#### 用户交互
- 用户查看数字足迹摘要和项目文件夹结构
- **确认点：** 用户确认没有遗漏重要内容，可补充遗漏的文档

#### 异常处理
| 异常情况 | 处理方式 |
|---------|---------|
| 某平台认证失败 | 跳过该平台，通知用户「XX平台连接失败，已继续其他平台」 |
| 内容不足（<3个项目） | 提示用户「数字足迹较少，建议手动补充项目文档」 |
| 扫描超时（>5分钟） | 返回已扫描结果，提示「部分平台扫描超时，已保存已扫描内容」 |

#### 优先级
**MVP（P0）**

---

### 2.2 Step 2：生成基础简历

#### 触发条件
- Step 1 完成后，或用户主动发送「生成简历」

#### 执行内容
1. 分析用户职业定位（基于技能向量 + 项目类型推断：后端/前端/算法/产品等）
2. 读取 `~/.jobtracer/footprint/projects/` 下各项目文件夹，提取关键贡献和量化成果
3. LLM 生成结构化 `resume.json`：
   - 基础信息（姓名、联系方式、学历）
   - 技能列表（从 skills_vector.json 提取）
   - 项目经历（含时间、角色、个人贡献、量化成果）
   - 简历定位（target_role）

#### 输出物
- `resume.json` — 结构化简历（含 version/name/contact/summary/skills/experience/projects/education 等字段）
- 用户可预览的简历预览界面

#### 用户交互
- **确认点：** 用户预览简历内容，确认后进入 Step 3
- 用户可编辑修改简历内容（编辑后同步更新 resume.json）

#### 异常处理
| 异常情况 | 处理方式 |
|---------|---------|
| 项目内容无法提取量化成果 | 生成含「项目描述」但不包含量化数据的简历，提示用户手动补充 |
| 职业定位模糊（多方向均可） | 生成多个简历版本供用户选择（如：后端开发/全栈） |

#### 优先级
**MVP（P0）**

---

### 2.3 Step 3：搜索合适工作

#### 触发条件
- Step 2 完成后，或用户确认简历后，或每日定时触发

#### 执行内容
1. 从 `resume.json` 提取技能关键词 + 项目关键词
2. **MVP：仅搜索 BOSS直聘**；Phase 2 扩展到前程无忧/牛客/LinkedIn/Indeed
3. 对每个 JD 进行多维匹配度评分：
   - 技能匹配（keyword match）：40%
   - 项目背景匹配（领域关键词 overlap）：20%
   - 经验层次匹配（工作年限/职级）：20%
   - 薪资匹配：20%
4. 按「匹配度 + 薪资 + 地区」综合排序
5. 关联用户相关项目/作品：读取 `~/.jobtracer/footprint/projects/`，找出与 JD 技能/领域匹配的项目

#### 多平台搜索策略

> **MVP范围：仅 BOSS直聘搜索，其他平台显示候选但不主动推送**

| 平台 | MVP方案 | Phase 2方案 |
|------|---------|-------------|
| **BOSS直聘** | 全量搜索 + 主动推送 | - |
| 前程无忧 | 仅显示候选（用户主动搜索） | 全量搜索 + 主动推送 |
| 牛客 | 仅显示候选 | 全量搜索 + 主动推送 |
| LinkedIn | 不支持（反自动化）| - |
| Indeed | 仅显示候选 | 全量搜索 + 主动推送 |

#### 输出物
- `job-tracker.json` — 职位列表（含匹配度评分、薪资、地区、JD摘要）
- 飞书 Bitable 职位追踪记录
- 每个匹配岗位附带「推荐项目列表」

#### 用户交互
- 用户可查看职位列表，按匹配度/薪资/地区筛选
- **确认点：** 用户选择要投递的职位（可多选）

#### 异常处理
| 异常情况 | 处理方式 |
|---------|---------|
| 某平台搜索失败 | 跳过该平台，继续其他平台；通知用户「XX平台搜索暂时失败」 |
| 无匹配职位（<3个） | 自动扩展搜索关键词（减少技能限制），提示用户「调整期望后找到X个职位」 |
| 搜索超时 | 返回已获取结果，超时平台标记为「待补充」 |

#### 优先级
**MVP（P0）**

---

### 2.4 Step 4：定制简历投递

#### 触发条件
- 用户确认投递的 JD 列表后

#### 执行内容
1. 对每个目标 JD：
   - LLM 分析 JD 关键词，提取核心技能要求
   - 在基础简历基础上，定制化调整 bullet points（强化相关经历，轻化无关内容）
   - 生成定制简历 HTML → PDF
   - 生成飞书文档（职位详情 + 简历截图 + 投递状态）
2. **BOSS直聘（MVP）**：调用 `opencli boss greet <uid>` 发招呼（附带定制招呼语）
3. **其他平台（MVP）**：生成一键复制内容
   - 定制招呼语 + 职位链接，用户手动投递

#### 多平台投递策略

> **MVP范围：仅 BOSS直聘自动化投递，其他平台均为一键复制模式**

| 平台 | MVP方案 | Phase 2方案 |
|------|---------|-------------|
| **BOSS直聘** | opencli boss greet | Playwright |
| 前程无忧 | 一键复制 | Playwright扩展 |
| 牛客 | 一键复制 | Playwright扩展 |
| LinkedIn | 一键复制（不做auto-apply，平台反自动化政策严格）| - |
| Indeed | 一键复制 | Playwright扩展 |

#### 输出物
- `customized_resumes/{jd_id}/customized.pdf` — 定制简历 PDF
- 飞书文档（职位详情 + 简历 + 投递状态）
- 投递状态更新到 Bitable

#### 用户交互
- **确认点：** 用户预览定制简历，确认后再执行投递
- 用户可编辑定制简历内容

#### 异常处理
| 异常情况 | 处理方式 |
|---------|---------|
| BOSS 发招呼被限制 | 降级为「生成招呼语 + 手动复制」模式，提示用户 |
| PDF 生成失败 | 生成 HTML 版本简历，提供下载链接 |
| JD 页面无法访问 | 标记该 JD 状态为「待补充」，提示用户手动补充 JD 内容 |

#### 优先级
**MVP（P0）**

---

### 2.5 Step 5：HR 沟通辅助

#### 触发条件
- 用户收到 HR 回复后，发送「帮我回复」+ HR 消息内容
- 或用户主动跟进节点时

#### 执行内容
1. LLM 分析 HR 消息意图，分类到以下类型之一：
   - `initial_contact`：初次联系
   - `project_inquiry`：询问项目经历
   - `skill_inquiry`：询问技术栈
   - `city_inquiry`：询问意向城市
   - `contact_inquiry`：询问联系方式
   - `salary_inquiry`：询问薪资期望
   - `interview_invite`：邀请面试
   - `offer_extended`：发送 offer
   - `rejection`：拒绝
   - `follow_up`：跟进
   - 等等（共14种意图）
2. 结合用户 `resume.json` 和求职状态，生成回复内容
3. **按意图分级决定是否自动发送：**

| 消息类型 | 处理方式 | 确认？ |
|---------|---------|--------|
| 初次联系 | 自动生成 + 发送 | ❌ |
| 问Availability | 自动发送 | ❌ |
| 问联系方式 | 自动发送 | ❌ |
| 问项目经历/技术 | 自动发送 | ❌ |
| 问意向城市 | 自动发送 | ❌ |
| 约面试 | 生成 + **确认时间** | ✅ |
| 谈薪资 | 生成 + **确认数字** | ✅ |
| 谈Offer | 生成 + **确认条款** | ✅ |
| 发Offer | 生成 + **确认接受** | ✅ |
| 拒绝/接受Offer | 生成 + **确认决定** | ✅ |
| 其他意图 | 自动发送 | ❌ |

#### 输出物
- 回复建议列表（飞书卡片展示，确认类消息显示确认按钮）
- 发送记录（同步到 job-tracker.json）

#### 用户交互
- 自动发送类：消息自动发出，用户可在聊天记录中查看
- 确认类（约面试/薪资/Offer/拒绝接受）：显示确认按钮，用户点击确认后发送；可选编辑修改回复内容

#### 异常处理
| 异常情况 | 处理方式 |
|---------|---------|
| HR 意图不明确 | 生成通用回复建议，标注「意图不明确，建议手动确认」 |
| 用户未配置薪资期望 | 提示用户补充「期望薪资」后再生成薪资相关回复建议 |

#### 优先级
**Phase 2（P1）**

---

### 2.6 Step 6：发送联系方式

#### 触发条件
- HR 明确要求发送联系方式或简历附件时

#### 执行内容
1. 识别 HR 要求的是「联系方式」还是「简历」
2. **如要简历：** 发送 Step 4 针对该岗位生成的定制简历 PDF
3. **如要联系方式：** 读取 `resume.json.contact`，过滤隐私信息
4. 用户确认后，通过飞书/邮件发送

#### 输出物
- 发送的联系方式/简历内容预览
- 发送记录（同步到 job-tracker.json）

#### 用户交互
- **确认点：** 必须用户确认，不自动发送
- 用户可编辑联系方式内容

#### 异常处理
| 异常情况 | 处理方式 |
|---------|---------|
| 简历文件丢失 | 重新生成该 JD 的定制简历（基于缓存的 JD 数据） |
| 联系方式不完整 | 提示用户补充缺失信息 |

#### 优先级
**Phase 2（P1）**

---

### 2.7 Step 7：面试准备

#### 触发条件
- 约到面试后，用户发送「准备面试」或「面试准备」

#### 执行内容
1. 读取该职位的 JD 和用户简历
2. 生成个性化面题库：
   - **基础知识问题**（基于 JD 推断的岗位类型：如后端→OS/网络/数据库；前端→浏览器原理/JS 基础）
   - **技能问题**（基于 JD 技术栈：如 Java→Spring/多线程；Python→协程/装饰器）
   - **STAR 法则问题**（基于简历项目经历）
   - **量化成果追问**（针对简历中含数字的 bullet points）
   - **反问面试官问题**
3. 生成每个问题的回答方向（思路框架 + 相关素材位置）
4. 模拟面试模式：用户说「练习面试」，JobTracer 随机出题，用户回答后给出反馈

#### 输出物
- `interview_prep.md` — 面题库 + 回答方向
- 飞书文档（可分享）
- 模拟面试记录

#### 用户交互
- 用户可按类别筛选面题
- 用户可开启「模拟面试」模式进行练习
- **确认点：** 用户确认面题库内容是否涵盖核心考察点

#### 异常处理
| 异常情况 | 处理方式 |
|---------|---------|
| JD 内容不完整 | 基于简历推断岗位类型，生成通用版面题库 |
| 面题库过少（<5题） | 自动补充通用高频面题 |

#### 优先级
**Phase 2（P1）**

---

### 2.8 Step 8：求职复盘与数据沉淀

#### 触发条件
- 用户拿到 offer / 求职告一段落 / 每周五

#### 执行内容
1. 生成求职复盘报告：
   - 投递了多少职位（按平台分布）
   - 响应率、面试转化率
   - 被拒原因分析（如果有）
   - 市场薪资行情总结
   - 表现最好的项目/技能点
2. 更新 ProjectTrace 索引：本次求职经历沉淀到 MEMORY.md
3. 更新用户偏好：薪资底线、偏好行业、可接受条件

#### 输出物
- `career_review_YYYY-MM-DD.md` — 求职复盘报告
- 更新 `feedback.json`（用户反馈数据）

#### 用户交互
- 用户可编辑复盘报告内容
- **确认点：** 用户确认复盘报告后，数据正式沉淀

#### 异常处理
| 异常情况 | 处理方式 |
|---------|---------|
| 投递数据不完整 | 生成部分复盘，标注「部分数据缺失」 |
| 无 offer 结果 | 生成阶段性复盘，聚焦于「已投递+面试转化」分析 |

#### 优先级
**Phase 2（P2）**

---

### 2.9 功能优先级总览

| Step | 功能 | 优先级 | 说明 |
|------|------|--------|------|
| Step 1 | 数字足迹聚合 | MVP（P0） | 复用 ProjectTrace 全部 Connector |
| Step 2 | 基础简历生成 | MVP（P0） | LLM 解析 footprint → resume.json |
| Step 3 | 多平台岗位搜索 | MVP（P0） | BOSS + 51job + 牛客 + LinkedIn |
| Step 3 | JD 匹配度评分 | MVP（P0） | 关键词匹配 + 语义匹配 |
| Step 4 | 定制简历 HTML→PDF | MVP（P0） | 针对每个 JD 生成定制版 |
| Step 4 | BOSS 直聘发招呼 | MVP（P1） | 带定制招呼语 |
| Step 4 | 飞书 Bitable 职位追踪 | MVP（P0） | 状态管理和通知 |
| Step 5 | HR 沟通辅助 | Phase 2（P1） | 意图分类 + 回复生成 |
| Step 6 | 发送联系方式 | Phase 2（P1） | 定制简历发送 |
| Step 7 | 个性化面题库 | Phase 2（P1） | JD + 简历生成面题 |
| Step 7 | 模拟面试 | Phase 2（P1） | 随机出题 + 反馈 |
| Step 8 | 求职复盘报告 | Phase 2（P2） | 自动生成复盘总结 |
| — | 薪资谈判辅助 | Phase 2（P2） | 基于市场数据给建议 |
| — | 简历多版本管理 | Phase 2（P2） | 技术/管理/国央企 不同版本 |

---

## 3. 非功能需求

### 3.1 性能要求

| 指标 | 要求 | 说明 |
|------|------|------|
| 数字足迹扫描 | 单平台 < 60s，总计 < 5min | 增量扫描优先 |
| 简历生成 | < 30s | LLM 调用时间，含重试 |
| 岗位搜索 | < 120s | 并行搜索，多平台聚合 |
| JD 匹配评分 | < 5s/条 | 批量处理时优化 |
| 定制简历 PDF | < 15s | 含 HTML 渲染 |
| 响应时间（日常交互） | < 5s | 用户发送消息到收到回复 |

### 3.2 安全需求

| 需求 | 说明 |
|------|------|
| **隐私本地存储** | 简历和求职数据优先本地存储，不强制上云 |
| **数据加密** | SQLite 索引文件设置 `chmod 600` |
| **敏感信息过滤** | 自动跳过银行卡号、密码、API Key 等内容 |
| **平台授权** | 连接任何平台前必须获得用户明确授权 |
| **内容来源透明** | 简历中引用的项目成果需标注来源，用户可追溯 |

### 3.3 兼容性

| 项目 | 要求 |
|------|------|
| **飞书版本** | 飞书桌面版 + 移动版（iOS/Android） |
| **操作系统** | macOS 12+、Windows 10+、Linux（Ubuntu 20.04+） |
| **浏览器** | Chrome 90+、Safari 15+、Edge 90+ |
| **Python** | 3.11+ |
| **Node.js** | 18+（用于 job-hunter CLI） |

### 3.4 可用性

| 指标 | 要求 |
|------|------|
| **系统成功率** | 各 Step 核心功能成功率 ≥ 95% |
| **异常恢复** | 失败操作可重试，不丢失用户数据 |
| **容错设计** | 单平台失败不影响整体流程，异步降级 |
| **数据一致性** | resume.json / job-tracker.json 等核心数据文件需事务性写入 |

---

## 4. 数据需求

### 4.1 需要存储的数据

> **统一数据目录：** 所有数据存储在 `~/.jobtracer/` 下，避免路径分散

```
~/.jobtracer/
├── memory/                    # 核心状态数据
│   ├── state.json             # 求职状态
│   ├── resume.json            # 结构化简历
│   ├── preferences.json      # 用户偏好（薪资/城市/平台）
│   ├── resume_versions/       # 简历版本历史
│   ├── job-tracker.json       # 职位追踪
│   ├── hr_conversations.json  # HR沟通记录
│   └── user_preferences.json  # 用户偏好
├── footprint/                 # 数字足迹（ProjectTrace输出）
│   ├── summary.md            # 数字足迹摘要
│   ├── skills_vector.json    # 技能向量
│   └── projects/             # 按项目组织的文档结构
├── jobs/                      # 职位数据
│   ├── job-tracker.json      # 职位追踪
│   └── jd_cache/             # JD内容缓存
├── resumes/                   # 简历版本
│   └── versions/
├── customized_resumes/        # 各JD定制简历
│   └── {jd_id}/
│       └── customized.pdf
├── interview_prep/            # 面题库
│   └── {job_id}/
├── cookies/                   # 各平台登录态（Playwright）
│   ├── boss.json
│   ├── 51job.json
│   └── ...
├── reports/                  # 复盘报告
│   └── career_review_*.md
└── logs/                     # 同步日志
```

### 4.2 数据存储选型

**存储策略：JSON文件 + SQLite**

| 数据类型 | 存储方式 | 说明 |
|---------|---------|------|
| 核心配置（resume.json/state.json） | JSON文件 | 小数据量，频繁读写，事务性要求高 |
| 职位列表（大量） | SQLite | 数据量大，需要高效查询和索引 |
| HR沟通记录 | SQLite | 数据量大，需要按job_id查询 |
| 面题库 | JSON文件 | 按需读取，单次使用 |
| 文件夹结构 | 本地文件 | projects/ 按项目组织 |

**SQLite Schema（用于大数据量场景）：**

```sql
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
    related_projects TEXT  -- JSON数组
);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_platform ON jobs(platform);
CREATE INDEX idx_jobs_match_score ON jobs(match_score);

-- hr_conversations表
CREATE TABLE hr_conversations (
    id TEXT PRIMARY KEY,
    job_id TEXT REFERENCES jobs(id),
    direction TEXT,  -- 'inbound' | 'outbound'
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
    questions JSON,  -- 按类别存储面题
    status TEXT DEFAULT 'generated',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_prep_job ON interview_prep(job_id);
```

**注：** Phase 1 小数据量时先用 JSON 文件，Phase 2 数据增长后迁移到 SQLite。

---

### 4.3 数据字典

#### resume.json

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| version | string | 是 | 简历版本号，如 "v1.0" |
| name | string | 是 | 姓名 |
| contact.phone | string | 是 | 手机号 |
| contact.email | string | 是 | 邮箱 |
| contact.location | string | 否 | 意向城市 |
| summary | string | 是 | 个人简介 |
| skills.technical | string[] | 是 | 技术栈 |
| skills.soft | string[] | 否 | 软技能 |
| experience[].company | string | 是 | 公司名称 |
| experience[].title | string | 是 | 职位名称 |
| experience[].duration | string | 是 | 任职时间 |
| experience[].highlights | string[] | 是 | 工作亮点（bullet points） |
| experience[].source_docs | string[] | 否 | 来源文档路径 |
| projects[].name | string | 是 | 项目名称 |
| projects[].role | string | 是 | 项目角色 |
| projects[].description | string | 是 | 项目描述 |
| projects[].metrics | string | 否 | 量化成果 |
| projects[].source_docs | string[] | 否 | 来源文档路径 |
| education | object | 是 | 学历信息 |
| meta.generated_from | string | 是 | 数据来源："digital_footprint" |
| meta.user_confirmed | boolean | 是 | 用户是否已确认 |
| meta.generated_at | string | 是 | 生成时间（ISO 8601） |

#### job-tracker.json

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| job_id | string | 是 | 职位唯一 ID（平台+原始ID） |
| platform | string | 是 | 来源平台：boss/51job/linkedin 等 |
| title | string | 是 | 职位名称 |
| company | string | 是 | 公司名称 |
| location | string | 否 | 工作地点 |
| salary | object | 否 | 薪资范围 {min, max, currency} |
| match_score | number | 是 | 匹配度评分（0-100） |
| jd_summary | string | 否 | JD 摘要 |
| status | string | 是 | 状态：new/applied/screening/interview/offer/rejected |
| applied_at | string | 否 | 投递时间 |
| related_projects | object[] | 否 | 推荐关联项目 |
| created_at | string | 是 | 记录创建时间 |

#### hr_conversations.json

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| conversation_id | string | 是 | 对话唯一 ID |
| job_id | string | 是 | 关联职位 ID |
| direction | string | 是 | 方向："inbound" \| "outbound" |
| intent | string | 是 | HR 意图类型 |
| message_preview | string | 是 | 消息摘要（前100字） |
| message_full | string | 否 | 完整消息内容 |
| suggested_replies | object[] | 否 | AI 生成的回复选项 |
| user_selected_reply | string | 否 | 用户选择的回复 |
| created_at | string | 是 | 创建时间 |

#### interview_prep.json

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| prep_id | string | 是 | 唯一 ID |
| job_id | string | 是 | 关联职位 ID |
| questions | object | 是 | 面题库（分类别存储） |
| questions.basic_knowledge | object[] | 是 | 基础知识题 |
| questions.technical | object[] | 是 | 技术题 |
| questions.behavioral | object[] | 是 | 行为题（STAR） |
| questions.reverse | string[] | 是 | 反问面试官问题 |
| prep_status | string | 是 | 状态："generated" \| "practicing" \| "completed" |
| created_at | string | 是 | 创建时间 |

### 4.3 数据流图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           数据流架构                                          │
│                                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │                     ProjectTrace 数字足迹聚合层                        │    │
│  │                           │                                          │    │
│  │  输入：本地文件 │ 飞书 │ GitHub │ OpenClaw │ 企业微信 │ 钉钉 │ AI Agent │    │
│  │                           │                                          │    │
│  │  输出：digital_footprint_summary.md                                   │    │
│  │       ~/.jobtracer/footprint/projects/（结构化项目文件夹）                    │    │
│  │       skills_vector.json                                             │    │
│  └───────────────────────────┼──────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │                    JobTracer Core 工作流层                             │    │
│  │                                                                      │    │
│  │  Step 1 → Step 2 → Step 3 → Step 4 → Step 5 → Step 6 → Step 7 → Step 8│    │
│  │  │      │      │      │      │      │      │      │      │           │    │
│  │  │      │      │      │      │      │      │      │      │           │    │
│  │  ▼      ▼      ▼      ▼      ▼      ▼      ▼      ▼      ▼           │    │
│  │ resume  jobs  customized job-    hr_      contact interview career   │    │
│  │ .json   .json resumes  tracker  conv.     sent    prep     review    │    │
│  │                      │         │                         │           │    │
│  └───────────────────────┼─────────┼─────────────────────────┼───────────┘    │
│                          │         │                         │                 │
│                          ▼         ▼                         ▼                 │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │                       输出层 & 通知层                                  │    │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │    │
│  │  │定制简历 │  │飞书文档 │  │飞书Bitable│  │邮件/消息│  │飞书通知 │       │    │
│  │  │  PDF    │  │  Card   │  │  Record  │  │  投递   │  │  Alert  │       │    │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘       │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. 依赖与风险

### 5.1 外部依赖

| 依赖项 | 类型 | 说明 | 风险等级 |
|--------|------|------|----------|
| **飞书 MCP** | 工具 | 飞书文档读取、知识库访问 | 中（依赖飞书服务可用性） |
| **钉钉 dws CLI** | 工具 | 钉钉文档同步 | 中（依赖钉钉 CLI 安装和认证） |
| **BOSS 直聘** | 平台 | 职位搜索、发招呼 | 高（平台政策不确定） |
| **GitHub API** | API | 项目内容同步 | 低（API 稳定，有免费额度） |
| **ProjectTrace** | 组件 | 数字足迹聚合引擎 | 中（核心依赖，若异常影响全流程） |
| **OpenAI API** | API | LLM 调用（简历生成、意图分类） | 中（成本和可用性） |
| **前程无忧/牛客** | 平台 | 职位搜索 | 中（平台 API 稳定性） |

### 5.2 技术风险

| 风险 | 可能性 | 影响 | 应对策略 |
|------|--------|------|----------|
| ProjectTrace 聚类准确率不足 | 中 | 高 | Phase 1 重点测试聚类效果，必要时降级为手动指定项目 |
| 数字足迹内容不足 | 中 | 中 | 提供手动补充入口，允许用户上传额外文档 |
| JD 匹配评分不准确 | 中 | 中 | Phase 2 引入人工反馈调优机制 |
| BOSS 直聘发招呼被限制 | 高 | 中 | 降级为"生成招呼语+手动复制"模式 |
| LLM 输出质量不稳定 | 中 | 高 | Phase 1 使用 GPT-4，Phase 2 考虑本地模型 |
| 飞书 MCP 服务不可用 | 低 | 高 | 降级为本地文件扫描，延迟同步飞书内容 |

### 5.3 业务风险

| 风险 | 说明 | 应对 |
|------|------|------|
| **隐私合规** | 简历包含大量个人数据，需明确数据使用政策 | 本地存储优先，明确告知用户数据用途 |
| **BOSS 直聘 API 合规** | 自动化发消息可能违反平台规则 | 限制发消息频率，提供手动模式 |
| **LinkedIn 反自动化政策** | LinkedIn 明确反自动化投递 | 不做 LinkedIn auto-apply，仅提供「一键复制」 |
| **简历内容来源** | 数字足迹内容可能包含敏感信息 | 增加隐私过滤规则，自动跳过密码/密钥等 |

### 5.4 应对策略总览

| 策略 | 具体措施 |
|------|----------|
| **降级机制** | 每个 Step 都有对应的降级方案，单点失败不影响整体 |
| **用户确认点** | AI 生成的简历、回复、定制内容均需用户确认后再执行关键操作 |
| **数据本地优先** | 简历和职位数据优先存在本地，不强制上云 |
| **隐私过滤** | 扫描阶段自动过滤敏感信息（密码、银行卡号、API Key 等） |

---

## 6. 评审记录

### 6.1 评审 Checklist

- [ ] **功能完整性**：Step 1-8 是否都有清晰描述，每个 Step 的触发条件、执行内容、输出物、用户交互、异常处理是否完整
- [ ] **优先级合理性**：MVP 范围是否合适（聚焦核心闭环，不过度设计 Phase 2/3 功能）
- [ ] **数据一致性**：数据需求是否与功能匹配（resume.json / job-tracker.json / hr_conversations.json 字段定义是否完整）
- [ ] **技术可行性**：依赖和风险是否识别完整，降级机制是否覆盖主要异常场景
- [ ] **用户体验**：用户确认点是否设置合理（AI 输出需确认的关键节点），通知机制是否适度（不打扰用户）

### 6.2 评审记录表

| 评审时间 | 评审人 | 结论 | 主要意见 |
|---------|-------|------|---------|
| 2026-06-02 | 分析师Agent | 通过（有条件认可） | Step 5-8描述深度已补充；建议Step 5纳入Phase 1验证计划 |
| 2026-06-02 | 开发Agent | 条件通过 | BOSS opencli前置依赖需确认；jobs表需补充字段；需Phase 1→2迁移方案 |

### 6.3 待技术验证项（PRD通过前置条件）

| # | 验证项 | 负责 | 状态 |
|---|--------|------|------|
| 1 | BOSS opencli boss greet 功能是否可用 | 开发 | 待验证 |
| 2 | BOSS直聘搜索API/爬虫方案可行性 | 开发 | 待验证 |
| 3 | 前程无忧/牛客平台API可用性 | 开发 | 待验证 |
| 4 | PDF生成（weasyprint/playwright）方案 | 开发 | 待验证 |

> **注：** 完成技术方案后更新本PRD，技术验证通过后状态变更为「技术方案通过」，进入开发阶段。

---

## 附录

### A. 缩写说明

| 缩写 | 全称 | 说明 |
|------|------|------|
| JD | Job Description | 职位描述 |
| BOSS | BOSS 直聘 | 招聘平台 |
| MCP | Model Context Protocol | 模型上下文协议 |
| ATS | Applicant Tracking System | 招聘管理系统 |
| STAR | Situation, Task, Action, Result | 面试行为法 |
| LLM | Large Language Model | 大语言模型 |

### B. 参考文档

| 文档 | 路径 |
|------|------|
| JobTracer 智能求职工作流设计方案 | `/Users/jinqianfei/openclaw-workspaces/product-solution/JobTracer智能求职工作流方案.md` |
| 求职工作流竞品分析报告 | `/Users/jinqianfei/openclaw-workspaces/product-solution/求职工作流竞品分析报告.md` |
| ProjectTrace 数字足迹聚合器方案 | `/Users/jinqianfei/openclaw-workspaces/product-solution/数字足迹聚合器方案.md` |

### C. 修改日志

| 版本 | 日期 | 修改内容 |
|------|------|----------|
| v1.0.0 | 2026-06-02 | 初始版本 |

---

_本文档由 ProductSolution Agent 生成_