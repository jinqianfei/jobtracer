# JobTracer PRD 技术复审报告（开发视角）

> **评审人：** 开发工程师（高级）
> **评审时间：** 2026-06-02
> **评审文件：** `/Users/jinqianfei/openclaw-workspaces/product-solution/JobTracer PRD.md`
> **评审版本：** v1.0.0

---

## 一、上次评审问题修复验证

| 序号 | 问题 | 修复状态 | 验证结果 |
|------|------|----------|----------|
| 1 | BOSS直聘风险（自动化发消息违规） | ✅ 已修复 | PRD 中已明确降级为 `opencli boss greet` + 一键复制模式，并标注了平台政策风险 |
| 2 | 数据路径不统一 | ✅ 已修复 | 已统一到 `~/.jobtracer/` 目录结构，4.1节完整定义了目录树 |
| 3 | SQLite schema 缺失 | ✅ 已修复 | 4.2节已补充完整的 SQLite Schema（含 jobs/hr_conversations/interview_prep 三张表及索引） |
| 4 | 增量同步策略未说明 | ✅ 已修复 | 3.1节性能要求中明确"增量扫描优先"，5.1节依赖项中 ProjectTrace 已标注为核心依赖 |

**结论：** 上次评审提出的 4 项技术问题均已在 PRD 中修复，修复方案合理。

---

## 二、数据存储方案评审

### 2.1 存储策略合理性

| 数据类型 | 存储方式 | 合理性评估 |
|----------|----------|------------|
| 核心配置（resume.json/state.json） | JSON文件 | ✅ 合理：小数据量、频繁读写、需人工可读 |
| 职位列表（大量） | SQLite | ✅ 合理：数据量大、需要高效查询和索引 |
| HR沟通记录 | SQLite | ✅ 合理：按 job_id 查询场景多 |
| 面题库 | JSON文件 | ✅ 合理：按需读取、单次使用 |
| 文件夹结构 | 本地文件 | ✅ 合理：projects/ 按项目组织 |

**评估：** JSON + SQLite 的混合策略符合场景，Phase 1 用 JSON 文件、Phase 2 迁移 SQLite 的分阶段设计合理。

### 2.2 路径统一性 ✅

`~/.jobtracer/` 目录结构清晰，包含：
- `memory/`：核心状态数据
- `footprint/`：数字足迹
- `jobs/`：职位数据
- `resumes/`：简历版本
- `customized_resumes/`：定制简历
- `interview_prep/`：面题库
- `cookies/`：平台登录态
- `reports/`：复盘报告
- `logs/`：同步日志

### 2.3 SQLite Schema 评审

```sql
-- jobs 表
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
```

**发现的问题：**

1. **缺失字段**：`jobs` 表缺少 `url` 字段（职位链接），这在 Step 4 中需要"一键打开"职位页面
2. **jd_summary 类型**：存储为 TEXT 但实际是摘要文本，TEXT 合理，但应明确最大长度
3. **related_projects 存储为 TEXT**：存储 JSON 数组字符串，查询时不方便，建议 Phase 2 考虑单独建关联表

**建议补充：**
```sql
ALTER TABLE jobs ADD COLUMN url TEXT;
ALTER TABLE jobs ADD COLUMN recruiter_uid TEXT;  -- 用于 BOSS 直聘发招呼
```

### 2.4 数据字典完整性

| 数据文件 | 字段定义完整度 | 问题 |
|----------|---------------|------|
| resume.json | ✅ 完整 | 无问题 |
| job-tracker.json | ✅ 完整 | 建议补充 `url` 字段说明 |
| hr_conversations.json | ✅ 完整 | 无问题 |
| interview_prep.json | ✅ 完整 | 无问题 |

---

## 三、技术可行性评审

### 3.1 依赖项分析

| 依赖项 | 风险等级 | 技术可行性 | 评估 |
|--------|----------|-----------|------|
| 飞书 MCP | 中 | ✅ 可行 | 有成熟 SDK，但需考虑服务可用性 |
| 钉钉 dws CLI | 中 | ✅ 可行 | 命令行工具稳定 |
| BOSS 直聘 | 高 | ⚠️ 部分受限 | `opencli boss greet` 受限于 opencli 的 BOSS 功能是否已实现 |
| GitHub API | 低 | ✅ 可行 | API 稳定，有免费额度 |
| ProjectTrace | 中 | ✅ 可行 | 核心组件 |
| OpenAI API | 中 | ✅ 可行 | 需考虑成本和降级 |
| 前程无忧/牛客 | 中 | ⚠️ 需确认 | 平台是否提供公开 API？若无，需用 Playwright 爬取 |

