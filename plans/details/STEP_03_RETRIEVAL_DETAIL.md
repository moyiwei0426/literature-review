# STEP 03 - Retrieval 检索系统（开发细则）

更新时间：2026-03-18 16:00 CST

## 1. 目标
从多个学术来源稳定召回候选论文，并统一为标准对象。

## 2. 代码文件拆解
- `services/retrieval/openalex_client.py`
- `services/retrieval/arxiv_client.py`
- `services/retrieval/semanticscholar_client.py`
- `services/retrieval/crossref_client.py`
- `services/retrieval/unpaywall_client.py`
- `services/retrieval/aggregator.py`
- `services/retrieval/normalizer.py`
- `services/retrieval/query_builder.py`
- `services/retrieval/storage.py`
- `tests/test_retrieval_*.py`

## 3. 直接可做的开发任务

### Task 3.1 Query Builder
文件：`services/retrieval/query_builder.py`

需要做：
1. 定义查询输入模型：
   - query
   - year_from / year_to
   - max_results
   - language
   - include_sources
   - seed_papers
2. 支持三类策略：关键词、种子扩展、综述反向扩展
3. 输出标准化 query plan

验收：
- 输入一个 topic，可生成统一 query plan

### Task 3.2 OpenAlex Client
文件：`services/retrieval/openalex_client.py`

需要做：
1. 封装 search 方法
2. 处理分页
3. 抽取 title/authors/year/doi/abstract/pdf_url/citation_count
4. 保存原始 payload
5. 映射为 `paper_candidate`

验收：
- 能对主题返回标准候选对象列表

### Task 3.3 arXiv Client
文件：`services/retrieval/arxiv_client.py`

需要做：
1. 封装 query 与解析返回
2. 抽取 arxiv_id、pdf_url、categories、summary
3. 映射为 `paper_candidate`

### Task 3.4 Semantic Scholar Client
文件：`services/retrieval/semanticscholar_client.py`

需要做：
1. 封装论文搜索
2. 补充 citation/reference 信息
3. 映射为标准对象

### Task 3.5 Crossref / Unpaywall 补全
文件：
- `services/retrieval/crossref_client.py`
- `services/retrieval/unpaywall_client.py`

需要做：
1. 按 DOI 补 venue / publisher / OA 信息
2. 找开放 PDF 或 landing page

### Task 3.6 Normalizer
文件：`services/retrieval/normalizer.py`

需要做：
1. 统一标题、作者、年份字段
2. 处理 abstract 缺失
3. 统一来源命名
4. 将各客户端结果转成统一 `paper_candidate`

### Task 3.7 Aggregator
文件：`services/retrieval/aggregator.py`

需要做：
1. 调多个来源 client
2. 合并结果
3. 记录来源与得分
4. 输出候选列表和原始日志

### Task 3.8 Storage
文件：`services/retrieval/storage.py`

需要做：
1. 保存 raw responses
2. 保存 normalized candidates
3. 先支持 JSON 文件落盘，后续可接 DB

## 4. 建议开发顺序
1. `query_builder.py`
2. `openalex_client.py`
3. `arxiv_client.py`
4. `normalizer.py`
5. `aggregator.py`
6. `storage.py`
7. `semanticscholar_client.py`
8. `crossref_client.py` / `unpaywall_client.py`

## 5. 最小可运行版本定义
做到下面这些就可开下一阶段：
- 输入 topic
- 从 OpenAlex + arXiv 拉结果
- 统一成 `paper_candidate`
- 保存 JSON 结果
- 输出 30+ 候选论文

## 6. 验收样例
输入：`large language model literature review automation`
输出：
- `data/raw/retrieval/*.json`
- `data/generated/candidates/*.json`
- 控制台打印候选数量和来源统计
