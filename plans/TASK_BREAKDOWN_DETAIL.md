# TASK_BREAKDOWN_DETAIL — 任务拆解详情

> 源文档：plans/TASK_BREAKDOWN.md（235行，接近阈值）  
> 主文档摘要见：`../../PROJECT_DOC_CATALOG.md`  
> 详细内容见：`plans/details/STEP_*_DETAIL.md`（9个子文档）

---

## 里程碑总览

### M1：项目骨架与状态管理
**目标**：建立固定项目目录、状态文件、开发基线

**交付物**：
- [x] 目录结构建立
- [x] 项目 README
- [x] 架构文档
- [x] 状态文件与日志文件
- [x] 下一步任务队列

---

### M2：文献检索与去重
**目标**：输入 topic/query，返回结构化候选文献库

**交付物**：
- [x] OpenAlex 检索客户端
- [x] arXiv 检索客户端
- [x] Semantic Scholar 检索客户端
- [x] Crossref/Unpaywall 元数据补全
- [x] 统一候选 schema
- [x] 去重器（DOI / arXiv / 标题相似）
- [x] 检索任务 API
- [x] 文献入库

---

### M3：PDF 获取与解析
**目标**：自动下载开放 PDF，切分结构与 chunk

**交付物**：
- [x] PDF 下载器
- [x] 解析器（PyMuPDF fallback）
- [x] chunk 切分逻辑
- [x] PDF 缓存管理

---

### M4：单篇结构化提取
**目标**：从 PDF 提取 PaperProfile（研究问题/方法/发现/局限性）

**交付物**：
- [x] LLM extraction prompt
- [x] MiniMax-M2 adapter
- [x] PaperProfile schema
- [x] extraction 服务

---

### M5：Claims-Evidence 矩阵
**目标**：从多篇论文生成 claims-evidence matrix

**交付物**：
- [ ] matrix 生成服务
- [ ] claims 结构化提取
- [ ] evidence 对齐
- [ ] 冲突检测

---

### M6：Novelty / Gap 分析
**目标**：识别文献中的研究空白

**交付物**：
- [ ] gap_candidate 生成
- [ ] gap_verify 验证
- [ ] gap_score 评分
- [ ] gap 报告输出

---

### M7：综述提纲与LaTeX
**目标**：生成完整综述草稿

**交付物**：
- [x] outline 生成
- [x] section 生成
- [x] citation grounding
- [x] LaTeX 合成
- [ ] LaTeX 编译（需 MiKTeX / TeXLive）

---

### M8：Pipeline CLI + 一键运行
**目标**：一条命令覆盖全链路

**交付物**：
- [x] `python3 scripts/cli.py run-review`
- [x] `--mode local/online`
- [x] `--pdf-dir` 本地 PDF 模式
- [x] `--query` 检索模式

---

### M9：持久化与可重跑
**目标**：所有中间结果落库，可追溯

**交付物**：
- [x] PostgreSQL schema（`001_initial.sql`）
- [x] BibTeX 管理（bib_manager.py）
- [x] JSON 报告生成
- [ ] 完整测试覆盖

---

## 步骤文件索引

| 步骤 | 主文档 | 详细内容 |
|------|--------|----------|
| STEP 1: Foundation | `plans/steps/STEP_01_FOUNDATION.md` | `plans/details/STEP_01_FOUNDATION_DETAIL.md` |
| STEP 2: Schema | `plans/steps/STEP_02_SCHEMA.md` | `plans/details/STEP_02_SCHEMA_DETAIL.md` |
| STEP 3: Retrieval | `plans/steps/STEP_03_RETRIEVAL.md` | `plans/details/STEP_03_RETRIEVAL_DETAIL.md` |
| STEP 4: Dedup | `plans/steps/STEP_04_DEDUP.md` | `plans/details/STEP_04_DEDUP_DETAIL.md` |
| STEP 5: Parsing | `plans/steps/STEP_05_PARSING.md` | `plans/details/STEP_05_PARSING_DETAIL.md` |
| STEP 6: Extraction | `plans/steps/STEP_06_EXTRACTION.md` | `plans/details/STEP_06_EXTRACTION_DETAIL.md` |
| STEP 7: Analysis | `plans/steps/STEP_07_ANALYSIS.md` | `plans/details/STEP_07_ANALYSIS_DETAIL.md` |
| STEP 8: Gap | `plans/steps/STEP_08_GAP.md` | `plans/details/STEP_08_GAP_DETAIL.md` |
| STEP 9: Writing | `plans/steps/STEP_09_WRITING.md` | `plans/details/STEP_09_WRITING_DETAIL.md` |