**关键风险：**

1. **BOSS 直聘 `opencli boss greet` 命令**：PRD 依赖 `opencli` 工具，但未说明该工具的 BOSS 直聘功能是否已实现。建议在实现计划中明确标注此项为**前置依赖**。

2. **前程无忧/牛客 平台 API**：PRD 未明确这两个平台是否有公开 API。如果无 API，需使用 Playwright 模拟浏览器操作，实现复杂度大幅提升。

### 3.2 降级机制评审 ✅

PRD 在各 Step 中均设计了降级机制，整体覆盖较好：

| Step | 降级机制 | 完整性 |
|------|----------|--------|
| Step 1 | 平台认证失败跳过 + 超时返回已扫描结果 | ✅ 完整 |
| Step 2 | 量化成果缺失时生成不含数据的简历 | ✅ 完整 |
| Step 3 | 平台搜索失败跳过 + 无匹配时自动扩展关键词 | ✅ 完整 |
| Step 4 | BOSS 发招呼被限 → 降级为手动复制 | ✅ 完整 |
| Step 5 | HR 意图不明确时生成通用回复 | ✅ 完整 |

**建议补充：**
- Step 4 中 PDF 生成失败时降级为 HTML，但 HTML 也失败时未说明。建议增加"降级为纯文本简历"兜底方案。

### 3.3 性能指标评审

| 指标 | 要求 | 技术可行性 |
|------|------|-----------|
| 数字足迹扫描 | 单平台 < 60s，总计 < 5min | ⚠️ 依赖平台响应速度，需实际压测验证 |
| 简历生成 | < 30s | ✅ LLM 调用时间可控 |
| 岗位搜索 | < 120s | ⚠️ 多平台并行搜索，需确认平台并发限制 |
| JD 匹配评分 | < 5s/条 | ✅ 合理 |
| 定制简历 PDF | < 15s | ✅ HTML 渲染 + PDF 生成可控 |
| 响应时间（日常交互） | < 5s | ✅ 合理 |

---

## 四、实现复杂度与风险评估

### 4.1 MVP (P0) 实现复杂度

| Step | 功能 | 复杂度 | 风险点 |
|------|------|--------|--------|
| Step 1 | 数字足迹聚合 | 中 | ProjectTrace 聚类准确性、项目文档解析能力 |
| Step 2 | 基础简历生成 | 低 | LLM prompt 调优、多版本生成 |
| Step 3 | 多平台岗位搜索 | 高 | 各平台接口差异、无 API 时需 Playwright |
| Step 3 | JD 匹配度评分 | 低 | 关键词匹配算法已成熟 |
| Step 4 | 定制简历 PDF | 中 | HTML 模板渲染、PDF 生成库选型 |
| Step 4 | BOSS 发招呼 | 高 | **依赖 opencli boss greet 功能是否已实现** |
| Step 4 | 飞书 Bitable 职位追踪 | 中 | 飞书 API 调用、Bitable 数据模型设计 |

**最大风险点：Step 3 多平台搜索 + Step 4 BOSS 发招呼**

这两项是 MVP 中技术风险最高的，建议在 Sprint 1 中优先实现和验证。

### 4.2 Phase 2 (P1) 功能技术债务

| 功能 | 技术债务说明 |
|------|-------------|
| HR 沟通辅助（Step 5） | 意图分类需要训练数据或大量标注，当前用 LLM 做 zero-shot 分类，效果待验证 |
| 模拟面试 | 需要维护题库 + 反馈算法，实现复杂度中等 |
| 面试准备面题库 | 依赖 JD 解析质量，需处理 JD 内容不完整的边界情况 |

### 4.3 数据迁移风险

PRD 提到 Phase 1 用 JSON，Phase 2 迁移 SQLite。**潜在风险：**

1. **数据结构变化**：JSON 到 SQLite 迁移时，数据结构可能需要转换（如 `projects[].metrics` 的嵌套结构）
2. **迁移脚本**：需提前设计迁移策略，避免数据丢失
3. **建议**：在 4.2 节补充"Phase 1→2 数据迁移方案"章节

---

## 五、其他技术问题

### 5.1 安全设计评审 ✅

| 安全需求 | 设计完整性 | 评估 |
|----------|-----------|------|
| 隐私本地存储 | ✅ | 简历和求职数据优先本地存储 |
| 数据加密 | ✅ | SQLite 索引文件设置 `chmod 600` |
| 敏感信息过滤 | ✅ | 自动跳过银行卡号、密码、API Key 等 |
| 平台授权 | ✅ | 连接任何平台前必须获得用户明确授权 |
| 内容来源透明 | ✅ | 简历中标注项目成果来源 |

