# JobTracer 智能求职工作流设计方案

> **产品名称：** JobTracer（求职足迹）
> **Slogan：** _"你的每一步足迹，都成为面试的底气。"_
> **Version：** v1.0.0 Draft
> **继承自：** ProjectTrace × job-hunter

---

## 1. 核心设计理念

### 1.1 名字与内涵

- **产品名：JobTracer**
- **中文名：智能求职工作流**
- **「足迹」双重含义：**
  1. **求职足迹** — 用户在数字世界留下的所有与职业相关的痕迹：项目文档、技术积累、协作记录、职业关系
  2. **求职追踪** — 从投递到面试到入职的完整过程记录，步步有迹可循

### 1.2 愿景

> _成为每个求职者的「第二大脑」——把你散落在各处的数字足迹，自动整理成面试的底气；从简历到岗位匹配，从HR沟通到面试准备，步步为营，Offer自然而然。_

### 1.3 与 ProjectTrace × job-hunter 的关系

| 组件 | 角色 | 说明 |
|------|------|------|
| **ProjectTrace** | 数字足迹聚合引擎 | 负责扫描本地文件/飞书/GitHub等，构建项目知识库 |
| **job-hunter** | 求职工作流编排器 | 负责简历解析、岗位搜索、投递管理、状态追踪 |
| **JobTracer** | 整合产品 | ProjectTrace 负责"源头供料"，job-hunter 负责"下游应用"，形成完整闭环 |

**整合逻辑：**

```
ProjectTrace（数字足迹聚合）
    │
    │  输出：项目文档摘要 + 技术栈 + 成就亮点
    │        协作经历 + 成果量化数据
    ▼
JobTracer（智能求职工作流）
    │
    ├──→ 简历生成器（基于ProjectTrace输出，生成结构化简历）
    ├──→ 岗位搜索引擎（基于简历技能匹配JD）
    ├──→ HR沟通引擎（智能回复建议 + 跟进提醒）
    └──→ 面试题库引擎（基于简历和JD生成个性化面题库）
```

### 1.4 设计原则

| 原则 | 说明 |
|------|------|
| **数字足迹优先** | 简历内容从用户已有的项目文档中提取，而非要求用户手动输入 |
| **用户确认** | AI生成的简历初稿需用户确认再投递，AI输出是辅助而非替代 |
| **步步可溯** | 每个环节（简历版本、投递记录、HR回复、面试反馈）都有记录 |
| **隐私本地** | 简历和求职数据优先本地存储，不强制上云 |
| **质量优先于数量** | 投递贵精不贵多，AI帮助找准匹配度高的岗位 |

---

## 2. Agent 角色定义

### 2.1 SOUL.md

```markdown
# SOUL.md - JobTracer

你是一个温暖而专业的「求职伙伴」。

## 性格特质

- **懂你**：你理解用户的职业积累不是一张纸，而是多年散落在各处的心血——每一行代码、每一份文档、每一个项目成果。当你说「你的简历准备好了」，那背后是有真实积累支撑的。
- **精准而不卷**：你不追求投100个岗位，你追求投10个最合适的。每个岗位的简历都经过针对性定制，每个HR的回复都有策略。
- **主动但不打扰**：你会在合适的时间出现——新职位发现时、重要节点推进时、需要做选择时。你不会一天发10条消息，但关键时刻你一定在。
- **有温度**：求职有焦虑，你理解。你会在用户收到拒信时说"继续加油"，在用户拿到offer时说"太棒了"。

## 工作方式

- 数字足迹聚合 → 简历生成 → 岗位匹配 → 定制投递 → HR沟通 → 面试准备
- 每个步骤AI辅助，用户做最终决策
- 进度随时可查，状态透明

## 语言风格

- 直接、专业，但有温度
- 用「我帮你查了一下」「根据你的简历」「今天发现了2个新职位」这类表达
- 避免空洞的「好的，我来帮您」
- 数据说话：「匹配度92%」「高于该岗位平均薪资20%」
```

### 2.2 IDENTITY.md

```markdown
# IDENTITY.md

- **Name:** JobTracer
- **Type:** AI驱动的智能求职工作流Agent
- **Emoji:** 🎯
- **人格：** 温暖、专业、精准的职业伙伴
- **职责：** 聚合数字足迹，生成求职简历，匹配合适岗位，辅助HR沟通，备战面试

## 安全守则

1. **不读取密码/密钥** — 不读取本地电脑上的任何密码、API密钥信息
2. **不上报隐私** — 简历和求职数据仅用于求职辅助，不上传任何第三方服务器
3. **授权先行** — 连接任何平台前必须获得用户明确授权
4. **数据本地优先** — 简历和职位数据优先存在本地，不强制上云
5. **内容来源透明** — 简历中引用的项目成果需标注来源（用户已有文档），用户可追溯
```

---

## 3. 完整用户旅程（8步）

### Step 1: 数字足迹聚合

**入口：** 用户说「开始求职」

**执行内容：**
- 扫描本地项目文档（调用 ProjectTrace 核心引擎）
- 扫描飞书文档/知识库（Lark/Feishu）
- 读取 GitHub 项目（Issues/Wiki/Repo内容）
- 读取 OpenClaw MEMORY.md（了解用户背景）
- **读取企业文档平台：**
  - 钉钉文档/知识库（dws CLI）
  - 企业微信文档（WeCom API）
  - 飞书文档/知识库（Lark/Feishu MCP）
- **读取各AI Agent平台的工作记录和记忆：**
  - OpenClaw（MEMORY.md、memory/目录、workspace文件）
  - Claude Code（项目目录、工作历史）
  - Codex/GitHub Copilot（代码协作记录）
  - Trae（工作区记录）
  - Qoder（工作记录）
  - WorkBuddy智能体平台（工作记录、项目记忆）
- 整合所有数字足迹，按项目组织

**输出：**
1. `digital_footprint_summary.md` —— 供用户直接查看，包含：
   - 技能图谱（技术栈/软技能）
   - 项目经历摘要（按项目分类）
   - 成果量化数据（可写入简历的亮点）
   - 协作经历概览
2. `~/ProjectTrace/projects/` —— 结构化项目文件夹（供后续简历生成使用）：
   ```
   ~/ProjectTrace/projects/
   ├── ProjectAlpha/
   │   ├── _index.md           # 项目索引（名称/时间/角色/成果）
   │   ├── docs/               # 文档类资料
   │   ├── code_snippets/      # 关键代码片段
   │   ├── data/               # 数据/成果文件
   │   └── metadata.json       # 项目元数据
   ├── ProjectBeta/
   │   └── ...
   └── _unclassified/          # 尚未归类的内容
   ```

**用户确认：** 用户查看数字足迹摘要 + 项目文件夹结构，确认没有遗漏重要内容

---

### Step 2: 生成基础简历

**输入：** 
- Step 1 的 `digital_footprint_summary.md`（用户数字足迹摘要）
- Step 1 输出的 `~/ProjectTrace/projects/`（结构化项目文件夹）
- 用户补充信息（工作年限、学历、求职意向城市、期望薪资）

**执行内容：**
1. **理解用户职业定位**
   - 分析数字足迹摘要，推断用户当前/目标职业角色（如：后端开发/产品经理/算法工程师）
   - 结合工作年限和技术栈，确定简历定位
2. **深度阅读项目文件夹**
   - 逐个读取 `projects/ProjectX/_index.md`，理解每个项目的核心价值
   - 阅读 `projects/ProjectX/docs/` 和 `code_snippets/`，提取关键技术贡献
   - 从 `metadata.json` 获取项目时间、角色、成果量化数据
3. **LLM 生成结构化简历**
   - 根据职业定位，筛选 relevant 的项目经历
   - 将量化数据转化为简历 bullet points（注意区分「项目成果」vs「个人贡献」）
   - 生成符合目标岗位的简历结构和表达方式

**输出：** 
- `resume.json`（结构化简历，含基础字段 + 项目经历 + 技能列表）
- 用户可预览、编辑、确认

**与 ProjectTrace 的数据流：**

```
ProjectTrace 索引
    │
    ├── 项目文档内容（content_full_path）
    ├── 项目元数据（项目名、时间、角色）
    ├── 向量特征（skills、technologies）
    └── skills_vector.json
    │
~/ProjectTrace/projects/（结构化项目文件夹）
    │
    ├── ProjectAlpha/_index.md    （项目核心价值 + 成果数据）
    ├── ProjectAlpha/docs/        （文档资料）
    ├── ProjectAlpha/code_snippets/（关键代码/技术贡献）
    └── ProjectAlpha/metadata.json（项目元数据）
           │
           ▼
    简历生成器（LLM）
    ① 理解职业定位：分析技术栈 + 项目类型 → 确定简历方向
    ② 阅读项目文件夹：提取关键贡献 + 量化成果
    ③ 生成结构化简历：筛选 relevant 项目 + 撰写 bullet points
           │
           ▼
    resume.json（结构化简历）
           │
           ├── name, contact, education
           ├── skills（从技术栈向量提取）
           ├── projects[]（从 ProjectTrace 项目索引提取）
           │    └── 每个项目含：名称/时间/角色/个人贡献/量化成果
           └── target_role（简历定位，如：后端开发工程师）
```

---

### Step 3: 搜索合适工作

**入口：** 用户确认简历后，或每日定时触发

**执行内容：**
- 读取 `resume.json` 提取**技能关键词 + 项目关键词**
  - 技能关键词：Python/Java/React/SQL 等硬技能
  - 项目关键词：从项目经历中提取的领域关键词（如「电商」「供应链」「推荐系统」「中台建设」）
- 并行搜索 BOSS直聘 / 前程无忧 / 牛客 / LinkedIn / Indeed
  - 使用技能词 + 项目词组合搜索，提高召回率
- 对每个JD进行**多维匹配度评分**：
  - 技能匹配（keyword match）
  - 项目背景匹配（领域关键词 overlap）
  - 经验层次匹配（工作年限/职级要求）
  - 薪资/地区匹配
- 按**匹配度 + 薪资 + 地区**综合排序
- **匹配岗位时，同步关联用户相关的项目/作品**
  - 读取 `~/ProjectTrace/projects/`，找出与JD技能/领域匹配的项目
  - 为每个匹配岗位附带「推荐项目列表」（项目名 + 核心成果 + 可附上的作品链接）

**输出：** 
- `job-tracker.json`（职位列表）+ 飞书Bitable记录
- 每个匹配岗位附带**相关项目推荐**（供投递时附加，展示用户真实项目经验）

---

### Step 4: 定制简历投递

**输入：** 用户确认投递的 JD 列表

**执行内容：**
- 对每个目标JD：
  - LLM 分析 JD 关键词
  - 在基础简历基础上，定制化调整 bullet points（强化相关经历）
  - 生成定制简历 HTML → PDF
  - 生成飞书文档（职位详情 + 简历截图 + 投递状态）
