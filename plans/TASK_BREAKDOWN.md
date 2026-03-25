# ARIS-Lit 开发任务拆解（MVP → 可扩展版）

更新时间：2026-03-18

## 0. 项目目标
构建一个“工具优先 + 模型补强”的文献综述流水线系统，支持：
1. 文献检索与去重
2. PDF 获取与解析
3. 单篇结构化提取
4. Claims-Evidence 矩阵生成
5. Novelty / Gap 分析
6. 综述提纲与 LaTeX 草稿生成

---

## 1. 开发原则
- 工具负责确定性：检索、去重、Bib、编译、统计、校验。
- 模型负责高阶理解：抽取、归纳、批评、写作。
- 所有中间结果可落库、可重跑、可追溯。
- 每次任务推进，必须先更新 `progress/STATUS.md` 与 `progress/WORKLOG.md`。

---

## 2. 里程碑

### M1：项目骨架与状态管理
目标：建立固定项目目录、状态文件、开发基线。
交付：
- [ ] 目录结构建立
- [ ] 项目 README
- [ ] 架构文档
- [ ] 状态文件与日志文件
- [ ] 下一步任务队列

### M2：文献检索与去重
目标：输入 topic/query，返回结构化候选文献库。
交付：
- [ ] OpenAlex 检索客户端
- [ ] arXiv 检索客户端
- [ ] Semantic Scholar 检索客户端
- [ ] Crossref/Unpaywall 元数据补全
- [ ] 统一候选 schema
- [ ] 去重器（DOI / arXiv / 标题相似）
- [ ] 检索任务 API
- [ ] 文献入库

### M3：PDF 获取与解析
目标：自动下载开放 PDF，切分结构与 chunk。
交付：
- [ ] PDF 下载器
- [ ] GROBID 解析适配器
- [ ] PyMuPDF 兜底解析器
- [ ] section/chunk 切分器
- [ ] parse quality score
- [ ] 原文与解析结果落盘/落库

### M4：单篇结构化提取
目标：从单篇论文生成 paper profile + claims + evidence。
交付：
- [ ] 提取 schema 定义
- [ ] 提取 prompt 模板
- [ ] LLM adapter
- [ ] JSON 输出校验器
- [ ] claim-evidence 绑定逻辑
- [ ] limitation 抽取与显式/推断区分

### M5：多篇横向分析
目标：生成 claims-evidence matrix 与 coverage report。
交付：
- [ ] coverage analyzer
- [ ] method/task/language 统计
- [ ] contradiction analyzer
- [ ] claims-evidence matrix builder
- [ ] 可导出 CSV/JSON

### M6：Novelty / Gap 分析
目标：生成“候选 gap → critic → verifier → 最终 gap 报告”。
交付：
- [ ] gap schema
- [ ] gap generator
- [ ] critic agent prompt
- [ ] verifier agent prompt
- [ ] 支持证据/反证据绑定
- [ ] gap report 导出

### M7：写作与 LaTeX
目标：输出综述提纲、章节草稿、BibTeX、LaTeX、PDF。
交付：
- [ ] outline planner
- [ ] section writer
- [ ] citation grounder
- [ ] style rewriter
- [ ] BibTeX manager
- [ ] LaTeX composer
- [ ] PDF compile pipeline

---

## 3. 按周拆解（建议）

### Week 1：基础设施与项目骨架
- [ ] 建立项目目录
- [ ] 确定技术栈（FastAPI / Prefect / Postgres / pgvector / Redis）
- [ ] 建立配置文件与环境变量规范
- [ ] 建立 docs/ARCHITECTURE.md
- [ ] 建立 progress/STATUS.md、WORKLOG.md、NEXT_ACTIONS.md
- [ ] 约定 JSON schema 与代码目录

### Week 2：Retrieval MVP
- [ ] 接 OpenAlex
- [ ] 接 arXiv
- [ ] 定义 paper candidate schema
- [ ] 写检索聚合器
- [ ] 写去重器
- [ ] 保存候选文献到本地 JSON / DB
- [ ] 做一个 CLI 或 API 验证单 topic 检索

