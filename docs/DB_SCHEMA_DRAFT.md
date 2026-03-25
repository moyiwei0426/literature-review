# DB SCHEMA DRAFT

更新时间：2026-03-18 16:48 CST

## 建议核心表
- `projects`
- `queries`
- `papers`
- `paper_sources`
- `paper_files`
- `paper_chunks`
- `paper_profiles`
- `claims`
- `claim_evidence_links`
- `gaps`
- `drafts`
- `references_bib`

## 关键关系
- `queries.project_id -> projects.id`
- `paper_sources.paper_id -> papers.id`
- `paper_files.paper_id -> papers.id`
- `paper_chunks.paper_id -> papers.id`
- `paper_profiles.paper_id -> papers.id`
- `claims.paper_id -> papers.id`
- `claim_evidence_links.claim_id -> claims.id`
- `claim_evidence_links.chunk_id -> paper_chunks.id`
- `gaps.project_id -> projects.id`
- `drafts.project_id -> projects.id`

## 预留 pgvector 字段
建议后续在以下位置考虑 embedding：
- `paper_chunks.embedding`
- `claims.embedding`
- `gaps.embedding`

## 当前状态
这是草案版本，后续会在 Retrieval / Parsing / Extraction 进入稳定实现后再细化为正式迁移脚本。
