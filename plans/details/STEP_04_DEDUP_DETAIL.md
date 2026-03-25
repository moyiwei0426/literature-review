# STEP 04 - Dedup 去重与实体统一（开发细则）

更新时间：2026-03-18 16:00 CST

## 1. 目标
把 Retrieval 得到的候选论文去重并合并为主实体。

## 2. 代码文件拆解
- `services/retrieval/deduper.py`
- `services/retrieval/title_normalizer.py`
- `services/retrieval/merge_rules.py`
- `services/retrieval/provenance.py`
- `tests/test_dedup_*.py`

## 3. 直接可做的开发任务

### Task 4.1 标题标准化
文件：`services/retrieval/title_normalizer.py`

需要做：
1. 小写化
2. 去标点
3. 去多余空格
4. 去版本后缀
5. 保留 normalized_title

### Task 4.2 精确匹配规则
文件：`services/retrieval/merge_rules.py`

需要做：
1. DOI match
2. arXiv ID match
3. title 完全匹配

### Task 4.3 模糊匹配规则
文件：`services/retrieval/merge_rules.py`

需要做：
1. title 相似度阈值
2. title + first author + year 联合判断
3. 给出 merge confidence

### Task 4.4 来源信息保留
文件：`services/retrieval/provenance.py`

需要做：
1. 保存每条记录来自哪个 source
2. 保存 source_id
3. 保存原始 metadata 引用

### Task 4.5 主去重器
文件：`services/retrieval/deduper.py`

需要做：
1. 输入 candidates
2. 先跑精确规则
3. 再跑模糊规则
4. 生成 `paper_master`
5. 输出 dedup report

## 4. 建议开发顺序
1. `title_normalizer.py`
2. `merge_rules.py`
3. `provenance.py`
4. `deduper.py`
5. tests

## 5. 最小可运行版本定义
- 相同 DOI 合并
- 相同 arXiv ID 合并
- 标题近似论文能标记候选合并
- 输出去重前后数量变化

## 6. 验收样例
输入：50 篇候选论文
输出：
- 42 篇 `paper_master`
- 一份 `dedup_report.json`
- 每篇 master 记录来源列表