- BOSS直聘：调用 `opencli boss greet <uid>` 发招呼（附带定制招呼语）
- 其他平台：生成飞书卡片，包含一键跳转链接

**用户确认点：** 用户预览定制简历，确认后再执行投递

---

### Step 5: HR沟通辅助

**触发条件：** 用户收到HR回复（或主动跟进节点）

**用户设置：** 用户可选择「手动确认模式」或「自动回复模式」
- 手动确认（默认）：生成回复建议 → 用户确认 → 发送
- 自动回复：AI结合简历 + HR消息直接生成回复 → 自动发送（需用户开启）

**执行内容：**
1. 读取HR发来的消息内容
2. LLM分析意图（可能包括但不限于）：
   - 询问项目经历/技术栈
   - 询问意向城市/到岗时间
   - 询问薪资期望
   - 约面试
   - 要简历/联系方式
   - 问方案/谈offer
   - 发offer
3. 结合用户`resume.json`中的实际项目经历、技能栈、求职意向来生成回复
4. 生成回复建议（2-3个选项）
5. 用户选择后，帮写正式回复内容（或自动发送）

**场景示例：**

| HR消息 | 可能的回复选项 | JobTracer建议 |
|--------|-------------|---------------|
| "您好，感兴趣聊一下吗？" | 积极/中性/观望 | 根据匹配度推荐积极 |
| "期望薪资是多少？" | 报高价/报中价/报区间 | 结合市场数据建议 |
| "这周三能参加面试吗？" | 确认/请求改期/婉拒 | 结合日程推荐 |
| "恭喜通过，请确认offer" | 接受/谈条件/等待其他 | 结合策略建议 |
| "您做过哪些推荐系统项目？" | 结合简历项目经历回答 | 提取resume.json对应项目描述 |
| "base哪个城市？" | 结合resume.json意向城市回答 | 直接引用用户求职意向 |
| "能发一下您的简历吗？" | 直接发送/附上定制版 | 发送Step 4生成的定制简历 |
| "方便电话聊聊吗？" | 确认电话/婉拒/改微信 | 结合用户偏好设置 |

---

### Step 6: 发送联系方式

**触发条件：** HR明确要求发送联系方式或简历附件

**执行内容：**
- 识别HR是要求「联系方式」还是「简历」
- **如要简历：** 直接发送Step 4生成的**定制简历PDF**（针对该岗位优化的版本）
- **如要联系方式：** 读取用户联系方式（resume.json.contact）
- 检查隐私信息（过滤敏感数据）
- 用户确认后，通过飞书/邮件发送

**注意：** 此步骤必须用户确认，不自动发送

---

### Step 7: 面试准备

**触发条件：** 约到面试后，用户说「准备面试」

**执行内容：**
- 读取该职位的 JD 和用户简历
- 生成个性化面题库：
  - **基础知识问题**（基于JD所属岗位/行业必备知识，如：后端开发→计算机网络/操作系统/数据库）
  - **技能问题**（基于JD技术栈，如：Java→Spring/多线程/JVM；Python→协程/装饰器）
  - 基于简历提取项目经历 → 生成STAR法则面试问题
  - 常见行为面题（根据简历推断适合的问题）
- 生成每个问题的回答方向（关键词 + 思路框架）

**输出：**
- `interview_prep.md`（面题库 + 回答方向）
- 飞书文档（可分享给用户）
- 模拟面试模式：用户说「练习面试」，JobTracer 随机出题，用户回答后给出反馈

**与 ProjectTrace 的关系：** 项目经历的问题和答案，直接引用 ProjectTrace 聚合的项目文档内容

---

### Step 8: 求职复盘与数据沉淀

**触发时机：** 用户拿到offer / 求职告一段落 / 每周五

**执行内容：**
- 生成求职复盘报告：
  - 投递了多少职位（按平台分布）
  - 响应率、面试转化率
  - 被拒原因分析（如果有）
  - 市场薪资行情总结
  - 表现最好的项目/技能点（供下次求职参考）
- 更新 ProjectTrace 索引：本次求职经历沉淀到 MEMORY.md
- 更新用户偏好：薪资底线、偏好行业、可接受条件

**输出：** `career_review_YYYY-MM-DD.md` + 更新 `feedback.json`

---

## 4. 功能范围与优先级

### 4.1 MVP（Phase 1）— 核心闭环，4周

| 功能 | 优先级 | 依赖 | 说明 |
|------|--------|------|------|
| 数字足迹聚合（复用ProjectTrace） | P0 | ProjectTrace | 本地文件 + 飞书 + GitHub + OpenClaw + 企业微信 + 钉钉 + AI Agent平台 |
| 基础简历生成（JSON） | P0 | 数字足迹 | LLM解析生成结构化简历 |
| 多平台岗位搜索 | P0 | job-hunter | BOSS + 51job + 牛客 + LinkedIn |
| JD匹配度评分 | P0 | 简历 + JD | keyword match + 语义匹配 |
| 定制简历HTML→PDF生成 | P0 | 简历 + JD | 针对每个JD生成定制版 |
| BOSS直聘自动招呼 | P1 | job-hunter | 带定制招呼语 |
| 飞书Bitable职位追踪 | P0 | job-hunter | 状态管理和通知 |
| HR沟通辅助 | P1 | 职位追踪 | 读取HR消息 → 生成回复建议 |
| 每日定时巡检 | P1 | job-hunter | 新职位发现 → 飞书通知 |

### 4.2 Phase 2 — 扩展能力，6周

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 个性化面题库生成 | P1 | 基于 JD + 简历生成面题 |
| 模拟面试模式 | P1 | 随机出题 → 反馈打分 |
| HR回复邮件生成 | P2 | 针对不同意图的邮件模板 |
| 简历多版本管理 | P2 | 技术/管理/国央企 不同版本 |
| 求职复盘报告 | P2 | 自动生成复盘总结 |
| 薪资谈判辅助 | P2 | 基于市场数据给谈判建议 |
| GitHub贡献图谱同步 | P2 | 提取GitHub活动作为能力证明 |
| LinkedIn简历导入 | P2 | 读取LinkedIn信息 |

### 4.3 Phase 3 — 长期愿景，8周+

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 团队协作版（企业猎头） | P3 | 团队管理 + 数据看板 |
| 模拟面试语音模式 | P3 | 实时语音转文字 + AI反馈 |
| 智能Offer比较 | P3 | 多Offer对比分析 |
| 猎头/内推发现 | P3 | 识别可内推的机会 |
| 职业规划（长期） | P3 | 基于用户背景的职业路径建议 |
| API开放 | P3 | 供其他Agent调用JobTracer索引 |

---

## 5. 整体架构

### 5.0 核心架构决策：Agent + 工具调用

**核心观点：** 不要试图让 MCP Server 变成"有灵魂的Agent"，它更适合做"执行层工具"。上下文感知和用户理解应该由 Agent 层来做。

**最终选择：飞书Bot + OpenClaw Agent（当前最优解）**

```
┌─────────────────────────────────────────────────────┐
│  OpenClaw Agent（飞书Bot）                           │
│                                                      │
│  Agent 层（有记忆、有上下文）                          │
│  ├── MEMORY.md（用户背景/偏好/求职意向）              │
│  ├── SOUL.md（人格定义/沟通风格）                     │
│  ├── AGENTS.md（能力定义）                           │
│  └── memory/（每日记录/求职历史）                    │
│              │                                       │
│              ▼                                       │
│  工具层（Tool Calling）                               │
│  ├── dws CLI（钉钉文档/知识库）                      │
│  ├── 飞书 MCP（文档/多维表格）                       │
│  ├── 本地文件扫描（ProjectTrace Core）               │
│  ├── GitHub API（项目/Issues/Wiki）                   │
│  └── supply-chain-tools（MCP工具集）                 │
│              │                                       │
│              ▼                                       │
│  交互层（飞书）                                       │
│  ├── 消息卡片推送                                    │
│  ├── Bitable 状态管理                                │
│  └── 文档/简历分享                                   │
└─────────────────────────────────────────────────────┘
```

**为什么这是最优解：**

| 维度 | 优势 |
|------|------|
| 上下文完整 | MEMORY/SOUL/AGENTS.md 全在本地，Agent随时读取 |
| 工具丰富 | dws CLI + 飞书MCP + 文件扫描 + GitHub API = 完整执行层 |
| 消息触达 | 飞书推送通知，用户随时可交互 |
| 数据本地 | 所有数据在用户自己机器上，隐私安全 |
| 开发成本低 | 复用了现有 OpenClaw 基础设施 |

**MCP 在这个架构里的定位：**
- MCP Server = **暴露执行层工具给外部调用**
- 让 OpenClaw Agent 调用外部服务的能力（GitHub API、钉钉 API 等）
- 不是让外部Agent调用 JobTracer

**未来 SAAS 扩展：**
- 把这套架构复制到云端
- 用户注册 → 配置自己的数据源 → 得到自己的 Agent
- 本质上是"Agent托管服务"

---

### 5.1 数据流架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           JobTracer 系统架构                                │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     ProjectTrace 数字足迹聚合层                      │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │  │
│  │  │本地文件 │ │ 飞书    │ │ GitHub  │ │OpenClaw │ │企业微信 │ │钉钉    │ │邮件    │ │AI Agent │ │  │
│  │  │Connector│ │MCP Conn.│ │ Connector│ │Connector│ │WeCom   │ │dws CLI │ │Conn.   │ │Platforms│ │  │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ │  │
│  │       └──────────┬┴──────────┬┴──────────┬┴──────────┬┴──────────┬┴──────────┴─────────┘        │  │
│  │                  ↓          ↓          ↓          ↓          ↓          ↓                            │  │
│  │           ┌─────────────────────────────────┐                       │  │
│  │           │    Project Clustering Engine     │                       │  │
│  │           │  （项目识别 + 聚类 + 置信度）    │                       │  │
│  │           └───────────────┬─────────────────┘                       │  │
│  └───────────────────────────┼─────────────────────────────────────────┘  │
│                              │ 数字足迹输出                                │
│  ┌───────────────────────────┼─────────────────────────────────────────┐  │
│  │                    JobTracer Core 工作流层                           │  │
│  │                           ↓                                          │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │  │
│  │  │ 简历生成器   │→ │ 岗位搜索引擎  │→ │ HR沟通引擎   │→ │面试题库  │ │  │
│  │  │ Resume      │  │ Job Search   │  │ HR Helper    │  │ Interview│ │  │
│  │  │ Generator   │  │ Engine      │  │             │  │ Prep     │ │  │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └────┬─────┘ │  │
│  │         ↓                ↓                ↓                ↓      │  │
│  │  ┌──────────────────────────────────────────────────────────────┐ │  │
│  │  │              Job Tracker（统一状态管理 + Bitable）              │ │  │
│  │  └──────────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                              ↓                                            │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                       输出层 & 通知层                               │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │  │
│  │  │定制简历 │  │飞书文档 │  │飞书Bitable│  │邮件/消息│  │飞书通知 │  │  │
│  │  │  PDF    │  │  Card   │  │  Record  │  │  投递   │  │  Alert  │  │  │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 模块职责

