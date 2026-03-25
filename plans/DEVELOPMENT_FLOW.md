# ARIS-Lit 具体开发流程总表

更新时间：2026-03-18 15:51 CST

本文件用于把项目开发流程拆成可执行阶段，并指向每个阶段的单独文件。

## 开发主线
1. Step 01 - 基础设施与项目规范
2. Step 02 - 数据模型与 Schema 设计
3. Step 03 - Retrieval 检索系统
4. Step 04 - Dedup 去重与实体统一
5. Step 05 - PDF 获取与 Parsing 解析
6. Step 06 - Extraction 结构化提取
7. Step 07 - Analysis 横向分析与 Matrix
8. Step 08 - Novelty / Gap 分析
9. Step 09 - Writing / BibTeX / LaTeX 输出

## 单文件索引
- `plans/steps/STEP_01_FOUNDATION.md`
- `plans/steps/STEP_02_SCHEMA.md`
- `plans/steps/STEP_03_RETRIEVAL.md`
- `plans/steps/STEP_04_DEDUP.md`
- `plans/steps/STEP_05_PARSING.md`
- `plans/steps/STEP_06_EXTRACTION.md`
- `plans/steps/STEP_07_ANALYSIS.md`
- `plans/steps/STEP_08_GAP.md`
- `plans/steps/STEP_09_WRITING.md`

## 开发细则索引
- `plans/details/STEP_01_FOUNDATION_DETAIL.md`
- `plans/details/STEP_02_SCHEMA_DETAIL.md`
- `plans/details/STEP_03_RETRIEVAL_DETAIL.md`
- `plans/details/STEP_04_DEDUP_DETAIL.md`
- `plans/details/STEP_05_PARSING_DETAIL.md`
- `plans/details/STEP_06_EXTRACTION_DETAIL.md`
- `plans/details/STEP_07_ANALYSIS_DETAIL.md`
- `plans/details/STEP_08_GAP_DETAIL.md`
- `plans/details/STEP_09_WRITING_DETAIL.md`
- `plans/IMPLEMENTATION_READY_CHECKLIST.md`

## 阅读顺序
每次进入项目时建议按以下顺序读取：
1. `progress/STATUS.md`
2. `plans/NEXT_ACTIONS.md`
3. `progress/WORKLOG.md`
4. `plans/DEVELOPMENT_FLOW.md`
5. 当前正在执行的 `plans/steps/STEP_XX_*.md`

## 交付规则
每个步骤文件都包含：
- 目标
- 输入
- 输出
- 子任务
- 开发顺序
- 验收标准
- 常见风险
- 完成定义
