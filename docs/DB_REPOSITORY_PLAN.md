# DB REPOSITORY PLAN

## 当前状态
已新增两层 repository：
1. `FileRepository`：文件型过渡持久化
2. `SQLiteRepository`：本地 SQLite 过渡数据库

## 设计意图
- 上层路由/服务先依赖 repository 抽象，而不是具体 DB
- 后续切 PostgreSQL 时，可新增 `PostgresRepository`，尽量不改上层调用方式

## 当前已落地
- `storage/repositories/base.py`
- `storage/repositories/file_repository.py`
- `storage/repositories/sqlite_repository.py`
- `storage/repositories/sql/schema.sql`
- `scripts/db/init_sqlite.py`

## 当前已补充的实体级 repository
- `ProjectsRepository`
- `PapersRepository`
- `ChunksRepository`
- `ProfilesRepository`
- `GapsRepository`
- `DraftsRepository`

## 当前已补充的查询/CRUD 能力
在 SQLite 过渡层上，实体 repository 已支持：
- `save`
- `get`
- `get_latest`
- `list_ids`
- `list_records`
- `exists`
- `delete`

## 已补充的业务查询能力
- `ProfilesRepository.find_by_paper_id()`
- `ProfilesRepository.find_by_domain()`
- `DraftsRepository.find_by_title()`
- `DraftsRepository.find_with_compile_status()`
- `DraftsRepository.find_by_version()`
- `GapsRepository.find_verified()`
- `GapsRepository.find_scored_above()`
- `PapersRepository.find_by_year()`
- `PapersRepository.find_by_venue()`
- `PapersRepository.find_by_doi()`
- `PapersRepository.find_by_arxiv_id()`
- `ChunksRepository.find_by_paper_id()`
- `ChunksRepository.find_by_section()`
- `ProjectsRepository.find_by_status()`
- `ProjectsRepository.find_by_topic()`

## 下一步
- 从当前 payload 存储继续过渡到实体级 CRUD 字段映射
- 为更多实体增加按 project_id / paper_id 的过滤能力
- 再切到 PostgreSQL / migration 工具链
