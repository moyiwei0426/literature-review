# LOGGING

## 目标
统一日志格式，便于追踪 project 和 task。

## 当前格式
`timestamp | level | logger_name | project=<id> task=<id> | message`

## 使用方式
- 通过 `infra.app_logging.get_logger(name, project_id=..., task_id=...)` 获取 logger
- 后续 worker / API / CLI 都复用同一套日志适配器

## 当前实际落地
### `scripts/run_local_review.py`
- 每次运行会在对应输出目录落盘：`run.log`
- 与 `summary.json` / `artifacts.json` / `validation_report.json` 一起构成一次 run 的完整记录
- `summary.json` 中会显式记录：
  - `run_log`
  - `extraction_strategy`
  - `writing_strategy`
  - `validation`

### 推荐查看顺序
1. `summary.json`：先看这次 run 的整体状态与策略
2. `run.log`：看按步骤展开的运行日志
3. `validation_report.json`：看写作链具体健康度
4. 其余 artifacts：`review.md` / `sections.json` / `evidence_table.md`

## 后续增强
- JSON 日志
- trace id
- workflow run id
- API / worker 统一 run-level 文件日志
