"""
ShadowReviewer — multi-round shadow critique for ARIS-Lit writing output.

Architecture:
  1. Shadow model (gpt-4o) reviews written sections for logical flaws
  2. If CRITICAL_FLAW found → loop back to executor for revision (max 3 rounds)
  3. Returns structured critique report + optionally revised sections

Input:  sections.json, matrix.json, outline.json
Output: shadow_report.json
"""
from __future__ import annotations

import json
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from services.llm.adapter import LLMAdapter

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class CritiqueFinding:
    section_id: str
    section_title: str
    severity: str           # CRITICAL_FLAW | WARNING | SUGGESTION
    location: str           # paragraph index, sentence, or "general"
    claim: str              # what the finding asserts
    evidence: str           # why this is a problem (with specifics from matrix/text)
    fix_guidance: str       # concrete suggestion for revision
    paper_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_id": self.section_id,
            "section_title": self.section_title,
            "severity": self.severity,
            "location": self.location,
            "claim": self.claim,
            "evidence": self.evidence,
            "fix_guidance": self.fix_guidance,
            "paper_refs": self.paper_refs,
        }


@dataclass
class CritiqueRound:
    round: int
    findings: list[CritiqueFinding]
    critique_text: str          # raw LLM output for auditability
    has_critical_flaws: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "round": self.round,
            "has_critical_flaws": self.has_critical_flaws,
            "findings": [f.to_dict() for f in self.findings],
            "critique_text": self.critique_text,
        }


@dataclass
class ShadowReport:
    section_count: int
    rounds: list[CritiqueRound]
    final_sections: list[dict[str, Any]]   # revised if loops ran; original if no loops
    adopted_fixes: list[str]                 # human-readable log of what was changed
    overall_stable: bool                     # True if passed without CRITICAL_FLAW

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_count": self.section_count,
            "rounds": [r.to_dict() for r in self.rounds],
            "final_sections": self.final_sections,
            "adopted_fixes": self.adopted_fixes,
            "overall_stable": self.overall_stable,
        }

    def summary(self) -> str:
        total_critical = sum(
            1 for r in self.rounds for f in r.findings if f.severity == "CRITICAL_FLAW"
        )
        total_warnings = sum(
            1 for r in self.rounds for f in r.findings if f.severity == "WARNING"
        )
        return (
            f"ShadowReviewer: {len(self.rounds)} rounds, "
            f"{total_critical} CRITICAL_FLAW, {total_warnings} WARNING, "
            f"stable={self.overall_stable}"
        )


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_SHADOW_CRITIQUE_PROMPT = textwrap.dedent("""\
    You are a rigorous academic peer reviewer. Your task is to identify **specific, evidence-based**
    weaknesses in a literature review section draft.

    ## Your identity
    You are the SHADOW REVIEWER. You are adversarial but constructive. You do not accept vague
    praise — every claim you make must cite a specific failure in the provided section text or matrix.

    ## Input you receive
    - SECTION: a section draft (section_id, title, paragraphs)
    - MATRIX: a structured comparison matrix of paper claims (may be empty)
    - OUTLINE: the planned structure for this section

    ## What to look for (in priority order)

    ### CRITICAL_FLAW (must fix before acceptance)
    1. **Claim without evidence anchor** — the section makes a specific claim (e.g., "X is the dominant factor")
       but no paper in the matrix actually supports it. Check against matrix.claim_text.
    2. **Contradiction with matrix** — the section asserts something that matrix papers directly contradict.
    3. **Missing required rhetorical move** — intro/conclusion/gap sections missing their mandated structure.
    4. **Metric comparability failure** — section compares metrics that are defined or normalized differently
       across studies without noting this.
    5. **Cross-study overgeneralization** — results from one dataset/context claimed as general truth.

    ### WARNING (should address)
    6. **Under-specified gap** — gap section does not include insufficiency reason or consequence.
    7. **Citation drift** — section cites papers that don't directly support the claim in that location.
    8. **Structural imbalance** — a taxonomy/comparison section lacks an explicit comparison paragraph.

    ### SUGGESTION (optional improvements)
    9. **Clarity/style** — a sentence is ambiguous or could be more precise.
    10. **Missing boundary condition** — a finding is stated without its scope/limitation.

    ## Output format
    For each finding, produce a JSON entry. Return ALL findings as a JSON list inside a
    "findings" key. If a section has NO issues, return an empty list for that section.

    Output MUST be valid JSON:
    {
      "findings": [
        {
          "section_id": "sec-3",
          "section_title": "Methodological Approaches",
          "severity": "CRITICAL_FLAW",   // or WARNING or SUGGESTION
          "location": "paragraph 2, sentence 3",
          "claim": "the dominant paradigm is discrete choice modeling",
          "evidence": "Matrix row for paper Chen2020 shows they actually use a neural network approach, not discrete choice.",
          "fix_guidance": "Qualify the claim to specify which paper uses which approach, or restructure to group by method family.",
          "paper_refs": ["Chen2020"]
        }
      ],
      "section_summary": {
        "sec-3": "Has 1 CRITICAL_FLAW: overgeneralizes method prevalence. Needs qualification."
      }
    }

    ## Critical rules
    - Only flag something as CRITICAL_FLAW if you can point to specific contradictory evidence in the matrix or section text.
    - Do NOT flag stylistic preferences as CRITICAL_FLAW.
    - Do NOT invent paper references that are not in the matrix.
    - If the matrix is sparse or empty, note this as a WARNING rather than claiming a specific contradiction.
    - Your output must be parseable JSON. No markdown code blocks, no preamble, no explanation.
""")

