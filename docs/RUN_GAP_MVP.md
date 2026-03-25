# RUN GAP MVP

## 当前最小流程
1. 准备 coverage report / claims-evidence matrix / contradiction report
2. 调用 `generate_candidate_gaps(matrix, coverage, contradiction)`
3. 调用 `verify_gaps(candidate_gaps, coverage, matrix)`
4. 调用 `score_gaps(verified_gaps)`
5. 使用 `GapStorage` 保存结果

## 当前状态
- 已有 candidate gap generator
- 已有 verifier
- 已有 scorer
- 已有 gap prompts 与 gap storage
- 下一步是接入真实 critic/verifier 模型判断
