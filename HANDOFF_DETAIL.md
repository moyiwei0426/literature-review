# HANDOFF_DETAIL — 项目维修交接详情

> 源文档：projects/aris-lit/HANDOFF.md（202行，贴线）  
> 主文档摘要见：`../../PROJECT_DOC_CATALOG.md`  
> 此文档为维修交接专用，按需生成，非持续维护

---

## 项目基本信息

**路径**：`/Users/momo/.openclaw/workspace/projects/aris-lit/`

**当前运行 session**：`young-valley`（pid 93266）

**运行命令**：
```bash
python3 scripts/cli.py run-review --mode local --pdf-dir data/manual_uploads \
  --title "Pedestrian Crossing Behavior Review" --no-compile
```

**最新输出目录**（进行中）：`data/generated/e2e_review_20260322_212437/`  
**最新完整输出目录**：`data/generated/e2e_review_20260322_210919/`

---

## 已完成的修复

### Fix 1：Bib entries 作者/年份 Unknown
**文件**：`services/bib/bib_manager.py`

**修复**：新增 `_parse_filename_metadata(paper_id)` 函数，从文件名解析年份和作者姓氏  
**文件名格式**：`{序号}_{年份}_{第一作者姓氏}_{期刊缩写}.pdf`  
**验证**：✅ bib.tex 生成正常

---

### Fix 2：report.json 序列化报错
**文件**：`scripts/run_review.py` 中的 `_strip()` 函数

**问题**：PaperProfile 等 Pydantic 对象无法直接 JSON 序列化

**修复**：强化 `_strip()` 函数，支持 `model_dump()` 递归序列化  
**状态**：部分生效，`report.json` 仍报错（profiles 字段未完全 strip）

---

### Fix 3：Coverage themes = 0 / year_distribution = {}
**文件**：`services/analysis/coverage_analyzer.py`

**修复**：
- 新增 `_parse_year(paper_id)` 函数
- 语言归一化（English/Chinese 大小写归一）
- `themes` 字段改用 `method_family` 的 key 列表

**验证**：✅ 单测通过

---

## 未完成的修复

### 待修 1：PaperProfile JSON 序列化未完全解决
**下一步**：
```python
profiles_serializable = _strip(profiles)
report["steps"].append({..., "profiles": profiles_serializable})
```
或：根本不把 profiles Pydantic 对象放进 report dict

---

### 待修 2：从 PDF 首页提取真实元数据
**涉及**：
- `services/extraction/extractor.py` — PaperExtractor
- `core/models/profile.py` — PaperProfile 模型缺少 year/authors/journal 字段

**方法**：FallbackTextExtractor 后用正则抽 title/authors/year/journal

---

### 待修 3：Paper #02/#12/#13 extraction 报错
**排查方向**：PDF 解析文本过短 / LLM 返回 JSON 格式错误  
**方法**：单独对这 3 篇 PDF 运行 extractor 看具体报错

---

### 待修 4：Paper #05 是 ScienceDirect 报错页
**文件**：`data/manual_uploads/05_2018_deb_trf.pdf`（612字符，内容为报错页）  
**解决**：需用户重新下载此论文正确 PDF

---

## 快速验证命令

```bash
# 验证 bib_manager
python3 -c "
import sys; sys.path.insert(0, '.')
from services.bib.bib_manager import build_bib_entries
matrix = [{'paper_id': '01_2001_hamed_safety_science', 'title': 'Test', 'claim_text': 'test'}]
bib = build_bib_entries(matrix)
print(bib[0]['entry'])
"

# 验证 coverage_analyzer
python3 -c "
import sys; sys.path.insert(0, '.')
from services.analysis.coverage_analyzer import build_coverage_report
from core.models import PaperProfile
p = PaperProfile(paper_id='test', title='Test', research_problem='...',
  method_summary='...', method_family=['sim'], tasks=['crossing'],
  datasets=[], limitations=[], chunks=[], language_scope='Chinese')
print(build_coverage_report([p]))
"
```