| 模块 | 职责 | 继承/复用 |
|------|------|----------|
| **数字足迹聚合层** | 扫描各平台内容，按项目聚类 | 复用 ProjectTrace 全部 Connector + 聚类引擎 |
| **简历生成器** | 解析数字足迹摘要 + 用户输入 → 结构化 resume.json | 新增，基于 LLM |
| **岗位搜索引擎** | 多平台搜索 + JD匹配评分 + 去重排序 | 复用 job-hunter 搜索模块 |
| **HR沟通引擎** | 分析HR意图 + 生成回复建议 + 发送辅助 | 新增，基于 LLM + job-tracker |
| **面试题库引擎** | 基于 JD + 简历生成个性化面题 + 模拟练习 | 新增，基于 LLM |
| **Job Tracker** | 统一状态管理 + Bitable 联动 | 复用 job-hunter job-tracker |
| **通知中心** | 飞书/邮件通知，触发条件管理 | 复用 job-hunter 通知机制 |

### 5.3 与现有 job-hunter Skill 的整合方案

**核心原则：复用而非重复**

job-hunter skill 作为「求职状态管理层」，JobTracer 作为「工作流编排层」，两者通过数据层解耦：

```
job-hunter skill
    │
    ├── memory/state.json          ← 求职状态（共享）
    ├── memory/resume.json         ← 简历数据（JobTracer生成，job-hunter消费）
    ├── memory/job-tracker.json    ← 职位追踪（JobTracer写入，job-hunter读取）
    ├── memory/feedback.json       ← 用户反馈（共享）
    └── scripts/                   ← 工具脚本（搜索、PDF生成、去重排序）
             │
             └── JobTracer 可直接调用这些脚本，无需重写

JobTracer 新增
    │
    ├── digital_footprint/         ← 数字足迹聚合结果（JobTracer独享）
    │   ├── footprint_summary.md
    │   ├── projects_index.json
    │   └── skills_vector.json
    ├── custom_resumes/           ← 各JD定制简历（JobTracer独享）
    ├── interview_prep/           ← 面题库（JobTracer独享）
    └── jobtracer_config.yaml      ← JobTracer特定配置（与job-hunter配置分离）
```

**整合接口：**

| 数据流方向 | 触发条件 | 数据内容 |
|-----------|---------|---------|
| ProjectTrace → job-hunter | 用户确认「开始求职」 | resume.json（由数字足迹生成）|
| job-hunter → ProjectTrace | 用户反馈「薪资太低」| 更新 salary_threshold 回传 |
| JobTracer → job-tracker | 新建职位记录 | job_id + status + match_score |
| JobTracer → interview_prep | 面试准备请求 | 从 job-tracker 获取 JD + resume → 生成面题 |

**skill 调用约定：**

JobTracer 需要调用 job-hunter 的工具时，通过 OpenClaw agent 间消息传递：

```bash
# 搜索职位（调用 job-hunter 脚本）
node ~/.agents/skills/job-hunter/scripts/dedup-sort.mjs '<jobs_json>'

# 生成定制简历PDF（调用 job-hunter 脚本）
node ~/.agents/skills/job-hunter/scripts/html-to-pdf.mjs '<html_path>'

# BOSS发招呼（调用 job-hunter 命令）
opencli boss greet <uid>
```

---

## 6. 每个功能模块详细设计

### 6.1 数字足迹聚合模块

**继承自：** ProjectTrace 全部 Connector + 聚类引擎

**JobTracer 专有的增强：**

#### 6.1.1 AI Agent平台Connector（新增）

JobTracer 特有的数据源——从各AI Agent平台读取用户的工作记录和记忆，这是核心差异化之一：

```python
class AIAgentPlatformsConnector:
    """"读取用户在各AI Agent平台的工作记录"""
    
    def __init__(self):
        self.platforms = {
            "openclaw": OpenClawConnector(),
            "claude_code": ClaudeCodeConnector(),
            "codex": CodexConnector(),
            "trae": TraeConnector(),
            "qoder": QoderConnector(),
        }
    
    def scan_all(self) -> List[ContentItem]:
        """并发扫描所有AI Agent平台"""
        items = []
        for name, connector in self.platforms.items():
            try:
                items.extend(connector.scan())
            except Exception as e:
                log.warning(f"Failed to scan {name}: {e}")
        return items
```

**各平台接入方案：**


| 平台 | 读取内容 | 接入方式 |
|------|---------|---------|
| **OpenClaw** | MEMORY.md、memory/目录、workspace文件 | 直接文件读取 |
| **Claude Code** | 项目目录、`.claude`目录、工作历史 | 本地目录扫描 |
| **Codex/GitHub Copilot** | 代码片段历史、项目协作记录 | API调用（需用户授权）|
| **Trae** | 工作区记录、项目上下文 | 本地数据库读取 |
| **Qoder** | 工作记录、项目目录 | 本地数据读取 |

**注意：** 各AI Agent平台的数据路径需用户配置或自动检测，敏感信息自动过滤（密码/API Key等）。

#### 6.1.2 简历相关特征提取

在 ProjectTrace 聚类结果基础上，增加「简历特征提取」子模块：

```python
class ResumeFeatureExtractor:
    """从 ProjectTrace 聚类结果中提取简历相关特征"""

    def extract_skills(self, project_items: List[ContentItem]) -> List[str]:
        """从项目文档中提取技术栈（Python/Java/React/SQL等）"""
        # 使用 TF-IDF 提取技术关键词
        # 结合职位名称推断技能（如"后端开发" → Python/Java/Spring/MySQL）

    def extract_quantified_achievements(self, project_items: List[ContentItem]) -> List[str]:
        """从项目中提取可量化的成果"""
        # 识别数字 pattern："提升30%性能"、"用户100万+"、"订单量50万/天"
        # 结合项目描述，生成可写进简历的 bullet points

    def extract_collaboration_patterns(self, project_items: List[ContentItem]) -> List[str]:
        """从项目中提取协作相关经历"""
        # 识别跨团队协作、甲方对接、技术方案评审等
        # 生成「团队协作」「项目管理」相关描述

    def generate_footprint_summary(self, user_profile: dict) -> str:
        """生成数字足迹摘要（供简历生成使用）"""
        return markdown_report
```

#### 6.1.2 技能向量构建

```python
# 构建用户技能向量（用于JD匹配）
skills_vector = {
    "technical": {
        "languages": ["Python", "JavaScript", "SQL"],
        "frameworks": ["React", "Spring Boot", "FastAPI"],
        "databases": ["MySQL", "PostgreSQL", "Redis"],
        "cloud": ["AWS", "Docker", "Kubernetes"],
        "ml_ai": ["PyTorch", "LLM", "RAG", "LangChain"]
    },
    "soft_skills": ["项目管理", "跨团队协作", "技术方案设计", "代码评审"],
    "certifications": ["PMP", "AWS Certified Solutions Architect"]
}
```

---

### 6.2 简历生成器模块

#### 6.2.1 简历结构（resume.json）

```json
{
  "version": "v1.0",
  "name": "张三",
  "contact": {
    "phone": "138xxxx8888",
    "email": "zhangsan@gmail.com",
    "location": "上海"
  },
  "summary": "8年+后端开发经验，擅长分布式系统设计，曾主导电商平台核心交易系统重构，日峰值订单50万+。",
  "skills": {
    "technical": ["Python", "Java", "Go", "MySQL", "Redis", "Kafka", "K8s"],
    "soft": ["技术方案设计", "跨团队协作", "Mentoring"]
  },
  "experience": [
    {
      "company": "XX科技",
      "title": "高级后端工程师",
      "duration": "2021.03 - 至今",
      "highlights": [
        "主导交易系统重构，采用微服务架构，峰值TPS提升3倍（5万→15万）",
        "设计并落地订单按量计费系统，支持10万+商户接入",
        "搭建自动化测试体系，代码覆盖率从35%提升至78%"
      ],
      "source_docs": ["~/ProjectTrace/projects/XX电商/docs/交易系统设计.md"]
    }
  ],
  "projects": [
    {
      "name": "订单按量计费系统",
      "role": "Owner",
      "description": "支持多租户按量计费的SaaS系统",
      "metrics": "10万+商户，日均订单50万+",
      "source_docs": ["飞书文档链接"]
    }
  ],
  "education": {
    "school": "XX大学",
    "degree": "硕士",
    "major": "计算机科学",
    "graduation": "2018"
  },
  "meta": {
    "generated_from": "digital_footprint",
    "user_confirmed": false,
    "generated_at": "2026-06-02T10:00:00+08:00"
  }
}
```

#### 6.2.2 简历定制策略（针对JD）

```python
def customize_resume_for_jd(resume: dict, jd: dict) -> dict:
    """
    针对特定JD定制简历
    原则：强化相关内容，轻化无关内容，不编造
    """

    # 1. 提取JD关键词及其权重
    jd_keywords = extract_jd_keywords(jd)  # {'微服务': 0.8, 'Kafka': 0.7, 'Java': 0.6}

    # 2. 对简历每个bullet point打分
    def score_bullet(bullet, jd_keywords):
        score = 0
        for kw, weight in jd_keywords.items():
            if kw in bullet:
                score += weight
        return score

    # 3. 高分bullet前置，低分bullet后移或删除
    # 4. 在summary中强调相关经验
    # 5. 生成定制版简历（保留原始数据，仅调整展示顺序和措辞）
```

---

### 6.3 岗位搜索引擎模块

#### 6.3.1 搜索策略

```python
def build_search_queries(resume: dict, state: dict) -> List[dict]:
    """从简历和求职状态构建搜索关键词"""

    queries = []

    # 核心技能 → 搜索词
    for skill in resume['skills']['technical'][:5]:
        queries.append({
            "keyword": f"{skill} 工程师",
            "weight": 1.0,
            "platform": "all"
        })

    # 职位title → 搜索词
    if 'expected_position' in state:
        queries.append({
            "keyword": state['expected_position'],
            "weight": 1.5,
            "platform": "all"
        })

    # 城市 + 技能组合
    if 'city' in state:
        for skill in resume['skills']['technical'][:3]:
            queries.append({
                "keyword": f"{state['city']} {skill} 招聘",
                "weight": 0.8,
                "platform": "boss,51job"
            })

    return queries
```

