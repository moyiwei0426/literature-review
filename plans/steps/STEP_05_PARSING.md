# STEP 05 - PDF 获取与 Parsing 解析

## 目标
获取论文全文 PDF，并将其解析为章节化、可追溯的 chunk 数据。

## 输入
- `paper_master`
- PDF URL / open access 链接 / 用户上传文件

## 输出
- 原始 PDF 文件
- 结构化章节文本
- 带页码和 section 的 chunk 列表
- parse quality score

## 子任务
1. 实现 PDF 下载器
2. 保存原始 PDF
3. 使用 GROBID 做主解析
4. 使用 PyMuPDF 做 fallback
5. 识别 abstract/introduction/method/experiment/conclusion 等 section
6. 按段落或语义块切 chunk
7. 保留 page_start/page_end/order_index
8. 计算 parse quality score

## 开发顺序
1. 先做 PDF 获取
2. 再接 GROBID
3. 再做 fallback
4. 再做 section splitter 和 chunker
5. 最后做质量评分

## 验收标准
- 大部分论文可成功拿到 PDF
- 解析结果可供模型直接使用
- chunk 能回溯到页码和 section

## 常见风险
- 双栏论文错乱
- 表格公式干扰抽取
- references 混入正文

## 完成定义
- 对一批论文可稳定生成可用 chunk 数据