**建议补充：**
- cookies/ 目录下的平台登录态文件也需要设置 `chmod 600`
- 建议增加"退出登录时自动清除敏感数据"机制

### 5.2 兼容性评审 ✅

| 项目 | 要求 | 评估 |
|------|------|------|
| 飞书版本 | 桌面 + 移动 | ✅ 合理 |
| 操作系统 | macOS/Windows/Linux | ✅ 合理 |
| 浏览器 | Chrome/Safari/Edge | ✅ 合理 |
| Python | 3.11+ | ✅ 合理 |
| Node.js | 18+ | ✅ 合理（job-hunter CLI） |

### 5.3 数据一致性保障

PRD 提到"核心数据文件需事务性写入"，但**未说明具体实现方案**。建议：

1. 使用 `sqlite3` 的事务机制（而非 JSON 文件）保证原子性写入
2. 或使用 `filelock` 库对 JSON 文件加锁
3. 建议在实现文档中明确数据一致性保障方案

### 5.4 日志与可追溯性

PRD 中 `logs/` 目录已规划，但**未定义日志规范**：
- 日志级别（DEBUG/INFO/WARNING/ERROR）
- 日志格式（JSON 还是文本）
- 日志轮转策略（按大小/按时间）
- 敏感信息脱敏规则

**建议补充：** 在实现文档中增加日志规范章节。

---

## 六、总结与建议

### 6.1 通过项 ✅

1. 上次评审的 4 项技术问题均已修复
2. 数据存储方案整体合理，路径统一
3. SQLite Schema 设计基本完整，索引合理
4. 降级机制覆盖主要异常场景
5. 安全需求设计完整

### 6.2 需补充项 ⚠️

| 序号 | 问题 | 严重程度 | 建议 |
|------|------|----------|------|
| 1 | `jobs` 表缺少 `url` 和 `recruiter_uid` 字段 | 中 | 补充字段定义 |
| 2 | BOSS 直聘 `opencli boss greet` 是否已实现未确认 | 高 | 明确为前置依赖，Sprint 1 验证 |
| 3 | 前程无忧/牛客平台是否有公开 API 未明确 | 高 | 确认 API 情况，否则改用 Playwright 方案 |
| 4 | Phase 1→2 数据迁移方案缺失 | 中 | 补充迁移策略章节 |
| 5 | PDF 生成完全失败的兜底方案未说明 | 低 | 补充纯文本简历兜底方案 |
| 6 | 日志规范缺失 | 低 | 补充日志级别/格式/轮转规范 |
| 7 | cookies/ 目录文件权限未明确 | 低 | 明确设置 `chmod 600` |

### 6.3 技术可行性结论

**总体评估：技术可行性较高，但存在 2 个高风险项需在 Sprint 1 验证。**

- ✅ 数据存储方案合理，路径统一
- ✅ 降级机制完善
- ✅ 安全设计完整
- ⚠️ BOSS 直聘功能依赖 opencli 实现状态
- ⚠️ 多平台搜索依赖各平台 API 可用性

### 6.4 建议的开发优先级

| 优先级 | 任务 | 理由 |
|--------|------|------|
| P0 | 验证 opencli boss greet 功能是否可用 | 高风险前置依赖 |
| P0 | 确认前程无忧/牛客 API 情况 | 影响 Step 3 实现方案 |
| P0 | 搭建数据存储层（JSON + SQLite） | 基础架构 |
| P1 | 实现 Step 1 数字足迹聚合 | MVP 核心功能 |
| P1 | 实现 Step 2 简历生成 | MVP 核心功能 |
| P2 | 实现 Step 3 岗位搜索（多平台） | MVP 核心功能，分平台迭代 |
| P2 | 实现 Step 4 定制简历 PDF | MVP 核心功能 |

---

## 七、评审结论

| 维度 | 结论 |
|------|------|
| 上次问题修复 | ✅ 4项问题均已修复 |
| 数据存储方案 | ✅ 路径统一，策略合理，Schema 基本完整 |
| 技术可行性 | ⚠️ 2个高风险项需Sprint 1验证 |
| 实现复杂度 | 中（多平台整合是主要复杂度来源） |
| 安全设计 | ✅ 完整 |
| **综合结论** | **条件通过（待验证高风险项后正式通过）** |

---

**下一步行动：**
1. 确认 `opencli boss greet` 功能状态
2. 确认前程无忧/牛客 API 可用性
3. 补充缺失字段到 SQLite Schema
4. 开始 Sprint 1 技术验证