#### 6.3.2 JD匹配度评分算法

```python
def calculate_match_score(resume: dict, jd: dict) -> float:
    """
    JD匹配度评分（0-100）
    基于：关键词匹配（40%）+ 经验年限（20%）+ 薪资匹配（20%）+ 地区匹配（20%）
    """

    score = 0

    # 1. 关键词匹配（40分）
    resume_skills = set(resume['skills']['technical'])
    jd_skills = set(extract_jd_technical_skills(jd))
    skill_overlap = len(resume_skills & jd_skills) / max(len(jd_skills), 1)
    score += skill_overlap * 40

    # 2. 经验年限（20分）
    resume_years = calculate_experience_years(resume)
    jd_min_years = extract_jd_min_years(jd)
    if resume_years >= jd_min_years:
        score += 20
    elif resume_years >= jd_min_years * 0.8:
        score += 15
    else:
        score += 5

    # 3. 薪资匹配（20分）
    expected = resume.get('salary_expectation', state.get('expected_salary', 0))
    jd_salary = extract_jd_salary(jd)
    if jd_salary and expected and jd_salary >= expected * 0.85:
        score += 20
    elif jd_salary and jd_salary < expected * 0.7:
        score += 5  # 薪资太低

    # 4. 地区匹配（20分）
    if state.get('city') in jd.get('location', ''):
        score += 20

    return min(100, int(score))
```

---

### 6.4 HR沟通引擎模块

#### 6.4.1 意图分类

```python
HR_INTENTS = {
    "initial_contact": "初次联系，询问兴趣",
    "project_inquiry": "询问项目经历/技术细节",
    "skill_inquiry": "询问技术栈/技能",
    "city_inquiry": "询问意向城市/工作地点",
    "availability_inquiry": "询问时间availability",
    "salary_inquiry": "询问薪资期望",
    "contact_inquiry": "询问联系方式",
    "resume_request": "要简历/简历附件",
    "solution_inquiry": "询问方案/作品/案例",
    "interview_invite": "邀请参加面试",
    "offer_extended": "发送offer",
    "rejection": "礼貌拒绝",
    "follow_up": "跟进进度",
    "additional_info": "要求补充信息"
}
```

#### 6.4.2 回复生成策略

```python
def generate_hr_replies(intent: str, context: dict) -> List[dict]:
    """
    根据HR意图生成多个回复选项
    返回：[{option: str, tone: str, recommended: bool}]
    """

    replies = {
        "salary_inquiry": [
            {
                "option": f"我的期望薪资是{context['expected_salary']}元/月，结合市场行情和我的经验，期待在合理范围内。",
                "tone": "中性",
                "recommended": True  # 基于用户数据
            },
            {
                "option": "薪资方面我比较灵活，更关注岗位的发展空间和团队技术栈是否能发挥我的优势。",
                "tone": "观望",
                "recommended": False
            }
        ],
        "interview_invite": [
            {
                "option": "感谢您的邀请，我周三下午2-4点有时间参加面试，请问方便吗？",
                "tone": "积极",
                "recommended": True
            },
            {
                "option": "我周三有两个会议，可能不太方便，请问周四上午或者周五下午可以吗？",
                "tone": "中性",
                "recommended": False
            }
        ],
        "project_inquiry": [
            {
                "option": f"我有相关项目经验，{context.get('relevant_project', '已在简历中详细列出')},核心贡献是...",
                "tone": "积极",
                "recommended": True
            }
        ],
        "city_inquiry": [
            {
                "option": f"我的意向城市是{context.get('target_city', '简历中已注明')},可以考虑远程或出差。",
                "tone": "中性",
                "recommended": True
            }
        ],
        "contact_inquiry": [
            {
                "option": f"我的联系方式是：电话{context.get('phone', '')}，邮箱{context.get('email', '')}。",
                "tone": "中性",
                "recommended": True
            }
        ],
        "resume_request": [
            {
                "option": "简历已准备好，稍后发送给您。请问发送到哪个邮箱？",
                "tone": "积极",
                "recommended": True
            }
        ]
    }

    return replies.get(intent, [])
```

---

### 6.5 面试题库引擎模块

#### 6.5.1 面题库生成策略

```python
def generate_interview_questions(resume: dict, jd: dict, num_questions: int = 15) -> dict:
    """
    基于简历和JD生成个性化面题库
    """

    questions = {
        "basic_knowledge": [],  # 基础知识（岗位/行业必备，如OS/网络/数据结构）
        "technical": [],       # 技术技能问题（JD技术栈）
        "behavioral": [],       # 行为问题（STAR法则，基于简历经历）
        "situational": [],      # 场景问题（假设性问题）
        "reverse": []          # 反问面试官的问题
    }

    # 1. 从JD推断岗位类型 → 生成基础知识问题
    job_level = infer_job_level(jd)  # 推断职级（初级/中级/高级）
    job_category = infer_job_category(jd)  # 推断岗位类别（后端/前端/算法/产品等）
    basic_knowledge_map = {
        "后端": ["计算机网络","操作系统","数据结构与算法","数据库"],
        "前端": ["浏览器原理","HTML/CSS/JavaScript基础","网络协议","性能优化"],
        "算法": ["机器学习基础","统计学习方法","深度学习基础","数据结构与算法"],
        "产品": ["需求分析","竞品分析","用户研究","数据分析"],
    }
    for topic in basic_knowledge_map.get(job_category, ["计算机网络","操作系统","数据结构"]):
        questions["basic_knowledge"].append({
            "question": f"请谈谈你对{topic}的理解，以及在实际项目中是如何应用的？",
            "type": "basic_knowledge",
            "topic": topic,
            "level": job_level
        })

    # 2. 从JD提取技术关键词 → 生成技术技能问题
    jd_tech_keywords = extract_jd_technical_skills(jd)
    for kw in jd_tech_keywords[:5]:
        questions["technical"].append({
            "question": f"请介绍一下{kw}在你经历过的项目中的实际应用场景，以及遇到过哪些挑战？",
            "type": "technical",
            "difficulty": "medium",
            "keywords": [kw]
        })

    # 3. 从简历项目经历 → 生成STAR法则面题
    for project in resume['projects'][:3]:
        questions["behavioral"].append({
            "question": f"请用STAR法则介绍一下{project['name']}这个项目，"
                        f"特别是你遇到的最大挑战是什么，如何解决的？",
            "type": "behavioral",
            "source": project['name'],
            "star_framework": True
        })

    # 3. 量化成果问题
    for exp in resume['experience']:
        for highlight in exp.get('highlights', []):
            if any(c.isdigit() for c in highlight):
                questions["behavioral"].append({
                    "question": f"{highlight} 这个成果是如何实现的？具体你做了什么？",
                    "type": "behavioral",
                    "metric_focused": True
                })

    # 4. 反问面试官问题（展示候选人主动思考）
    questions["reverse"] = [
        "这个岗位的日常工作主要涉及哪些技术栈？",
        "团队目前面临的最大技术挑战是什么？",
        "入职后3-6个月的期望是什么？",
        "这个岗位的成长路径是怎样的？"
    ]

    return questions
```

#### 6.5.2 回答方向生成

```python
def generate_answer_guidance(question: dict, resume: dict) -> str:
    """
    为每个问题生成回答方向
    不是给出标准答案，而是给出思路框架 + 相关素材位置
    """

    if question['type'] == 'behavioral':
        # 找到简历中对应的经历
        related_exp = find_related_experience(question, resume)
        return f"""
回答思路：
1. Situation（背景）：{related_exp.get('context', '项目背景请参考')}
2. Task（任务）：你在这个项目中的角色是什么
3. Action（行动）：你具体做了什么（避免说"我们团队"）
4. Result（结果）：量化的成果（如有）

相关素材（来自你的数字足迹）：
- 项目：{related_exp.get('name')}
- 来源文档：{related_exp.get('source_docs')}
"""
    elif question['type'] == 'technical':
        return f"""
回答思路：
1. 简要介绍该技术的核心概念（1-2句话）
2. 描述在你经历的项目中的实际应用场景
3. 遇到的挑战及解决方案
4. 如果重来会有哪些改进

相关素材请参考你的数字足迹中相关项目的文档。
"""
```

---

## 7. 与现有 job-hunter skill 的整合方案

### 7.1 架构整合图

```
job-hunter skill（求职状态管理层）
    │
    ├── 职责：管理 state.json / resume.json / job-tracker.json / feedback.json
    ├── 搜索命令：opencli boss/51job/nowcoder/linkedin search
    ├── 工具脚本：dedup-sort.mjs / html-to-pdf.mjs / apply-feedback.mjs
    └── 调度：每日 cron 定时巡检
              │
              │ 数据写入（resume.json / job-tracker.json）
              ▼
JobTracer（工作流编排层）
    │
    ├── 职责：编排完整求职旅程（Step 1-8）
    ├── 数字足迹聚合（ProjectTrace）
    ├── 简历生成（基于数字足迹）
    ├── HR沟通引擎
    ├── 面试题库引擎
    └── 求职复盘报告

    两者通过数据文件解耦，通过 skill 间消息传递协作
```

### 7.2 共享数据接口

| 数据文件 | 主要写入方 | 主要读取方 | 说明 |
|---------|----------|----------|------|
| `memory/state.json` | job-hunter | 两者共享 | 求职状态、城市、薪资 |
| `memory/resume.json` | JobTracer | 两者共享 | 简历JSON |
| `memory/job-tracker.json` | JobTracer | 两者共享 | 职位追踪 |
| `memory/feedback.json` | 两者共享 | 两者共享 | 用户反馈 |

### 7.3 整合流程示例

#### 示例1：用户说「开始求职」

```
1. JobTracer 接收请求
2. 调用 ProjectTrace 执行数字足迹扫描
3. 生成 digital_footprint_summary.md
4. 生成 resume.json（调用 LLM）
5. 将 resume.json 写入 job-hunter 的 memory/ 目录
6. 更新 job-hunter state.status = "job-hunting"
7. 触发 job-hunter 搜索流程
8. 将搜索结果写入 job-tracker.json
9. 生成飞书通知，告知用户发现X个职位
```

#### 示例2：用户收到HR消息，说「帮我回复」

```
1. JobTracer 接收用户粘贴的HR消息
2. 调用 LLM 进行意图分类 → "salary_inquiry"
3. 读取 resume.json 的薪资期望 + job-tracker.json 的其他offer情况
4. 生成多个回复选项
5. 用户选择后，帮写正式回复内容
```

---

## 8. 差异化竞争分析

### 8.1 市场空白（引用竞品分析报告结论）

**发现1：无全链路整合者**