_SHADOW_FIX_PROMPT = textwrap.dedent("""\
    You are a revision engine. You receive a SHADOW CRITIQUE and must revise the section accordingly.

    ## Input
    - ORIGINAL_SECTION: the section draft as written
    - SHADOW_CRITIQUE: the critique findings (JSON)

    ## Your task
    For each CRITICAL_FLAW in the critique, rewrite the relevant paragraph(s) to fix the problem.
    For WARNINGs, incorporate the guidance if doing so would clearly improve the section.
    SUGGESTIONs are optional.

    ## Rules
    - Do not throw away the entire section — fix only what is broken.
    - Preserve the section_id, title, and overall structure.
    - Preserve paragraph-level metadata (move_type, purpose, theme_refs, gap_refs, citation_keys) if present.
    - Keep citations that are already present; do not add new paper citations not supported by the critique.
    - Return ONLY valid JSON:
      {
        "revised_sections": [
          {
            "section_id": "sec-3",
            "title": "Methodological Approaches",
            "text": "revised full section text with fixes applied",
            "paragraphs": [...],   // preserve metadata if present
            "fixes_applied": ["fixed claim overgeneralization in para 2", "added missing comparison paragraph"]
          }
        ]
      }
    - Output must be valid JSON. No markdown.
""")

# ---------------------------------------------------------------------------
# Main reviewer class
# ---------------------------------------------------------------------------

