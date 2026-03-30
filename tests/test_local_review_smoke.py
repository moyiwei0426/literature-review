from __future__ import annotations

import json
from pathlib import Path

from core.models import PaperClaim, PaperProfile
import scripts.run_local_review as local_review


def _write_fake_pdf(directory: Path, name: str) -> Path:
    path = directory / name
    path.write_bytes(b"%PDF-1.4\n% fake pdf fixture\n")
    return path


class _FakeLink:
    def __init__(self, claim_id: str, chunk_id: str) -> None:
        self.claim_id = claim_id
        self.chunk_id = chunk_id

    def model_dump(self, mode: str = "json") -> dict[str, str]:
        return {"claim_id": self.claim_id, "chunk_id": self.chunk_id}


def test_run_local_review_writes_artifacts_and_skips_demo_pdf(tmp_path, monkeypatch) -> None:
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    _write_fake_pdf(pdf_dir, "cli-demo-paper.pdf")
    real_pdf = _write_fake_pdf(pdf_dir, "01_2001_hamed_safety_science.pdf")
    output_dir = tmp_path / "out"

    seen_paper_ids: list[str] = []

    def fake_parse_pdf(pdf_path: Path, extractor) -> tuple[dict, list[dict], dict]:
        assert pdf_path == real_pdf
        return (
            {
                "status": "ok",
                "full_text": "Pedestrian Crossing Behavior Under Mixed Traffic\nSafety Science 2001\n",
                "page_count": 1,
            },
            [{"chunk_id": f"{pdf_path.stem}-c1", "paper_id": pdf_path.stem, "section": "Body", "text": "evidence"}],
            {"title": "", "authors": [], "overall_score": 0.9},
        )

    def fake_extract_profile(paper_id: str, chunks: list[dict], extractor, *, parsed=None, timeout_seconds=0):
        seen_paper_ids.append(paper_id)
        profile = PaperProfile(
            paper_id=paper_id,
            title="Untitled",
            authors=[],
            year=None,
            venue=None,
            research_problem="Understand pedestrian crossing behavior.",
            method_summary="Structured evidence synthesis.",
            method_family=["observational"],
            tasks=["crossing"],
            datasets=["field"],
            main_claims=[
                PaperClaim(
                    claim_id="c1",
                    claim_text="Crossing behavior varies by traffic context.",
                    claim_type="application",
                    evidence_chunk_ids=[chunks[0]["chunk_id"]],
                    confidence=0.8,
                )
            ],
            limitations=[],
        )
        return profile, [_FakeLink("c1", chunks[0]["chunk_id"])], {"provider": "stub", "fallback_used": True}

    monkeypatch.setattr(local_review, "parse_pdf", fake_parse_pdf)
    monkeypatch.setattr(local_review, "extract_profile", fake_extract_profile)
    monkeypatch.setattr(local_review, "build_coverage_report", lambda profiles: {"paper_count": len(profiles), "themes": ["observational"]})
    monkeypatch.setattr(local_review, "build_claims_evidence_matrix", lambda profiles: [{"paper_id": profiles[0].paper_id, "claim_text": "Crossing behavior varies by traffic context."}])
    monkeypatch.setattr(local_review, "detect_contradictions", lambda profiles: {"contradiction_count": 0, "contradictions": []})
    monkeypatch.setattr(local_review, "generate_candidate_gaps", lambda matrix, coverage, contradiction: [{"gap_id": "g1", "gap_statement": "Need broader validation."}])
    monkeypatch.setattr(local_review, "verify_gaps", lambda candidates, coverage, matrix: candidates)
    monkeypatch.setattr(local_review, "score_gaps", lambda verified: [{"gap_id": "g1", "review_worthiness": 0.8, **verified[0]}])
    monkeypatch.setattr(local_review, "build_synthesis_map", lambda *args, **kwargs: {"overview": {"paper_count": 1}, "top_themes": []})
    monkeypatch.setattr(local_review, "select_organization", lambda synthesis_map, matrix: {"recommended_structure": "method_taxonomy"})
    monkeypatch.setattr(local_review, "build_outline", lambda *args, **kwargs: [{"section_id": "sec-1", "title": "Introduction"}])
    monkeypatch.setattr(local_review, "build_section_plans", lambda *args, **kwargs: [{"section_id": "sec-1", "title": "Introduction", "argument_moves": []}])
    monkeypatch.setattr(local_review, "build_paragraph_plans", lambda *args, **kwargs: [{"section_id": "sec-1", "title": "Introduction", "blocks": []}])
    monkeypatch.setattr(local_review, "write_sections", lambda *args, **kwargs: [{"section_id": "sec-1", "title": "Introduction", "text": "Evidence paragraph.", "paragraphs": [{"text": "Evidence paragraph.", "move_type": "evidence", "citation_targets": ["01_2001_hamed_safety_science"]}]}])
    monkeypatch.setattr(local_review, "ground_citations", lambda sections, matrix: [{"section_id": "sec-1", "title": "Introduction", "text": "Evidence paragraph.", "citation_keys": ["01_2001_hamed_safety_science"], "paragraphs": [{"text": "Evidence paragraph.", "move_type": "evidence", "citation_keys": ["01_2001_hamed_safety_science"]}]}])
    monkeypatch.setattr(local_review, "rewrite_style", lambda sections, **kwargs: sections)
    monkeypatch.setattr(local_review, "validate_review_writing", lambda **kwargs: {"summary": {"overall_status": "pass", "weak_section_count": 0, "finding_count": 0}})
    monkeypatch.setattr(local_review, "build_bib_entries", lambda matrix: [{"paper_id": "01_2001_hamed_safety_science", "entry": "@article{p1,title={Demo}}"}])
    monkeypatch.setattr(local_review, "prune_bib_entries", lambda entries, used_keys: entries)
    monkeypatch.setattr(local_review, "build_appendix_artifact", lambda *args, **kwargs: {"evidence_table": [{"paper_id": "01_2001_hamed_safety_science"}]})
    monkeypatch.setattr(local_review, "build_conclusion_artifact", lambda *args, **kwargs: {"text": "Conclusion"})
    monkeypatch.setattr(local_review, "build_review_abstract", lambda *args, **kwargs: {"text": "Abstract"})
    monkeypatch.setattr(local_review, "build_review_keywords", lambda *args, **kwargs: {"keywords": ["pedestrian crossing"]})
    monkeypatch.setattr(local_review, "compose_latex", lambda *args, **kwargs: "\\section{Introduction}")
    monkeypatch.setattr(local_review, "compose_review_markdown", lambda *args, **kwargs: "# Review")
    monkeypatch.setattr(local_review, "export_json", lambda path, payload: path.write_text(json.dumps(payload), encoding="utf-8"))
    monkeypatch.setattr(local_review, "export_csv", lambda path, rows: path.write_text("paper_id\n01_2001_hamed_safety_science\n", encoding="utf-8"))
    monkeypatch.setattr(local_review, "export_markdown_table", lambda path, rows: path.write_text("| paper_id |\n| --- |\n| 01_2001_hamed_safety_science |\n", encoding="utf-8"))

    result = local_review.run_local_review(pdf_dir=pdf_dir, title="Trial Review", output_dir=output_dir, skip_compile=True, timeout_seconds=5)

    assert result["status"] == "success"
    assert seen_paper_ids == ["01_2001_hamed_safety_science"]
    assert result["warnings"] == ["Stub extraction fallback used for 1 paper(s): 01_2001_hamed_safety_science"]
    assert result["extraction_strategy"] == {
        "mode": "rule_based",
        "paper_count": 1,
        "fallback_paper_count": 1,
        "fallback_papers": ["01_2001_hamed_safety_science"],
        "recovered_after_retry_count": 0,
        "recovered_after_retry_papers": [],
    }
    assert result["writing_strategy"]["mode"] == "live"
    assert result["writing_strategy"]["fallback_triggered"] is False
    assert result["writing_strategy"]["fallback_adopted"] is False
    assert result["writing_strategy"]["fallback_reason"] is None
    assert result["writing_strategy"]["initial_validation"] == "pass"
    assert result["writing_strategy"]["final_validation"] == "pass"
    assert result["writing_strategy"]["selected_track"] == "polished"
    assert result["writing_strategy"]["selection_report"]["reason"]
    assert result["run_log"].endswith("run.log")
    assert result["artifacts"]["summary.json"]["exists"] is True
    assert result["artifacts"]["review.tex"]["exists"] is True
    assert result["artifacts"]["review.md"]["exists"] is True
    assert result["artifacts"]["validation_report.json"]["exists"] is True
    assert result["artifacts"]["bib.tex"]["exists"] is True

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["extracted"] == 1
    assert summary["warnings"] == result["warnings"]
    assert summary["run_log"].endswith("run.log")
    assert summary["extraction_strategy"] == result["extraction_strategy"]
    assert summary["writing_strategy"] == result["writing_strategy"]
    assert (output_dir / "artifacts.json").exists()