现有竞品呈现"三段分裂"：
- **A段（简历）**：Kickresume、Rezi、Enhancv → 擅长简历，不懂投递
- **B段（投递）**：Lazyapply、Simplify → 强自动化，但无后续
- **C段（面试）**：Offer蛙、Google Interview Warmup → 专注面试，缺前端

**没有任何一个产品真正打通 A→B→C 全链路。**

**发现2：自动化的信任危机**

主流auto-apply工具（Lazyapply 2.4/5、AiApply F评级）口碑差，核心问题：
1. 表单填写错误多
2. 目标定位不准（投错岗位/语言）
3. 平台封禁风险（LinkedIn明确反自动化）
4. 无退款保障

**市场存在对"有质量的自动化"的强需求缺口。

**发现3：数字足迹聚合是空白中的空白**

竞品均要求用户手动输入简历内容。没有任何工具从用户已有的：
- LinkedIn 账号
- GitHub 项目
- 微信/小红书分享内容
- 工作文档（如Notion、飞书）
自动聚合数字足迹，生成结构化简历素材。

**发现4：HR沟通环节完全缺失**

没有竞品提供：
- 简历投递后的自动跟进邮件生成
- HR消息的AI回复建议
- Offer谈判策略
- 薪资谈判支持

**发现5：国内市场无真正全链路产品**

国内产品（职徒简历、Offer蛙）均是单点工具，无全链路；海外Teal是全链路最强，但缺面试模拟环节，且无中文本地化。

### 8.2 JobTracer 差异化定位

| 差异化维度 | 竞品缺口 | JobTracer机会 |
|-----------|---------|--------------|
| **全链路覆盖** | 无竞品覆盖A→B→C | 首年聚焦三个核心节点，其余节点集成合作 |
| **数字足迹聚合** | 完全空白 | 接入LinkedIn/GitHub/飞书，自动生成简历素材 |
| **有质量的自动化** | Lazyapply们重数量轻质量 | AI+人工审核hybrid模式，确保投递质量 |
| **HR沟通辅助** | 完全空白 | Offer前/后的AI沟通助手 |
| **面试全流程准备** | Teal/Resume Worded均无 | 面试押题+真实模拟+反馈闭环 |
| **国内本地化** | 海外产品均无 | 中文简历/Boss直聘/猎聘/领英全支持 |

---

## 9. 数据存储设计

### 9.1 扩展 SQLite Schema（在 ProjectTrace 基础上新增）

```sql
-- 继承 ProjectTrace 的表结构，新增以下JobTracer专用表：

-- 表7: 简历版本表
CREATE TABLE resume_versions (
  id TEXT PRIMARY KEY,
  version_label TEXT,              -- 'v1.0', 'v2.0', 'JD定制-某公司'
  resume_data TEXT,                -- JSON，完整简历数据
  source TEXT,                     -- 'digital_footprint' | 'manual' | 'jd_customized'
  jd_id TEXT,                      -- 如果是JD定制版，记录对应的JD
  created_at TEXT DEFAULT (datetime('now')),
  is_active INTEGER DEFAULT 1
);

-- 表8: 简历定制记录表
CREATE TABLE resume_customizations (
  id TEXT PRIMARY KEY,
  resume_version_id TEXT,
  jd_id TEXT NOT NULL,
  jd_title TEXT,
  jd_company TEXT,
  customization_notes TEXT,        -- JSON，调整了哪些bullet points
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (resume_version_id) REFERENCES resume_versions(id)
);

-- 表9: HR沟通记录表
CREATE TABLE hr_conversations (
  id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL,
  direction TEXT,                  -- 'inbound' | 'outbound'
  intent TEXT,                     -- 'initial_contact' | 'salary_inquiry' etc.
  message_preview TEXT,            -- 消息摘要（前100字）
  message_full TEXT,               -- 完整消息
  suggested_replies TEXT,          -- JSON，AI生成的回复选项
  user_selected_reply TEXT,        -- 用户选择的回复
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (job_id) REFERENCES jobs(id)
);

-- 表10: 面试准备记录表
CREATE TABLE interview_prep (
  id TEXT PRIMARY KEY,
  job_id TEXT,
  questions TEXT,                  -- JSON，面题库
  prep_status TEXT DEFAULT 'generated',  -- 'generated' | 'practicing' | 'completed'
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (job_id) REFERENCES jobs(id)
);

-- 表11: 求职复盘表
CREATE TABLE career_reviews (
  id TEXT PRIMARY KEY,
  review_period TEXT,              -- 'weekly' | 'monthly' | 'offer_received' | 'job_ended'
  start_date TEXT,
  end_date TEXT,
  report TEXT,                    -- Markdown，复盘报告内容
  metrics TEXT,                    -- JSON，统计数据
  created_at TEXT DEFAULT (datetime('now'))
);
```

### 9.2 数据目录结构

```
~/.JobTracer/
├── .index/
│   ├── trace.db              # SQLite 主索引（继承ProjectTrace）
│   └── jobtracer.db          # JobTracer 专用索引
├── digital_footprint/
│   ├── footprint_summary.md
│   ├── projects_index.json
│   └── skills_vector.json
├── resumes/
│   ├── base/
│   │   ├── v1.0.json
│   │   └── v1.0.pdf
│   └── customized/
│       └── {jd_id}/
│           ├── customized.json
│           └── customized.pdf
├── interview_prep/
│   └── {job_id}/
│       ├── questions.json
│       └── notes.md
└── config.yaml
```

---

## 10. 开发计划

### Phase 1: MVP（目标：4周）

**目标：** 实现「数字足迹聚合 → 简历生成 → 岗位搜索 → 定制投递」核心闭环

| Week | 任务 | 交付物 |
|------|------|--------|
| Week 1 | 架构搭建：复用ProjectTrace + job-hunter数据层整合 | 可运行的空壳项目 |
| Week 1 | 数字足迹聚合：调用ProjectTrace生成footprint_summary | 数字足迹摘要 |
| Week 2 | 简历生成器：LLM解析footprint → resume.json | 结构化简历JSON |
| Week 2 | 岗位搜索：复用job-hunter搜索模块集成 | 多平台职位列表 |
| Week 3 | JD匹配评分 + 定制简历HTML生成 | 匹配度评分 + 定制简历 |
| Week 3 | BOSS发招呼 + 飞书文档生成 | 投递状态更新 |
| Week 4 | 飞书Bitable集成 + 每日巡检 | 完整MVP可演示版本 |
| Week 4 | 内部测试 + Bug修复 | Beta测试报告 |

**MVP成功标准：**
- ✅ 能够从ProjectTrace提取数字足迹并生成可读简历
- ✅ 多平台搜索可用，JD匹配评分展示
- ✅ 针对特定JD生成的定制简历可读
- ✅ BOSS直聘发招呼成功

### Phase 2: 扩展能力（目标：6周）

| Week | 任务 |
|------|------|
| Week 5-6 | HR沟通引擎 + 意图分类 + 回复生成 |
| Week 7-8 | 个性化面题库生成 + 模拟面试模式 |
| Week 9-10 | 简历多版本管理 + 求职复盘报告 |
| Week 11-12 | 薪资谈判辅助 + LinkedIn/GitHub导入 |

**Phase 2成功标准：**
- ✅ HR沟通辅助可用，生成多个回复选项
- ✅ 面题库生成准确，关联简历经历
- ✅ 模拟面试模式可运行

### Phase 3: 生态整合（目标：8周+）

| Milestone | 任务 |
|-----------|------|
| M1 | 模拟面试语音模式（实时语音转文字 + AI反馈）|
| M2 | 智能Offer比较 + 多Offer分析 |
| M3 | 猎头/内推发现 |
| M4 | API开放（供其他Agent调用JobTracer索引）|

---

## 11. 技术选型

### 11.1 编程语言

**选择：Python 3.11+**

| 考量因素 | 说明 |
|----------|------|
| 生态丰富 | 文档解析、HTTP请求、向量库都有成熟库 |
| Agent友好 | 与 OpenClaw/Claude 等AI平台集成方便 |
| 跨平台 | macOS/Linux/Windows 均可运行 |
| LLM调用 | OpenAI SDK、Anthropic SDK 均有 Python 版本 |

### 11.2 核心依赖

```txt
# JobTracer 专用新增依赖：
openai>=1.0.0             # LLM调用（简历生成、HR意图分类等）
anthropic>=0.8.0         # Anthropic API（备选）

# 复用 ProjectTrace 依赖（见ProjectTrace方案）
# 复用 job-hunter 依赖（见job-hunter SKILL.md）
```

### 11.3 项目结构

```
JobTracer/
├── __init__.py
├── main.py                    # 入口文件
├── soul.md                    # Agent人格定义
├── identity.md                # Agent身份定义
│
├── core/                      # 核心引擎
│   ├── __init__.py
│   ├── resume_generator.py    # 简历生成器（新增）
│   ├── jd_matcher.py         # JD匹配度评分（新增）
│   ├── hr_helper.py          # HR沟通引擎（新增）
│   ├── interview_prep.py     # 面试题库引擎（新增）
│   ├── career_review.py      # 求职复盘（新增）
│   └── workflow.py           # 工作流编排（新增）
│
├── integrations/             # 集成层
│   ├── __init__.py
│   ├── projecttrace/         # ProjectTrace 集成（调用其Connector+聚类引擎）
│   └── jobhunter/            # job-hunter 集成（调用其脚本和状态管理）
│
├── output/                    # 输出生成
│   ├── __init__.py
│   ├── resume_template.html  # 简历HTML模板
│   ├── pdf_generator.py      # PDF生成
│   └── feishu_doc.py         # 飞书文档生成
│
├── config/
│   └── default.yaml          # 默认配置
│
├── memory/                    # JobTracer 专用内存
│   ├── digital_footprint/
│   ├── resume_versions/
│   └── interview_prep/
│
├── tests/
│   └── test_workflows.py     # 工作流测试
│
├── requirements.txt
└── README.md
```

---

## 12. 风险与应对

### 12.1 核心风险

| 风险 | 可能性 | 影响 | 应对策略 |
|------|--------|------|----------|
| **ProjectTrace 聚类准确率不足** | 中 | 高 | Phase 1 重点测试聚类效果，必要时降级为手动指定项目 |
| **数字足迹内容不足** | 中 | 中 | 提供手动补充入口，允许用户上传额外文档 |
| **JD匹配评分不准确** | 中 | 中 | Phase 2 引入人工反馈调优机制 |
| **BOSS直聘发招呼被限制** | 高 | 中 | 降级为"生成招呼语+手动复制"模式 |
| **LLM输出质量不稳定** | 中 | 高 | Phase 1 使用GPT-4，Phase 2 考虑本地模型 |

### 12.2 合规风险

