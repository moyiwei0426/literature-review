# STEP 02 - 数据模型与 Schema 设计

## 目标
定义后续所有模块共享的数据对象，避免 Retrieval、Parsing、Extraction 各自输出不同格式。

## 输入
- 项目目标与总体架构
- 需要支撑的主要产物：paper candidate / chunk / profile / claim / gap / draft

## 输出
- JSON Schema 文件
- 数据对象说明
- 后续数据库表设计草案

## 子任务
1. 定义 `paper_candidate`
2. 定义 `paper_master`
3. 定义 `paper_file`
4. 定义 `paper_chunk`
5. 定义 `paper_profile`
6. 定义 `claim`
7. 定义 `claim_evidence_link`
8. 定义 `gap`
9. 定义 `draft`
10. 约定字段枚举、受控词表、可空字段

## 开发顺序
1. 先定义 Retrieval 相关对象
2. 再定义 Parsing 相关对象
3. 再定义 Extraction/Analysis 对象
4. 最后定义 Writing 对象

## 验收标准
- 模型输出能被 schema 校验
- 工具输出能稳定入库
- 多模块之间字段含义一致

## 常见风险
- 字段命名前后不一致
- 受控词表缺失导致统计困难
- schema 太松，无法约束模型输出

## 完成定义
- 核心 schema 文件全部落地并可用于校验
