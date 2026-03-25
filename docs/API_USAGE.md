# API USAGE

## 当前最小 API 路由
- `POST /retrieval/run`
- `POST /parsing/run`
- `POST /extraction/run`
- `POST /analysis/run`
- `POST /gap/run`
- `POST /writing/run`

## 说明
- 当前为 MVP 路由
- 结果会同时保存到 `data/repository/` 下的分类 JSON
- 便于后续接 DB repository 时平滑替换
