# STEP 03 - Retrieval 检索系统

## 目标
给定研究主题或查询词，从多个学术来源召回候选论文，并统一为标准格式。

## 输入
- topic / query
- 检索参数（年份、语言、来源、数量）

## 输出
- 原始检索结果
- 统一格式的候选文献列表
- 多源检索日志

## 子任务
1. 接入 OpenAlex client
2. 接入 arXiv client
3. 接入 Semantic Scholar client
4. 接入 Crossref / Unpaywall 做补全
5. 编写 retrieval aggregator
6. 定义 query 参数结构
7. 保存原始返回与标准化结果
8. 支持关键词检索、种子论文扩展、综述反向扩展

## 开发顺序
1. 先做 OpenAlex
2. 再做 arXiv
3. 再做 aggregator
4. 再补充其他来源与扩展策略

## 验收标准
- 对一个 topic 能稳定返回 30~100 篇候选
- 统一输出 schema
- 原始结果和标准结果都可保存

## 常见风险
- 数据源字段不一致
- query 过宽噪声太大
- query 过窄召回不足

## 完成定义
- 至少两个来源可用，且有统一候选输出
