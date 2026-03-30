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


---

## 2026-03-25 — 方案 C 双轨写作链路实施记录

### 目标
把当前单轨 drafting / rewrite 流程扩成：
- `safe`：paragraph-first、强约束、先保结构与证据
- `polished`：在 safe 基础上对高价值段落做 constrained polish

### 本轮实施要求
- 保持 `write_sections(...)` / `rewrite_style(...)` 等主接口尽量兼容
- `run_local_review.py` 要能输出双轨结果、校验结果、版本选择结果
- `summary.json` / `artifacts.json` 要反映双轨指标
- 增加最小但有效的回归测试

### 2026-03-25 20:18 — quality-first 继续优化

**1. polished 轨表达增强**
- 在 `style_rewriter.py` 里把高价值段落单独处理：
  - `synthesis`：更强调跨研究归纳与 field-level takeaway
  - `comparison`：更明确 side-by-side 对比与 tradeoff
  - `contradiction`：强调 mixed / conditional disagreement，而不是硬下结论
  - `gap`：把 `no studies` 之类易越界表达改写为 `limited evidence / remains unresolved`
  - `conclusion`：增强收束句，但保留边界条件
- 同时保留 citation retention，避免 polish 过程丢 citation。

**2. selector 改成质量优先但有风险护栏**
- `version_selector.py` 不再只比较 finding_count。
- 新增：
  - `quality_score`
  - `risk_score`
  - `hard_risk`
  - 可解释的 `signals`
- 风险项显式覆盖：
  - citation retention penalty
  - unsupported assertion penalty
  - role drift penalty
  - overstatement penalty
- 决策逻辑：只有在质量增益成立且风险在预算内时才选 polished；命中硬风险则回 safe。

**3. local review 输出可解释质量字段**
- `run_local_review.py` 现在会把：
  - `dual_track.safe.quality_metrics`
  - `dual_track.polished.quality_metrics`
  - `writing_strategy.selection_report`
  写入 summary/result，方便真实 review 输出排查。

**4. 回归测试补充**
- 新增 polished 高价值段落质量提升测试
- 新增 selector 风险拒绝测试
- 扩展 local review dual_track quality 字段断言

---

## 2026-03-26 — `AND NOT` 检索 / APA 参考文献 / DOCX 输出补齐

### 背景
这轮不是重做主链，而是补齐最终交付体验里的三个明显缺口：
1. 用户希望检索式能直接写 `AND NOT`
2. 用户希望文内引用之外，最终文稿里把 APA 格式梳理完整
3. 用户希望默认就有 Word 文档输出，不再额外手工转格式

### 本轮判断
#### 1. `AND NOT` 主体能力已经有一半在代码里
排查后发现：
- `query_builder.py` 已经具备 `parse_boolean_query(...)`
- `QueryPlan` 已能保存：
  - `raw_query`
  - `positive_terms`
  - `negative_terms`
- `aggregator.py` 已会把 `exclude_terms` 传入 source client
- `arxiv_client.py` 已能把 negative terms 组装到 arXiv 的布尔查询里

所以这块不是“从零接入”，而是确认整条链已连通，并把它纳入本轮正式交付说明。

#### 2. APA 之前只有“文内 parenthetical citation”，没有完整参考文献区
`markdown_composer.py` 之前已经能把段落里的 citation key 渲染成：
- `(Smith & Jones, 2023)`
这对正文可读性是够的，但还缺：
- 独立 `References` 章节
- APA 风格作者名格式化
- title / venue / doi 的汇总输出

这也是 Word 阅读版本里最直观的缺口。

#### 3. DOCX 之前是手工导出，不是主流程默认产物
已有环境可以转出 docx，但默认 pipeline 没有把它当作标准 artifact。
因此要补的是：
- 自动导出
- artifact manifest 记录
- 转换失败不拖垮主流程

### 本轮代码调整
#### A. `services/writing/markdown_composer.py`
**新增：**
- `_collect_cited_keys(...)`
  - 从 section / paragraph 层收集实际用到的 citation key
- `_render_references(...)`
  - 在正文与 appendix 后补出 `## References`
- `_format_apa_reference(...)`
  - 输出 APA 风格参考文献条目
- `_format_apa_reference_authors(...)`
  - 把作者列表转成 `Surname, A.` / `Surname, A., & Surname, B.` 形式
- `_format_reference_author_name(...)`
  - 处理 `Given Family` 与 `Family, Given` 两种输入

**调整：**
- `compose_markdown_review(...)`
  - 改成先构建 citation metadata，再渲染 sections / references
- `_build_citation_metadata(...)`
  - 改成合并式写法，避免 matrix 多行记录把已有的 title/authors/venue/doi 覆盖成空值

**结果：**
最终 `review.md` / `review.docx` 不只在正文里有 `(Author, Year)`，还会有可读的 APA 风格 `References` 区。

#### B. `services/analysis/exporters.py`
**新增：**
- `export_docx(markdown_path, output_path)`

**策略：**
- 优先 `pandoc`
- 回退 `textutil`
- 两者都没有则抛错，由调用层决定是否降级

#### C. `scripts/run_local_review.py`
**新增：**
- `review.md` 写出后自动尝试生成 `review.docx`
- 若失败，仅记 warning，不中断 review 主流程
- `artifacts.json` 新增 `review.docx`

#### D. `scripts/run_review.py`
**同步：**
- 在线 / 本地统一主流程同样自动补出 `review.docx`

### 测试补充
#### `tests/test_writing_smoke.py`
新增与增强：
- `References` 章节断言
- APA 参考文献条目断言
- DOI/venue 的格式化断言

### 本轮验证
已执行：
- `python3 -m py_compile services/analysis/exporters.py scripts/run_local_review.py scripts/run_review.py`
- `pytest tests/test_retrieval_smoke.py tests/test_writing_smoke.py -q`
- 手动从现有 `review.md` 导出 `review.docx`

### 本轮结果
用户现在拿到的最终 review 输出，默认应包含：
- `review.md`
- `review.docx`
- `review.tex`

同时：
- 检索式可以直接写 `AND NOT`
- Word / Markdown 阅读版本会有更完整的 APA 格式参考文献整理
