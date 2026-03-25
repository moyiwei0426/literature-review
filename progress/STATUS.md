# ARIS-Lit 项目状态

更新时间：2026-03-24 23:58 CST

## 当前阶段
阶段：C 版本稳定化（Phase C1 主链稳定化进行中，带动 C3/C4 收口）
状态：IN_PROGRESS

## 当前主入口
- 标准稳定入口：`scripts/run_local_review.py`
- 当前优先策略：先保主链稳定与 artifacts 可解释，不优先追求全 live 写作纯度

## 当前默认稳定策略（方向 A）
- Parsing：PyMuPDF fallback 可稳定使用
- Extraction：优先走 live LLM
- Writing：先尝试 live
- Fallback：若 live writing 产物经 validator 判定 fail，则自动切到 rule-based writing fallback
- Adoption：采用 validation 更好的那一版产物
- 结果暴露：`summary.json` 明确记录 `run_log`、`extraction_strategy`、`writing_strategy`、`validation`

## 核心链路状态
| 模块 | 状态 | 说明 |
|------|------|------|
| Retrieval | ✅ 可用 | OpenAlex + arXiv 链路已具备 |
| Dedup | ✅ 可用 | 基础去重链路已建立 |
| Parsing | ✅ 稳定 | 以 PyMuPDF fallback 为主；GROBID 仍非主稳定路径 |
| Extraction | ✅ 真实模型可用 | MiniMax-M2.5 已在本地 PDF review 场景验证 |
| Analysis | ✅ 稳定 | coverage / matrix / contradiction / synthesis_map 可稳定产出 |
| Gap | ✅ 可用 | candidate / verify / score 可跑 |
| Writing | ⚠️ 双态 | live writing 可用但不稳定；rule-based fallback 可稳定收口 |
| Validation | ✅ 关键兜底 | validator 已成为 writing fallback 触发依据 |
| Run Logging | ✅ 已落地 | `run_local_review.py` 每次运行写 `run.log` |

## 本轮稳定化已验证结果（2026-03-24）
### AAP 子集验证
- `aap_live_1paper_20260324_fallback`：✅ pass
- `aap_live_2paper_20260324_fallback`：✅ pass
- `aap_live_4paper_20260324_fallback`：✅ pass

### 已确认事实
- live extraction：可用
- live writing：会出现结构漂移，导致 validator fail
- fallback writing：能把最终结果拉回 validation pass
- 当前最务实可交付路径：**live extraction + validated fallback writing**

## 当前风险
1. live writing 本体仍不稳定，暂不能作为唯一交付路径。
2. GROBID 仍不是当前稳定主路径，PyMuPDF fallback 承担主解析职责。
3. 旧的 `progress/WORKLOG.md` / handoff 记录一度滞后，现已开始补齐本轮稳定化记录。
4. 项目根工作区 git 视角下，部分文件仍处于未正式纳管/未提交状态，不能用 commit 历史代替工作日志。

## 现在建议的查看顺序
1. `data/generated/<run>/summary.json`
2. `data/generated/<run>/run.log`
3. `data/generated/<run>/validation_report.json`
4. `plans/C_VERSION_STABILIZATION.md`
5. `progress/WORKLOG.md`

## 下一关键动作
1. 继续完成方向 A 的最终汇报收口（状态、日志、试跑口径统一）。
2. 在你确认方向 A 没问题后，再进入方向 B：专修 live writing 本体。
3. 若继续提升交接性，补充月度滚动工作日志与更统一的 run manifest。
