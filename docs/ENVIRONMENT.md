# ENVIRONMENT

## 目标
定义 ARIS-Lit 的基础环境变量与本地开发配置。

## 核心变量
- `APP_NAME`
- `ENV`
- `LOG_LEVEL`
- `DATA_DIR`
- `POSTGRES_URL`
- `REDIS_URL`
- `OPENALEX_BASE_URL`
- `ARXIV_BASE_URL`
- `SEMANTICSCHOLAR_BASE_URL`
- `CROSSREF_BASE_URL`
- `UNPAYWALL_BASE_URL`
- `LLM_PROVIDER`
- `LLM_MODEL`

## 使用方式
1. 复制 `.env.example` 为 `.env`
2. 根据本地环境修改数据库、缓存、模型配置
3. 运行 `python infra/settings.py` 检查是否能成功读取配置
