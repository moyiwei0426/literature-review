#!/usr/bin/env python3
"""
run_local_review.py — End-to-end literature review from LOCAL PDFs.

Usage:
    python3 scripts/run_local_review.py --pdf-dir data/manual_uploads --title "Pedestrian Crossing Behavior Review"

Steps:
    1. Parse     (FallbackTextExtractor → chunks)
    2. Extract   (PaperExtractor → PaperProfile + claims)
    3. Analysis  (coverage + matrix + contradictions)
    4. Gaps      (candidate + verify + score)
    5. Writing   (outline + sections + citation grounding + LaTeX)

Output: data/generated/review_{timestamp}/
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.models import PaperCandidate, PaperChunk, PaperMaster, PaperProfile
from services.analysis.coverage_analyzer import build_coverage_report
from services.analysis.contradiction_analyzer import detect_contradictions
from services.analysis.exporters import export_csv, export_json, export_markdown_table
from services.analysis.gap_generator import generate_candidate_gaps
from services.analysis.gap_scorer import score_gaps
from services.analysis.gap_verifier import verify_gaps
from services.analysis.matrix_builder import build_claims_evidence_matrix
from services.analysis.synthesis_mapper import build_synthesis_map
from services.bib.bib_manager import build_bib_entries, prune_bib_entries
from services.extraction.claim_linker import build_claim_evidence_links
from services.extraction.extractor import PaperExtractor
from services.extraction.storage import ExtractionStorage
from services.latex.compiler import LatexCompiler
from services.latex.latex_composer import compose_latex
from services.llm.adapter import LLMAdapter
from services.parsing.chunker import chunk_sections
from services.parsing.pymupdf_fallback import FallbackTextExtractor
from services.parsing.quality_scorer import score_parse_quality
from services.parsing.section_splitter import split_sections
from services.parsing.storage import ParsingStorage
from services.writing.appendix_builder import build_appendix_artifact
from services.writing.abstract_builder import build_review_abstract
from services.writing.citation_grounder import ground_citations
from services.writing.conclusion_builder import build_conclusion_artifact
from services.writing.keywords_builder import build_review_keywords
from services.writing.markdown_composer import compose_review_markdown
from services.writing.organization_selector import select_organization
from services.writing.outline_planner import build_outline
from services.writing.review_validator import validate_review_writing
from services.writing.section_planner import build_section_plans
from services.writing.paragraph_planner import build_paragraph_plans
from services.writing.section_writer import write_sections
from services.writing.style_rewriter import rewrite_style
from storage.repositories.entities import PapersRepository, ChunksRepository, ProfilesRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("run_local_review")


def _attach_run_log(output_dir: Path) -> Path:
    log_path = output_dir / "run.log"
    resolved = str(log_path.resolve())
    for handler in log.handlers:
        if isinstance(handler, logging.FileHandler) and getattr(handler, "baseFilename", None) == resolved:
            return log_path

    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    log.addHandler(handler)
    return log_path


class StepTimeout(Exception):
    pass


def _sigalrm_handler(signum, frame):
    raise StepTimeout()


def with_timeout(seconds: int, func, *args, **kwargs):
    old = signal.signal(signal.SIGALRM, _sigalrm_handler)
    signal.alarm(seconds)
    try:
        return func(*args, **kwargs)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def _metadata_from_filename(paper_id: str) -> dict[str, object]:
    parts = paper_id.split("_")
    year = None
    if len(parts) > 1 and parts[1].isdigit():
        year = int(parts[1])
    venue = " ".join(parts[3:]).replace("_", " ").strip() if len(parts) > 3 else None
    return {
        "year": year,
        "authors": [parts[2].capitalize()] if len(parts) > 2 and parts[2] else [],
        "venue": venue or None,
    }


def _extract_pdf_metadata(full_text: str, paper_id: str) -> dict[str, object]:
    meta = _metadata_from_filename(paper_id)
    lines = [line.strip() for line in full_text.splitlines() if line.strip()]
    first_page_text = "\n".join(lines[:40])

    if lines:
        title_candidates = []
        for line in lines[:12]:
            compact = " ".join(line.split())
            if len(compact) < 20 or len(compact) > 220:
                continue
            if re.search(r"^(abstract|keywords?|introduction|references)\b", compact, re.I):
                continue
            if re.search(r"@|doi|www\.|http", compact, re.I):
                continue
            title_candidates.append(compact)
        if title_candidates:
            meta["title"] = max(title_candidates, key=len)

    lowered = first_page_text.lower()
    if "transportation research part" in lowered and not meta.get("venue"):
        match = re.search(r"(Transportation Research Part\s+[A-Z][^\n]{0,80})", first_page_text, re.I)
        if match:
            meta["venue"] = match.group(1).strip(" .")
    elif not meta.get("venue"):
        match = re.search(r"\b(Accident Analysis and Prevention|Safety Science|Transportation Research Record)\b", first_page_text, re.I)
        if match:
            meta["venue"] = match.group(1)

    if not meta.get("year"):
        years = re.findall(r"\b(19\d{2}|20\d{2})\b", first_page_text)
        if years:
            meta["year"] = int(years[0])

    return meta


def _enrich_profile_metadata(profile: PaperProfile, metadata: dict[str, object], paper_id: str) -> PaperProfile:
    payload = profile.model_dump(mode="json")
    if not payload.get("title") or payload.get("title") == "Untitled":
        payload["title"] = metadata.get("title") or payload.get("title") or paper_id
    if not payload.get("authors"):
        payload["authors"] = metadata.get("authors") or []
    if not payload.get("year"):
        payload["year"] = metadata.get("year")
    if not payload.get("venue"):
        payload["venue"] = metadata.get("venue")
    return PaperProfile.model_validate(payload)


def _strip(obj):
    try:
        if hasattr(obj, "model_dump"):
            return {k: _strip(v) for k, v in obj.model_dump().items()}
        if hasattr(obj, "model_dump_json"):
            return json.loads(obj.model_dump_json())
        if isinstance(obj, list):
            return [_strip(i) for i in obj]
        if isinstance(obj, dict):
            return {k: _strip(v) for k, v in obj.items()}
        if hasattr(obj, "value") and isinstance(obj.value, (str, int, float, bool)):
            return obj.value
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        return str(obj)
    except Exception:
        return str(type(obj).__name__)


def _artifact_manifest(output_dir: Path, compile_result: dict | None = None) -> dict[str, dict[str, object]]:
    names = [
        "artifacts.json",
        "summary.json",
        "coverage.json",
        "matrix.json",
        "matrix.csv",
        "matrix.md",
        "contradiction.json",
        "candidate_gaps.json",
        "verified_gaps.json",
        "scored_gaps.json",
        "synthesis_map.json",
        "organization.json",
        "outline.json",
        "section_plans.json",
        "paragraph_plans.json",
        "sections.json",
        "validation_report.json",
        "review.md",
        "review.tex",
        "bib.tex",
        "abstract.json",
        "abstract.txt",
        "keywords.json",
        "keywords.txt",
        "appendix.json",
        "evidence_table.json",
        "evidence_table.md",
    ]
    if compile_result:
        names.append("review.pdf")

    manifest: dict[str, dict[str, object]] = {}
    for name in names:
        path = output_dir / name
        manifest[name] = {
            "path": str(path),
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() else 0,
        }
    return manifest


def parse_pdf(pdf_path: Path, extractor: FallbackTextExtractor) -> tuple[dict, list[dict], dict]:
    """Parse PDF and return (raw_parsed, chunks, quality_report)."""
    log.info("  Parsing: %s", pdf_path.name)
    parsed = extractor.extract(str(pdf_path))
    
    pseudo_parsed = {
        "abstract": None,
        "sections": [
            {
                "title": "Body",
                "text": parsed.get("full_text", ""),
                "page_start": 1,
                "page_end": parsed.get("page_count"),
            }
        ],
    }
    sections = split_sections(pseudo_parsed)
    paper_id = pdf_path.stem  # filename without extension
    chunks = chunk_sections(paper_id, sections)
    report = score_parse_quality({**pseudo_parsed, "sections": sections}, chunks)
    
    log.info("    → %d pages, %d chunks, quality=%.2f", 
              parsed.get("page_count", 0), len(chunks), report.get("overall_score", 0))
    return parsed, chunks, report


def extract_profile(
    paper_id: str,
    chunks: list[dict],
    extractor: PaperExtractor,
    *,
    parsed: dict | None = None,
    timeout_seconds: int = 180,
) -> tuple[PaperProfile, list[dict], dict]:
    """Extract PaperProfile from chunks."""
    log.info("  Extracting: %s", paper_id)
    chunk_objs = [PaperChunk.model_validate(c) for c in chunks]
    metadata = _extract_pdf_metadata(str((parsed or {}).get("full_text") or ""), paper_id)

    try:
        profile, report = with_timeout(timeout_seconds, extractor.extract, paper_id, chunk_objs)
        report = {**report, "fallback_used": False}
    except Exception as exc:
        log.warning("    primary extraction failed for %s, retrying with stub LLM: %s", paper_id, exc)
        stub_extractor = PaperExtractor(llm=LLMAdapter(provider="stub", model="stub-model"))
        profile, report = with_timeout(timeout_seconds, stub_extractor.extract, paper_id, chunk_objs)
        report = {
            **report,
            "fallback_used": True,
            "fallback_reason": str(exc),
            "primary_provider": getattr(extractor.llm, "provider", "unknown"),
        }

    profile = _enrich_profile_metadata(profile, metadata, paper_id)
    links = build_claim_evidence_links(profile)
    log.info("    → %d claims, %d links", len(profile.main_claims), len(links))
    return profile, links, report


def run_local_review(
    pdf_dir: Path,
    title: str,
    output_dir: Optional[Path] = None,
    skip_compile: bool = False,
    max_papers: Optional[int] = None,
    timeout_seconds: int = 180,
) -> dict:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = output_dir or PROJECT_ROOT / "data" / "generated" / f"local_review_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    run_log_path = _attach_run_log(output_dir)
    log.info("Output: %s", output_dir)
    log.info("Run log: %s", run_log_path)

    # Find PDFs
    exclude_names = {"cli-demo-paper"}
    pdfs = sorted([path for path in pdf_dir.glob("*.pdf") if path.stem not in exclude_names])
    if max_papers:
        pdfs = pdfs[:max_papers]
    log.info("Found %d PDFs in %s", len(pdfs), pdf_dir)

    if not pdfs:
        log.warning("No PDFs found!")
        return {"status": "error", "message": "No PDFs found"}

    extractor = FallbackTextExtractor()
    paper_extractor = PaperExtractor()
    parsing_storage = ParsingStorage()
    extraction_storage = ExtractionStorage()
    papers_repo = PapersRepository()
    chunks_repo = ChunksRepository()
    profiles_repo = ProfilesRepository()

    all_profiles = []
    all_matrix_rows = []
    processing_errors = []
    extraction_reports = []
    parsed_count = 0
    extracted_count = 0

    for pdf_path in pdfs:
        try:
            # Step 1: Parse
            paper_id = pdf_path.stem
            parsed, chunks, report = with_timeout(timeout_seconds, parse_pdf, pdf_path, extractor)
            
            # Save parsed results
            parsing_storage.save_parsed(paper_id, parsed)
            parsing_storage.save_chunks(paper_id, chunks)
            parsing_storage.save_quality_report(paper_id, report)
            papers_repo.save(paper_id, {
                "paper_id": paper_id,
                "title": report.get("title", paper_id),
                "authors": report.get("authors", []),
                "sources": ["local"],
            })
            chunks_repo.save(paper_id, chunks)
            parsed_count += 1

            # Step 2: Extract
            profile, links, extract_report = extract_profile(
                paper_id,
                chunks,
                paper_extractor,
                parsed=parsed,
                timeout_seconds=timeout_seconds,
            )
            extraction_storage.save_profile(paper_id, profile.model_dump(mode="json"))
            extraction_storage.save_claims(paper_id, [c.model_dump(mode="json") for c in profile.main_claims])
            extraction_storage.save_links(paper_id, [l.model_dump(mode="json") for l in links])
            extraction_storage.save_report(paper_id, {"claim_count": len(profile.main_claims), "link_count": len(links)})
            profiles_repo.save(paper_id, profile.model_dump(mode="json"))
            all_profiles.append(profile)
            extraction_reports.append({"paper_id": paper_id, **_strip(extract_report)})
            extracted_count += 1

            # Add to matrix rows
            for chunk in chunks:
                all_matrix_rows.append({
                    "paper_id": paper_id,
                    "chunk_id": chunk.get("chunk_id", ""),
                    "text": chunk.get("text", "")[:500],
                    "section": chunk.get("section", ""),
                })

        except Exception as e:
            log.error("  Error processing %s: %s", pdf_path.name, e)
            processing_errors.append({"paper_id": pdf_path.stem, "pdf_path": str(pdf_path), "error": str(e)})
            continue

    if not all_profiles:
        result = {
            "status": "error",
            "message": "No profiles extracted from local PDFs",
            "output_dir": str(output_dir),
            "run_log": str(run_log_path),
            "parsed": parsed_count,
            "extracted": extracted_count,
            "processing_errors": processing_errors,
            "extraction_reports": extraction_reports,
        }
        (output_dir / "summary.json").write_text(json.dumps(_strip(result), ensure_ascii=False, indent=2), encoding="utf-8")
        log.error("No profiles extracted; aborting review generation.")
        return result

    log.info("\n=== Step 3: Analysis ===")
    coverage = build_coverage_report(all_profiles)
    matrix = build_claims_evidence_matrix(all_profiles)
    contradiction = detect_contradictions(all_profiles)

    export_json(output_dir / "coverage.json", coverage)
    export_json(output_dir / "matrix.json", matrix)
    export_csv(output_dir / "matrix.csv", matrix)
    export_markdown_table(output_dir / "matrix.md", matrix)
    export_json(output_dir / "contradiction.json", contradiction)

    log.info("  Coverage: %d papers, %d themes", coverage["paper_count"], len(coverage.get("themes", [])))
    log.info("  Matrix: %d rows", len(matrix))
    log.info("  Contradictions: %d", contradiction["contradiction_count"])

    log.info("\n=== Step 4: Gap Analysis ===")
    candidates = generate_candidate_gaps(matrix, coverage, contradiction)
    verified = verify_gaps(candidates, coverage, matrix)
    scored = score_gaps(verified)
    synthesis_map = build_synthesis_map(
        matrix,
        coverage,
        contradiction,
        verified_gaps=verified,
        scored_gaps=scored,
    )
    organization = select_organization(synthesis_map, matrix)

    export_json(output_dir / "candidate_gaps.json", candidates)
    export_json(output_dir / "verified_gaps.json", verified)
    export_json(output_dir / "scored_gaps.json", scored)
    export_json(output_dir / "synthesis_map.json", synthesis_map)
    export_json(output_dir / "organization.json", organization)
    log.info("  %d candidates → %d verified → %d scored", len(candidates), len(verified), len(scored))
    log.info("  Organization: %s", organization.get("recommended_structure"))

    log.info("\n=== Step 5: Writing ===")
    writing_strategy = {
        "mode": "live" if not os.environ.get("ARIS_LIT_FORCE_STUB") else "rule_based",
        "fallback_triggered": False,
        "fallback_adopted": False,
        "fallback_reason": None,
        "initial_validation": None,
        "final_validation": None,
    }
    outline = build_outline(verified or scored, matrix, synthesis_map=synthesis_map, organization=organization)
    section_plans = build_section_plans(
        outline,
        matrix,
        verified,
        synthesis_map=synthesis_map,
        organization=organization,
    )
    paragraph_plans = build_paragraph_plans(
        section_plans,
        matrix,
        verified,
        synthesis_map=synthesis_map,
        organization=organization,
    )
    sections = write_sections(
        outline,
        matrix,
        verified,
        synthesis_map=synthesis_map,
        organization=organization,
    )
    grounded = ground_citations(sections, matrix)
    rewritten = rewrite_style(grounded)
    validation_report = validate_review_writing(
        outline=outline,
        section_plans=section_plans,
        paragraph_plans=paragraph_plans,
        drafted_sections=sections,
        grounded_sections=grounded,
        rewritten_sections=rewritten,
        verified_gaps=verified,
    )
    writing_strategy["initial_validation"] = validation_report.get("summary", {}).get("overall_status", validation_report.get("status"))
    llm = LLMAdapter()
    if (
        validation_report.get("summary", {}).get("overall_status") == "fail"
        and llm.provider != "stub"
        and llm.base_url
        and llm._has_auth()
        and not os.environ.get("ARIS_LIT_FORCE_STUB")
    ):
        writing_strategy["fallback_triggered"] = True
        writing_strategy["fallback_reason"] = "live_writing_validation_failed"
        log.warning("  Live writing validation failed; retrying writing stack with rule-based fallback.")
        old_force_stub = os.environ.get("ARIS_LIT_FORCE_STUB")
        os.environ["ARIS_LIT_FORCE_STUB"] = "1"
        try:
            outline_fb = build_outline(verified or scored, matrix, synthesis_map=synthesis_map, organization=organization)
            section_plans_fb = build_section_plans(
                outline_fb,
                matrix,
                verified,
                synthesis_map=synthesis_map,
                organization=organization,
            )
            paragraph_plans_fb = build_paragraph_plans(
                section_plans_fb,
                matrix,
                verified,
                synthesis_map=synthesis_map,
                organization=organization,
            )
            sections_fb = write_sections(
                outline_fb,
                matrix,
                verified,
                synthesis_map=synthesis_map,
                organization=organization,
            )
            grounded_fb = ground_citations(sections_fb, matrix)
            rewritten_fb = rewrite_style(grounded_fb)
            validation_fb = validate_review_writing(
                outline=outline_fb,
                section_plans=section_plans_fb,
                paragraph_plans=paragraph_plans_fb,
                drafted_sections=sections_fb,
                grounded_sections=grounded_fb,
                rewritten_sections=rewritten_fb,
                verified_gaps=verified,
            )
        finally:
            if old_force_stub is None:
                os.environ.pop("ARIS_LIT_FORCE_STUB", None)
            else:
                os.environ["ARIS_LIT_FORCE_STUB"] = old_force_stub

        current_failings = int(validation_report.get("summary", {}).get("finding_count", 0) or 0)
        fallback_failings = int(validation_fb.get("summary", {}).get("finding_count", 0) or 0)
        if fallback_failings <= current_failings:
            outline = outline_fb
            section_plans = section_plans_fb
            paragraph_plans = paragraph_plans_fb
            sections = sections_fb
            grounded = grounded_fb
            rewritten = rewritten_fb
            validation_report = validation_fb
            writing_strategy["fallback_adopted"] = True
            writing_strategy["mode"] = "rule_based_fallback"
            log.info(
                "  Adopted rule-based writing fallback (%s → %s findings).",
                current_failings,
                fallback_failings,
            )
    writing_strategy["final_validation"] = validation_report.get("summary", {}).get("overall_status", validation_report.get("status"))
    bib_entries = build_bib_entries(matrix)
    used_keys = []
    for section in grounded:
        used_keys.extend(section.get("citation_keys", []))
    pruned = prune_bib_entries(bib_entries, used_keys)
    # Convert to BibTeX string for writing
    bib_tex_str = "\n\n".join(entry.get("entry", "") for entry in pruned)
    appendix = build_appendix_artifact(
        matrix,
        profiles=all_profiles,
        verified_gaps=verified,
        synthesis_map=synthesis_map,
        organization=organization,
    )
    conclusion = build_conclusion_artifact(
        matrix,
        verified,
        synthesis_map=synthesis_map,
        organization=organization,
    )
    abstract = build_review_abstract(
        title,
        matrix,
        synthesis_map=synthesis_map,
        organization=organization,
        verified_gaps=verified,
        conclusion=conclusion,
        appendix=appendix,
    )
    keywords = build_review_keywords(
        matrix,
        synthesis_map=synthesis_map,
        organization=organization,
        appendix=appendix,
        abstract=abstract,
    )
    tex = compose_latex(title, rewritten, pruned, appendix=appendix, abstract=abstract, keywords=keywords)
    markdown = compose_review_markdown(
        title,
        rewritten,
        abstract=abstract,
        keywords=keywords,
        appendix=appendix,
    )

    (output_dir / "outline.json").write_text(json.dumps(outline, ensure_ascii=False, indent=2))
    (output_dir / "section_plans.json").write_text(json.dumps(section_plans, ensure_ascii=False, indent=2))
    (output_dir / "paragraph_plans.json").write_text(json.dumps(paragraph_plans, ensure_ascii=False, indent=2))
    (output_dir / "sections.json").write_text(json.dumps(rewritten, ensure_ascii=False, indent=2))
    (output_dir / "validation_report.json").write_text(json.dumps(validation_report, ensure_ascii=False, indent=2))
    (output_dir / "bib.tex").write_text(bib_tex_str, encoding="utf-8")
    (output_dir / "abstract.json").write_text(json.dumps(abstract, ensure_ascii=False, indent=2))
    (output_dir / "abstract.txt").write_text(abstract.get("text", ""), encoding="utf-8")
    (output_dir / "keywords.json").write_text(json.dumps(keywords, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "keywords.txt").write_text("\n".join(keywords.get("keywords", [])), encoding="utf-8")
    (output_dir / "appendix.json").write_text(json.dumps(appendix, ensure_ascii=False, indent=2))
    (output_dir / "evidence_table.json").write_text(json.dumps(appendix.get("evidence_table", []), ensure_ascii=False, indent=2))
    export_markdown_table(output_dir / "evidence_table.md", appendix.get("evidence_table", []))
    (output_dir / "review.md").write_text(markdown, encoding="utf-8")
    (output_dir / "review.tex").write_text(tex, encoding="utf-8")
    log.info("  %d outline sections, %d bib entries", len(outline), len(pruned))
    log.info(
        "  Validation: %s (%d weak sections, %d findings)",
        validation_report.get("summary", {}).get("overall_status", validation_report.get("status", "unknown")),
        validation_report.get("summary", {}).get("weak_section_count", 0),
        validation_report.get("summary", {}).get("finding_count", 0),
    )

    compile_result = None
    if not skip_compile:
        log.info("\n=== Step 6: LaTeX Compilation ===")
        compiler = LatexCompiler()
        compile_result = compiler.compile(output_dir / "review.tex")
        log.info("  Compile: %s", compile_result.get("status", "unknown"))

    extraction_strategy = {
        "mode": "live" if any(report.get("provider") not in {None, "stub"} for report in extraction_reports) else "rule_based",
        "paper_count": len(extraction_reports),
        "fallback_paper_count": len([report for report in extraction_reports if report.get("fallback_used")]),
        "fallback_papers": [report["paper_id"] for report in extraction_reports if report.get("fallback_used")],
        "recovered_after_retry_count": len([report for report in extraction_reports if report.get("recovered_after_retry")]),
        "recovered_after_retry_papers": [report["paper_id"] for report in extraction_reports if report.get("recovered_after_retry")],
    }

    warnings = []
    fallback_papers = extraction_strategy["fallback_papers"]
    if fallback_papers:
        warnings.append(
            f"Stub extraction fallback used for {len(fallback_papers)} paper(s): {', '.join(fallback_papers[:5])}"
        )
    if processing_errors:
        warnings.append(f"{len(processing_errors)} paper(s) failed during processing.")
    if writing_strategy.get("fallback_adopted"):
        warnings.append(
            "Rule-based writing fallback adopted after live writing validation failed."
        )

    result = {
        "status": "success",
        "output_dir": str(output_dir),
        "run_log": str(run_log_path),
        "parsed": parsed_count,
        "extracted": extracted_count,
        "processing_errors": processing_errors,
        "extraction_reports": extraction_reports,
        "coverage": coverage,
        "matrix_rows": len(matrix),
        "contradictions": contradiction["contradiction_count"],
        "gaps": {
            "candidates": len(candidates),
            "verified": len(verified),
            "scored": len(scored),
        },
        "synthesis_map": synthesis_map,
        "organization": organization,
        "extraction_strategy": extraction_strategy,
        "writing_strategy": writing_strategy,
        "abstract": abstract,
        "keywords": keywords,
        "outline_sections": len(outline),
        "bib_entries": len(pruned),
        "validation": validation_report.get("summary", {}),
        "compile": compile_result,
        "warnings": warnings,
    }

    # Save summary
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(_strip(result), ensure_ascii=False, indent=2), encoding="utf-8")
    artifacts_path = output_dir / "artifacts.json"
    artifacts = _artifact_manifest(output_dir, compile_result=compile_result)
    artifacts_path.write_text(json.dumps(artifacts, ensure_ascii=False, indent=2), encoding="utf-8")
    artifacts = _artifact_manifest(output_dir, compile_result=compile_result)
    result["artifacts"] = artifacts
    artifacts_path.write_text(json.dumps(artifacts, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_path.write_text(json.dumps(_strip(result), ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("\n=== Done! Output: %s ===", output_dir)
    return result


def main():
    parser = argparse.ArgumentParser(description="Run literature review on local PDFs")
    parser.add_argument("--pdf-dir", "-i", type=Path, required=True, help="Directory containing PDFs")
    parser.add_argument("--title", "-t", default="Local Literature Review", help="Review title")
    parser.add_argument("--output-dir", "-o", type=Path, default=None, help="Output directory")
    parser.add_argument("--no-compile", action="store_true", help="Skip LaTeX compilation")
    parser.add_argument("--max-papers", "-m", type=int, default=None, help="Max papers to process")
    parser.add_argument("--timeout", type=int, default=600, help="Timeout per paper (seconds)")
    
    args = parser.parse_args()
    
    result = run_local_review(
        pdf_dir=args.pdf_dir,
        title=args.title,
        output_dir=args.output_dir,
        skip_compile=args.no_compile,
        max_papers=args.max_papers,
        timeout_seconds=args.timeout,
    )
    print(json.dumps(_strip(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