class ShadowReviewer:
    """
    Multi-round shadow critique for ARIS-Lit literature review sections.

    Parameters
    ----------
    shadow_model : str
        Model to use for the shadow (critique) role. Default "gpt-4o".
        Must be a model supported by the configured LLM backend.
    executor_model : str | None
        Model to use for revision (fix) calls. Defaults to shadow_model if not set.
    max_rounds : int
        Maximum debate rounds. Default 3.
    strict : bool
        If True, exit early when no CRITICAL_FLAW is found (optimize for speed).
        If False, always run all rounds for completeness. Default False.
    """

    def __init__(
        self,
        shadow_model: str = "gpt-4o",
        executor_model: Optional[str] = None,
        max_rounds: int = 3,
        strict: bool = False,
    ) -> None:
        self.shadow_model = shadow_model
        self.executor_model = executor_model or shadow_model
        self.max_rounds = max_rounds
        self.strict = strict

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def review(
        self,
        sections: list[dict[str, Any]],
        matrix: list[dict[str, Any]],
        outline: Optional[list[dict[str, Any]]] = None,
    ) -> ShadowReport:
        """
        Run shadow critique on written sections.

        Parameters
        ----------
        sections : list[dict]
            Written sections from section_writer output.
            Each dict should have: section_id, title, text, paragraphs (optional).
        matrix : list[dict]
            Evidence matrix rows from matrix_builder.
        outline : list[dict] | None
            Outline sections for context (optional).

        Returns
        -------
        ShadowReport
            Structured report with critique rounds, findings, and final sections.
        """
        current_sections = _deep_copy_sections(sections)
        rounds: list[CritiqueRound] = []
        adopted_fixes: list[str] = []
        overall_stable = False

        for round_num in range(1, self.max_rounds + 1):
            # Build the critique prompt
            prompt_input = self._build_critique_input(current_sections, matrix, outline)

            # Call shadow model
            shadow_llm = LLMAdapter(provider="openai_compatible", model=self.shadow_model)
            try:
                critique_raw = shadow_llm.generate_json(
                    system_prompt=_SHADOW_CRITIQUE_PROMPT,
                    user_prompt=prompt_input,
                )
            except Exception as exc:
                # If shadow model fails, fall back to stub but log the failure
                import logging
                logging.warning(f"Shadow critique round {round_num} failed ({exc}), using stub.")
                stub_llm = LLMAdapter(provider="stub", model="stub-model")
                critique_raw = stub_llm.generate_json(
                    system_prompt=_SHADOW_CRITIQUE_PROMPT,
                    user_prompt=prompt_input,
                )

            # Parse critique — content is JSON-decoded dict/list; serialize for storage
            critique_content = critique_raw.content
            critique_text = json.dumps(critique_content, ensure_ascii=False) if critique_content else ""
            findings, parsed = _parse_critique(critique_text, current_sections)
            has_critical = any(f.severity == "CRITICAL_FLAW" for f in findings)

            critique_round = CritiqueRound(
                round=round_num,
                findings=findings,
                critique_text=critique_text,
                has_critical_flaws=has_critical,
            )
            rounds.append(critique_round)

            if not has_critical:
                overall_stable = True
                if self.strict:
                    break
                # Continue to check all sections even if first passes

            # If CRITICAL_FLAW found, call executor for revision
            if has_critical and round_num < self.max_rounds:
                revised = self._call_executor_fix(current_sections, findings, matrix)
                fixes_log = _diff_sections(current_sections, revised)
                adopted_fixes.extend(fixes_log)
                current_sections = revised

        return ShadowReport(
            section_count=len(current_sections),
            rounds=rounds,
            final_sections=current_sections,
            adopted_fixes=adopted_fixes,
            overall_stable=overall_stable,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_critique_input(
        self,
        sections: list[dict[str, Any]],
        matrix: list[dict[str, Any]],
        outline: Optional[list[dict[str, Any]]],
    ) -> str:
        """Build the user-prompt input for the shadow critique call."""
        # Serialize sections
        sections_summary = []
        for sec in sections:
            paragraphs = sec.get("paragraphs", [])
            if paragraphs:
                para_texts = "\n".join(
                    f"[P{i+1}] {p.get('text', '')}" for i, p in enumerate(paragraphs)
                )
            else:
                para_texts = sec.get("text", "")
            sections_summary.append({
                "section_id": sec.get("section_id", ""),
                "title": sec.get("title", ""),
                "paragraphs_text": para_texts,
            })

        prompt_parts = [
            "## SECTIONS TO REVIEW\n",
            json.dumps(sections_summary, ensure_ascii=False, indent=2),
            "\n\n## EVIDENCE MATRIX\n",
            json.dumps(matrix[:50], ensure_ascii=False, indent=2),  # cap at 50 rows for prompt size
        ]
        if outline:
            prompt_parts.extend([
                "\n\n## OUTLINE (planned structure)\n",
                json.dumps(outline, ensure_ascii=False, indent=2),
            ])
        return "\n".join(prompt_parts)

    def _call_executor_fix(
        self,
        sections: list[dict[str, Any]],
        findings: list[CritiqueFinding],
        matrix: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Call executor model to fix critical flaws."""
        fix_input = {
            "original_sections": sections,
            "critique_findings": [f.to_dict() for f in findings if f.severity == "CRITICAL_FLAW"],
            "matrix_sample": matrix[:30],
        }
        executor_llm = LLMAdapter(provider="openai_compatible", model=self.executor_model)
        try:
            response = executor_llm.generate_json(
                system_prompt=_SHADOW_FIX_PROMPT,
                user_prompt=json.dumps(fix_input, ensure_ascii=False),
            )
        except Exception:
            # Fall back: no revision if executor fails
            return sections

        content = response.content
        if isinstance(content, dict):
            revised_list = content.get("revised_sections", [])
        elif isinstance(content, list):
            revised_list = content
        else:
            return sections

        # Validate: make sure we got the same number of sections back
        if len(revised_list) != len(sections):
            return sections

        # Merge fixes back: preserve metadata from original sections
        merged = []
        for orig, revised in zip(sections, revised_list):
            merged_sec = {**orig}
            if "text" in revised:
                merged_sec["text"] = revised["text"]
            if "paragraphs" in revised and isinstance(revised["paragraphs"], list):
                # Merge metadata from original paragraphs into revised ones
                orig_paras = orig.get("paragraphs", [])
                rev_paras = revised["paragraphs"]
                merged_paras = []
                for i, rp in enumerate(rev_paras):
                    if i < len(orig_paras) and isinstance(orig_paras[i], dict):
                        merged_paras.append({**orig_paras[i], **rp})
                    else:
                        merged_paras.append(rp)
                merged_sec["paragraphs"] = merged_paras
            merged_sec["_shadow_revised"] = True
            merged_sec["_shadow_fixes"] = revised.get("fixes_applied", [])
            merged.append(merged_sec)
        return merged


# ---------------------------------------------------------------------------
# Standalone CLI
# ---------------------------------------------------------------------------

def run_shadow_review(
    sections_path: str | Path,
    matrix_path: str | Path,
    output_path: Optional[str | Path] = None,
    **kwargs,
) -> ShadowReport:
    """Convenience function to run shadow review from file paths."""
    sections = json.loads(Path(sections_path).read_text(encoding="utf-8"))
    matrix = json.loads(Path(matrix_path).read_text(encoding="utf-8"))
    reviewer = ShadowReviewer(**kwargs)
    report = reviewer.review(sections, matrix)
    if output_path:
        Path(output_path).write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return report


# ---------------------------------------------------------------------------
# Internal utilities
# ---------------------------------------------------------------------------

def _deep_copy_sections(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deep-copy sections to avoid mutating the original."""
    return json.loads(json.dumps(sections))


def _parse_critique(
    raw_text: str,
    sections: list[dict[str, Any]],
) -> tuple[list[CritiqueFinding], bool]:
    """Parse the shadow critique LLM output into CritiqueFinding objects.

    Returns (findings, parsed_ok):
      - findings: list of CritiqueFinding objects
      - parsed_ok: True if valid JSON was extracted and findings list is present
                  (empty findings list still returns True if JSON was valid)
    """
    findings: list[CritiqueFinding] = []
    parsed_ok = False

    # Try to extract JSON from the raw text
    text = raw_text.strip()
    # Strip markdown code blocks if present
    if text.startswith("```"):
        text = text.lstrip("`")
        text = re.sub(r"^json\s*", "", text, count=1, flags=re.IGNORECASE)
        text = text.rstrip("`")

    # Find JSON object or array
    json_start = text.find("{")
    if json_start == -1:
        json_start = text.find("[")

    if json_start != -1:
        try:
            parsed = json.loads(text[json_start:])
            raw_findings = parsed.get("findings", []) if isinstance(parsed, dict) else (parsed if isinstance(parsed, list) else [])
            parsed_ok = True
        except json.JSONDecodeError:
            raw_findings = []
    else:
        raw_findings = []

    section_map = {s.get("section_id", ""): s.get("title", "") for s in sections}

    for raw in raw_findings:
        if not isinstance(raw, dict):
            continue
        findings.append(CritiqueFinding(
            section_id=str(raw.get("section_id", "")),
            section_title=section_map.get(raw.get("section_id", ""), ""),
            severity=str(raw.get("severity", "WARNING")).upper(),
            location=str(raw.get("location", "general")),
            claim=str(raw.get("claim", "")),
            evidence=str(raw.get("evidence", "")),
            fix_guidance=str(raw.get("fix_guidance", "")),
            paper_refs=raw.get("paper_refs") if isinstance(raw.get("paper_refs"), list) else [],
        ))

    return findings, parsed_ok


def _diff_sections(
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
) -> list[str]:
    """Return a human-readable log of what changed between section versions."""
    changes: list[str] = []
    for orig, revised in zip(before, after):
        sid = orig.get("section_id", "?")
        fixes = revised.get("_shadow_fixes", [])
        changes.extend(fixes)
    return changes


# ---------------------------------------------------------------------------
# Imports needed at module level
# ---------------------------------------------------------------------------
import re
