# STEP 09 - Writing / BibTeX / LaTeX 输出（开发细则）

更新时间：2026-03-18 16:00 CST

## 1. 目标
根据 verified gaps 和结构化文献结果生成综述提纲、章节草稿、BibTeX、LaTeX 和 PDF。

## 2. 代码文件拆解
- `prompts/writing/outline_system.txt`
- `prompts/writing/section_system.txt`
- `services/writing/outline_planner.py`
- `services/writing/section_writer.py`
- `services/writing/citation_grounder.py`
- `services/writing/style_rewriter.py`
- `services/bib/bib_manager.py`
- `services/latex/latex_composer.py`
- `services/latex/compiler.py`
- `tests/test_writing_*.py`

## 3. 直接可做的开发任务

### Task 9.1 Outline Planner
需要做：
1. 根据 gaps 和 matrix 生成综述提纲
2. 为每节绑定输入文献范围

### Task 9.2 Section Writer
需要做：
1. 按 section 单独写作
2. 输入包括 claim/gap/evidence 摘要
3. 输出可审阅段落

### Task 9.3 Citation Grounder
需要做：
1. 为关键句绑定引用 key
2. 检查引用是否存在于 Bib 数据中

### Task 9.4 Style Rewriter
需要做：
1. 清理套话和 AI 痕迹
2. 强化基于证据的学术表述

### Task 9.5 Bib Manager
需要做：
1. 生成或整理 BibTeX
2. 删除未被引用条目
3. 修正 key 规范

### Task 9.6 LaTeX Composer / Compiler
需要做：
1. 拼装 `.tex`
2. 执行编译
3. 检查 citation undefined / build failure

## 4. 建议开发顺序
1. `outline_planner.py`
2. `section_writer.py`
3. `citation_grounder.py`
4. `bib_manager.py`
5. `latex_composer.py`
6. `compiler.py`
7. `style_rewriter.py`

## 5. 最小可运行版本定义
- 产出 outline
- 至少生成 2 个章节草稿
- 产出 `.bib` 和 `.tex`
- 能编译出一版 PDF

## 6. 验收样例
输入：verified gaps + paper metadata
输出：
- `outline.md`
- `draft.tex`
- `refs.bib`
- `review.pdf`
