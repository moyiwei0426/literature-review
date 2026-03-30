# ARIS-Lit 工作日志

## 2026-03-24

### 23:58 — C 版本稳定化（方向 A）记录补齐 + run 级日志落盘

**目标：**
把最近这轮 `run_local_review.py` 稳定化推进正式记录下来，并补齐“每次运行有落盘日志、每次关键修改有工作日志同步”的最小交接能力。

**本次确认的项目位置：**
- 当前阶段已从早期 MVP/骨架转入 **C 版本稳定化**
- 标准入口收敛到：`scripts/run_local_review.py`
- 当前默认稳定路径不是全 live，而是：
  - live extraction
  - live writing 先尝试
  - validator fail 后自动切 rule-based writing fallback
  - 采用 validation 更好的那一版产物

**本次补齐的记录动作（完整执行）：**
1. 更新 `progress/STATUS.md`
   - 从 2026-03-19 的旧阶段状态刷新到当前 C 稳定化状态
   - 明确默认稳定策略、风险、查看顺序、下一步动作

2. 更新 `progress/WORKLOG.md`
   - 追加本条日志，补齐最近这轮方向 A 收口记录

3. 更新 `docs/LOGGING.md`
   - 明确当前真实落地的日志机制：
     - `run_local_review.py` 每次运行输出 `run.log`
     - `summary.json` 记录 `run_log`、`extraction_strategy`、`writing_strategy`、`validation`
   - 明确推荐排查顺序：`summary.json` → `run.log` → `validation_report.json`

4. 更新 `scripts/run_local_review.py`
   - 为每次 run 在输出目录落盘 `run.log`
   - 在 `summary.json` / result 中显式记录：
     - `run_log`
     - `extraction_strategy`
     - `writing_strategy`
   - 让每次运行的策略与结果更可审计

**本轮关键代码修改（2026-03-24 已完成）：**
- `services/llm/adapter.py`
  - OAuth client 改懒加载
  - pytest / 回归环境默认可强制 stub
  - 避免 smoke / 本地回归误走真实 LLM

- `services/writing/section_writer.py`
  - conclusion 改为显式输出 paragraph move metadata
  - validator 可正确识别 `synthesis/comparison/gap`

- `scripts/run_local_review.py`
  - 新增 live writing fail → rule-based writing fallback
  - 新增 `writing_strategy` / `extraction_strategy` 结果字段
  - 新增 `run.log` 落盘

- `tests/test_local_review_smoke.py`
  - 补齐 `writing_strategy` / `extraction_strategy` 断言
  - 新增 fallback 行为测试，防止默认稳定策略退化

- `plans/C_VERSION_STABILIZATION.md`
  - 写入默认稳定策略（方向 A）
  - 写明 `summary.json` 中需要优先查看的字段

**本轮验证结果：**
### AAP 子集（真实 extraction + fallback writing）
- `data/generated/aap_live_1paper_20260324_fallback` → ✅ pass
- `data/generated/aap_live_2paper_20260324_fallback` → ✅ pass
- `data/generated/aap_live_4paper_20260324_fallback` → ✅ pass

### 结论
- live extraction：已证明可用
- live writing：仍不稳定，不能单独作为当前稳定交付路径
- fallback writing：已在 1 / 2 / 4 paper 规模上证明有效
- 当前最稳交付路径：**live extraction + validated fallback writing**

**本次测试：**
- `python3 -m pytest tests/test_local_review_smoke.py -q`
- 结果：`3 passed`

**当前明确边界：**
- 运行级记录：现在已具备 `summary.json + run.log + validation_report.json`
- 修改级记录：本次已手动同步进 `WORKLOG.md` / `STATUS.md`
- 仍未完成：自动化 changelog / git commit-based 追踪 / API/worker 统一文件日志

**下一步：**
1. 先向你做方向 A 的完整汇报
2. 你确认后，再进入方向 B：专修 live writing 本体

## 2026-03-19

### 19:44 — End-to-End 一键 Review 打通

**目标：** 统一检索入口，做一条 `run-review` 命令覆盖全链路。

**新增文件：**
- `scripts/run_review.py`：end-to-end 管线，支持：
  - Retrieval（OpenAlex + arXiv，可选来源）
  - Dedup（PaperMaster 去重）
  - PDF Fetch（arxiv 直连 PDF）
  - Parse（PyMuPDF fallback）
  - Extract（MiniMax-M2 LLM profile 抽取）
  - Analysis（matrix + coverage + contradictions）
  - Gaps（candidate + verify + score）
  - Writing（outline + sections + citation grounding v3）
  - LaTeX 合成（可选编译）
  - JSON 报告生成

**新增 CLI 命令：**
- `python3 scripts/cli.py run-review --query "xxx" --max 5 --max-pdfs 3`

**验证结果（真实论文）：**
```
✅ retrieval  ✅ dedup  ✅ fetch  ✅ extract
✅ analysis（4 claims, 6 gaps）
✅ writing（6 sections, tex=3644 chars）
```

**本日其他完成项：**
- Writing prompts 强化（section_system.txt / outline_system.txt）
- rule-based fallback 数据驱动升级
- citation_grounder v3（topic + claim-type + mention scoring）
- PaperProfile.title 字段修复
- `services/retrieval/local_watcher.py` 新增（PDF → parse → extract → analysis → writing）
- `scan-local-pdfs` / `watch-local-pdfs` 命令
- GROBID Docker 安装（Docker Desktop 已装，镜像拉取待解决网络问题）
- PostgreSQL 已就绪（001_initial schema 已应用）

## 2026-03-18

