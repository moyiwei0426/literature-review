# WORKLOG_DETAIL — 工作日志详情

> 当前重点：补齐 2026-03-24 这轮 C 版本稳定化（方向 A）推进的完整记录，并明确运行日志与修改日志的边界。

---

## 2026-03-24 — C 版本稳定化（方向 A）完整记录

### 本轮背景
本轮工作的核心不是继续扩功能，而是把 `scripts/run_local_review.py` 收成当前可交付、可试跑、可解释的稳定入口。

### 本轮主要判断
经过对 AAP 子集（Applied Spatial Analysis and Policy 相关 4 篇）逐步验证，已经明确：

1. **真实 extraction 可用**
   - 单篇 live extraction 已确认能够得到有语义内容的 `PaperProfile`
   - 2 篇、4 篇子集也能完成 extraction

2. **live writing 本体不稳定**
   - outline / section / rewrite 在真实模型路径下会出现结构漂移
   - 常见症状：section id 漂成 `sec-1/sec-2/...`、paragraph move metadata 丢失
   - 最终由 validator 判定 fail

3. **validated fallback 能稳定收口**
   - 当 live writing fail 时，自动切到 rule-based writing
   - 采用 validation 更好的结果
   - 这条策略已在 1 / 2 / 4 paper 三个规模验证通过

---

## 本轮代码修改明细

### 1. `services/llm/adapter.py`
**目的：** 让 smoke / 回归测试不被真实 provider 与 OAuth 初始化拖住。

**改动：**
- OAuth client 改为懒加载
- pytest / 回归环境允许强制 stub
- 避免 planner / writer smoke 因线上 provider 初始化而失稳

**效果：**
- `tests/test_planner_smoke.py`
- `tests/test_writing_smoke.py`
- `tests/test_local_review_smoke.py`
重新回到可作为回归信号的状态

---

### 2. `services/writing/section_writer.py`
**目的：** 让 conclusion 不再因为缺 paragraph move metadata 被 validator 打回。

**改动：**
- conclusion 改为输出 paragraph-level metadata
- 显式提供：
  - `synthesis`
  - `comparison`
  - `gap`

**效果：**
- conclusion 不再是纯文本黑盒
- validator 可正确识别 expected/observed moves

---

### 3. `scripts/run_local_review.py`
**目的：** 把方向 A 从“补丁逻辑”收成“默认稳定策略”。

**改动：**
- live writing 失败后自动触发 rule-based writing fallback
- summary/result 中新增：
  - `writing_strategy`
  - `extraction_strategy`
  - `run_log`
- 每次运行在输出目录落盘：`run.log`

**当前策略：**
- extraction：优先 live
- writing：先尝试 live
- 若 validator fail：自动 fallback 到 rule-based writing
- 最终采用 validation 更好的产物

---

### 4. `tests/test_local_review_smoke.py`
**目的：** 防止方向 A 后续退化。

**改动：**
- 对 `writing_strategy` 增加断言
- 对 `extraction_strategy` 增加断言
- 新增 fallback 行为测试

**验证：**
- `python3 -m pytest tests/test_local_review_smoke.py -q`
- 结果：`3 passed`

---

### 5. `plans/C_VERSION_STABILIZATION.md`
**目的：** 让项目内正式文档体现当前默认稳定策略。

**改动：**
- 明确 C1 阶段要在 `summary.json` 暴露：
  - `extraction_strategy`
  - `writing_strategy`
  - `validation`
- 明确方向 A 的默认稳定策略
- 明确推荐排查顺序：
  1. `summary.json`
  2. `run.log`
  3. `validation_report.json`

---

### 6. 状态与工作记录文件
**本次补齐：**
- `progress/STATUS.md`
- `progress/WORKLOG.md`
- `progress/WORKLOG_DETAIL.md`
- `docs/LOGGING.md`

**目的：**
- 让最近这轮稳定化推进不只存在于口头说明和运行产物里
- 形成可交接、可回顾的人工记录

---

## 本轮验证结果

### AAP 子集验证（真实 extraction + fallback writing）
- `data/generated/aap_live_1paper_20260324_fallback` → pass
- `data/generated/aap_live_2paper_20260324_fallback` → pass
- `data/generated/aap_live_4paper_20260324_fallback` → pass

### 关键观察
- 2-paper 场景中，`09_2018_jiang_aap` 出现过一次 extraction retry 后恢复成功
- 说明 extraction 并非完全零波动，但当前 retry/恢复能力足够支撑主链稳定化

---

## 当前记录体系的边界（明确）

### 现在已经具备
#### 1. 运行级记录
每次 `run_local_review.py` 运行后，输出目录会包含：
- `summary.json`
- `run.log`
- `validation_report.json`
- 其余 artifacts（review / sections / appendix / evidence table 等）

#### 2. 修改级记录
本轮已经人工同步到：
- `progress/STATUS.md`
- `progress/WORKLOG.md`
- `progress/WORKLOG_DETAIL.md`

### 现在还没有自动化做到
- 没有统一 changelog 自动生成
- 没有 git commit 历史可直接充当完整工作记录
- API / worker 尚未统一到 run-level 文件日志

---

## 当前结论
项目现在的整体位置已经不是 MVP 骨架，而是：

**C 版本稳定化阶段（方向 A 基本收住）**

最稳的可交付路径是：

**live extraction + validated fallback writing**

而不是：

**全 live writing**

这也是后续是否进入方向 B（live writing 本体修复）的清晰分界。
