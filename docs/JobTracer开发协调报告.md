# JobTracer MVP Sprint 1 开发协调报告

> **报告日期：** 2026-06-03  
> **基于文档：** JobTracer技术方案 v1.0.3（§7 开发计划）  
> **协调者：** ProjectManager Agent  

---

## 一、Sprint 1 概览

| 指标 | 数值 |
|------|------|
| 总任务数 | 14 个 |
| 总人天 | **11.5 人天** |
| 总任务（26个全版本）| Sprint 1 (14) + Sprint 2 (10) + Sprint 3 (2) = **26 任务 / 25.0 人天** |
| P0 任务 | 11 个 |
| P1 任务 | 3 个（1.5, 1.14） |
| P2 任务 | 0 个 |

**Sprint 1 阶段划分：**

| 阶段 | 时间 | 任务 | 人天 |
|------|------|------|------|
| Week 1：基础框架 + 数字足迹扫描 | Day 1-5 | 1.1~1.8 | 6.5d |
| Week 2：简历生成 + BOSS搜索 | Day 6-10 | 1.9~1.14 | 5.0d |

---

## 二、关键路径分析

### 2.1 关键路径识别

关键路径决定最短完成时间。沿任务依赖链，串行序列如下：

```
1.1 (0.5d) → 1.3 (1.0d) → 1.6 (1.0d) → 1.7 (1.5d) → 1.9 (1.5d) = 5.5d
                                          ↕ (并行)
                               1.8 (1.0d, 独立分支)
```

**完整关键路径序列（按串行估算）：**

| 步骤 | 任务 | 估算 | 累计 |
|------|------|------|------|
| 1 | 1.1 项目脚手架 | 0.5d | 0.5d |
| 2 | 1.3 本地文件扫描器 | 1.0d | 1.5d |
| 3 | 1.6 扫描器编排器 | 1.0d | 2.5d |
| 4 | 1.7 项目聚类引擎 | 1.5d | 4.0d |
| 5 | 1.2 存储目录初始化* | 0.5d | 4.5d |
| 6 | 1.8 数据存储层 | 1.0d | 5.5d |
| 7 | 1.9 简历生成器 | 1.5d | **7.0d** |

> \*1.2 与 1.1 无依赖关系，但 1.8 依赖 1.2，故 1.2 必须在 1.8 之前完成。

**📌 关键路径长度（串行）：7.0 人天**

### 2.2 并发优化空间

以下任务可**并行执行**（无相互依赖）：

| 并行组 | 任务 | 各自时长 | 可并行？ |
|--------|------|---------|---------|
| A | 1.1 项目脚手架、1.2 存储目录初始化 | 0.5d + 0.5d | ✅ 立即并行 |
| B | 1.3 本地文件扫描器、1.4 OpenClaw记忆扫描器 | 1.0d + 0.5d | ✅ 同日启动 |
| C | 1.10 HTML简历模板、1.11 BOSS搜索模块、1.12 JD缓存机制、1.14 飞书通知卡片 | 0.5d + 1.0d + 0.5d + 0.5d | ✅ 同日并行 |

### 2.3 最短完成时间（并发估算）

假设 **2人并行**，关键路径压缩：

| Day | 负责人A | 负责人B |
|-----|--------|--------|
| Day 1 | 1.1 项目脚手架 | 1.2 存储目录初始化 |
| Day 2 | 1.3 本地文件扫描器 | 1.4 OpenClaw记忆扫描器 |
| Day 3 | 1.5 GitHub扫描器(P1) | 1.6 扫描器编排器 |
| Day 4 | 1.8 数据存储层 | 1.7 项目聚类引擎 |
| Day 5 | 1.9 简历生成器 | 1.10 HTML简历模板 |
| Day 6-7 | 1.11 BOSS搜索模块 | 1.13 JD匹配评分 |
| Day 8 | 1.12 JD缓存机制 | 1.14 飞书通知卡片 |

**📌 Sprint 1 最短完成时间（2人并发）：~8 个工作日**

---

## 三、依赖矩阵（简化版）

### 3.1 解锁关系表