def test_run_local_review_uses_rule_based_writing_fallback_when_live_validation_fails(tmp_path, monkeypatch) -> None:
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    real_pdf = _write_fake_pdf(pdf_dir, "01_2001_hamed_safety_science.pdf")
    output_dir = tmp_path / "out"

    def fake_parse_pdf(pdf_path: Path, extractor) -> tuple[dict, list[dict], dict]:
        assert pdf_path == real_pdf
        return (
            {"status": "ok", "full_text": "Pedestrian Crossing Behavior Under Mixed Traffic\nSafety Science 2001\n", "page_count": 1},
            [{"chunk_id": f"{pdf_path.stem}-c1", "paper_id": pdf_path.stem, "section": "Body", "text": "evidence"}],
            {"title": "", "authors": [], "overall_score": 0.9},
        )

    def fake_extract_profile(paper_id: str, chunks: list[dict], extractor, *, parsed=None, timeout_seconds=0):
        profile = PaperProfile(
            paper_id=paper_id,
            title="Untitled",
            authors=[],
            year=None,
            venue=None,
            research_problem="Understand pedestrian crossing behavior.",
            method_summary="Structured evidence synthesis.",
            method_family=["observational"],
            tasks=["crossing"],
            datasets=["field"],
            main_claims=[
                PaperClaim(
                    claim_id="c1",
                    claim_text="Crossing behavior varies by traffic context.",
                    claim_type="application",
                    evidence_chunk_ids=[chunks[0]["chunk_id"]],
                    confidence=0.8,
                )
            ],
            limitations=[],
        )
        return profile, [_FakeLink("c1", chunks[0]["chunk_id"])], {"provider": "openai_compatible", "fallback_used": False}

    monkeypatch.setattr(local_review, "parse_pdf", fake_parse_pdf)
    monkeypatch.setattr(local_review, "extract_profile", fake_extract_profile)
    monkeypatch.setattr(local_review, "build_coverage_report", lambda profiles: {"paper_count": len(profiles), "themes": ["observational"]})
    monkeypatch.setattr(local_review, "build_claims_evidence_matrix", lambda profiles: [{"paper_id": profiles[0].paper_id, "claim_text": "Crossing behavior varies by traffic context."}])
    monkeypatch.setattr(local_review, "detect_contradictions", lambda profiles: {"contradiction_count": 0, "contradictions": []})
    monkeypatch.setattr(local_review, "generate_candidate_gaps", lambda matrix, coverage, contradiction: [])
    monkeypatch.setattr(local_review, "verify_gaps", lambda candidates, coverage, matrix: [])
    monkeypatch.setattr(local_review, "score_gaps", lambda verified: [])
    monkeypatch.setattr(local_review, "build_synthesis_map", lambda *args, **kwargs: {"overview": {"paper_count": 1}, "top_themes": []})
    monkeypatch.setattr(local_review, "select_organization", lambda synthesis_map, matrix: {"recommended_structure": "method_taxonomy"})

    state = {"build_outline": 0}

    def fake_build_outline(*args, **kwargs):
        state["build_outline"] += 1
        if state["build_outline"] == 1:
            return [{"section_id": "sec-live", "title": "Live Intro"}]
        return [{"section_id": "sec-fallback", "title": "Fallback Intro"}]

    monkeypatch.setattr(local_review, "build_outline", fake_build_outline)
    monkeypatch.setattr(local_review, "build_section_plans", lambda outline, *args, **kwargs: [{"section_id": outline[0]["section_id"], "title": outline[0]["title"], "argument_moves": []}])
    monkeypatch.setattr(local_review, "build_paragraph_plans", lambda outline, *args, **kwargs: [{"section_id": outline[0]["section_id"], "title": outline[0]["title"], "blocks": []}])
    monkeypatch.setattr(local_review, "write_sections", lambda outline, *args, **kwargs: [{"section_id": outline[0]["section_id"], "title": outline[0]["title"], "text": "Evidence paragraph.", "paragraphs": [{"text": "Evidence paragraph.", "move_type": "evidence", "citation_targets": ["01_2001_hamed_safety_science"]}]}])
    monkeypatch.setattr(local_review, "ground_citations", lambda sections, matrix: [{**sections[0], "citation_keys": ["01_2001_hamed_safety_science"], "paragraphs": [{"text": "Evidence paragraph.", "move_type": "evidence", "citation_keys": ["01_2001_hamed_safety_science"]}]}])
    monkeypatch.setattr(local_review, "rewrite_style", lambda sections, **kwargs: sections)

    validate_calls = {"count": 0}
    def fake_validate_review_writing(**kwargs):
        validate_calls["count"] += 1
        if validate_calls["count"] == 1:
            return {"summary": {"overall_status": "fail", "weak_section_count": 1, "finding_count": 4}}
        return {"summary": {"overall_status": "pass", "weak_section_count": 0, "finding_count": 0}}

    monkeypatch.setattr(local_review, "validate_review_writing", fake_validate_review_writing)
    monkeypatch.setattr(local_review, "build_bib_entries", lambda matrix: [{"paper_id": "01_2001_hamed_safety_science", "entry": "@article{p1,title={Demo}}"}])
    monkeypatch.setattr(local_review, "prune_bib_entries", lambda entries, used_keys: entries)
    monkeypatch.setattr(local_review, "build_appendix_artifact", lambda *args, **kwargs: {"evidence_table": [{"paper_id": "01_2001_hamed_safety_science"}]})
    monkeypatch.setattr(local_review, "build_conclusion_artifact", lambda *args, **kwargs: {"text": "Conclusion"})
    monkeypatch.setattr(local_review, "build_review_abstract", lambda *args, **kwargs: {"text": "Abstract"})
    monkeypatch.setattr(local_review, "build_review_keywords", lambda *args, **kwargs: {"keywords": ["pedestrian crossing"]})
    monkeypatch.setattr(local_review, "compose_latex", lambda *args, **kwargs: "\\section{Introduction}")
    monkeypatch.setattr(local_review, "compose_review_markdown", lambda *args, **kwargs: "# Review")
    monkeypatch.setattr(local_review, "export_json", lambda path, payload: path.write_text(json.dumps(payload), encoding="utf-8"))
    monkeypatch.setattr(local_review, "export_csv", lambda path, rows: path.write_text("paper_id\n01_2001_hamed_safety_science\n", encoding="utf-8"))
    monkeypatch.setattr(local_review, "export_markdown_table", lambda path, rows: path.write_text("| paper_id |\n| --- |\n| 01_2001_hamed_safety_science |\n", encoding="utf-8"))

    class FakeLLM:
        provider = "openai_compatible"
        base_url = "https://example.com"
        def _has_auth(self):
            return True
    monkeypatch.setattr(local_review, "LLMAdapter", lambda: FakeLLM())

    result = local_review.run_local_review(pdf_dir=pdf_dir, title="Trial Review", output_dir=output_dir, skip_compile=True, timeout_seconds=5)

    assert result["status"] == "success"
    assert result["extraction_strategy"] == {
        "mode": "live",
        "paper_count": 1,
        "fallback_paper_count": 0,
        "fallback_papers": [],
        "recovered_after_retry_count": 0,
        "recovered_after_retry_papers": [],
    }
    assert result["writing_strategy"]["mode"] == "rule_based_fallback"
    assert result["writing_strategy"]["fallback_triggered"] is True
    assert result["writing_strategy"]["fallback_adopted"] is True
    assert result["writing_strategy"]["fallback_reason"] == "live_writing_validation_failed"
    assert result["writing_strategy"]["initial_validation"] == "fail"
    assert result["writing_strategy"]["final_validation"] == "pass"
    assert result["writing_strategy"]["selected_track"] == "polished"
    assert result["writing_strategy"]["selection_report"]["reason"]
    assert "Rule-based writing fallback adopted after live writing validation failed." in result["warnings"]
    assert result["outline_sections"] == 1
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["writing_strategy"]["fallback_adopted"] is True


