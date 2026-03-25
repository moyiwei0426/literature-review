# C_VERSION_STABILIZATION.md

## 目标定义
C 版本 = 可交给别人试用、流程不太掉链子的稳定版。

重点不是继续加新功能，而是把现有主链收口为：
- 本地入口稳定可跑
- 关键 artifacts 稳定生成
- smoke tests 能作为可信回归信号
- 风险边界清楚，失败可解释

---

## 当前稳定化主线
优先以 `scripts/run_local_review.py` 作为 C 版本标准入口。

目标产物：
- `outline.json`
- `section_plans.json`
- `paragraph_plans.json`
- `sections.json`
- `validation_report.json`
- `abstract.json` / `abstract.txt`
- `keywords.json` / `keywords.txt`
- `appendix.json`
- `evidence_table.json` / `evidence_table.md`
- `review.md`
- `review.tex`

---

## 分阶段路线

### Phase C1: 主链稳定化（最高优先级）
目标：确保 `run_local_review.py --skip-compile` 可作为稳定试运行入口。

涉及文件：
- `scripts/run_local_review.py`
- `services/writing/__init__.py`
- `services/writing/outline_planner.py`
- `services/writing/section_planner.py`
- `services/writing/paragraph_planner.py`
- `services/writing/section_writer.py`
- `services/writing/citation_grounder.py`
- `services/writing/style_rewriter.py`
- `services/writing/review_validator.py`
- `services/latex/latex_composer.py`

验收标准：
- 本地 review 主链能完整生成核心 artifacts
- 失败时日志能定位在 parsing / writing / export 哪一层
- validation summary 能出现在最终结果中
- `summary.json` 明确暴露 extraction / writing strategy（是否 live、是否 fallback、最终是否 adopted）

默认稳定策略（方向 A）：
- extraction 优先走 live LLM
- writing 先尝试 live
- 若 live writing 产物 validator fail，则自动切到 rule-based writing fallback
- 最终采用 validation 更好的那一版产物

---

### Phase C2: gentle-r 收口（成文质量 + 写作链稳定性）
目标：收掉 paragraph prose 与 smoke 之间的漂移。

当前已知方向：
1. paragraph-level prose quality
2. citation grounding 可解释性增强
3. structure-preserving rewrite 文风质量提升
4. validator 反推写作薄弱点

当前优先项：
#### C2.1 paragraph-level prose quality
涉及文件：
- `services/writing/paragraph_planner.py`
- `services/writing/section_writer.py`
- `services/writing/style_rewriter.py`
- `tests/test_writing_smoke.py`
- `tests/test_planner_smoke.py`

当前实施思路：
- paragraph plan 保留 `sentence_plan` / `rhetorical_role`
- section writer 输出更像 academic review prose
- 减少固定模板味，如：
  - `core claim in this section`
  - `ready takeaway`
  - `minor aside`
- smoke tests 从“绑定旧模板词”改为“检查更自然的段落结构与约束”

验收标准：
- paragraph 仍保留 move metadata / citation metadata
- prose 更自然，不泄露指令味
- planner-aware citation grounding 不被破坏

---

### Phase C3: planner / writer / grounder / validator 协同加固
目标：统一最小契约，避免字段在链路中丢失或语义漂移。

重点检查字段：
- `move_type`
- `purpose`
- `theme_refs`
- `gap_refs`
- `citation_targets`
- `supporting_citations`
- `supporting_points`
- `sentence_plan`
- `citation_keys`

涉及文件：
- `services/writing/section_planner.py`
- `services/writing/paragraph_planner.py`
- `services/writing/section_writer.py`
- `services/writing/citation_grounder.py`
- `services/writing/style_rewriter.py`
- `services/writing/review_validator.py`

验收标准：
- planner 元数据在 writer / rewrite / grounding 后仍可追踪
- validator 的 expected/observed moves 与 writer 输出一致

---

### Phase C4: 测试分层与稳定回归
目标：让测试结果真正反映项目健康度。

测试分层：
1. 主链 smoke：`run_local_review.py` 关键产物
2. 写作链 smoke：writer / grounder / rewrite / validator
3. 规划链 smoke：outline / section planner / paragraph planner

当前重点文件：
- `tests/test_writing_smoke.py`
- `tests/test_planner_smoke.py`
- `tests/test_outline_planner_smoke.py`
- `tests/test_synthesis_organization_smoke.py`

验收标准：
- 失败时能快速判断是主链、规划链还是写作链问题
- 减少 brittle string assertions

---

## 当前风险记录
1. 部分 pytest 进程曾被外部 `SIGTERM` 杀掉，不能把“未完整跑完”当成通过。
2. prose 优化后，旧 smoke 对固定模板词的依赖会产生误报失败。
3. 当前状态更适合先以 `--skip-compile` 观察 markdown / json artifacts，而不是先要求 PDF 完全稳定。

---

## 推荐试跑命令
```bash
cd /Users/momo/.openclaw/workspace/projects/aris-lit
PYTHONPATH=. python3 scripts/run_local_review.py \
  --pdf-dir data/manual_uploads \
  --title "Test Review" \
  --skip-compile
```

优先查看：
- `data/generated/local_review_*/summary.json`
  - 看 `extraction_strategy`
  - 看 `writing_strategy`
  - 看 `validation`
- `review.md`
- `sections.json`
- `validation_report.json`
- `abstract.txt`
- `keywords.txt`
- `evidence_table.md`

---

## 完成 C 版本后建议继续的方向
### C+1
- citation grounding rationale
- validation report 更像 QA 报告
- evidence table 反哺 section selection

### C+2
- front matter / metadata
- review manifest
- appendix / table export 整洁化
- 更稳的 compile / final packaging
