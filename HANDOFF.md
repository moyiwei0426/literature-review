# ARIS-Lit 项目维修handoff文档
**生成时间：2026-03-22 21:35 GMT+8**
**Handoff 代理：中枢**
**目标代理：接手的维修代理**

---

## 项目路径
```
/Users/momo/.openclaw/workspace/projects/aris-lit/
```

## 项目简介
ARIS-Lit 是一个"工具优先 + 模型补强"的文献综述流水线。
- 从 OpenAlex/arXiv 检索论文，或从本地 PDF 处理
- 经过：parse → extract → analysis → gap → writing → LaTeX
- 目标用户正在开发一个关于 **行人过街行为 (pedestrian crossing behavior)** 的文献综述

---

## 当前运行状态
**正在运行：** `young-valley` session（pid 93266）
命令：`python3 scripts/cli.py run-review --mode local --pdf-dir data/manual_uploads --title "Pedestrian Crossing Behavior Review" --no-compile`

当前进度：
- 17 篇 PDF 在处理中（含 cli-demo-paper.pdf，但已设置排除逻辑）
- 最新提取到 #14_2020_wang_trf
- 正在等待 extraction + analysis + writing 完成

最新输出目录（进行中）：`data/generated/e2e_review_20260322_212437/`

最新完整输出目录（上一轮）：`data/generated/e2e_review_20260322_210919/`

---

## 已完成的修复

### Fix 1: Bib entries 作者/年份 Unknown
**文件：** `services/bib/bib_manager.py`

**问题：** `build_bib_entries()` 只从 matrix row 拿 authors/year/venue，数据全是 "Unknown" / 空 / "preprint"

**修复内容：**
- 新增 `_parse_filename_metadata(paper_id)` 函数，从文件名解析年份和作者姓氏
- 文件名格式：`{序号}_{年份}_{第一作者姓氏}_{期刊缩写}.pdf`
- 例如 `01_2001_hamed_safety_science` → year=2001, author_surname=Hamed
- 现在 bib 条目输出：`author={Hamed, [surname only]}, year={2001}`

**验证结果：** ✅ bib.tex 生成正常，year/author 有值（虽然是姓氏兜底）

---

### Fix 2: report.json 序列化报错
**文件：** `scripts/run_review.py` 中的 `_strip()` 函数

**问题：** Pipeline 最后 `print(json.dumps(report))` 时，Pydantic 对象（PaperProfile 等）无法序列化，报 `TypeError: Object of type PaperProfile is not JSON serializable`

**修复内容：**
- 强化 `_strip()` 函数，支持：
  - `model_dump()` → 递归序列化
  - `model_dump_json()` → 备选路径
  - 嵌套 list / dict 递归处理
  - Pydantic enum `.value` 提取
  - 未知类型自动转字符串，不抛异常
- **注意：** 这个问题发生在 Pipeline 最后打印 report json 时，核心输出文件（review.tex / coverage.json / sections.json 等）已正常写入，不受影响

**验证结果：** 部分生效（`_strip` 本身正确），但 report.json 仍报错，说明传入 `report["steps"]` 的 `profiles` 字段里的 Pydantic 对象还没被正确 strip

---

### Fix 3: Coverage themes = 0 / year_distribution = {}
**文件：** `services/analysis/coverage_analyzer.py`

**问题：**
- `year_distribution` 全空（PaperProfile 没有 year 字段）
- `chinese_coverage_count` 始终为 0（语言归一化没做）
- `themes` 字段根本没产出

**修复内容：**
- 新增 `_parse_year(paper_id)` 函数，从文件名解析年份
- 语言归一化：把 `English / english / en` → `english`；`Chinese / chinese / zh / 中文` → `chinese`
- 新增 `themes` 字段：直接用 `method_family` 的 key 列表
- `year_distribution` 现在有值

**验证结果：** ✅ 单测通过（mock profile 测试）

---

## 未完成的修复（待做）

### 待修 1: PaperProfile JSON 序列化未完全解决
**文件：** `scripts/run_review.py`

**问题：** `report["steps"]` 里还有 `PaperProfile` 对象，`_strip()` 虽已强化但profiles 字段没被正确处理就进了 report

**下一步：**
```python
# 在把 profiles 放入 report 之前，先转换：
profiles_serializable = _strip(profiles)
report["steps"].append({"name": "extract", "ok": ok4, "profiles": profiles_serializable, ...})
```

