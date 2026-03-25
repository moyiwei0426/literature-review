# STEP 06 - Extraction 结构化提取

## 目标
让模型基于单篇论文 chunks，输出受约束的结构化画像、claims 与 evidence 绑定。

## 输入
- 论文 metadata
- 章节文本 / chunk 列表
- 受约束 schema

## 输出
- `paper_profile`
- `claims`
- `claim_evidence_links`
- `limitations`

## 子任务
1. 定义 extraction prompt
2. 搭建统一 LLM adapter
3. 让模型输出 JSON 而不是自由文本
4. 进行 schema 校验
5. 抽取 research problem / method / datasets / metrics
6. 抽取 main claims
7. 为每个 claim 绑定 evidence chunk IDs
8. 区分 explicit limitation 与 inferred limitation
9. 保存 profile 和链接结果

## 开发顺序
1. 先打通单篇论文 profile 抽取
2. 再加 claims 提取
3. 再加 evidence linking
4. 最后做 limitation 分类和校验

## 验收标准
- 结构化输出完整率高
- 每个关键 claim 都有证据
- 输出可被后续 analysis 直接使用

## 常见风险
- 模型幻觉 claim
- evidence 绑定错 chunk
- limitation 过度脑补

## 完成定义
- 单篇论文可以稳定产出 profile + claims + evidence links
