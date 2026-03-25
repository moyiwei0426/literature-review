# STEP 05 - PDF 获取与 Parsing 解析（开发细则）

更新时间：2026-03-18 16:00 CST

## 1. 目标
从 `paper_master` 出发，下载 PDF、解析结构、切 chunk，为模型抽取做准备。

## 2. 代码文件拆解
- `services/parsing/pdf_fetcher.py`
- `services/parsing/grobid_adapter.py`
- `services/parsing/pymupdf_fallback.py`
- `services/parsing/section_splitter.py`
- `services/parsing/chunker.py`
- `services/parsing/quality_scorer.py`
- `services/parsing/storage.py`
- `tests/test_parsing_*.py`

## 3. 直接可做的开发任务

### Task 5.1 PDF Fetcher
需要做：
1. 读取 `pdf_url`
2. 下载 PDF
3. 校验 content-type
4. 保存到 `data/raw/pdfs/`
5. 保存下载状态

### Task 5.2 GROBID Adapter
需要做：
1. 调 GROBID 服务
2. 获取结构化 XML/TEI
3. 提取 title/abstract/body/references
4. 保留章节信息

### Task 5.3 PyMuPDF Fallback
需要做：
1. 在 GROBID 失败时抽纯文本
2. 保留页码映射
3. 输出 fallback 结构

### Task 5.4 Section Splitter
需要做：
1. 识别标准章节标题
2. 归并同义章节
3. 标记 `section_name`

### Task 5.5 Chunker
需要做：
1. 按段落切分
2. 控制 chunk 大小
3. 附带 page_start/page_end/order_index
4. 生成 chunk_id

### Task 5.6 Quality Scorer
需要做：
1. 检测是否有 abstract
2. 检测是否有 references
3. 检测文本长度是否异常
4. 计算 parse_quality_score

### Task 5.7 Storage
需要做：
1. 保存 parsed JSON
2. 保存 chunk JSON
3. 保存质量报告

## 4. 建议开发顺序
1. `pdf_fetcher.py`
2. `grobid_adapter.py`
3. `pymupdf_fallback.py`
4. `section_splitter.py`
5. `chunker.py`
6. `quality_scorer.py`
7. `storage.py`

## 5. 最小可运行版本定义
- 下载 PDF
- 至少一种方式拿到正文
- 切出 section 和 chunks
- 保存结构化结果

## 6. 验收样例
输入：10 篇 `paper_master`
输出：
- `data/raw/pdfs/*.pdf`
- `data/parsed/*.json`
- `data/generated/chunks/*.json`
- `parse_quality_report.json`
