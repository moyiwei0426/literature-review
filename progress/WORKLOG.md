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
