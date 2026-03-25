# STEP 06 - Extraction 结构化提取（开发细则）

更新时间：2026-03-18 16:00 CST

## 1. 目标
把单篇论文 chunks 转成结构化 profile、claims、evidence links。

## 2. 代码文件拆解
- `prompts/extraction/system.txt`
- `prompts/extraction/user.txt`
- `services/extraction/extractor.py`
- `services/extraction/claim_linker.py`
- `services/extraction/validators.py`
- `services/extraction/storage.py`
- `services/llm/adapter.py`
- `tests/test_extraction_*.py`

## 3. 直接可做的开发任务

### Task 6.1 LLM Adapter
需要做：
1. 统一模型调用接口
2. 支持 system/user prompt
3. 支持 JSON mode 或结构化输出
4. 记录 token、耗时、错误

### Task 6.2 Extraction Prompt
需要做：
1. 约束输出为 `paper_profile`
2. 指示抽取 research_problem / method / tasks / datasets / metrics
3. 指示提取 main claims 和 evidence chunk ids
4. 指示 limitation 分类

### Task 6.3 Extractor
需要做：
1. 读取论文 chunks
2. 组装上下文
3. 调 LLM
4. 输出 profile JSON

### Task 6.4 Validators
需要做：
1. schema 校验
2. claim 至少一个 evidence chunk
3. evidence chunk 必须存在
4. limitation 类型必须合法

### Task 6.5 Claim Linker
需要做：
1. 整理 claims
2. 建立 claim_id
3. 存储 claim-evidence links

### Task 6.6 Storage
需要做：
1. 保存 `paper_profile`
2. 保存 `claims`
3. 保存 `claim_evidence_links`
4. 保存 extraction 报告

## 4. 建议开发顺序
1. `services/llm/adapter.py`
2. prompts
3. `extractor.py`
4. `validators.py`
5. `claim_linker.py`
6. `storage.py`

## 5. 最小可运行版本定义
- 对单篇论文生成 profile JSON
- 至少提取 2~5 条 claims
- 每条 claim 绑定 evidence chunk id
- 输出通过 schema 校验

## 6. 验收样例
输入：1 篇论文 chunk 文件
输出：
- `paper_profile.json`
- `claims.json`
- `claim_evidence_links.json`
- extraction log
