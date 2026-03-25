# RUN ANALYSIS MVP

## 当前最小流程
1. 准备多个 `PaperProfile`
2. 调用 `build_coverage_report(profiles)`
3. 调用 `build_claims_evidence_matrix(profiles)`
4. 调用 `detect_contradictions(profiles)`
5. 用 `export_json/export_csv/export_markdown_table` 导出结果

## 当前状态
- 已有 coverage analyzer
- 已有 matrix builder
- 已有 contradiction analyzer
- 已有 JSON / CSV / Markdown 导出器
