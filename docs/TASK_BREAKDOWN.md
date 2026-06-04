# JobTracer 开发任务卡

> 总计：15 个任务，22.5 人天
> Sprint 2: 8.0人天 | Phase 2: 8.5人天 | 新增: 3.0人天

---

## 🔴 关键路径 P0（阻塞所有后续）

| ID | 任务 | 模块 | 工期 | 依赖 |
|----|------|------|------|------|
| S2-1 | BOSS 发招呼自动化 | boss/greet.py | 1.5d | 需 BOSS Cookie |
| S2-2 | 定制简历 PDF 生成 | resume/pdf_generator.py | 1.5d | 需 BOSS Cookie |
| S2-3 | 飞书实时通知 | notifications/feishu_notify.py | 1.0d | 无 |

---

## Sprint 2（8.0人天）

### P0
- [S2-1] BOSS 发招呼自动化 | boss/greet.py | 1.5d
- [S2-2] 定制简历 PDF 生成 | resume/pdf_generator.py | 1.5d
- [S2-3] 飞书实时通知 | notifications/feishu_notify.py | 1.0d

### P1
- [S2-4] 并发扫描优化 | scanner/footprint_scanner.py | 0.5d
- [S2-5] 异常处理与重试 | utils/retry.py | 1.0d

### P2
- [S2-6] SQLite 数据库迁移 | db/migrate.py | 2.0d
- [S2-7] 多平台搜索接入（51job/牛客）| platforms/ | 3.0d
- [S2-8] 增量扫描 | scanner/incremental.py | 0.5d

---

## Phase 2（8.5人天）

### P1
- [P2-1] HR 意图分类引擎 | hr/intent_classifier.py | 2.0d
- [P2-2] HR 回复建议生成 | hr/reply_generator.py | 1.5d
- [P2-3] 面题库生成器 | interview/question_bank.py | 2.0d

### P2
- [P2-4] STAR 法则指导 | interview/star_coach.py | 1.0d
- [P2-5] 模拟面试 | interview/simulator.py | 2.0d

---

## 新增任务（3.0人天）

- [NEW-1] AI 智能体平台扫描 | scanner/agent_scanner.py | 2.0d
- [NEW-2] OpenClaw 历史会话扫描 | scanner/agent_scanner.py | 1.0d

---

## 新增任务（内容理解级聚类）

> Phase 2.5 — 深度聚类升级

| ID | 任务 | 模块 | 工期 | 依赖 |
|----|------|------|------|------|
| [NEW-3] | 文件内容复制到项目目录 | clustering/engine.py | 1.0d | 现有聚类 |
| [NEW-4] | 读取文件内容生成摘要 | clustering/summarizer.py | 2.0d | NEW-3 |
| [NEW-5] | 合并相关项目（版本/模块聚合） | clustering/merger.py | 1.5d | NEW-4 |
| [NEW-6] | 更新 projects_index.json 完整字段 | clustering/engine.py | 0.5d | NEW-4 |


### NEW-3 ~ NEW-6 详细说明

**[NEW-3] 文件内容复制到项目目录**
- 问题：当前聚类只分组路径，`docs/` 和 `code_snippets/` 目录为空
- 解决：聚类后真正复制文件内容到 `projects/{id}/docs/`、`projects/{id}/code_snippets/`
- 验收：每个项目文件夹包含实际文件内容（非空）

**[NEW-4] 读取文件内容生成摘要**
- 问题：`_index.md` 只有路径列表，没有内容理解
- 解决：读取 .md/.txt/.py 等文件，用 LLM 生成摘要
- 摘要字段：`background`（背景）、`deliverables`（产出）、`results`（成果）、`solutions`（方案）
- 验收：每个项目有完整的4段式摘要

**[NEW-5] 合并相关项目**
- 问题：同一项目被拆散（如 JobTracer 分散在 32 个文件夹）
- 解决：基于内容相似度 + 路径关键词，合并相关项目
- 标准：内容相似度 > 0.7 或 路径包含相同顶级目录
- 验收：542 个碎片项目合并为 50~100 个有意义项目

**[NEW-6] 更新 projects_index.json 完整字段**
- 问题：projects_index.json 只有浅层信息，无摘要
- 解决：写入完整字段（background/deliverables/results/solutions/tags/merged_from）
- 验收：projects_index.json 每个项目包含全部结构化字段

---

## 并行开发分组

### Group A（可立即并行启动）
- AI 智能体平台扫描（NEW-1）
- OpenClaw 历史会话扫描（NEW-2）
- 并发扫描优化（S2-4）


### Group B（依赖 BOSS Cookie）
- BOSS 发招呼自动化（S2-1）
- 定制简历 PDF 生成（S2-2）


### Group C（可独立开发）
- 飞书实时通知（S2-3）
- 异常处理与重试（S2-5）
- SQLite 数据库迁移（S2-6）
- 多平台搜索接入（S2-7）
- 增量扫描（S2-8）

### Group D（Phase 2，并行）
- HR 意图分类引擎（P2-1）
- HR 回复建议生成（P2-2）
- 面题库生成器（P2-3）
- STAR 法则指导（P2-4）
- 模拟面试（P2-5）

### Group E（Phase 2.5 — 内容理解级聚类，按序）
- 文件内容复制（NEW-3）→ 读取内容生成摘要（NEW-4）→ 合并项目（NEW-5）→ 更新索引（NEW-6）