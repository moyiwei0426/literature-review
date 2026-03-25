# RUN RETRIEVAL MVP

## 当前最小流程
1. 构建 `QueryInput`
2. 调用 `build_query_plan()`
3. 使用 `RetrievalAggregator().run(plan)`
4. 使用 `dedupe_candidates()` 做去重

## 当前能力
- 支持 OpenAlex
- 支持 arXiv
- 支持统一候选对象输出
- 支持 JSON 落盘
- 支持最小去重

## 下一步
- 补 CLI/API 入口
- 补 Semantic Scholar / Crossref / Unpaywall
- 补正式 dedup report 落盘
