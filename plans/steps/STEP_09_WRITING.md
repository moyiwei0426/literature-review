# STEP 09 - Writing / BibTeX / LaTeX 输出

## 目标
基于 verified gaps 和文献矩阵生成综述提纲、章节草稿、参考文献和可编译 LaTeX。

## 输入
- verified gaps
- matrix
- paper metadata
- references / Bib 数据

## 输出
- outline
- section drafts
- `.bib`
- `.tex`
- `.pdf`

## 子任务
1. 生成综述 outline
2. 按 section 逐节写作
3. 做 citation grounding
4. 做 style rewrite 与去模板化
5. 管理 BibTeX 条目
6. 拼装 LaTeX
7. 编译 PDF
8. 检查 citation undefined / 未引用文献 / 编译错误

## 开发顺序
1. 先做 outline planner
2. 再做 section writer
3. 再做 citation grounder
4. 再做 BibTeX manager
5. 再做 LaTeX composer + compiler

## 验收标准
- 每一节都有明确输入来源
- 关键论断带 citation
- LaTeX 可编译
- 文风较学术，非空泛总结

## 常见风险
- 引用键不一致
- 文本“像论文”但缺证据
- LaTeX 构建失败

## 完成定义
- 能导出一版可审阅的综述初稿 PDF
