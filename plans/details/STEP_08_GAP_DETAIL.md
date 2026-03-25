# STEP 08 - Novelty / Gap 分析（开发细则）

更新时间：2026-03-18 16:00 CST

## 1. 目标
让系统基于结构化证据生成可信的研究空白点，而不是模板化套话。

## 2. 代码文件拆解
- `prompts/gap/critic_system.txt`
- `prompts/gap/verifier_system.txt`
- `services/analysis/gap_generator.py`
- `services/analysis/gap_scorer.py`
- `services/analysis/gap_verifier.py`
- `services/analysis/gap_storage.py`
- `tests/test_gap_*.py`

## 3. 直接可做的开发任务

### Task 8.1 Gap Generator
需要做：
1. 读取 matrix + coverage + contradiction
2. 生成 candidate gaps
3. 为每个 gap 绑定 supporting evidence

### Task 8.2 Critic Prompt
需要做：
1. 让模型扮演严厉审稿人
2. 审查 gap 是否真实
3. 标出套话、证据不足、夸大结论

### Task 8.3 Verifier
需要做：
1. 搜集 counter-evidence
2. 检查 gap 是否把“少”说成“没有”
3. 产出 verifier judgment

### Task 8.4 Gap Scorer
需要做：
1. confidence 评分
2. novelty_value 评分
3. review_worthiness 评分

### Task 8.5 Storage
需要做：
1. 保存 candidate gaps
2. 保存 critic 结果
3. 保存 verifier 结果
4. 导出最终 gap report

## 4. 建议开发顺序
1. `gap_generator.py`
2. critic prompt
3. `gap_verifier.py`
4. `gap_scorer.py`
5. `gap_storage.py`

## 5. 最小可运行版本定义
- 生成 5~10 条候选 gap
- 每条 gap 有支持证据
- 至少跑一轮 critic 和 verifier
- 输出排序后的最终 gap report

## 6. 验收样例
输入：matrix + coverage + contradiction
输出：
- `candidate_gaps.json`
- `verified_gaps.json`
- `gap_report.md`
