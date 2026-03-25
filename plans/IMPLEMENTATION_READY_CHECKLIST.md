# ARIS-Lit 实施就绪清单

更新时间：2026-03-18 16:00 CST

## 开工前必须具备
- [ ] Step 01 的 settings / logging / API or CLI 骨架
- [ ] Step 02 的核心 schema 文件
- [ ] Retrieval 最小可运行定义已确认
- [ ] Dedup 规则优先级已确认
- [ ] Parsing 的 PDF 获取与 fallback 策略已确认
- [ ] Extraction 的输出 schema 已确认

## 建议开工顺序
1. Step 01 先补 `infra/settings.py` 和 `api/main.py`
2. Step 02 先补四个核心 schema：paper_candidate / paper_chunk / paper_profile / gap
3. Step 03 做 OpenAlex + arXiv + aggregator
4. Step 04 做 deduper
5. Step 05 做 pdf_fetcher + grobid_adapter + chunker
6. Step 06 做 llm adapter + extractor + validators

## 第一批可以直接编码的文件
- `infra/settings.py`
- `infra/app_logging.py`
- `api/main.py`
- `schemas/paper_candidate.schema.json`
- `schemas/paper_chunk.schema.json`
- `schemas/paper_profile.schema.json`
- `schemas/gap.schema.json`
- `services/retrieval/query_builder.py`
- `services/retrieval/openalex_client.py`
- `services/retrieval/arxiv_client.py`
- `services/retrieval/aggregator.py`
- `services/retrieval/deduper.py`
