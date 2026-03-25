# SCHEMA SPEC

更新时间：2026-03-18 16:48 CST

## 目标
统一 ARIS-Lit 的核心数据对象，保证 Retrieval / Parsing / Extraction / Analysis / Writing 之间字段一致。

## 核心对象

### 1. PaperCandidate
用途：检索阶段的候选论文对象。
主要由工具层填充：检索源、标题、作者、年份、摘要、PDF 链接、召回分数。

### 2. PaperChunk
用途：Parsing 阶段生成的论文文本块。
主要由工具层填充：chunk id、section、页码、文本、顺序。

### 3. PaperProfile
用途：Extraction 阶段生成的单篇结构化画像。
主要由模型层填充：研究问题、方法、任务、数据集、指标、claims、limitations。

### 4. Gap
用途：Novelty / Gap 阶段生成的研究空白对象。
由 analysis + model critic/verifier 共同填充。

## 字段职责约定
- 工具优先字段：source、source_id、year、pdf_url、page_start、page_end、order_index
- 模型优先字段：research_problem、method_summary、main_claims、limitations、gap_statement
- 混合字段：confidence、retrieval_score、review_worthiness

## 已补充对象
本轮已补充：
- `paper_master`
- `paper_file`
- `claim`
- `claim_evidence_link`
- `draft`

## 后续扩展
后续将继续细化：
- DB 表结构映射
- 枚举词表与字段约束的集中管理