| 风险 | 说明 | 应对 |
|------|------|------|
| **隐私合规** | 简历包含大量个人数据 | 明确数据使用政策，本地存储优先 |
| **BOSS直聘API合规** | 自动化发消息可能违反平台规则 | 限制发消息频率，提供手动模式 |
| **简历内容来源** | 数字足迹内容可能包含敏感信息 | 增加隐私过滤规则 |

---

## 修改日志

| 版本 | 日期 | 修改内容 |
|------|------|----------|
| v1.0.0 | 2026-06-02 | 初始版本，整合ProjectTrace + job-hunter |

---

_本文档由 ProductSolution Agent 生成，整合了 ProjectTrace 数字足迹聚合方案 和 job-hunter 求职助手Skill_

---

## 13. 异常流程处理

### 13.1 异常处理设计原则

本章节定义 JobTracer 在各环节可能出现的异常场景及处理策略，确保系统在部分组件失效时仍能提供可接受的降级服务。

**整体设计原则：**

| 原则 | 说明 |
|------|------|
| **Graceful Degradation（优雅降级）** | 任何模块失败时，优先降级而非整体崩溃；能用多少用多少 |
| **用户知情权** | 异常发生后必须告知用户，让用户了解系统状态，不静默失败 |
| **不污染正常流程** | 异常记录进入错误日志，不影响用户主动发起的操作流程 |
| **可恢复性** | 临时性异常（网络超时、Token过期）提供自动重试；不可恢复异常提供手动补救入口 |
| **数据完整性** | 任何写入操作失败前，需确保已写入的数据不丢失（或有回滚机制） |
| **优先级分层** | P0 = 必须处理，影响核心求职流程；P1 = 重要但不阻断，可延后处理 |

**异常优先级分类标准：**

- **P0（必须处理）：** 发生在核心流程路径上，阻断用户完成主要任务，无降级方案
- **P1（重要但不阻断）：** 发生在外围功能，阻断局部功能但不阻断求职闭环，或有有效降级方案

---

### 13.2 A. 平台相关异常

#### A1. 平台登录失效 / Token 过期 【P0】

**涉及平台：** BOSS直聘、51job、LinkedIn

**异常描述：** 用户已授权的招聘平台账号 Token 过期或被强制下线，导致无法调用平台接口执行搜索、投递、发消息等操作。

**检测机制：**

```
1. API调用时返回 401 Unauthorized 或 403 Forbidden → 识别为 Token 失效
2. 主动心跳：每日巡检前对所有已授权平台执行 Token 验证
3. 平台专用错误码识别：
   - BOSS直聘：返回 error_code = "TOKEN_EXPIRED"
   - LinkedIn：返回 401 + "access token expired"
   - 51job：返回登出状态或验证码要求
```

**处理策略：**

```
Step 1: 检测到 Token 失效，立即停止该平台所有待执行操作（防止刷无用请求）
Step 2: 标记该平台状态为 "需要重新登录"（不影响其他平台继续工作）
Step 3: 缓存该平台已扫描到的数据（保留已完成的工作）
Step 4: 自动生成重新登录引导：
       - 飞书卡片：提示用户"XX平台登录状态已失效，请重新授权"
       - 提供一键授权链接（OAuth重新授权流程）
Step 5: 等待用户重新授权后再试，不自动降级切换其他平台：
       - 该平台暂时标记为"需要重新授权"，暂停该平台的搜索任务
       - 其他已授权平台不受影响，继续正常执行搜索/投递
       - 用户重新授权后，自动恢复该平台服务，已缓存数据完整保留
```

**用户通知方式：**

```
触发时机：检测到Token失效时
通知渠道：飞书卡片（Interactive Card）
通知内容：
- "⚠️ XX平台登录状态已失效"
- 失效原因（如果平台有返回）
- 重新授权按钮（一键跳转OAuth授权页）
- "重新授权后，自动恢复该平台服务，当前已扫描到的职位不受影响"
- 若所有平台均不可用：升级为 P0 告警，人工介入
```

**Code Snippet（检测逻辑）：**

```python
async def verify_and_refresh_token(platform: str, stored_token: dict) -> dict:
    try:
        response = await call_platform_api(platform, "/verify", stored_token)
        if response.status == 200:
            return stored_token  # Token 有效
    except AuthError as e:
        if e.code in ("TOKEN_EXPIRED", "UNAUTHORIZED", 401, 403):
            await mark_platform_status(platform, "requires_reauth")
            await notify_user_reauth(platform)
            return None
```

---

#### A2. 平台反爬 / 封禁 IP / 请求超时 【P1】

**涉及平台：** BOSS直聘、51job、牛客、LinkedIn

**异常描述：** 平台检测到异常请求行为后封禁 IP，或网络不稳定导致请求超时，常见于高频搜索或平台限流政策收紧。

**检测机制：**

```
1. HTTP 响应码识别：
   - 403 Forbidden / 418 I'm a teapot → IP被封禁
   - 429 Too Many Requests → 请求过于频繁
   - 超时（timeout > 30s）→ 网络异常或平台不可达
2. 业务层识别：
   - 返回验证码页面（CAPTCHA触发）
   - 返回空数据但无错误码（疑似反爬拦截）
   - 搜索结果数量异常为0（排除关键词本身无结果的情况）
3. 持续监控：连续3次请求超时 → 判定为平台不稳定
```

**处理策略（指数退避重试）：**

```
重试策略：指数退避（Exponential Backoff）
- 第1次重试：等待 2s
- 第2次重试：等待 4s
- 第3次重试：等待 8s
- 第4次重试：等待 16s
- 第5次重试：等待 30s，超时则放弃

降级方案（当平台持续不可用时）：
1. 标记该平台为 "unavailable" 状态，跳过该平台的搜索/投递
2. 自动切换到其他可用平台执行相同操作
3. 记录平台不可用原因和持续时间，供后续分析
4. 降低整体巡检频率（从每日巡检降级为每2日巡检一次）

IP封禁应对：
- 如果使用代理IP池，自动切换到下一个可用代理IP
- 如果无代理池，降级为手动搜索模式（生成搜索关键词列表供用户手动搜索）
```

**用户告警阈值：**

```
⚠️ 触发用户通知的阈值：
- 单平台连续3次请求失败 → 通知用户"XX平台暂时不可用，已自动切换"
- 单日超过10次请求失败 → 通知用户"XX平台今日请求失败次数过多，建议手动检查"
- 所有平台均不可用 → P0告警，通知用户当前无法自动执行求职操作，提供手动模式入口
```

**Code Snippet（指数退避）：**

```python
async def request_with_backoff(url: str, max_retries: int = 5) -> Response:
    for attempt in range(max_retries):
        try:
            response = await fetch(url, timeout=30)
            return response
        except (TimeoutError, HTTPError) as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt  # 2, 4, 8, 16, 32 秒
            await asyncio.sleep(wait_time)
```

---

#### A3. 搜索结果为空 【P1】

**涉及平台：** 全平台

**异常描述：** 用户在特定关键词/城市组合下搜索，平台返回空结果。可能由关键词过于冷门、平台数据源问题、或用户条件过严导致。

**区分两种场景：**

| 场景 | 判断标准 | 处理策略 |
|------|---------|---------|
| **主动搜索** | 用户手动触发搜索，关键词明确 | 关键词扩展 + 平台切换建议 |
| **定时巡检** | 每日自动巡检，基于已有简历 | 降低巡检频率，次日重新尝试 |

**处理策略：**

```
主动搜索场景（用户主动发起）：
1. 关键词扩展：
   - 使用简历中的次要技能词替换主要技能词（如"Java"→"后端开发"）
   - 放宽城市限制（"上海"→"上海或北京"）
   - 使用近义词/上下位词（"后端"→"服务端"、"Java"→"Java生态"）
2. 平台切换：
   - 平台A无结果 → 自动切换到平台B/C搜索相同关键词
   - 提示用户："在XX平台未找到匹配职位，已切换到YY平台搜索"
3. 用户引导：
   - 生成"关键词调整建议"，列出去掉了哪些限定条件
   - 询问用户是否手动调整搜索条件

定时巡检场景（自动触发）：
1. 记录本次搜索关键词+平台+结果数量
2. 如果连续3日同一关键词无结果 → 生成周报告知用户
3. 自动扩展搜索关键词池（增加同义词/相近领域）
4. 不频繁打扰用户，将问题汇总到每日/每周通知中
```

**用户通知方式：**

```
主动搜索场景：
- 即时卡片：显示搜索结果为0，提供关键词调整建议和手动调整入口
- 不判定为错误，以"提示"形式呈现

定时巡检场景：
- 纳入每日通知："今日巡检发现：XX关键词在过去3天均未找到新职位，建议调整关键词"
```

---

### 13.3 B. 数据相关异常

#### B1. 数字足迹为空（冷启动场景） 【P0】

**异常描述：** 新用户首次使用 JobTracer，系统无法从任何数据源聚合到有效数字足迹，导致简历生成无法进行。

**判断标准：** 执行 Step 1 数字足迹扫描后，所有 Connector 均返回空结果或无有效内容。

**处理策略（最小化启动路径）：**

```
【最小化启动路径】上传简历文档 = 最快启动方式（1分钟完成）

阶段1：引导上传简历文档（首选）
1. 用户上传简历文件（PDF 或 DOCX）→ JobTracer 自动解析 → 生成结构化简历
   - 入口：「上传简历文档」
   - 支持格式：PDF、DOCX
   - 引导话术：「上传简历文档是最快的启动方式，只需1分钟」

阶段2：增强选项（用户在上传简历后可选择性补充）
2. LinkedIn 导入（如已绑定账号，读取个人主页内容）
3. GitHub 导入（如已绑定，扫描仓库名称/描述/Star项目）
4. 飞书文档/知识库（扫描项目文档）

阶段3：兜底选项
5. 手动输入关键信息（最少5个字段：姓名/工作年限/核心技术栈/项目经历概要/求职目标城市）
```
阶段2：增强选项（用户在上传简历后可选择性补充）
2. LinkedIn 导入（如已绑定账号，读取个人主页内容）
3. GitHub 导入（如已绑定，扫描仓库名称/描述/Star项目）
4. 飞书文档/知识库（扫描项目文档）

阶段3：兜底选项
5. 手动输入关键信息（最少5个字段：姓名/工作年限/核心技术栈/项目经历概要/求职目标城市）

```

**激励话术：**
```
💡 还没有数字足迹？上传简历文档是最快的启动方式，只需1分钟。

上传后，你还可以补充：
• 连接LinkedIn → 自动获取职业信息
• 连接GitHub → 自动同步代码项目
• 连接飞书 → 一键同步项目文档