| 完成后解锁的任务 | 依赖条件 | 说明 |
|----------------|---------|------|
| 1.3 本地文件扫描器 | 1.1 ✅ | Phase B |
| 1.4 OpenClaw记忆扫描器 | 1.1 ✅ | Phase B |
| 1.5 GitHub扫描器 | 1.1 | Phase B |
| **1.6 扫描器编排器** | **1.3 + 1.4** | Phase C，核心编排器 |
| 1.7 项目聚类引擎 | 1.6 + 1.5 | Phase D，需两个都完成 |
| **1.8 数据存储层** | **1.2** | Phase E，独立分支 |
| **1.9 简历生成器** | **1.7 + 1.8** | Phase F，关键路径 |
| 1.10 HTML简历模板 | 1.9 | Phase G |
| 1.11 BOSS搜索模块 | 1.9 + 1.13 | Phase G |
| 1.12 JD缓存机制 | 1.11 | Phase G |
| 1.13 JD匹配评分 | 1.9 + 1.11 | Phase G |
| 1.14 飞书通知卡片 | 1.9 + 1.13 | Phase G |

### 3.2 依赖关系图（ASCII）

```
[1.1]────┬──→ [1.3] ──────────────┐
         ├──→ [1.4] ──────────────┤
         └──→ [1.5] ──────────────┼──→ [1.6] ──→ [1.7] ──┐
[1.2]─────────────→ [1.8] ──────────────────────────────┼──→ [1.9] ──┐
                                                                          ↓
                                                               [1.10][1.11]
                                                               [1.12][1.14]
                                                                    [1.13]
```

---

## 四、立即可启动任务（Phase A）

根据技术方案 §7.1，以下 **2 个任务无任何依赖，可立即启动**：

### 任务 1.1：项目脚手架

| 字段 | 内容 |
|------|------|
| **估算** | 0.5 人天 |
| **优先级** | P0 |
| **验收标准** | 项目可 import；pip install -r requirements.txt 成功 |
| **技术依据** | 技术方案 §6.4 项目结构；§6.1 核心依赖（Python 3.11+ / httpx / PyMuPDF / openpyxl / weasyprint / aiofiles）|

**建议实现内容：**
```
jobtracer/
  __init__.py
  scanner/
    __init__.py
    footprint_scanner.py
    local_scanner.py
    feishu_scanner.py
    github_scanner.py
    openclaw_scanner.py
  clustering/
    __init__.py
    engine.py
  resume/
    __init__.py
    generator.py
    customizer.py
  boss/
    __init__.py
    search.py
    greet.py
  matching/
    __init__.py
    scorer.py
  hr/
    __init__.py
    engine.py
  interview/
    __init__.py
    prep.py
  storage/
    __init__.py
    manager.py
  utils/
    __init__.py
    file_utils.py
    html_utils.py
  config.py
  main.py
  requirements.txt
```

### 任务 1.2：存储目录初始化

| 字段 | 内容 |
|------|------|
| **估算** | 0.5 人天 |
| **优先级** | P0 |
| **验收标准** | ~/.jobtracer/ 目录存在；state.json / preferences.json 格式正确 |
| **技术依据** | 技术方案 §4.1 目录结构；§4.2 JSON文件格式（state.json / preferences.json 字段定义） |

**目录结构：**
```
~/.jobtracer/
├── memory/
│   ├── state.json
│   └── preferences.json
├── footprint/
│   ├── summary.md
│   └── projects/
├── jobs/
│   ├── job-tracker.json
│   └── jd_cache/
├── customized_resumes/
├── interview_prep/
├── cookies/
├── logs/
└── reports/
```

---

## 五、开发建议

### 5.1 Phase A 任务分配建议

| 建议分工 | 负责人 | 任务 |
|---------|--------|------|
| **方案A（单人顺序）** | 开发者 | 先 1.1（0.5d），再做 1.2（0.5d） |
| **方案B（单人并行片段）** | 开发者 | 上午 1.1，下午 1.2，同一天完成 |
| **方案C（双人并行）** | Dev A | 1.1 项目脚手架 |
|  | Dev B | 1.2 存储目录初始化 |