### 15:33
- 建立固定项目目录：`projects/aris-lit/`
- 建立 `README.md`
- 建立 `plans/TASK_BREAKDOWN.md`
- 建立 `progress/STATUS.md`
- 建立 `progress/WORKLOG.md`
- 约定项目推进时优先读取状态文件与任务文件

下一步：
- 初始化核心 schema
- 细化 Retrieval / Dedup 的文件级开发清单
- 明确 DB 与 API/CLI 最小入口

## 2026-03-25

### 19:35 — 方案 C 双轨写作链路（safe / polished）落地

**目标：**
按顺序把方案 C 的双轨写作链路接入现有 writing / local review 主流程，并补齐日志、测试、summary / artifacts 指标。

**本轮计划（按实现顺序执行）：**
1. 定义双轨 draft model / schema
2. paragraph plan 增加强约束字段
3. 新增 evidence bundle 构建器
4. section_writer 接 safe 轨 paragraph-first
5. 新增 paragraph-level validator
6. 新增 section-level validator
7. style_rewriter 改 constrained polish
8. polished 优先覆盖 synthesis / comparison / contradiction / gap / conclusion
9. polished 独立 validator / 校验扩展
10. run_local_review 接双轨流程
11. 新增 version_selector
12. 在 summary / artifacts 中记录双轨指标

**约束：**
- 尽量保持现有接口兼容
- 必补测试：paragraph planner 新字段、evidence bundle、safe/polished 选择、run_local_review 双轨结果字段

### 20:18 — 方案 C 双轨写作链路质量增强（quality-first）

**本轮目标：**
1. 强化 polished 轨在 `synthesis / comparison / contradiction / gap / conclusion` 段落上的综述表达质量，减少模板味与空转过渡。
2. 把 version selector 从“只看是否不更差”推进到“质量增益 + 风险约束”联合决策。
3. 在 `run_local_review.py` 的 summary / dual_track 字段里补上质量选择依据，方便后续真实样本排查。
4. 补回归测试覆盖：高价值段落 polish 提升、selector 风险约束、dual_track quality 字段。

**已完成：**
- `services/writing/style_rewriter.py`
  - 为高价值 move 增加 rule-based 质量增强：更好的开头句、比较句、收束句。
  - 增加 citation retention 保护与 overclaim 降噪，避免把“证据有限”写成“完全没有”。
  - polished 段落输出 `quality_notes`，供 selector 读质量信号。
- `services/writing/version_selector.py`
  - 新增 quality/risk scorecard。
  - 明确把 citation retention / unsupported assertion / role drift / overstatement 作为硬风险或高权重风险。
  - 选择理由从单一 reason 扩成可解释 scorecard。
- `scripts/run_local_review.py`
  - dual_track 新增 `quality_metrics`。
  - writing_strategy 新增 `selection_report`，让本地 review summary 能直接看到选轨依据。
- 测试：补 polished 高价值段落、selector 风险拒绝、run_local_review quality 字段断言。

## 2026-03-26

### 11:35 — 检索式 `AND NOT` + APA 引文整理 + DOCX 输出补齐

**目标：**
把本轮用户直接反馈的三个交付问题一次性补齐：
1. 检索式支持显式 `AND NOT`
2. 最终综述在 Markdown / Word 输出中更完整地呈现 APA 风格引文
3. 最终产物默认补出 `review.docx`，便于直接查看和发送

**本轮确认与处理：**
- `services/retrieval/query_builder.py`
  - 已采用布尔检索解析，支持把 `AND NOT` 后的排除词拆进 `negative_terms`
  - `build_query_plan(...)` 会把排除词写入 `filters.exclude_terms`
- `services/retrieval/aggregator.py`
  - 已把 `exclude_terms` 传入 OpenAlex / arXiv 检索客户端
- `services/retrieval/arxiv_client.py`
  - 检索表达式会组装为 `all:"A" AND all:"B" AND NOT all:"C"` 形式
- `services/retrieval/openalex_client.py`
  - 当前通过检索后过滤方式落实排除词，保证 `AND NOT` 在 OpenAlex 源也可生效

**本轮新增/补强：**
- `services/writing/markdown_composer.py`
  - 保留现有正文内 APA 风格 parenthetical citation
  - 新增 `References` 章节
  - 将已使用引文按出现顺序汇总，输出 APA 风格参考文献条目
  - 参考文献条目支持作者、年份、标题、venue、doi 的格式化
  - citation metadata 合并逻辑改为“优先保留已有非空字段”，避免 matrix 多行覆盖掉标题/作者
- `services/analysis/exporters.py`
  - 新增 `export_docx(...)`
  - 优先用 `pandoc`，回退 `textutil`
- `scripts/run_local_review.py`
  - 生成 `review.md` 后自动导出 `review.docx`
  - `artifacts.json` 纳入 `review.docx`
- `scripts/run_review.py`
  - 同步自动导出 `review.docx`
- `tests/test_writing_smoke.py`
  - 新增 APA 参考文献输出断言
  - 补 `References` 章节断言

**本轮验证：**
- `python3 -m py_compile services/analysis/exporters.py scripts/run_local_review.py scripts/run_review.py`
- `pytest tests/test_retrieval_smoke.py tests/test_writing_smoke.py -q`
- 手动验证：现有 `review.md` 可成功导出 `review.docx`

**交付结果：**
- 最终输出默认包含：`review.md` / `review.docx` / `review.tex`
- 检索式可直接接受：`A AND B AND NOT C OR D`
- Markdown/Word 阅读版本现在会附带 APA 风格 `References` 章节
