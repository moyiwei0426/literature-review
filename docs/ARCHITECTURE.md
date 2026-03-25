# ARIS-Lit 技术架构（初版）

更新时间：2026-03-18

## 总原则
工具优先，模型补强。

## 六个核心流水线阶段
1. Retrieval：多源检索与聚合
2. Dedup：论文实体统一
3. Parsing：PDF 获取、解析、切 chunk
4. Extraction：单篇结构化抽取 + claim/evidence 绑定
5. Analysis：matrix、coverage、contradiction、gap
6. Writing：outline、section、citation、BibTeX、LaTeX

## 技术栈建议
- API：FastAPI
- Workflow：Prefect
- DB：PostgreSQL + pgvector
- Queue：Redis
- Parsing：GROBID + PyMuPDF
- Retrieval：OpenAlex / arXiv / Semantic Scholar / Crossref / Unpaywall
- LLM：统一 adapter，支持主模型与 critic/verifier 模型
- Compile：latexmk 或 tectonic

## 项目推进规范
每次任务开始前必须读取：
- `plans/TASK_BREAKDOWN.md`
- `progress/STATUS.md`
- `progress/WORKLOG.md`
- `plans/NEXT_ACTIONS.md`

每次任务结束后必须更新：
- `progress/STATUS.md`
- `progress/WORKLOG.md`
- `plans/NEXT_ACTIONS.md`