def test_run_local_review_returns_error_when_no_profiles_extract(tmp_path, monkeypatch) -> None:
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    _write_fake_pdf(pdf_dir, "01_2001_hamed_safety_science.pdf")
    output_dir = tmp_path / "out"

    def fake_parse_pdf(pdf_path: Path, extractor) -> tuple[dict, list[dict], dict]:
        return (
            {"status": "ok", "full_text": "text", "page_count": 1},
            [{"chunk_id": f"{pdf_path.stem}-c1", "paper_id": pdf_path.stem, "section": "Body", "text": "evidence"}],
            {"title": "", "authors": [], "overall_score": 0.8},
        )

    def fake_extract_profile(*args, **kwargs):
        raise RuntimeError("LLM unavailable")

    monkeypatch.setattr(local_review, "parse_pdf", fake_parse_pdf)
    monkeypatch.setattr(local_review, "extract_profile", fake_extract_profile)

    result = local_review.run_local_review(pdf_dir=pdf_dir, title="Trial Review", output_dir=output_dir, skip_compile=True, timeout_seconds=5)

    assert result["status"] == "error"
    assert result["extracted"] == 0
    assert result["processing_errors"][0]["paper_id"] == "01_2001_hamed_safety_science"
    assert not (output_dir / "review.tex").exists()

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "error"
    assert summary["message"] == "No profiles extracted from local PDFs"