### Week 3：Parsing MVP
- [ ] 接 PDF 下载器
- [ ] 跑通 GROBID
- [ ] 做 PyMuPDF fallback
- [ ] 生成 section + chunk
- [ ] 保存 parse 结果
- [ ] 抽样检查解析质量

### Week 4：Extraction MVP
- [ ] 定义 paper profile schema
- [ ] 写 extraction prompts
- [ ] 接 LLM gateway
- [ ] 单篇论文抽取 paper profile
- [ ] 单篇论文抽取 claims + evidence links
- [ ] 校验 JSON 结构与引用 chunk 是否存在

### Week 5：Analysis MVP
- [ ] 统计 method/task/language 分布
- [ ] 构建 matrix builder
- [ ] 导出 claims-evidence matrix
- [ ] 初版 contradiction analyzer

### Week 6：Gap MVP
- [ ] 生成 candidate gaps
- [ ] critic agent 审查
- [ ] verifier agent 复核
- [ ] 导出 gap report

### Week 7：Writing MVP
- [ ] 生成 review outline
- [ ] 分节写作
- [ ] citation grounding
- [ ] BibTeX 清理
- [ ] LaTeX 组装
- [ ] 编译 PDF

---

## 4. 模块任务清单

## 4.1 Retrieval
- [ ] `services/retrieval/openalex_client.py`
- [ ] `services/retrieval/arxiv_client.py`
- [ ] `services/retrieval/semanticscholar_client.py`
- [ ] `services/retrieval/crossref_client.py`
- [ ] `services/retrieval/unpaywall_client.py`
- [ ] `services/retrieval/aggregator.py`
- [ ] `schemas/paper_candidate.schema.json`

## 4.2 Dedup
- [ ] `services/retrieval/deduper.py`
- [ ] title normalize
- [ ] DOI match
- [ ] arXiv id match
- [ ] fuzzy title match

## 4.3 Parsing
- [ ] `services/parsing/pdf_fetcher.py`
- [ ] `services/parsing/grobid_adapter.py`
- [ ] `services/parsing/pymupdf_fallback.py`
- [ ] `services/parsing/section_splitter.py`
- [ ] `services/parsing/chunker.py`
- [ ] `schemas/paper_chunk.schema.json`

## 4.4 Extraction
- [ ] `schemas/paper_profile.schema.json`
- [ ] `prompts/extraction/system.txt`
- [ ] `prompts/extraction/user.txt`
- [ ] `services/extraction/extractor.py`
- [ ] `services/extraction/claim_linker.py`
- [ ] `services/extraction/validators.py`

## 4.5 Analysis
- [ ] `services/analysis/coverage_analyzer.py`
- [ ] `services/analysis/contradiction_analyzer.py`
- [ ] `services/analysis/matrix_builder.py`
- [ ] `schemas/gap.schema.json`

## 4.6 Writing
- [ ] `services/writing/outline_planner.py`
- [ ] `services/writing/section_writer.py`
- [ ] `services/writing/citation_grounder.py`
- [ ] `services/writing/style_rewriter.py`
- [ ] `services/bib/bib_manager.py`
- [ ] `services/latex/latex_composer.py`
- [ ] `services/latex/compiler.py`

---

## 5. 每次推进的执行规则
每次任务开始前：
1. 读取 `progress/STATUS.md`
2. 读取 `plans/NEXT_ACTIONS.md`
3. 读取 `progress/WORKLOG.md` 最新记录

每次任务结束后：
1. 更新 `progress/STATUS.md`
2. 在 `progress/WORKLOG.md` 追加一条记录
3. 重写 `plans/NEXT_ACTIONS.md`
4. 若架构有变，更新 `docs/ARCHITECTURE.md`

---

## 6. 当前建议优先级
P0：
- 项目骨架
- 状态管理
- retrieval + dedup MVP

P1：
- parsing MVP
- extraction MVP

P2：
- matrix + gap

P3：
- writing + LaTeX
