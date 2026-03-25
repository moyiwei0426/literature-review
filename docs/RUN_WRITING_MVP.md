# RUN WRITING MVP

## 当前最小流程
1. 准备 verified gaps 和 matrix
2. 调用 `build_outline()`
3. 调用 `write_sections()`
4. 调用 `ground_citations()`
5. 调用 `rewrite_style()`
6. 调用 `build_bib_entries()` / `prune_bib_entries()`
7. 调用 `compose_latex()` 生成 `.tex`
8. 调用 `LatexCompiler().compile()` 做最小编译检查

## 当前状态
- 已有 outline planner
- 已有 section writer
- 已有 citation grounding
- 已有 style rewriter
- 已有 bib manager
- 已有 latex composer / compiler stub