📌 小提示：数字足迹越丰富，简历越精准。
```

```python
def detect_cold_start(projects_index: dict, footprint_summary: dict) -> bool:
    """判断是否为冷启动场景"""
    has_projects = len(projects_index.get("projects", [])) > 0
    has_skills = len(footprint_summary.get("skills", [])) > 0
    has_experience = len(footprint_summary.get("experience", [])) > 0
    
    # 三者均为空，判定为冷启动
    return not (has_projects or has_skills or has_experience)
```

**用户通知方式：**

```
触发时机：冷启动检测完成后，无有效数字足迹
通知形式：飞书卡片 + 引导按钮
卡片内容：
- "🔍 首次使用，还没找到你的数字足迹"
- 4个导入入口按钮（按优先级排列）
- 激励话术
- "这些信息只需要提供一次，之后会自动更新"
```

---

#### B2. 数字足迹扫描失败（部分数据源不可用） 【P1】

**涉及数据源：** 飞书、钉钉、企业微信、GitHub、AI Agent平台（OpenClaw/Claude Code等）

**异常描述：** 数字足迹扫描过程中，部分数据源连接失败（如飞书授权过期、企业微信无法连接、GitHub API限流），但其他数据源成功。

**检测机制：**

```
1. Connector级别错误捕获：
   - 每个 Connector 执行扫描后返回 (status, data, error)
   - status ∈ {success, partial, failed}
   
2. 错误类型识别：
   - 飞书/钉钉/企业微信：OAuth token失效 → 需要重新授权
   - GitHub：API限流（403 + "rate limit exceeded"）→ 等待冷却
   - 本地文件：路径不存在/权限不足 → 跳过该路径
   - AI Agent平台：连接超时 → 标记为不可用

3. 部分失败判断：
   - 任一 Connector 返回 failed → 标记该数据源为"扫描失败"
   - 全部 Connector 均 failed → 升级为 P0 告警
   - 存在至少一个 Connector success → 降级继续
```

**处理策略：**

```
部分失败降级策略：
1. 成功的数据源：
   - 立即处理已扫描到的内容，不等待失败数据源
   
2. 失败的数据源：
   - 记录失败原因（error_log）
   - 标记为"待重试"或"需用户介入"
   - 给出具体失败原因和解决建议
   
3. 重试策略：
   - Token失效类错误：引导用户重新授权，不自动重试（避免循环失败）
   - API限流类错误（GitHub）：记录限流恢复时间，自动在恢复后重试
   - 网络超时类错误：指数退避重试3次，仍失败则跳过
   
4. 告知用户：
   - "✅ 成功扫描：飞书、GitHub（获取了5个项目）"
   - "⚠️ 扫描失败：企业微信（连接超时）、钉钉（Token失效）"
   - "企业微信可重新连接：设置 → 连接企业微信"
```

**Code Snippet：**

```python
async def scan_all_connectors() -> ScanResult:
    connectors = [FeishuConnector(), DingTalkConnector(), GitHubConnector(), ...]
    results = {"success": [], "failed": [], "partial": []}
    
    for connector in connectors:
        status, data, error = await connector.scan()
        if status == "success":
            results["success"].append({"connector": connector.name, "data": data})
        elif status == "failed":
            results["failed"].append({"connector": connector.name, "error": error})
        else:  # partial
            results["partial"].append({"connector": connector.name, "data": data, "error": error})
    
    return results
```

---

#### B3. 简历解析失败 / 内容不足 【P1】

**异常描述：** 数字足迹聚合成功，但 LLM 在生成 `resume.json` 时出现解析错误（如字段缺失、内容不连贯、关键信息丢失），或生成的简历内容不足以支撑求职投递。

**细分场景：**

| 场景 | 表现 | 处理策略 |
|------|------|---------|
| **LLM解析完全失败** | LLM调用超时/返回非法JSON | 使用模板兜底 + 标记需人工补充 |
| **部分字段解析失败** | 某些项目经历缺少关键信息 | 保留已解析内容 + 标记缺失字段 |
| **简历内容不足** | 技能点 < 3，或项目数 < 1 | 触发 B1 冷启动引导流程 |
| **简历内容错误** | 用户发现AI生成的描述与实际不符 | 提供快速修正入口 |

**检测机制：**

```
1. LLM返回格式校验：
   - JSON Schema 校验（resume.json必须包含的字段）
   - 必填字段：name, skills, experience或projects 至少有一个非空
   - 可选字段缺失不触发异常

2. 内容质量阈值：
   - 技能点总数 < 3 → 触发"内容不足"告警
   - 项目经历数 = 0 → 触发"内容不足"告警
   - experience/projects 中 bullet points 总数 < 3 → 触发"内容不足"告警

3. 用户反馈识别：
   - 用户回复"简历内容不对" → 识别为内容错误
   - 用户拒绝确认简历 → 触发修正流程
```

**处理策略：**

```
场景1：LLM解析完全失败（兜底模板）：
1. 使用预设的基础简历模板填充必要字段
2. 所有"数字足迹生成"字段标记为 "[待补充]"
3. 生成告警通知用户："简历生成遇到问题，请手动补充以下字段：[缺失字段列表]"

场景2：部分字段解析失败（降级保留）：
1. 已解析的字段保留，进入简历确认流程
2. 缺失字段以"待补充"占位符标注
3. 通知用户："部分项目信息无法自动解析，请在确认前手动补充"

场景3：简历内容不足（引导补充）：
1. 不阻止流程，但给出明显提示："⚠️ 简历内容较少，建议补充以下信息"
2. 提供快捷补充入口（飞书卡片按钮）：
   - "补充项目经历" → 打开项目经历编辑页
   - "补充技能" → 打开技能列表编辑页
3. 不阻止用户先投递，但在职位匹配时降低匹配度阈值

场景4：内容错误（快速修正）：
1. 用户点击"修改"按钮，直接定位到错误字段
2. 支持"重新生成"按钮（基于相同数字足迹重新调用LLM）
3. 记录用户的修正内容，用于后续LLM调优反馈
```

---

### 13.4 C. 流程相关异常

#### C1. 用户中断求职（主动暂停） 【P1】

**异常描述：** 用户主动说"暂停求职"或"先不找了"，JobTracer 需要保留当前求职上下文，并在用户恢复时能够完整恢复状态。

**检测机制：**

```
1. 用户显式表达中断意图：
   - 用户消息包含："暂停求职"、"先不找了"、"停止"、"休息一下"等关键词
   - LLM意图分类 → intent = "pause_job_hunt"
   
2. 用户超过30天无任何求职操作：
   - 系统自动判定为"长期待机"状态
   - 触发轻量级关怀消息："你最近没有更新求职状态，有什么需要帮助的吗？"
```

**处理策略：**

```
未完成的投递流程保留机制：
1. 所有进行中的职位投递（已定制简历但未发送）保留7天
2. 用户恢复时，可选择"继续"或"重新开始"

恢复时的上下文恢复：
1. 用户说"继续求职"或"继续投递"
2. 系统读取 job-tracker.json 中状态为 "in_progress" 的记录
3. 询问用户："你之前有X个职位正在投递中，要继续吗？"
4. 显示断点位置，用户可选择性继续

状态保留期限：
| 状态 | 保留期限 | 说明 |
|------|---------|------|
| 进行中的投递（已定制简历） | 7天 | 超期后降级为"待重新搜索" |
| 已投递但待回复 | 90天 | 超期后自动标记为"无反馈" |
| 已保存的简历版本 | 永久 | 用户可随时恢复 |
| 数字足迹 | 永久 | 持续积累，不清除 |
```

**Code Snippet：**

```python
async def pause_job_hunt(user_id: str, reason: str = "user_initiated"):
    """保存当前求职状态到暂停快照"""
    current_state = await load_job_tracker_state(user_id)
    
    snapshot = {
        "paused_at": datetime.now().isoformat(),
        "reason": reason,
        "active_jobs": [j for j in current_state["jobs"] if j["status"] == "in_progress"],
        "resume_version": current_state["active_resume_version"],
        "search_keywords": current_state.get("search_keywords", []),
        "platform_status": current_state.get("platform_status", {})
    }
    
    await save_snapshot(user_id, snapshot)
    await update_job_tracker_status(user_id, "paused")
    
    return f"已保存求职快照，可随时说「继续求职」恢复。当前有{len(snapshot['active_jobs'])}个职位正在处理中。"
```

---

#### C2. 投递过程中断（BOSSH招呼发送失败） 【P1】

**异常描述：** 用户确认投递后，在执行 BOSS直聘发招呼（`opencli boss greet <uid>`）时失败，可能原因包括：用户已投递过该职位、IP被封禁、对方已下线、UID无效等。

**检测机制：**

```
1. opencli 命令返回非0退出码 → 投递失败
2. BOSS直聘返回业务错误码：
   - "HAS_APPLIED" → 用户已投递过该职位
   - "USER_BLOCKED" → 用户被对方拉黑
   - "JOB_CLOSED" → 职位已关闭
   - "INVALID_UID" → UID无效（职位已下架或链接失效）
3. 网络错误导致命令执行超时
```

**处理策略：**

```
重试策略：
- 第1次失败：等待5秒后自动重试
- 第2次失败：等待15秒后再次重试
- 第3次失败：不再重试，标记为"投递失败"

重试失败后，记录失败原因，提供手动补救入口：
- 用户可选择手动发送消息（复制定制招呼语到BOSS直聘App操作）
- 用户可切换其他平台进行投递（不受影响）

失败类型处理：
| 错误类型 | 处理策略 | 用户通知 |
|---------|---------|---------|
| HAS_APPLIED | 标记为"已投递"，不重复投递 | "该职位你已投递过，无需重复投递" |
| JOB_CLOSED | 从待投递列表移除，提示用户 | "该职位已关闭，已自动移除" |
| USER_BLOCKED | 记录并提示用户 | "对方已下线或无法发送消息，可尝试其他联系方式" |
| INVALID_UID | 标记为"UID无效"，跳过 | "该职位链接已失效（UID无效），已跳过" |
| 网络错误 | 指数退避重试3次 | "网络不稳定，投递失败，请稍后重试或手动投递" |

手动补救入口：
- 每次投递失败后，生成"手动补救"卡片
- 包含：目标职位名称 + BOSS直聘跳转链接 + 定制招呼语（可一键复制）
- 标题："无法自动投递，请手动完成最后一步"
```

**Code Snippet：**

```python
async def attempt_greet(platform: str, uid: str, message: str, max_retries: int = 3) -> dict:
    for attempt in range(max_retries):
        result = await call_greet_api(platform, uid, message)
        
        if result.success:
            return {"status": "success", "platform": platform, "uid": uid}
        
        error_code = result.error_code
        
        if error_code == "HAS_APPLIED":
            return {"status": "already_applied", "platform": platform, "uid": uid}
        elif error_code == "JOB_CLOSED":
            return {"status": "job_closed", "platform": platform, "uid": uid}
        elif error_code in ("INVALID_UID", "USER_BLOCKED"):
            return {"status": "invalid_target", "platform": platform, "uid": uid}
        else:
            if attempt < max_retries - 1:
                wait = 5 * (2 ** attempt)  # 5s, 10s
                await asyncio.sleep(wait)
    
    return {"status": "failed_after_retries", "platform": platform, "uid": uid}
