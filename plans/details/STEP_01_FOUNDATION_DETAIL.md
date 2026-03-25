# STEP 01 - 基础设施与项目规范（开发细则）

更新时间：2026-03-18 16:00 CST

## 1. 目标
把项目从“文档规划”推进到“可持续开发环境”，让后续每个模块都知道：代码放哪里、配置怎么读、状态怎么更新、运行方式是什么。

## 2. 直接可做的开发任务

### Task 1.1 建立运行配置骨架
文件：
- `infra/settings.py`
- `.env.example`
- `docs/ENVIRONMENT.md`

需要做：
1. 定义 `AppSettings`：
   - app_name
   - env
   - log_level
   - data_dir
   - postgres_url
   - redis_url
   - openalex_base_url
   - arxiv_base_url
   - semanticscholar_base_url
   - crossref_base_url
   - unpaywall_base_url
   - llm_provider
   - llm_model
2. 支持从环境变量读取
3. 约定 `.env` 中的 key 命名
4. 输出 `.env.example`

验收：
- 运行一个简单脚本可打印当前 settings
- 缺少关键配置时报错清晰

### Task 1.2 建立日志规范
文件：
- `infra/logging.py`
- `docs/LOGGING.md`

需要做：
1. 定义统一 logger
2. 支持模块名、任务 id、project id
3. 日志级别：INFO/WARN/ERROR/DEBUG
4. 日志格式统一
5. 预留写文件能力

验收：
- 任意模块导入 logger 可输出统一格式日志

### Task 1.3 建立最小 API 骨架
文件：
- `api/main.py`
- `api/routes/health.py`
- `api/routes/projects.py`

需要做：
1. 提供 `/health`
2. 提供 `/projects` 占位接口
3. 提供应用启动入口
4. 输出 API 基础文档

验收：
- 服务可启动
- `/health` 返回 200

### Task 1.4 建立最小 CLI 骨架
文件：
- `scripts/cli.py`

需要做：
1. 支持 `init-project`
2. 支持 `show-status`
3. 支持 `run-retrieval --query ...` 占位命令

验收：
- CLI 可以正常打印帮助信息

### Task 1.5 固化进度更新规则
文件：
- `progress/STATUS.md`
- `progress/WORKLOG.md`
- `plans/NEXT_ACTIONS.md`
- `docs/PROJECT_OPERATIONS.md`

需要做：
1. 统一“开始前读取、结束后更新”流程
2. 规定每次开发更新格式
3. 规定下一步动作只保留最关键 3~5 项

验收：
- 任意后续任务都能按此规范追加记录

## 3. 推荐开发顺序
1. `infra/settings.py`
2. `.env.example`
3. `infra/logging.py`
4. `api/main.py`
5. `scripts/cli.py`
6. `docs/ENVIRONMENT.md` / `docs/PROJECT_OPERATIONS.md`

## 4. 完成标准
- API 和 CLI 至少有一个可启动入口
- settings 与 logging 可复用
- 开发规范文件明确
- 项目可以正式进入模块开发
