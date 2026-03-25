# RUN PARSING MVP

## 当前最小流程
1. 准备 `PaperMaster`
2. 调用 `PDFFetcher.fetch()` 下载 PDF
3. 调用 `GrobidAdapter.parse()` 或 `FallbackTextExtractor.extract()`
4. 使用 `split_sections()` 规范化 section
5. 使用 `chunk_sections()` 生成 chunks
6. 使用 `score_parse_quality()` 生成质量报告
7. 使用 `ParsingStorage` 保存 parsed / chunks / reports

## 当前状态
- Fetcher 已实现最小下载能力
- GROBID / fallback 目前是 stub
- section splitter / chunker / quality scorer 已可离线工作
