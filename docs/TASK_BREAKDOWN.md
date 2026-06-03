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