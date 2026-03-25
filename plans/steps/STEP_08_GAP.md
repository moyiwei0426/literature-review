# STEP 08 - Novelty / Gap 分析

## 目标
基于矩阵、覆盖统计、冲突分析，生成有证据支撑的研究空白和综述价值点。

## 输入
- claims-evidence matrix
- coverage report
- contradiction report

## 输出
- candidate gaps
- critic 审查结果
- verifier 复核结果
- 最终 gap report

## 子任务
1. 生成 candidate gaps
2. 对每个 gap 绑定支持证据
3. 搜集潜在反证据
4. 运行 critic agent 做“刻薄审稿人”审查
5. 运行 verifier 纠偏
6. 为 gap 打分：confidence / novelty value / review worthiness
7. 导出 gap report

## 开发顺序
1. 先生成候选 gap
2. 再做证据与反证据绑定
3. 再做 critic
4. 再做 verifier
5. 最后排序与导出

## 验收标准
- gap 不是空话，而是证据驱动
- 能区分“研究较少”和“尚无系统总结”
- 可直接进入综述引言或 future work

## 常见风险
- 检索不全导致假 gap
- 模型把套话包装成创新点
- 只列支持证据，不看反例

## 完成定义
- 产出一份可信的研究空白点清单