**推荐方案C（双人并行）**，理由：
- 两个任务均为 P0，且互不依赖
- 完成后可立即解锁 4 个 Phase B 任务（1.3/1.4/1.5/1.8）
- 效率最高

### 5.2 技术栈建议

| 类别 | 选型 | 说明 |
|------|------|------|
| 语言 | Python 3.11+ | 技术方案明确 |
| 异步HTTP | httpx 0.27+ | GitHub API 调用 |
| PDF读取 | PyMuPDF (fitz) | 简历上传解析 |
| Excel读取 | openpyxl 3.1+ | 本地文件扫描 |
| PDF生成 | WeasyPrint 60+（备选 Playwright） | 定制简历输出 |
| 异步文件IO | aiofiles 24+ | 并行扫描优化 |
| LLM调用 | OpenAI GPT-4 / Claude 3.5 | 简历生成/聚类 |

### 5.3 潜在风险点

| 风险 | 可能性 | 影响 | 应对 |
|------|--------|------|------|
| BOSS Cookie 过期 | 高 | 中 | 提示用户重新授权（技术方案 §3.2 / §8.1） |
| PDF中文字体缺失 | 中 | 中 | WeasyPrint 中文字体配置备选 Playwright（§6.3） |
| LLM输出质量不稳定 | 中 | 高 | 用户确认节点 + Prompt优化（§8.3） |
| 数字足迹为空（冷启动）| 高 | 低 | B1 路径：简历上传→LLM解析→resume.json（§2.2 B1） |
| GitHub API 限流 | 中 | 低 | 降级为只读 README（技术方案 §2.2） |

### 5.4 并发优化要点

根据技术方案 §2.2 扫描器设计，关键并发设计点：

```python
# scanner/footprint_scanner.py — 并行扫描架构
async def scan_all(self, timeout_seconds: int = 300) -> dict:
    tasks = []
    if self.config.get('local_enabled'):
        tasks.append(self._scan_local())     # ~60s 超时
    if self.config.get('feishu_enabled'):
        tasks.append(self._scan_feishu())
    if self.config.get('github_enabled'):
        tasks.append(self._scan_github())
    if self.config.get('openclaw_enabled'):
        tasks.append(self._scan_openclaw())  # 快速，通常 <5s
    
    # asyncio.gather 并行执行，return_exceptions 防止单点失败
    results = await asyncio.gather(*tasks, return_exceptions=True)
```

**扫描超时控制（技术方案 §2.2）：**
- 本地文件扫描：60s 超时
- 全局扫描（含所有数据源）：300s 超时
- 单平台失败不影响整体（return_exceptions 保护）

---

## 六、Sprint 1 后续关键里程碑

| 里程碑 | 预计时间 | 关键任务 | 解锁内容 |
|--------|---------|---------|---------|
| M1：Phase B 完成 | Day 2 | 1.3/1.4/1.5 完成 | 解锁 1.6 扫描器编排器 |
| M2：数字足迹结构化 | Day 5 | 1.6+1.7 完成 | 1.9 简历生成就绪 |
| M3：简历生成就绪 | Day 6-7 | 1.8+1.9 完成 | Phase G 全部解锁 |
| M4：BOSS 搜索完成 | Day 8-9 | 1.10~1.14 完成 | Sprint 1 交付 |

---

## 七、总结

| 指标 | 数值 |
|------|------|
| **关键路径长度（串行）** | **7.0 人天** |
| **Sprint 1 最短完成时间（2人并发）** | **~8 个工作日** |
| **建议优先启动任务** | **1.1 项目脚手架 + 1.2 存储目录初始化** |
| **立即可并行任务数** | 1.1 + 1.2 可并行（2个任务/1.0人天） |

**立即行动项：**
1. ✅ 启动 1.1（项目脚手架）— 立即可做
2. ✅ 启动 1.2（存储目录初始化）— 立即可做
3. 🔲 准备 1.3/1.4 开发环境（等 1.1 完成后）
4. 🔲 确认 GitHub Token 配置（为 1.5 准备）

---

*本报告由 ProjectManager Agent 基于 JobTracer技术方案 v1.0.3 §7 自动生成*