# STEP 07 - Analysis 横向分析与 Matrix

## 目标
将多篇论文的结构化结果聚合为可比矩阵、覆盖统计和矛盾分析结果。

## 输入
- 多篇 `paper_profile`
- `claims`
- `claim_evidence_links`

## 输出
- coverage report
- claims-evidence matrix
- contradiction report

## 子任务
1. 统计 method/task/language/year/dataset 分布
2. 构建 claims-evidence matrix
3. 标注论文间的可比维度
4. 识别冲突结论和不可横比情况
5. 导出 CSV / JSON / Markdown

## 开发顺序
1. 先做 coverage analyzer
2. 再做 matrix builder
3. 再做 contradiction analyzer
4. 最后做导出层

## 验收标准
- 多篇论文可以横向展开比较
- 覆盖情况可视化/结构化明确
- 冲突点可被后续 gap 使用

## 常见风险
- 不同论文术语体系不统一
- 指标不同却被错误比较
- matrix 只是摘要堆叠而非对齐

## 完成定义
- 输出可直接作为 novelty check 输入