def test_run_local_review_records_dual_track_fields(tmp_path, monkeypatch) -> None:
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    real_pdf = _write_fake_pdf(pdf_dir, "01_2001_hamed_safety_science.pdf")
    output_dir = tmp_path / "out"

    monkeypatch.setattr(local_review, "parse_pdf", lambda pdf_path, extractor: ({"status": "ok", "full_text": "text", "page_count": 1}, [{"chunk_id": f"{real_pdf.stem}-c1", "paper_id": real_pdf.stem, "section": "Body", "text": "evidence"}], {"title": "", "authors": [], "overall_score": 0.9}))
    monkeypatch.setattr(local_review, "extract_profile", lambda paper_id, chunks, extractor, **kwargs: (PaperProfile(paper_id=paper_id, title="Untitled", authors=[], year=None, venue=None, research_problem="p", method_summary="m", method_family=["obs"], tasks=["crossing"], datasets=["field"], main_claims=[PaperClaim(claim_id="c1", claim_text="t", claim_type="application", evidence_chunk_ids=[chunks[0]["chunk_id"]], confidence=0.8)], limitations=[]), [_FakeLink("c1", chunks[0]["chunk_id"])], {"provider": "stub", "fallback_used": True}))
    monkeypatch.setattr(local_review, "build_coverage_report", lambda profiles: {"paper_count": 1, "themes": ["obs"]})
    monkeypatch.setattr(local_review, "build_claims_evidence_matrix", lambda profiles: [{"paper_id": profiles[0].paper_id, "claim_text": "t"}])
    monkeypatch.setattr(local_review, "detect_contradictions", lambda profiles: {"contradiction_count": 0, "contradictions": []})
    monkeypatch.setattr(local_review, "generate_candidate_gaps", lambda *args, **kwargs: [])
    monkeypatch.setattr(local_review, "verify_gaps", lambda *args, **kwargs: [])
    monkeypatch.setattr(local_review, "score_gaps", lambda *args, **kwargs: [])
    monkeypatch.setattr(local_review, "build_synthesis_map", lambda *args, **kwargs: {"overview": {}, "top_themes": []})
    monkeypatch.setattr(local_review, "select_organization", lambda *args, **kwargs: {"recommended_structure": "method_taxonomy"})
    monkeypatch.setattr(local_review, "build_outline", lambda *args, **kwargs: [{"section_id": "sec-1", "title": "Conclusion"}])
    monkeypatch.setattr(local_review, "build_section_plans", lambda *args, **kwargs: [{"section_id": "sec-1", "title": "Conclusion", "argument_moves": [{"move_id": "m1", "move_type": "synthesis"}]}])
    monkeypatch.setattr(local_review, "build_paragraph_plans", lambda *args, **kwargs: [{"section_id": "sec-1", "title": "Conclusion", "blocks": [{"block_id": "b1", "move_type": "synthesis"}]}])
    monkeypatch.setattr(local_review, "write_sections", lambda *args, **kwargs: [{"section_id": "sec-1", "title": "Conclusion", "text": "It is worth noting that closing text.", "paragraphs": [{"text": "It is worth noting that closing text.", "move_type": "synthesis", "polish_eligible": True, "citation_targets": [real_pdf.stem], "evidence_bundle": {"allowed_citation_keys": [real_pdf.stem], "required_citation_count": 0}}]}])
    monkeypatch.setattr(local_review, "ground_citations", lambda sections, matrix: [{**sections[0], "citation_keys": [real_pdf.stem], "paragraphs": [{**sections[0]["paragraphs"][0], "citation_keys": [real_pdf.stem]}]}])
    monkeypatch.setattr(local_review, "validate_review_writing", lambda **kwargs: {"summary": {"overall_status": "pass", "weak_section_count": 0, "finding_count": 0}})
    monkeypatch.setattr(local_review, "build_bib_entries", lambda matrix: [{"paper_id": real_pdf.stem, "entry": "@article{p1,title={Demo}}"}])
    monkeypatch.setattr(local_review, "prune_bib_entries", lambda entries, used_keys: entries)
    monkeypatch.setattr(local_review, "build_appendix_artifact", lambda *args, **kwargs: {"evidence_table": [{"paper_id": real_pdf.stem}]})
    monkeypatch.setattr(local_review, "build_conclusion_artifact", lambda *args, **kwargs: {"text": "Conclusion"})
    monkeypatch.setattr(local_review, "build_review_abstract", lambda *args, **kwargs: {"text": "Abstract"})
    monkeypatch.setattr(local_review, "build_review_keywords", lambda *args, **kwargs: {"keywords": ["pedestrian crossing"]})
    monkeypatch.setattr(local_review, "compose_latex", lambda *args, **kwargs: "\section{Introduction}")
    monkeypatch.setattr(local_review, "compose_review_markdown", lambda *args, **kwargs: "# Review")
    monkeypatch.setattr(local_review, "export_json", lambda path, payload: path.write_text(json.dumps(payload), encoding="utf-8"))
    monkeypatch.setattr(local_review, "export_csv", lambda path, rows: path.write_text("paper_id\n1\n", encoding="utf-8"))
    monkeypatch.setattr(local_review, "export_markdown_table", lambda path, rows: path.write_text("| paper_id |\n", encoding="utf-8"))

    result = local_review.run_local_review(pdf_dir=pdf_dir, title="Trial Review", output_dir=output_dir, skip_compile=True, timeout_seconds=5)
    assert result["dual_track"]["selected_track"] in {"safe", "polished"}
    assert result["artifacts"]["draft.json"]["exists"] is True
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert "dual_track" in summary
    assert summary["dual_track"]["safe"]["quality_metrics"]["quality_notes"] >= 0
    assert summary["dual_track"]["polished"]["quality_metrics"]["citation_retention_penalty"] == 0
    assert summary["writing_strategy"]["selected_track"] == result["dual_track"]["selected_track"]
    assert summary["writing_strategy"]["selection_report"]["reason"]
