# STEP 07 - Analysis 横向分析与 Matrix（开发细则）

更新时间：2026-03-18 16:00 CST

## 1. 目标
基于多篇论文的结构化结果生成 coverage report、claims-evidence matrix、contradiction report。

## 2. 代码文件拆解
- `services/analysis/coverage_analyzer.py`
- `services/analysis/matrix_builder.py`
- `services/analysis/contradiction_analyzer.py`
- `services/analysis/exporters.py`
- `tests/test_analysis_*.py`

## 3. 直接可做的开发任务

### Task 7.1 Coverage Analyzer
需要做：
1. 统计 method/task/language/year/dataset 分布
2. 输出 coverage JSON
3. 统计中文场景覆盖

### Task 7.2 Matrix Builder
需要做：
1. 把 paper profile 和 claims 展开成行
2. 绑定 evidence、dataset、metric、limitation
3. 输出 matrix JSON/CSV

### Task 7.3 Contradiction Analyzer
需要做：
1. 找同任务不同结论
2. 找指标不可横比
3. 找术语定义冲突

### Task 7.4 Exporters
需要做：
1. 导出 JSON
2. 导出 CSV
3. 导出 Markdown 表格

## 4. 建议开发顺序
1. `coverage_analyzer.py`
2. `matrix_builder.py`
3. `exporters.py`
4. `contradiction_analyzer.py`

## 5. 最小可运行版本定义
- 输入多篇 profile
- 输出 coverage report
- 输出 matrix.csv
- 输出简单 contradiction notes

## 6. 验收样例
输入：30 篇论文 profile
输出：
- `coverage_report.json`
- `claims_evidence_matrix.csv`
- `contradiction_report.json`