或者更简单：根本不把 `profiles` Pydantic 对象放进 report dict，直接删掉或只放 summary 信息。

---

### 待修 2: 从 PDF 首页提取真实元数据（高价值）
**目标：** 彻底解决 bib entries 质量（author / title / journal / year 全从 PDF 正文提取）

**涉及文件：**
- `services/extraction/extractor.py` — PaperExtractor
- `core/models/profile.py` — PaperProfile 模型缺少 year/authors/journal 字段

**方法：**
1. 在 `FallbackTextExtractor.extract()` 后，额外从首页文本里用正则/规则抽 title / authors / year / journal
2. 或者在 `PaperExtractor.extract()` 的 prompt 里补充"必须提取年份和完整作者列表"
3. 把这些字段加到 `PaperProfile` 模型

---

### 待修 3: Paper #02 / #12 / #13 extraction 报错
**问题：** 这三篇在 extraction 阶段报错，0 claims 或报错退出

**排查方向：**
- 可能是 PDF 解析出的文本过短（#05 之前只有 2 页还是报错页）
- 可能是 LLM 返回的 JSON 格式不对导致 parse 失败
- 需要单独对这 3 篇 PDF 运行 extractor 看具体报错

---

### 待修 4: Paper #05 是 ScienceDirect 报错页
**文件：** `data/manual_uploads/05_2018_deb_trf.pdf`

**问题：** 此文件不是真实论文，是 ScienceDirect 的报错页（2 页，612 字符，内容为 "There was a problem providing the content you requested"）

**解决：** 需要用户重新下载此论文的正确 PDF

---

## 关键文件路径

### Pipeline 入口
- `scripts/cli.py` — CLI 入口，新增 `--mode local/online --pdf-dir` 等参数
- `scripts/run_review.py` — 主流水线，支持 online + local 两种模式
- `scripts/run_local_review.py` — 独立本地 PDF 流水线（新增）

### 已修改的服务文件
- `services/bib/bib_manager.py` — **已修改**（Fix 1）
- `services/analysis/coverage_analyzer.py` — **已修改**（Fix 3）
- `scripts/run_review.py` — **已修改**（Fix 2 + Fix 3）

### 流水线测试数据
- PDF 目录：`data/manual_uploads/`（17 篇论文 + 1 篇 cli-demo-paper.pdf）
- 命名格式：`{序号}_{年份}_{第一作者姓氏}_{期刊缩写}.pdf`
- 最新运行输出：`data/generated/e2e_review_20260322_212437/`（进行中）
- 上一完整输出：`data/generated/e2e_review_20260322_210919/`

### 环境
- Python：3.14（homebrew 安装在 /opt/homebrew）
- 依赖：`pip install pydantic httpx fitz` 等
- LLM API：MiniMax M2.5（通过 `services/llm/adapter.py` 调用）

---

## 运行命令参考

```bash
cd /Users/momo/.openclaw/workspace/projects/aris-lit

# 本地 PDF 模式（已实现）
python3 scripts/cli.py run-review --mode local --pdf-dir data/manual_uploads --title "Pedestrian Crossing Behavior Review" --no-compile

# 线上检索模式
python3 scripts/cli.py run-review --mode online --query "pedestrian crossing behavior" --max 20 --max-pdfs 10

# 查看帮助
python3 scripts/cli.py run-review --help
```

---

## 快速验证命令

```bash
# 验证 bib_manager
python3 -c "
import sys; sys.path.insert(0, '.')
from services.bib.bib_manager import build_bib_entries
matrix = [{'paper_id': '01_2001_hamed_safety_science', 'title': 'Untitled', 'claim_text': 'test'}]
bib = build_bib_entries(matrix)
print(bib[0]['entry'])
"

# 验证 coverage_analyzer
python3 -c "
import sys; sys.path.insert(0, '.')
from services.analysis.coverage_analyzer import build_coverage_report
from core.models import PaperProfile
p = PaperProfile(paper_id='04_2014_zeng_trc', title='Test', research_problem='...', method_summary='...', method_family=['sim'], tasks=['crossing'], datasets=[], limitations=[], chunks=[], language_scope='Chinese')
print(build_coverage_report([p]))
"
```
