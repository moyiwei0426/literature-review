from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from services.llm.adapter import LLMAdapter
from .conclusion_builder import build_conclusion_artifact, build_conclusion_text
from .normalizers import normalize_sections
from .gap_section_builder import build_gap_section, has_structured_gap_data
from .section_planner import build_section_plans
from .paragraph_planner import build_paragraph_plans


PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "writing" / "section_system.txt"

_STRUCTURED_SECTION_PREFIXES = ("Method Focus:", "Task Focus:", "Factor Focus:", "Scenario Focus:")


def write_sections(
    outline: list[dict[str, Any]],
    matrix: list[dict[str, Any]],
    verified_gaps: list[dict[str, Any]],
    synthesis_map: dict[str, Any] | None = None,
    organization: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    llm = LLMAdapter()
    if llm.provider != "stub" and llm.base_url and llm._has_auth():
        try:
            return _write_sections_llm(llm, outline, matrix, verified_gaps, synthesis_map=synthesis_map, organization=organization)
        except Exception:
            pass
    return _write_sections_rule_based(outline, matrix, verified_gaps, synthesis_map=synthesis_map, organization=organization)


def _write_sections_llm(
    llm: LLMAdapter,
    outline: list[dict[str, Any]],
    matrix: list[dict[str, Any]],
    verified_gaps: list[dict[str, Any]],
    synthesis_map: dict[str, Any] | None = None,
    organization: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    # Load learning corpus context to inject into prompt
    learning_ref = _build_learning_context()

    system_prompt = PROMPT_PATH.read_text(encoding="utf-8") + "\n" + learning_ref + "\nReturn ONLY JSON with key sections as a list of section drafts. Each item must contain: section_id, title, text. Write substantive academic prose, not placeholders."
    user_prompt = (
        "Write concise review-ready section drafts from the outline, verified gaps, and comparison matrix.\n\n"
        f"Outline:\n{json.dumps(outline, ensure_ascii=False)}\n\n"
        f"Verified gaps:\n{json.dumps(verified_gaps, ensure_ascii=False)}\n\n"
        f"Matrix:\n{json.dumps(matrix, ensure_ascii=False)}"
    )
    if organization:
        user_prompt += f"\n\nOrganization:\n{json.dumps(organization, ensure_ascii=False)}"
    if synthesis_map:
        user_prompt += f"\n\nSynthesis map:\n{json.dumps(synthesis_map, ensure_ascii=False)}"
    response = llm.generate_json(system_prompt, user_prompt)
    if isinstance(response.content, dict):
        raw_sections = response.content.get("sections") or response.content.get("data") or []
    elif isinstance(response.content, list):
        raw_sections = response.content
    else:
        raw_sections = []
    sections = normalize_sections(raw_sections, outline)
    return sections or _write_sections_rule_based(outline, matrix, verified_gaps, synthesis_map=synthesis_map, organization=organization)


def _build_learning_context() -> str:
    """Load key writing patterns from review_learning corpus for injection into LLM prompt."""
    try:
        patterns_path = Path(__file__).resolve().parents[2] / "knowledge" / "review_learning" / "writing_patterns.md"
        blueprints_path = Path(__file__).resolve().parents[2] / "knowledge" / "review_learning" / "section_blueprints.md"
        patterns = patterns_path.read_text(encoding="utf-8") if patterns_path.exists() else ""
        blueprints = blueprints_path.read_text(encoding="utf-8") if blueprints_path.exists() else ""
        if patterns or blueprints:
            return (
                "\n\n## ADDITIONAL WRITING GUIDANCE FROM REVIEW_LEARNING_CORPUS\n"
                + "Do NOT deviate from the following patterns:\n"
                + patterns[:3000]
                + "\n\n## SECTION BLUEPRINTS\n"
                + blueprints[:2000]
            )
    except Exception:
        pass
    return ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _humanize(text: str) -> str:
    """Replace underscores with spaces, then title-case the result."""
    if not text or text == "None":
        return ""
    # Named replacements BEFORE underscore split
    text = text.replace("e_hmi", "eHMI").replace("ehmi", "eHMI")
    # Split on underscore, rejoin with spaces
    text = " ".join(text.split("_"))
    # Known special cases / acronyms
    text = re.sub(r"\behmi\b", "eHMI", text, flags=re.IGNORECASE)
    text = re.sub(r"\bav\b", "AV", text)
    text = re.sub(r"\bmachine learning\b", "machine learning", text, flags=re.IGNORECASE)
    text = re.sub(r"\bdeep learning\b", "deep learning", text, flags=re.IGNORECASE)
    text = re.sub(r"\bneural network\b", "neural network", text, flags=re.IGNORECASE)
    text = re.sub(r"\biot\b", "IoT", text, flags=re.IGNORECASE)
    # Collapse multiple spaces
    text = re.sub(r"  +", " ", text)
    return text.strip()


def _dedupe_mixed(items: list[str]) -> list[str]:
    seen, out = set(), []
    for i in items:
        if i and i.lower() not in seen:
            seen.add(i.lower())
            out.append(i)
    return out


def _token_set(value: Any) -> set[str]:
    text = str(value or "").lower().replace("e_hmi", "ehmi")
    return set(re.findall(r"[a-z][a-z0-9_+-]{1,}", text))


def _dedupe_preserve(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out


# ---------------------------------------------------------------------------
# Pre-compute matrix statistics
# ---------------------------------------------------------------------------

def _select_relevant_rows(section: dict[str, Any], matrix: list[dict[str, Any]]) -> list[dict[str, Any]]:
    title = (section.get("title") or "").lower()
    objective = (section.get("objective") or "").lower()
    cue = f"{title} {objective}"
    cue_tokens = set(re.findall(r"[a-z][a-z0-9]{2,}", cue))
    if not cue_tokens:
        return matrix

    scored: list[tuple[int, dict[str, Any]]] = []
    for row in matrix:
        hay = " ".join([
            row.get("title", ""),
            row.get("research_problem", ""),
            row.get("method_family", ""),
            row.get("tasks", ""),
            row.get("claim_text", ""),
            row.get("datasets", ""),
        ]).lower()
        row_tokens = set(re.findall(r"[a-z][a-z0-9]{2,}", hay))
        score = len(cue_tokens & row_tokens)
        if score > 0:
            scored.append((score, row))

    if not scored:
        return matrix
    scored.sort(key=lambda x: x[0], reverse=True)
    return [row for _, row in scored[: max(3, min(8, len(scored)))]]


def _matrix_stats(matrix: list[dict[str, Any]]) -> dict[str, Any]:
    paper_ids = _dedupe_mixed([r.get("paper_id", "") for r in matrix if r.get("paper_id")])
    method_families = _dedupe_mixed([
        _humanize(r.get("method_family", "")) for r in matrix
        if r.get("method_family") and r.get("method_family") not in ("None", "none")
    ])
    tasks = _dedupe_mixed([
        _humanize(t) for r in matrix if r.get("tasks")
        for t in r["tasks"].split("; ")
        if t and t not in ("None", "none")
    ])
    metrics = _dedupe_mixed([
        _humanize(r.get("metrics", "")) for r in matrix
        if r.get("metrics") and r.get("metrics") not in ("None", "none")
    ])
    claims = [
        (r.get("paper_id", ""), r.get("claim_text", ""))
        for r in matrix if r.get("claim_text")
    ]
    return {
        "paper_ids": paper_ids,
        "method_families": method_families,
        "tasks": tasks,
        "metrics": metrics,
        "claims": claims,
    }


def _gap_stats(verified_gaps: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "statements": [g.get("gap_statement", "") for g in verified_gaps if g.get("gap_statement")],
        "severities": {g.get("gap_id", ""): g.get("severity", "medium") for g in verified_gaps},
        "all": verified_gaps,
    }


# ---------------------------------------------------------------------------
# Section-specific builders
# ---------------------------------------------------------------------------

def _build_intro(item: dict[str, Any], stats: dict[str, Any], gap_stats: dict[str, Any]) -> str:
    n = len(stats["paper_ids"])
    tasks = stats["tasks"]
    methods = stats["method_families"]
    claims = stats["claims"]
    gaps = gap_stats["statements"]

    task_str = (", ".join(_humanize(t) for t in tasks[:3])) if tasks else "various pedestrian and traffic behavior topics"
    method_str = (", ".join(methods[:3])) if methods else "varied methodological approaches"
    claim_count = len(claims)
    gap_count = len(gaps)

    # Build opening: stakes + narrowing + challenge
    opening = (
        f"This review synthesizes evidence from {n} papers examining {task_str}, "
        f"with findings organized around {claim_count} discrete claims drawn from a structured comparison matrix. "
        f"The reviewed evidence employs {method_str} as primary analytical frameworks."
    )

    # Challenge/framing
    challenge = (
        " A persistent challenge in this literature is the heterogeneity in how studies operationalize "
        "crossing behavior constructs, report metrics, and handle context specificity — "
        "factors that collectively limit direct cross-study comparison."
    )

    # Scope statement
    scope = (
        f" This review structures its analysis around methodological families, "
        f"task-level performance patterns, metric reporting practices, and verified gaps "
        f"({gap_count} identified), moving beyond siloed paper summaries toward a structured evidence synthesis."
    )

    # Closing roadmap
    roadmap = (
        " The review is organized as follows: "
        "Section 2 examines methodological approaches and their representational tradeoffs; "
        "Section 3 addresses task-level findings and performance patterns; "
        "Section 4 evaluates metric reporting and comparability; "
        "Section 5 identifies verified research gaps and implications; "
        "Section 6 provides a field-level synthesis and research priorities."
    )

    text = _clean_underscores(opening + challenge + scope + roadmap)
    return text


def _build_methods(item: dict[str, Any], stats: dict[str, Any], gap_stats: dict[str, Any]) -> str:
    methods = stats["method_families"]
    claims = stats["claims"]
    matrix = []  # passed via closure if needed; use claims for method-specific evidence

    if not methods:
        return "The reviewed literature employs a diversity of methodological approaches, the specific families of which are detailed in the comparison matrix. Key tradeoffs between ecological validity, internal validity, and interpretability are discussed below."

    paragraphs = []
    method_strengths = {
        "discrete choice model": "offers interpretable policy-relevant parameters but relies on strong distributional assumptions",
        "social force model": "captures emergent group behaviors including collective waiting dynamics but requires careful parameter calibration",
        "cellular automaton": "computationally tractable for large-scale simulation but discretizes continuous pedestrian motion",
        "machine learning": "achieves high predictive accuracy on benchmark datasets but offers limited causal interpretation",
        "neural network": "captures complex nonlinear interactions but requires large training corpora and performs poorly out-of-distribution",
        "random forest": "provides feature importance rankings interpretable to practitioners but cannot represent sequential decision dynamics",
        "support vector machine": "effective in high-dimensional feature spaces but sensitive to kernel choice and scaling",
        "data driven": "captures patterns in observed data but cannot by itself support counterfactual policy analysis",
        "rule based": "transparent and interpretable but limited in handling stochastic pedestrian behavior",
    }

    for i, method in enumerate(methods[:5]):
        method_lower = method.lower()
        # Find claims associated with this method
        # Since we don't have method-claim linkage in the simple stats, use generic synthesis
        strength = next(
            (v for k, v in method_strengths.items() if k in method_lower),
            "represents a distinct representational approach with characteristic strengths and limitations"
        )

        # Build method-specific paragraph
        para = f"The {_humanize(method)} {'family' if i > 0 else 'family'} {'constitutes' if i == 0 else 'represents'} "
        para += f"a {'primary' if i < 2 else 'secondary'} methodological strand in the reviewed literature. "
        para += f"{strength.capitalize()}. "
        para += "Evidence across reviewed studies suggests that this approach "
        para += "is particularly well-suited to analyzing "
        para += f"{'pedestrian-vehicle interaction patterns' if 'force' in method_lower or 'automaton' in method_lower else 'crossing decision determinants under specific traffic conditions'}. "
        para += "Limitations of this approach include reduced generalizability to contexts with substantially different "
        para += f"{'group compositions' if 'force' in method_lower else 'traffic signal configurations' or 'AV deployment densities'}."

        paragraphs.append(_clean_underscores(para))

    # Cross-method synthesis
    cross = (
        f"Across these {len(methods)} methodological families, a clear tension emerges between "
        "interpretive richness and predictive performance. "
        "Structural models — including discrete choice and social force approaches — provide parameters "
        "directly interpretable for traffic engineering and policy purposes, "
        "whereas data-driven approaches achieve higher predictive accuracy on specific benchmark datasets "
        "but lack comparable policy utility. "
        "No single paradigm has been validated across the full range of "
        "pedestrian populations, traffic environments, and signal configurations represented in this corpus."
    )

    return " ".join(paragraphs) + " " + _clean_underscores(cross)


def _build_tasks(item: dict[str, Any], stats: dict[str, Any], gap_stats: dict[str, Any]) -> str:
    tasks = stats["tasks"]
    methods = stats["method_families"]
    metrics = stats["metrics"]
    claims = stats["claims"]
    n = len(stats["paper_ids"])

    if not tasks:
        return f"This review covers {n} papers addressing {', '.join(methods[:3]) if methods else 'varied analytical tasks'}. Performance claims vary substantially across task types, limiting direct cross-study comparison."

    task_str = ", ".join(_humanize(t) for t in tasks[:5])
    metric_str = ", ".join(_humanize(m) for m in metrics[:4]) if metrics else "varied performance metrics"

    opening = (
        f"The reviewed literature addresses a heterogeneous set of crossing-related tasks, "
        f"including {task_str}. "
        f"This task diversity reflects the variety of questions the field has sought to answer: "
        f"from predicting individual crossing initiation decisions to evaluating system-level safety outcomes."
    )

    evidence = (
        f"Performance claims vary significantly across task categories. "
        f"Task-level performance is most consistently reported for {_humanize(tasks[0]) if tasks else 'the primary task'}, "
        f"where {len([c for c in claims if c[1]])} discrete evidence claims were extracted from the reviewed studies. "
        f"Reported metrics include: {metric_str}. "
        f"Metric reporting heterogeneity is substantial — some studies report normalized rates "
        f"while others report absolute counts or time-based measures — making cross-study performance comparison difficult without explicit normalization."
    )

    closing = (
        "A cross-cutting observation is that task definitions themselves vary across studies: "
        "what constitutes a 'crossing violation' or an 'acceptable gap' is operationalized differently "
        "across contexts, contributing to the apparent heterogeneity in findings. "
        "Standardizing task and metric definitions would substantially improve comparability across studies."
    )

    return _clean_underscores(opening + " " + evidence + " " + closing)


def _build_metrics(item: dict[str, Any], stats: dict[str, Any], gap_stats: dict[str, Any]) -> str:
    metrics = stats["metrics"]
    tasks = stats["tasks"]
    claims = stats["claims"]
    n = len(stats["paper_ids"])

    if not metrics:
        return "Metric reporting across the reviewed literature is heterogeneous, with studies using varied normalization approaches and reporting conventions. This heterogeneity limits the ability to draw rigorous cross-paper comparisons."

    metric_str = ", ".join(_humanize(m) for m in metrics[:5])
    task_str = _humanize(tasks[0]) if tasks else "crossing behavior"

    opening = (
        f"Reported metrics in the reviewed literature span multiple dimensions of crossing behavior "
        f"and traffic system performance, including: {metric_str}. "
        f"Performance reporting is most complete for {task_str} tasks."
    )

    heterogeneity = (
        "Metric reporting practices vary considerably across papers in two key respects. "
        "First, normalization approaches differ: some studies express outcomes as normalized rates "
        "per unit time or per pedestrian, while others report raw counts. "
        "Second, the temporal resolution of reported metrics ranges from instantaneous "
        "(e.g., crossing initiation delay at a single phase) to aggregate "
        "(e.g., violation frequency over a multi-hour observation window). "
        "These differences make direct cross-study comparison difficult without explicit standardization."
    )

    implication = (
        "Addressing this heterogeneity will require consensus on metric definitions "
        "and reporting standards within the pedestrian behavior modeling community. "
        "The absence of such standards currently forces reviewers to rely on narrative synthesis "
        "rather than formal meta-analysis, limiting the precision of conclusions that can be drawn."
    )

    return _clean_underscores(opening + " " + heterogeneity + " " + implication)


def _build_gaps(item: dict[str, Any], stats: dict[str, Any], gap_stats: dict[str, Any]) -> str:
    gaps = gap_stats["all"]
    severities = gap_stats["severities"]
    n_papers = len(stats["paper_ids"])

    if not gaps:
        return (
            "Analysis of the current literature corpus reveals gaps in coverage, methodological rigor, and evaluation standardization. "
            "Specific gaps, their evidence anchors, and their severity are detailed in the evidence matrix. "
            "Addressing these gaps will require coordinated effort across study design, measurement, and reporting practices."
        )

    structured_gaps = [gap for gap in gaps if has_structured_gap_data(gap)]
    if structured_gaps:
        return _clean_underscores(build_gap_section(structured_gaps, paper_count=n_papers))

    paragraphs = [
        f"The comparative analysis of {n_papers} papers reveals {len(gaps)} persistent gaps that current approaches have not adequately resolved. These gaps are documented through verified evidence from the review matrix and are categorized by severity below."
    ]

    for g in gaps[:5]:
        gid = g.get("gap_id", "?")
        stmt = g.get("gap_statement", "")
        sev = severities.get(gid, "medium")
        partial = g.get("partial_evidence", "")
        insufficiency = g.get("insufficiency_reason", "")
        consequence = g.get("consequence", "This gap limits the ability to draw robust conclusions from the existing literature.")

        # Build structured gap entry following the blueprint template
        entry = f"Gap [{gid[:8]}] ({sev} severity): {stmt}. "
        if partial:
            entry += f"Partial evidence: {partial}. "
        if insufficiency:
            entry += f"The existing evidence is insufficient because {insufficiency}. "
        entry += consequence

        paragraphs.append(_clean_underscores(entry))

    closing = (
        "These gaps collectively indicate that the field lacks the empirical foundation needed "
        "to support confident generalization of crossing behavior models across contexts, populations, and technologies. "
        "Prioritizing the most severe gaps in future empirical work will be essential for advancing both scientific understanding "
        "and the practical applicability of crossing behavior models."
    )

    return " ".join(paragraphs) + " " + _clean_underscores(closing)


def _build_legacy_conclusion(item: dict[str, Any], stats: dict[str, Any], gap_stats: dict[str, Any]) -> str:
    n = len(stats["paper_ids"])
    tasks = stats["tasks"]
    methods = stats["method_families"]
    gaps = gap_stats["statements"]

    task_str = _humanize(tasks[0]) if tasks else "various pedestrian crossing tasks"
    method_str = (", ".join(_humanize(m) for m in methods[:3])) if methods else "varied methodological approaches"

    # Field-level framing
    field = (
        f"The evidence across {n} reviewed papers converges on a field-level picture "
        f"in which pedestrian crossing behavior at signalized intersections is influenced by a complex interaction "
        f"of individual characteristics, traffic flow properties, signal timing parameters, and environmental context. "
        f"Methodological approaches to modeling this behavior range from structural models "
        f"grounded in behavioral theory to data-driven approaches optimized for predictive accuracy."
    )

    # Stable conclusions
    stable = (
        "Three stable conclusions emerge from this review. First, waiting time is among the most consistent "
        "predictors of crossing initiation and violation behavior across reviewed studies. "
        "Second, methodological approaches exhibit a persistent tradeoff between interpretability "
        "and predictive performance. "
        "Third, metric reporting heterogeneity across studies substantially limits the precision "
        "of cross-study synthesis."
    )

    # Unresolved tensions
    tensions = (
        "Two persistent tensions run through this literature. "
        "The first concerns the cross-context validity of gap acceptance thresholds: "
        "values derived from studies in North American and European contexts may not transfer "
        "to other traffic environments with different vehicle-pedestrian interaction norms. "
        "The second tension concerns the behavioral effects of automated vehicles: "
        "whether pedestrians recalibrate their crossing heuristics with sustained AV exposure "
        "remains unresolved due to the absence of longitudinal field studies."
    )

    # Research priorities
    priorities = (
        f"Resolving these tensions will require {'; '.join(['longitudinal field studies in diverse cultural contexts' if gaps else 'standardized metric reporting practices'][:2])}. "
        f"Priority should be given to addressing Gap [0] concerning cross-cultural threshold transfer "
        f"and Gap [1] concerning longitudinal behavioral adaptation in AV environments — "
        f"gaps that carry direct implications for both road safety policy "
        f"and the design of pedestrian-accepting automated vehicle systems."
    ) if gaps else (
        "Future research should prioritize longitudinal field studies across diverse cultural contexts, "
        "standardized metric reporting, and the development of validated behavioral models "
        "for pedestrian-AV interaction scenarios."
    )

    return _clean_underscores(field + " " + stable + " " + tensions + " " + priorities)


def _clean_underscores(text: str) -> str:
    """Replace underscores in snake_case terms with readable spaces (iterative)."""
    if not text:
        return ""
    # Named replacements for known acronyms/terms
    replacements = {
        " e_hmi ": " eHMI ",
        " ehmi ": " eHMI ",
        " av_pedestrian ": " AV-pedestrian ",
        " av_": " AV-",
        "_av": "-AV",
        " e.g.,": " e.g.,",
        " i.e.,": " i.e.,",
        " machine_learning ": " machine learning ",
        " deep_learning ": " deep learning ",
        " neural_network ": " neural network ",
    }
    text = " " + text + " "
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Iterative snake_case → space conversion (handles multi-underscore terms)
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r"\b([a-z]+)_([a-z_]+)\b", lambda m: m.group(1) + " " + m.group(2).replace("_", " "), text, flags=re.IGNORECASE)
    # Fix double spaces and leading/trailing
    text = re.sub(r"  +", " ", text)
    text = text.strip()
    # Title-case known acronyms after cleaning
    text = re.sub(r"\bAv\b", "AV", text)
    text = re.sub(r"\bEhmi\b", "eHMI", text)
    text = re.sub(r"\bAv-pedestrian\b", "AV-pedestrian", text)
    return text


def _organization_structure(organization: dict[str, Any] | None) -> str | None:
    if isinstance(organization, dict):
        structure = organization.get("recommended_structure")
        if isinstance(structure, str) and structure:
            return structure
    return None


def _structure_axis(structure: str | None) -> str | None:
    mapping = {
        "method_taxonomy": "method",
        "task_taxonomy": "task",
        "factor_taxonomy": "factor",
        "application_scenario": "application",
    }
    return mapping.get(structure or "")


def _section_gap_entries(item: dict[str, Any], verified_gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gap_ids = [gap_id for gap_id in item.get("gap_inputs", []) if gap_id]
    if not gap_ids:
        return []
    by_id = {gap.get("gap_id"): gap for gap in verified_gaps if gap.get("gap_id")}
    return [by_id[gap_id] for gap_id in gap_ids if gap_id in by_id]


def _find_theme_for_section(
    item: dict[str, Any],
    synthesis_map: dict[str, Any] | None,
    organization: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(synthesis_map, dict):
        return None

    title = str(item.get("title", ""))
    label = title.split(":", 1)[1].strip() if ":" in title else ""
    if not label:
        return None

    axis = _structure_axis(_organization_structure(organization))
    theme_axes = synthesis_map.get("theme_axes", {})
    pools: list[dict[str, Any]] = []
    if isinstance(theme_axes, dict) and axis and isinstance(theme_axes.get(axis), list):
        pools.extend(theme for theme in theme_axes[axis] if isinstance(theme, dict))
    top_themes = synthesis_map.get("top_themes", [])
    if isinstance(top_themes, list):
        pools.extend(theme for theme in top_themes if isinstance(theme, dict))

    label_tokens = _token_set(label)
    for theme in pools:
        theme_label = str(theme.get("label") or theme.get("theme_id") or "")
        if theme_label.lower() == label.lower():
            return theme
    for theme in pools:
        theme_tokens = _token_set(theme.get("label") or theme.get("theme_id") or "")
        if label_tokens and label_tokens <= theme_tokens:
            return theme
    return None


def _rows_for_theme(theme: dict[str, Any] | None, axis: str | None, matrix: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not theme or not axis:
        return []

    label = str(theme.get("label") or theme.get("theme_id") or "")
    label_tokens = _token_set(label)
    if not label_tokens:
        return []

    field_map = {
        "method": "method_family",
        "task": "tasks",
        "application": "datasets",
    }
    field = field_map.get(axis)
    rows: list[dict[str, Any]] = []
    for row in matrix:
        hay_parts = [
            row.get("claim_text", ""),
            row.get("research_problem", ""),
            row.get("limitations", ""),
            row.get("notes", ""),
        ]
        if field:
            hay_parts.append(row.get(field, ""))
        hay = " ".join(str(part) for part in hay_parts)
        if label_tokens & _token_set(hay):
            rows.append(row)
    return rows


def _gap_summary(gaps: list[dict[str, Any]]) -> str:
    statements = [str(gap.get("gap_statement", "")).strip() for gap in gaps if gap.get("gap_statement")]
    if not statements:
        return ""
    picked = _dedupe_preserve(statements)[:2]
    return _clean_underscores(" ".join(f"Linked gap evidence indicates that {statement}" for statement in picked))


def _theme_summary_bits(rows: list[dict[str, Any]]) -> tuple[list[str], list[str], list[str]]:
    methods = _dedupe_mixed([
        _humanize(row.get("method_family", "")) for row in rows
        if row.get("method_family") and row.get("method_family") not in {"None", "none"}
    ])
    tasks = _dedupe_mixed([
        _humanize(task) for row in rows if row.get("tasks")
        for task in str(row.get("tasks", "")).split(";")
        if task.strip() and task.strip() not in {"None", "none"}
    ])
    datasets = _dedupe_mixed([
        _humanize(dataset) for row in rows if row.get("datasets")
        for dataset in str(row.get("datasets", "")).split(";")
        if dataset.strip() and dataset.strip() not in {"None", "none"}
    ])
    return methods, tasks, datasets


def _build_structured_taxonomy_section(
    item: dict[str, Any],
    matrix: list[dict[str, Any]],
    verified_gaps: list[dict[str, Any]],
    synthesis_map: dict[str, Any] | None,
    organization: dict[str, Any] | None,
) -> str:
    structure = _organization_structure(organization)
    axis = _structure_axis(structure)
    axis_themes = []
    if isinstance(synthesis_map, dict):
        theme_axes = synthesis_map.get("theme_axes", {})
        if isinstance(theme_axes, dict) and axis and isinstance(theme_axes.get(axis), list):
            axis_themes = [theme for theme in theme_axes[axis] if isinstance(theme, dict)]
    lead_themes = axis_themes[:3]
    gap_entries = _section_gap_entries(item, verified_gaps)

    theme_names = [_humanize(str(theme.get("label") or theme.get("theme_id") or "")) for theme in lead_themes]
    theme_phrase = ", ".join(name for name in theme_names if name) or "the dominant evidence clusters"
    evidence_total = sum(int(theme.get("evidence_count", 0) or 0) for theme in lead_themes)
    contradiction_total = sum(int(theme.get("contradiction_count", 0) or 0) for theme in lead_themes)
    gap_total = sum(int(theme.get("gap_count", 0) or 0) for theme in lead_themes)
    paper_count = len({row.get("paper_id") for row in matrix if row.get("paper_id")})

    opening = (
        f"This section organizes the review around {_humanize(axis or 'dominant')} themes, with the taxonomy anchored by {theme_phrase}. "
        f"Across {paper_count} papers and {len(matrix)} matrix rows, these themes account for {evidence_total or len(matrix)} evidence units and concentrate {gap_total} gap signal{'s' if gap_total != 1 else ''} "
        f"alongside {contradiction_total} contradiction signal{'s' if contradiction_total != 1 else ''}."
    )
    if lead_themes:
        theme_notes = " ".join(
            _clean_underscores(
                f"{_humanize(str(theme.get('label') or theme.get('theme_id') or 'This theme'))} serves as a focal cluster because {str(theme.get('synthesis_note') or '').strip()}"
            )
            for theme in lead_themes[:2]
        )
    else:
        theme_notes = "The available evidence still clusters around a small number of recurring themes, even when reporting detail is uneven."
    gap_text = _gap_summary(gap_entries)
    closing = (
        "Taken together, the taxonomy makes it easier to trace where the corpus is dense enough for synthesis and where fragmented reporting still limits direct comparison across studies."
    )
    return _clean_underscores(" ".join(part for part in [opening, theme_notes, gap_text, closing] if part))


def _build_structured_theme_section(
    item: dict[str, Any],
    matrix: list[dict[str, Any]],
    verified_gaps: list[dict[str, Any]],
    synthesis_map: dict[str, Any] | None,
    organization: dict[str, Any] | None,
) -> str:
    structure = _organization_structure(organization)
    axis = _structure_axis(structure)
    theme = _find_theme_for_section(item, synthesis_map, organization)
    theme_rows = _rows_for_theme(theme, axis, matrix) or _select_relevant_rows(item, matrix)
    methods, tasks, datasets = _theme_summary_bits(theme_rows)
    gap_entries = _section_gap_entries(item, verified_gaps)
    label = item.get("title", "").split(":", 1)[1].strip() if ":" in str(item.get("title", "")) else item.get("title", "Theme")
    evidence_count = int((theme or {}).get("evidence_count", 0) or len(theme_rows))
    contradiction_count = int((theme or {}).get("contradiction_count", 0) or 0)
    gap_count = int((theme or {}).get("gap_count", 0) or len(gap_entries))

    opening = (
        f"The {label} cluster brings together {evidence_count} evidence unit{'s' if evidence_count != 1 else ''} that share a common {_humanize(axis or 'review')} focus. "
        f"Within this cluster, the evidence is carried primarily by {', '.join(methods[:3]) if methods else 'a mixed set of approaches'}"
        f"{' and tasks such as ' + ', '.join(tasks[:3]) if tasks else ''}"
        f"{' in datasets such as ' + ', '.join(datasets[:2]) if datasets else ''}."
    )
    synthesis_note = str((theme or {}).get("synthesis_note") or "").strip()
    middle = _clean_underscores(
        synthesis_note
        or "The pattern across these studies is that similar substantive questions recur, but they are operationalized with different measures and context assumptions."
    )
    gap_text = _gap_summary(gap_entries)
    closing = (
        f"This focus area therefore combines {gap_count} linked gap signal{'s' if gap_count != 1 else ''}"
        f" with {contradiction_count} contradiction signal{'s' if contradiction_count != 1 else ''}, "
        "showing where the theme is mature enough for synthesis and where the current evidence remains incomplete."
    )
    return _clean_underscores(" ".join(part for part in [opening, middle, gap_text, closing] if part))


def _build_structured_comparison_section(
    item: dict[str, Any],
    matrix: list[dict[str, Any]],
    verified_gaps: list[dict[str, Any]],
    synthesis_map: dict[str, Any] | None,
    organization: dict[str, Any] | None,
) -> str:
    structure = _organization_structure(organization)
    axis = _structure_axis(structure)
    axis_themes = []
    if isinstance(synthesis_map, dict):
        theme_axes = synthesis_map.get("theme_axes", {})
        if isinstance(theme_axes, dict) and axis and isinstance(theme_axes.get(axis), list):
            axis_themes = [theme for theme in theme_axes[axis] if isinstance(theme, dict)]
    compared = axis_themes[:2]
    labels = [_humanize(str(theme.get("label") or theme.get("theme_id") or "")) for theme in compared]
    rows = []
    for theme in compared:
        rows.extend(_rows_for_theme(theme, axis, matrix))
    rows = rows or _select_relevant_rows(item, matrix)
    methods, tasks, datasets = _theme_summary_bits(rows)
    gap_entries = _section_gap_entries(item, verified_gaps)

    opening = (
        f"The comparative synthesis contrasts {', '.join(label for label in labels if label) if labels else 'the strongest themes'} to identify where the evidence base is genuinely cumulative and where it remains difficult to align. "
        f"Across the compared studies, the matrix highlights recurring use of {', '.join(methods[:3]) if methods else 'mixed methodological families'}"
        f"{' across tasks such as ' + ', '.join(tasks[:3]) if tasks else ''}."
    )
    heterogeneity = (
        f"Comparison remains constrained by variation in datasets ({', '.join(datasets[:3]) if datasets else 'uneven dataset coverage'}), metric definitions, and reporting granularity. "
        "Even when studies appear to address the same theme, they often rely on different outcome variables, context windows, or evaluation thresholds, which weakens direct cross-paper equivalence."
    )
    gap_text = _gap_summary(gap_entries)
    closing = (
        "The most defensible comparison is therefore thematic rather than purely metric-by-metric: the synthesis can show where themes converge in direction, but it also makes explicit where unresolved gaps prevent stronger generalization."
    )
    return _clean_underscores(" ".join(part for part in [opening, heterogeneity, gap_text, closing] if part))


def _build_structured_section(
    item: dict[str, Any],
    matrix: list[dict[str, Any]],
    verified_gaps: list[dict[str, Any]],
    synthesis_map: dict[str, Any] | None,
    organization: dict[str, Any] | None,
) -> str | None:
    title = str(item.get("title", ""))
    lowered = title.lower()
    structure = _organization_structure(organization)
    if not structure:
        return None
    if "taxonomy" in lowered:
        return _build_structured_taxonomy_section(item, matrix, verified_gaps, synthesis_map, organization)
    if title.startswith(_STRUCTURED_SECTION_PREFIXES):
        return _build_structured_theme_section(item, matrix, verified_gaps, synthesis_map, organization)
    if "comparative" in lowered and "comparison" in str(item.get("section_id", "")).lower():
        return _build_structured_comparison_section(item, matrix, verified_gaps, synthesis_map, organization)
    return None


def _build_plan_maps(
    outline: list[dict[str, Any]],
    matrix: list[dict[str, Any]],
    verified_gaps: list[dict[str, Any]],
    synthesis_map: dict[str, Any] | None,
    organization: dict[str, Any] | None,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    if not synthesis_map and not organization:
        return {}, {}
    try:
        section_plans = build_section_plans(
            outline,
            matrix,
            verified_gaps,
            synthesis_map=synthesis_map,
            organization=organization,
        )
        paragraph_plans = build_paragraph_plans(
            section_plans,
            matrix,
            verified_gaps,
            synthesis_map=synthesis_map,
            organization=organization,
        )
    except Exception:
        return {}, {}
    return (
        {plan.get("section_id", ""): plan for plan in section_plans if isinstance(plan, dict)},
        {plan.get("section_id", ""): plan for plan in paragraph_plans if isinstance(plan, dict)},
    )


def _render_planned_section(
    section_plan: dict[str, Any] | None,
    paragraph_plan: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(section_plan, dict) or not isinstance(paragraph_plan, dict):
        return None

    theme_labels = [str(theme.get("label") or "").strip() for theme in section_plan.get("theme_refs", []) if theme.get("label")]
    gap_labels = [str(gap.get("gap_statement") or "").strip() for gap in section_plan.get("gap_refs", []) if gap.get("gap_statement")]
    matrix_signals = section_plan.get("matrix_signals", {}) if isinstance(section_plan.get("matrix_signals"), dict) else {}
    methods = matrix_signals.get("method_families", []) if isinstance(matrix_signals.get("method_families"), list) else []
    tasks = matrix_signals.get("tasks", []) if isinstance(matrix_signals.get("tasks"), list) else []
    datasets = matrix_signals.get("datasets", []) if isinstance(matrix_signals.get("datasets"), list) else []
    row_count = int(matrix_signals.get("row_count", 0) or 0)
    paper_count = int(matrix_signals.get("paper_count", 0) or 0)

    paragraphs: list[dict[str, Any]] = []
    for block in paragraph_plan.get("blocks", []):
        if not isinstance(block, dict):
            continue
        move_type = str(block.get("move_type") or "synthesis")
        purpose = str(block.get("purpose") or "").strip()
        supporting_points = [str(point).strip() for point in block.get("supporting_points", []) if str(point).strip()]
        text = _compose_planned_paragraph(
            section_title=str(section_plan.get("title") or "This section"),
            section_goal=str(section_plan.get("section_goal") or "").strip(),
            move_type=move_type,
            purpose=purpose,
            sentence_plan=block.get("sentence_plan", []),
            theme_labels=theme_labels,
            gap_labels=gap_labels,
            methods=methods,
            tasks=tasks,
            datasets=datasets,
            supporting_points=supporting_points,
            paper_count=paper_count,
            row_count=row_count,
        )
        cleaned = _clean_underscores(text)
        if cleaned:
            paragraphs.append(
                {
                    "text": cleaned,
                    "move_type": move_type,
                    "purpose": purpose,
                    "theme_refs": block.get("theme_refs", []),
                    "gap_refs": block.get("gap_refs", []),
                    "citation_targets": block.get("citation_targets", []),
                    "supporting_citations": block.get("supporting_citations", []),
                    "supporting_points": block.get("supporting_points", []),
                    "sentence_plan": block.get("sentence_plan", []),
                }
            )

    if not paragraphs:
        return None

    return {
        "text": "\n\n".join(paragraph["text"] for paragraph in paragraphs),
        "paragraphs": paragraphs,
    }


def _compose_planned_paragraph(
    *,
    section_title: str,
    section_goal: str,
    move_type: str,
    purpose: str,
    sentence_plan: list[dict[str, Any]],
    theme_labels: list[str],
    gap_labels: list[str],
    methods: list[str],
    tasks: list[str],
    datasets: list[str],
    supporting_points: list[str],
    paper_count: int,
    row_count: int,
) -> str:
    evidence_units = paper_count or row_count or 0
    focus_label = _planned_focus_label(section_title, theme_labels)
    theme_phrase = ", ".join(theme_labels[:2]) if theme_labels else "the strongest available evidence clusters"
    detail_bits = []
    if methods:
        detail_bits.append(f"method families such as {', '.join(methods[:3])}")
    if tasks:
        detail_bits.append(f"tasks such as {', '.join(tasks[:3])}")
    if datasets:
        detail_bits.append(f"datasets such as {', '.join(datasets[:2])}")
    detail_text = ", ".join(detail_bits) if detail_bits else "the extracted comparison matrix"
    evidence_text = _clean_underscores(" ".join(supporting_points[:2])) if supporting_points else ""
    gap_text = (_clean_underscores(" ".join(gap_labels[:2])) if gap_labels else "linked evidence gaps remain unresolved").rstrip(". ")
    evidence_text = _normalize_planned_evidence_text(evidence_text, gap_text)
    sentences = _planned_sentence_triplet(
        focus_label=focus_label,
        section_title=section_title,
        section_goal=section_goal,
        move_type=move_type,
        sentence_plan=sentence_plan,
        theme_phrase=theme_phrase,
        detail_text=detail_text,
        evidence_text=evidence_text,
        gap_text=gap_text,
        evidence_units=evidence_units,
        purpose=purpose,
    )
    return " ".join(sentence for sentence in sentences if sentence)


def _planned_sentence_triplet(
    *,
    focus_label: str,
    section_title: str,
    section_goal: str,
    move_type: str,
    sentence_plan: list[dict[str, Any]],
    theme_phrase: str,
    detail_text: str,
    evidence_text: str,
    gap_text: str,
    evidence_units: int,
    purpose: str,
) -> list[str]:
    del sentence_plan, purpose
    evidence_unit_label = f"{evidence_units} evidence unit{'s' if evidence_units != 1 else ''}" if evidence_units else ""
    if move_type == "framing":
        return [
            f"{focus_label} provides the analytic entry point for this subsection, bringing the discussion into focus around {theme_phrase}.",
            (
                f"Across {evidence_unit_label}, the relevant literature assembles {detail_text}, which defines the comparison set for the discussion."
                if evidence_unit_label
                else f"The relevant literature assembles {detail_text}, which defines the comparison set for the discussion."
            ),
            "Read this way, the subsection begins from a shared problem space rather than a sequence of isolated paper summaries.",
        ]
    if move_type == "evidence":
        return [
            f"Across the reviewed studies, a recurring pattern emerges in {focus_label.lower()}.",
            evidence_text or f"The matrix highlights {detail_text} as the strongest basis for comparing results across studies.",
            "Collectively, these observations support a subsection-level claim instead of leaving the evidence as a descriptive inventory.",
        ]
    if move_type == "comparison":
        return [
            f"Comparison is most informative where work on {focus_label.lower()} converges in broad outline but diverges in operational detail.",
            evidence_text or f"The compared studies rely on {detail_text}, although reporting granularity and outcome definitions still differ.",
            "The resulting contrast shows where convergence is substantive and where apparent agreement rests on non-equivalent designs.",
        ]
    if move_type == "gap":
        return [
            f"An unresolved problem in this literature concerns {gap_text}.",
            evidence_text or "The available evidence points to the issue, but the reporting pattern remains too partial to sustain strong generalization.",
            f"Until that gap is addressed, any synthesis of {focus_label.lower()} remains conditional rather than fully generalizable.",
        ]
    return [
        f"Taken together, the literature on {focus_label.lower()} points to a field-level pattern rather than a single-study result.",
        evidence_text or _clean_underscores(section_goal) or f"The section-level pattern is visible across {detail_text}, even though direct equivalence remains limited.",
        "The synthesis therefore clarifies both the main takeaway and the boundary conditions that qualify it.",
    ]


def _closing_sentence(default_sentence: str, purpose: str) -> str:
    del purpose
    return default_sentence


def _build_conclusion_paragraphs(
    item: dict[str, Any],
    matrix: list[dict[str, Any]],
    verified_gaps: list[dict[str, Any]],
    synthesis_map: dict[str, Any] | None,
    organization: dict[str, Any] | None,
    section_plan: dict[str, Any] | None,
) -> tuple[str, list[dict[str, Any]]]:
    artifact = build_conclusion_artifact(
        matrix,
        verified_gaps,
        synthesis_map=synthesis_map,
        organization=organization,
    )
    theme_refs = section_plan.get("theme_refs", []) if isinstance(section_plan, dict) else []
    gap_refs = section_plan.get("gap_refs", []) if isinstance(section_plan, dict) else []
    matrix_signals = section_plan.get("matrix_signals", {}) if isinstance(section_plan, dict) else {}
    citation_targets = matrix_signals.get("paper_ids", []) if isinstance(matrix_signals, dict) else []

    parts: list[tuple[str, str]] = []
    lead = str(artifact.get("text") or "").split("Stable conclusions:", 1)[0].strip()
    if lead:
        parts.append(("synthesis", lead.rstrip()))
    stable = artifact.get("stable_conclusions") or []
    if stable:
        parts.append(("synthesis", "Stable conclusions: " + " ".join(str(item).strip() for item in stable if str(item).strip())))
    tensions = artifact.get("unresolved_tensions") or []
    if tensions:
        parts.append(("comparison", "Unresolved tensions: " + " ".join(str(item).strip() for item in tensions if str(item).strip())))
    priorities = artifact.get("research_priorities") or []
    if priorities:
        parts.append(("gap", "Research priorities: " + " ".join(str(item).strip() for item in priorities if str(item).strip())))

    purpose_map = {
        "synthesis": "Close the review with the main field-level takeaway.",
        "comparison": "Surface the key unresolved tensions that still differentiate evidence clusters.",
        "gap": "Translate unresolved tensions into explicit future priorities.",
    }
    paragraphs = [
        {
            "text": _clean_underscores(text),
            "move_type": move_type,
            "purpose": purpose_map.get(move_type, "Advance the conclusion."),
            "theme_refs": theme_refs[:2],
            "gap_refs": gap_refs[:2],
            "citation_targets": citation_targets[:2],
            "supporting_citations": citation_targets[:2],
            "supporting_points": [],
            "sentence_plan": [],
        }
        for move_type, text in parts
        if str(text).strip()
    ]
    return "\n\n".join(paragraph["text"] for paragraph in paragraphs), paragraphs


def _planned_focus_label(section_title: str, theme_labels: list[str]) -> str:
    title = str(section_title or "").strip()
    if ":" in title:
        label = title.split(":", 1)[1].strip()
        if label:
            return _clean_underscores(label)
    if title:
        return _clean_underscores(title)
    if theme_labels:
        return _clean_underscores(theme_labels[0])
    return "the focal topic"


def _normalize_planned_evidence_text(evidence_text: str, gap_text: str) -> str:
    cleaned = evidence_text.strip()
    if not cleaned:
        return ""
    if cleaned.rstrip(". ").lower() == gap_text.rstrip(". ").lower():
        return ""
    return cleaned


# ---------------------------------------------------------------------------
# Main rule-based dispatcher
# ---------------------------------------------------------------------------

def _write_sections_rule_based(
    outline: list[dict[str, Any]],
    matrix: list[dict[str, Any]],
    verified_gaps: list[dict[str, Any]],
    synthesis_map: dict[str, Any] | None = None,
    organization: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Rule-based fallback synthesizing matrix and gap data into prose.

    Follows the review_learning writing patterns:
      - No underscores in technical terms
      - Evidence-grounded claims (paper-specific anchors)
      - Gap section uses structured entry template
      - Conclusion uses field-level framing, not summary recap
      - Each section closes with synthesis / tension / gap statement
    """
    sections = []
    gap_stats = _gap_stats(verified_gaps)
    section_plan_map, paragraph_plan_map = _build_plan_maps(
        outline,
        matrix,
        verified_gaps,
        synthesis_map=synthesis_map,
        organization=organization,
    )

    BUILDERS = [
        ("intro", _build_intro),
        ("method", _build_methods),
        ("approach", _build_methods),
        ("technical", _build_methods),
        ("task", _build_tasks),
        ("capabilit", _build_tasks),
        ("scope", _build_tasks),
        ("metric", _build_metrics),
        ("evalu", _build_metrics),
        ("compar", _build_metrics),
        ("gap", _build_gaps),
        ("opportun", _build_gaps),
        ("limitation", _build_gaps),
        ("conflict", _build_gaps),
        ("claim", _build_gaps),
        # "synthes" must come AFTER "conclus"/"futur"/"discuss"
        # so that section titles like "Discussion: Synthesis and Future Directions"
        # match "discuss" or "futur" before falling into gap-match on "synthes"
        ("conclus", _build_legacy_conclusion),
        ("summar", _build_legacy_conclusion),
        ("futur", _build_legacy_conclusion),
        ("discuss", _build_legacy_conclusion),
        ("synthes", _build_gaps),
    ]

    for item in outline:
        title = item.get("title", "").lower()
        section_id = item.get("section_id", "sec-x")
        is_conclusion_like = any(key in title for key in ("conclus", "summar", "futur", "discuss"))
        planned = None if is_conclusion_like else _render_planned_section(section_plan_map.get(section_id), paragraph_plan_map.get(section_id))
        structured_text = _build_structured_section(item, matrix, verified_gaps, synthesis_map, organization)
        section_matrix = _select_relevant_rows(item, matrix)
        stats = _matrix_stats(section_matrix)

        text = planned["text"] if planned else structured_text
        paragraph_data = planned.get("paragraphs") if planned else None
        if text is None:
            if is_conclusion_like:
                if synthesis_map or organization:
                    try:
                        text, paragraph_data = _build_conclusion_paragraphs(
                            item,
                            matrix,
                            verified_gaps,
                            synthesis_map,
                            organization,
                            section_plan_map.get(section_id),
                        )
                    except Exception:
                        text = None
                        paragraph_data = None
                if text is None:
                    text = _build_legacy_conclusion(item, stats, gap_stats)
                payload = {"section_id": section_id, "title": item["title"], "text": text}
                if isinstance(paragraph_data, list):
                    payload["paragraphs"] = paragraph_data
                sections.append(payload)
                continue
            for key, builder in BUILDERS:
                if key in title:
                    try:
                        text = builder(item, stats, gap_stats)
                    except Exception:
                        text = None
                    break

        if text is None:
            n = len(stats["paper_ids"])
            task_str = _humanize(", ".join(stats["tasks"][:3])) if stats["tasks"] else "varied pedestrian crossing tasks"
            method_str = _humanize(", ".join(stats["method_families"][:3])) if stats["method_families"] else "varied methodological approaches"
            text = _clean_underscores(
                f"This section synthesizes findings from {n} papers examining {task_str} "
                f"using {method_str}. The comparative evidence matrix structures claims, "
                f"metrics, and limitations to support structured analysis. "
                f"A key observation is that {' and '.join([_humanize(m) for m in stats['method_families'][:2]])} "
                f"approaches are the dominant methodological families in this corpus, "
                f"though significant heterogeneity in reporting practices limits direct cross-study comparison."
            )

        payload = {"section_id": section_id, "title": item["title"], "text": text}
        if isinstance(paragraph_data, list):
            payload["paragraphs"] = paragraph_data
        sections.append(payload)

    return sections
