# RUN EXTRACTION MVP

## 当前最小流程
1. 准备 `PaperChunk` 列表
2. 使用 `PaperExtractor().extract(paper_id, chunks)` 生成 `PaperProfile`
3. 使用 `build_claim_evidence_links(profile)` 生成 claim-evidence links
4. 使用 `ExtractionStorage` 保存 profile / claims / links / report

## 当前状态
- 已有 LLM adapter stub
- 已有 extraction prompts
- 已有 extractor / validator / claim_linker / storage
- 当前输出仍为本地 stub 驱动，下一步接入真实模型提供商
