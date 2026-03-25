# STEP 02 - 数据模型与 Schema 设计（开发细则）

更新时间：2026-03-18 16:00 CST

## 1. 目标
把项目的数据对象一次性定义清楚，避免后续模块返工。

## 2. 直接可做的开发任务

### Task 2.1 定义核心 JSON Schema
文件：
- `schemas/paper_candidate.schema.json`
- `schemas/paper_master.schema.json`
- `schemas/paper_file.schema.json`
- `schemas/paper_chunk.schema.json`
- `schemas/paper_profile.schema.json`
- `schemas/claim.schema.json`
- `schemas/claim_evidence_link.schema.json`
- `schemas/gap.schema.json`
- `schemas/draft.schema.json`

需要做：
1. 为每个 schema 定义 required 字段
2. 定义字段类型、枚举、是否可空
3. 给关键字段写 description
4. 为时间字段统一格式

### Task 2.2 定义 Pydantic 模型
文件：
- `core/models/paper.py`
- `core/models/chunk.py`
- `core/models/profile.py`
- `core/models/gap.py`

需要做：
1. 建立与 JSON Schema 对应的内部模型
2. 提供 schema 校验和序列化方法
3. 定义受控枚举：claim_type / limitation_type / gap_type

### Task 2.3 定义字段规范文档
文件：
- `docs/SCHEMA_SPEC.md`

需要做：
1. 解释每个对象用途
2. 解释字段含义
3. 说明哪些字段由工具填，哪些由模型填
4. 说明后续 DB 对应关系

### Task 2.4 设计数据库表草案
文件：
- `docs/DB_SCHEMA_DRAFT.md`

需要做：
1. 列出 projects / papers / chunks / claims / gaps / drafts 等表
2. 标注主键外键
3. 标明哪些字段后续可做 pgvector

## 3. 推荐开发顺序
1. `paper_candidate`
2. `paper_chunk`
3. `paper_profile`
4. `claim`
5. `gap`
6. 其他辅助对象
7. Pydantic 模型
8. DB 草案

## 4. 完成标准
- 核心 schema 文件可直接用于后续模块
- 关键枚举已定
- 内部模型与 schema 对齐
- DB 草案可指导建表