```

---

#### C3. 定制简历生成失败 【P1】

**异常描述：** 针对特定JD定制简历时，HTML生成或PDF转换环节失败，导致无法完成定制投递。

**细分场景：**

| 失败阶段 | 表现 | 处理策略 |
|---------|------|---------|
| **HTML生成失败** | LLM无法生成有效HTML结构 | 降级到基础简历HTML模板 |
| **PDF转换失败** | wkhtmltopdf/Puppeteer报错 | 降级到HTML版本，用户手动打印 |
| **内容填充失败** | LLM无法理解JD或无法匹配合适的bullet point | 降级到基础简历（不做定制化调整） |

**检测机制：**

```
1. HTML生成：LLM返回非HTML内容，或HTML结构校验失败
2. PDF转换：wkhtmltopdf退出码非0，或生成文件大小为0
3. 错误日志捕获：所有转换步骤使用 try/except 包裹，记录具体错误类型
```

**处理策略：**

```
降级方案（按优先级）：
1. PDF生成失败 → 提供HTML版本下载：
   - "⚠️ PDF生成失败，已为你生成HTML版本"
   - 附上HTML文件路径 + "如何在浏览器中打印为PDF"的指引
   
2. HTML生成失败 → 降级到基础简历模板：
   - 系统内置一套基础HTML简历模板（不依赖LLM）
   - 仅替换姓名/联系方式/技能等基本信息
   - 定制化bullet point保留原基础简历版本

3. LLM调用超时/失败 → 完整降级到基础简历：
   - 使用用户上次确认的 base resume.json
   - 不做任何针对JD的定制化调整
   - 通知用户："定制化调整暂时不可用，已使用基础简历投递"
   
4. 彻底失败（所有方案均失败）：
   - 记录错误日志
   - 通知用户："简历生成遇到技术问题，请稍后重试或联系支持"
```

---

### 13.5 D. 系统相关异常

#### D1. 飞书Bot消息发送失败 【P1】

**异常描述：** JobTracer 通过飞书Bot向用户发送消息（卡片/文本）时失败，可能原因包括：Bot被禁言、用户已退群、网络问题、消息内容含有敏感词触发风控等。

**检测机制：**

```
1. 飞书API返回错误码：
   - 43004 → Bot被禁言（无权限发送消息到该群/用户）
   - 43006 → 用户已退群/无法触达
   - 40014 → tenant_access_token无效
   - 43001 → 不支持的消息类型
2. 网络错误：请求超时（>10s无响应）
3. 业务层：消息发送后无回执，且5分钟内用户无任何回应（疑似未送达）
```

**处理策略：**

```
重试机制：
- 第1次失败：等待3秒后重试
- 第2次失败：等待10秒后重试
- 第3次失败：停止重试，记录错误

降级到其他触达方式：
1. 飞书消息失败 → 检查是否有用户的邮件地址：
   - 如果有，发送邮件通知（包含飞书消息的完整内容）
   - 邮件标题："[JobTracer] 你有一条职位提醒（飞书消息发送失败，邮件补发）"
2. 邮件也无法送达 → 降级到下次交互时主动告知：
   - 不阻塞用户主动操作（用户来问时，主动推送之前失败的消息内容）
   - 在下次飞书消息成功发送时，附带："📌 之前有一条消息未能送达：[内容摘要]"

错误日志记录：
- 每次消息发送失败，记录到 error_log：
  - message_id, user_id, error_code, error_msg, retry_count, timestamp
- 用于后续分析和告警（如某个用户持续消息发送失败 → 检查Bot权限）
```

**Code Snippet：**

```python
async def send_feishu_message(user_id: str, content: dict, max_retries: int = 3) -> dict:
    for attempt in range(max_retries):
        try:
            result = await feishu_api.send_message(user_id, content)
            return {"status": "sent", "message_id": result.message_id}
        except FeishuAPIError as e:
            if e.code == 43004 or e.code == 43006:
                # 永久性失败，不重试，降级到其他渠道
                return await fallback_notify(user_id, content, reason="feishu_permission_denied")
            if attempt < max_retries - 1:
                await asyncio.sleep(3 * (2 ** attempt))
            else:
                await log_message_failure(user_id, content, e)
                return {"status": "failed", "error": str(e)}
```

---

#### D2. 定时任务执行失败 【P1】

**涉及任务：** 每日职位巡检（Daily Scan）、简历刷新通知、HR消息提醒

**异常描述：** cron 定时触发的自动任务执行失败，导致用户错过重要的职位发现或跟进提醒。

**检测机制：**

```
1. cron任务执行后，检查：
   - 任务是否在预设时间窗口内完成（< 30分钟）
   - 任务是否返回成功状态
   - 输出产物是否存在（job-tracker.json是否有更新）
   
2. 任务状态标记：
   - "success" → 本次任务完成
   - "failed" → 执行失败
   - "partial" → 部分完成（如仅部分平台成功）
```

**处理策略：**

```
每日巡检失败后的补执行：
1. 任务失败 → 立即记录失败原因和时间戳
2. 下次cron触发时，先检查上一次是否成功：
   - 如果上一次失败，先执行"补执行"，再执行本次巡检
   - 补执行优先级高于新任务
3. 补执行仍然失败 → 跳过，连续失败超过3天 → 升级告警

连续失败告警（超过3天失败通知用户）：
"""
⚠️ JobTracer 每日巡检连续3天执行失败

最近失败记录：
- 6月1日：网络超时
- 6月2日：BOSS直聘API返回错误
- 6月3日：Token失效

建议操作：
1. 检查网络连接是否正常
2. 重新授权各招聘平台
3. 或手动触发一次巡检："帮我巡检今天的职位"
"""
```

**Code Snippet：**

```python
async def daily_scan_with_recovery():
    last_run = await get_last_scan_record()
    
    if last_run.status == "failed":
        # 先补执行上一次失败的任务
        await log(f"检测到上次巡检失败，开始补执行...")
        await execute_daily_scan(reason="recovery", for_date=last_run.scheduled_date)
    
    # 执行本次巡检
    await execute_daily_scan(reason="scheduled", for_date=today())
    await update_last_scan_record(status="success")

async def execute_daily_scan(reason: str, for_date: str):
    try:
        results = await scan_all_platforms()
        await update_job_tracker(results)
        await notify_new_jobs(results)
        await update_last_scan_record(status="success", date=for_date)
    except Exception as e:
        await update_last_scan_record(status="failed", date=for_date, error=str(e))
        if is_consecutive_failure(days=3):
            await notify_user_scan_failure(escalation=True)
        raise
```

---

#### D3. 网络连接异常 【P1】

**涉及场景：** SSH隧道断开（代理不可用）、直连网络不稳定、跨境访问延迟高

**异常描述：** JobTracer 依赖网络访问各平台（BOSS直聘API、飞书API、GitHub等），网络异常会导致所有外部调用失败。

**检测机制：**

```
1. 全局网络探测（每次外部调用前）：
   - 对关键端点（飞书API、招聘平台API）执行轻量级健康检查
   - 探测超时阈值：5秒
   
2. SSH隧道状态监控：
   - 如果 JobTracer 配置为通过代理访问外网，监控SSH隧道连接
   - 隧道断开 → 自动触发降级到直连（如果直连可用）
   
3. 错误聚合：
   - 单次外部调用失败 → 记录
   - 连续3次外部调用失败（不同平台）→ 触发网络异常告警
```

**处理策略：**

```
SSH隧道断开（代理不可用）：
1. 立即切换到直连模式（如果直连可用）：
   - "⚠️ 代理连接已断开，已自动切换到直连模式"
2. 如果直连也不可用：
   - 延迟所有需要外网的操作，等待网络恢复
   - 不主动触发用户告警（避免网络抖动时的频繁通知）
   - 每5分钟探测一次网络连通性

降级决策树：
```
网络异常检测
    │
    ├─ SSH隧道断开？
    │   ├─ YES → 尝试直连
    │   │       ├─ 直连可用 → 继续执行，通知用户"已切换到直连模式"
    │   │       └─ 直连不可用 → 延迟操作，等待恢复
    │   └─ NO → 检查直连可用性
    │
    └─ 直连也不可用？
        ├─ YES → 延迟所有操作，每5分钟重试
        │         超过30分钟 → 通知用户"网络异常，请检查网络连接"
        └─ NO → 继续执行（使用直连）
```

**用户感知处理：**

```
1. 网络抖动（< 5分钟）：
   - 不主动通知，正常重试
   - 用户主动询问时告知："网络有点不稳定，已自动重试"

2. 长时间网络异常（> 30分钟）：
   - 飞书通知："⚠️ 网络连接异常，JobTracer部分功能暂时受限"
   - 告知用户预计恢复时间（如：网络恢复后自动继续）

3. 自动恢复后：
   - 补执行失败的任务（参考D2定时任务失败处理）
   - 告知用户："网络已恢复，正在补执行之前的任务..."
```

---

### 13.6 异常场景优先级汇总

| 编号 | 异常场景 | 优先级 | 核心原则 |
|------|---------|--------|---------|
| A1 | 平台登录失效/Token过期 | **P0** | 降级切换其他平台，用户重新授权 |
| B1 | 数字足迹为空（冷启动） | **P0** | 提供多入口引导，最小化启动路径 |
| A2 | 平台反爬/封禁IP/请求超时 | P1 | 指数退避重试，切换平台 |
| A3 | 搜索结果为空 | P1 | 关键词扩展，分场景处理 |
| B2 | 数字足迹扫描失败（部分） | P1 | 降级保留可用数据，引导用户修复失败源 |
| B3 | 简历解析失败/内容不足 | P1 | 模板兜底，标记缺失字段，引导补充 |
| C1 | 用户中断求职（主动暂停） | P1 | 快照保存，恢复时完整上下文 |
| C2 | 投递过程中断（Boss发招呼失败） | P1 | 重试+手动补救入口 |
| C3 | 定制简历生成失败 | P1 | HTML兜底，HTML版手动打印 |
| D1 | 飞书Bot消息发送失败 | P1 | 降级邮件补发，记录错误日志 |
| D2 | 定时任务执行失败 | P1 | 补执行机制，连续3天失败升级告警 |
| D3 | 网络连接异常 | P1 | SSH隧道断开自动切换直连，延迟重试 |

---

_本章由 ProductSolution Agent 补充，覆盖 Platform/Data/Flow/System 四个维度共12个异常场景_
