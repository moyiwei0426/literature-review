#!/usr/bin/env python3
"""
run_review.py — End-to-end literature review pipeline.

Usage:
    python3 scripts/run_review.py --query "automated literature review NLP" --max 5

Steps:
    1. Retrieval  (OpenAlex + arXiv)
    2. Dedup
    3. PDF fetch  (arxiv only; openalex PDFs require browser)
    4. Parse      (PyMuPDF fallback)
    5. Extract    (LLM → PaperProfile)
    6. Analysis   (matrix + coverage + contradictions)
    7. Gaps       (candidate + verify + score)
    8. Writing    (outline + sections + citation grounding)
    9. LaTeX      (compose + optional compile)
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
import re

# ── path setup ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.models import PaperCandidate, PaperChunk, PaperMaster, PaperProfile
from services.analysis.coverage_analyzer import build_coverage_report
from services.analysis.contradiction_analyzer import detect_contradictions
from services.analysis.exporters import export_markdown_table
from services.analysis.gap_generator import generate_candidate_gaps
from services.analysis.gap_scorer import score_gaps
from services.analysis.gap_verifier import verify_gaps
from services.analysis.matrix_builder import build_claims_evidence_matrix
from services.analysis.synthesis_mapper import build_synthesis_map
from services.bib.bib_manager import build_bib_entries, prune_bib_entries
from services.extraction.extractor import PaperExtractor
from services.latex.compiler import LatexCompiler
from services.latex.latex_composer import compose_latex
from services.parsing.chunker import chunk_sections
from services.parsing.pdf_fetcher import PDFFetcher
from services.parsing.pymupdf_fallback import FallbackTextExtractor
from services.parsing.section_splitter import split_sections
from services.retrieval.aggregator import RetrievalAggregator
from services.retrieval.deduper import dedupe_candidates
from services.retrieval.query_builder import QueryInput, QueryPlan, build_query_plan
from services.writing.citation_grounder import ground_citations
from services.writing.conclusion_builder import build_conclusion_artifact
from services.writing.appendix_builder import build_appendix_artifact
from services.writing.abstract_builder import build_review_abstract
from services.writing.keywords_builder import build_review_keywords
from services.writing.markdown_composer import compose_review_markdown
from services.writing.organization_selector import select_organization
from services.writing.outline_planner import build_outline
from services.writing.review_validator import validate_review_writing
from services.writing.section_planner import build_section_plans
from services.writing.paragraph_planner import build_paragraph_plans
from services.writing.section_writer import write_sections
from services.writing.style_rewriter import rewrite_style
from infra.settings import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("run_review")


def _metadata_from_filename(paper_id: str) -> dict:
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


def _extract_pdf_metadata(full_text: str, paper_id: str) -> dict:
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
        m = re.search(r"(Transportation Research Part\s+[A-Z][^\n]{0,80})", first_page_text, re.I)
        if m:
            meta["venue"] = m.group(1).strip(" .")
    elif not meta.get("venue"):
        m = re.search(r"\b(Accident Analysis and Prevention|Safety Science|Transportation Research Record)\b", first_page_text, re.I)
        if m:
            meta["venue"] = m.group(1)

    if not meta.get("year"):
        years = re.findall(r"\b(19\d{2}|20\d{2})\b", first_page_text)
        if years:
            meta["year"] = int(years[0])

    return meta


def _strip(obj):
    try:
        if hasattr(obj, "model_dump"):
            return {k: _strip(v) for k, v in obj.model_dump().items()}
        if hasattr(obj, "model_dump_json"):
            import json as _json
            return _json.loads(obj.model_dump_json())
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


# ── timeout helpers ──────────────────────────────────────────────────────────
import signal

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


# ── per-step wrappers (return (success, result_or_error)) ──────────────────────
def step_retrieval(query: str, max_results: int, sources: list[str]) -> tuple[bool, dict]:
    try:
        plan = build_query_plan(QueryInput(query=query, max_results=max_results))
        plan.include_sources = sources
        agg = RetrievalAggregator()
        result = with_timeout(30, agg.run, plan)
        candidates = result["candidates"]
        log.info("  Retrieved %d candidates from %s", len(candidates), sources)
        return True, {"candidates": candidates}
    except StepTimeout:
        return False, {"error": "timeout after 30s"}
    except Exception as exc:
        return False, {"error": str(exc)}


def step_dedup(candidates: list[PaperCandidate]) -> tuple[bool, dict]:
    try:
        deduped_masters, dedup_report = with_timeout(10, dedupe_candidates, candidates)
        log.info("  Deduped %d → %d (masters)", len(candidates), len(deduped_masters))
        return True, {"deduped": deduped_masters, "dedup_report": dedup_report}
    except Exception as exc:
        return False, {"error": str(exc)}


def step_fetch_pdfs(masters_or_candidates: list, limit: int = 10) -> tuple[bool, dict]:
    """Fetch PDFs from PaperMaster or PaperCandidate list."""
    fetched = []
    count = 0
    for item in masters_or_candidates:
        if count >= limit:
            break

        # Support both PaperMaster (has pdf_candidates) and PaperCandidate (has pdf_url)
        pdf_url: Optional[str] = None
        paper_id = getattr(item, "paper_id", "unknown")

        if hasattr(item, "pdf_candidates") and item.pdf_candidates:
            pdf_url = item.pdf_candidates[0]
        elif hasattr(item, "pdf_url") and item.pdf_url:
            pdf_url = item.pdf_url
        elif hasattr(item, "arxiv_id") and item.arxiv_id:
            pdf_url = f"https://arxiv.org/pdf/{item.arxiv_id}.pdf"

        if not pdf_url:
            continue

        try:
            master = PaperMaster(
                paper_id=paper_id,
                canonical_title=getattr(item, "title", "") or "",
                normalized_title=getattr(item, "title", "") or "",
                authors=getattr(item, "authors", []) or [],
                year=getattr(item, "year", None),
                abstract=getattr(item, "abstract", None),
                arxiv_id=getattr(item, "arxiv_id", None),
                pdf_candidates=[pdf_url],
            )
            fetcher = PDFFetcher()
            result = with_timeout(30, fetcher.fetch, master)
            if result.get("status") == "downloaded":
                fetched.append({
                    "paper_id": paper_id,
                    "title": getattr(item, "title", ""),
                    "pdf_path": result.get("path"),
                    "source": getattr(item, "source", "unknown"),
                })
                count += 1
                log.info("  Downloaded PDF: %s", paper_id)
        except StepTimeout:
            log.warning("  Timeout fetching %s", paper_id)
        except Exception as exc:
            log.warning("  Failed to fetch %s: %s", paper_id, exc)

    log.info("  Fetched %d PDFs (limit=%d)", len(fetched), limit)
    return True, {"fetched": fetched}


def step_parse_and_extract(pdf_paths: list[dict]) -> tuple[bool, dict]:
    """Parse PDFs and extract PaperProfiles. Returns (profiles, parsing_errors)."""
    profiles: list[PaperProfile] = []
    parse_errors: list[dict] = []
    extractor_llm = PaperExtractor()

    for item in pdf_paths:
        paper_id = item["paper_id"]
        pdf_path = item["pdf_path"]
        if not pdf_path or not Path(pdf_path).exists():
            parse_errors.append({"paper_id": paper_id, "error": "PDF not found"})
            continue

        try:
            # Parse
            fallback = FallbackTextExtractor()
            parsed = with_timeout(20, fallback.extract, str(pdf_path))
            if parsed.get("status") != "ok":
                parse_errors.append({"paper_id": paper_id, "error": parsed.get("status", "unknown")})
                continue

            full_text = parsed.get("full_text", "")
            page_count = parsed.get("page_count", 0)

            # Chunk
            sections = [{"title": "Body", "text": full_text, "page_start": 1, "page_end": page_count}]
            chunk_dicts = chunk_sections(paper_id, sections)
            paper_chunks = [PaperChunk(**c) for c in chunk_dicts]

            # Extract profile (with internal retries + failure snapshots)
            def do_extract():
                return extractor_llm.extract(paper_id, paper_chunks, max_attempts=3)
            profile, extract_report = with_timeout(180, do_extract)
            if profile is not None:
                metadata = _extract_pdf_metadata(full_text, paper_id)
                if hasattr(profile, "model_dump"):
                    payload = profile.model_dump()
                else:
                    payload = dict(profile)
                if not payload.get("title") or payload.get("title") == "Untitled":
                    payload["title"] = metadata.get("title") or payload.get("title") or paper_id
                if not payload.get("authors"):
                    payload["authors"] = metadata.get("authors") or []
                if not payload.get("year"):
                    payload["year"] = metadata.get("year")
                if not payload.get("venue"):
                    payload["venue"] = metadata.get("venue")
                profile = PaperProfile.model_validate(payload)
                profiles.append(profile)
                log.info(
                    "  Extracted profile: %s (%d claims, attempts=%s, latency=%sms)",
                    paper_id,
                    len(profile.main_claims),
                    extract_report.get("attempts", 1),
                    extract_report.get("latency_ms", "?"),
                )
            else:
                parse_errors.append({"paper_id": paper_id, "error": "LLM returned None"})
        except StepTimeout:
            parse_errors.append({"paper_id": paper_id, "error": "timeout"})
            log.warning("  Extraction timeout: %s", paper_id)
        except Exception as exc:
            parse_errors.append({"paper_id": paper_id, "error": str(exc)})
            log.warning("  Extraction failed: %s: %s", paper_id, exc)

    log.info("  Parsed+extracted %d profiles, %d errors", len(profiles), len(parse_errors))
    return True, {"profiles": profiles, "parse_errors": parse_errors}


def step_analysis(profiles: list[PaperProfile]) -> tuple[bool, dict]:
    if not profiles:
        return False, {"error": "no profiles to analyze"}

    try:
        matrix = build_claims_evidence_matrix(profiles)
        coverage = build_coverage_report(profiles)
        contradictions = detect_contradictions(profiles)

        def do_gaps():
            cands = generate_candidate_gaps(matrix, coverage, contradictions)
            verif = verify_gaps(cands, coverage, matrix)
            scored = score_gaps(verif)
            return cands, verif, scored
        candidates, verified_gaps, gaps = with_timeout(30, do_gaps)
        synthesis_map = build_synthesis_map(
            matrix,
            coverage,
            contradictions,
            verified_gaps=verified_gaps,
            scored_gaps=gaps,
        )

        log.info("  Matrix: %d rows, Coverage: %s, Gaps: %d",
                  len(matrix), coverage.get("paper_count", "?"), len(gaps))
        return True, {
            "matrix": matrix,
            "coverage": coverage,
            "contradictions": contradictions,
            "candidate_gaps": candidates,
            "verified_gaps": verified_gaps,
            "gaps": gaps,
            "synthesis_map": synthesis_map,
        }
    except StepTimeout:
        return False, {"error": "timeout"}
    except Exception as exc:
        return False, {"error": str(exc)}


def step_write(
    gaps: list,
    verified_gaps: list,
    matrix: list,
    title: str,
    compile_pdf: bool,
    profiles: list | None = None,
    synthesis_map: dict | None = None,
    organization: dict | None = None,
) -> tuple[bool, dict]:
    if not gaps or not matrix:
        return False, {"error": "no gaps or matrix"}

    try:
        effective_gaps = verified_gaps or gaps
        outline = with_timeout(30, build_outline, effective_gaps, matrix, synthesis_map=synthesis_map, organization=organization)
        section_plans = with_timeout(
            30,
            build_section_plans,
            outline,
            matrix,
            effective_gaps,
            synthesis_map=synthesis_map,
            organization=organization,
        )
        paragraph_plans = with_timeout(
            30,
            build_paragraph_plans,
            section_plans,
            matrix,
            effective_gaps,
            synthesis_map=synthesis_map,
            organization=organization,
        )
        sections = with_timeout(
            60,
            write_sections,
            outline,
            matrix,
            effective_gaps,
            synthesis_map=synthesis_map,
            organization=organization,
        )
        grounded = with_timeout(30, ground_citations, sections, matrix)
        rewritten = with_timeout(30, rewrite_style, grounded)
        validation_report = with_timeout(
            30,
            validate_review_writing,
            outline,
            section_plans,
            paragraph_plans,
            sections,
            grounded,
            rewritten,
            verified_gaps or gaps,
        )

        bib = build_bib_entries(matrix)
        used_keys = []
        for s in grounded:
            used_keys.extend(s.get("citation_keys", []))
        pruned = prune_bib_entries(bib, used_keys)

        appendix = build_appendix_artifact(
            matrix,
            profiles=profiles or [],
            verified_gaps=verified_gaps or gaps,
            synthesis_map=synthesis_map,
            organization=organization,
        )
        conclusion = build_conclusion_artifact(
            matrix,
            verified_gaps or gaps,
            synthesis_map=synthesis_map,
            organization=organization,
        )
        abstract = build_review_abstract(
            title,
            matrix,
            synthesis_map=synthesis_map,
            organization=organization,
            verified_gaps=verified_gaps or gaps,
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

        log.info("  Writing: %d sections, %d bib entries, tex=%d chars",
                 len(rewritten), len(pruned), len(tex))
        log.info(
            "  Validation: %s (%d weak sections, %d findings)",
            validation_report.get("summary", {}).get("overall_status", validation_report.get("status", "unknown")),
            validation_report.get("summary", {}).get("weak_section_count", 0),
            validation_report.get("summary", {}).get("finding_count", 0),
        )
        return True, {
            "outline": outline, "sections": rewritten, "bib": pruned,
            "section_plans": section_plans,
            "paragraph_plans": paragraph_plans,
            "validation": validation_report.get("summary", {}),
            "abstract": abstract,
            "keywords": keywords,
            "appendix": appendix,
            "evidence_table": appendix.get("evidence_table", []),
            "markdown": markdown,
            "tex": tex,
            "validation_report": validation_report,
            "compile_result": {},
        }
    except StepTimeout:
        return False, {"error": "timeout"}
    except Exception as exc:
        return False, {"error": str(exc)}


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="End-to-end literature review pipeline")
    parser.add_argument("--query", "-q", default=None, help="Search query (required for online mode)")
    parser.add_argument("--max", "-m", type=int, default=5, help="Max candidates to fetch (default 5)")
    parser.add_argument("--max-pdfs", type=int, default=5, help="Max PDFs to download (default 5)")
    parser.add_argument("--title", default="ARIS-Lit Literature Review", help="Review title")
    parser.add_argument("--project", default=None, help="Project name (used in output dir)")
    parser.add_argument("--sources", default="openalex,arxiv", help="Comma-separated sources")
    parser.add_argument("--no-compile", action="store_true", help="Skip LaTeX compilation")
    parser.add_argument("--output-dir", default=None, help="Override output directory")
    # Local PDF mode
    parser.add_argument("--mode", default="online", choices=["online", "local"], help="Pipeline mode: online (retrieve) or local (existing PDFs)")
    parser.add_argument("--pdf-dir", type=Path, default=None, help="Directory containing local PDFs (for --mode local)")
    parser.add_argument("--max-papers", type=int, default=None, help="Max papers to process locally")
    args = parser.parse_args()

    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    project = args.project or f"review_{datetime.now():%Y%m%d_%H%M%S}"
    settings = get_settings()
    output_dir = Path(args.output_dir) if args.output_dir else settings.data_dir / "generated" / f"e2e_{project}"
    output_dir.mkdir(parents=True, exist_ok=True)

    log.info("=== ARIS-Lit End-to-End Review ===")
    if args.mode == "local":
        log.info("Mode: LOCAL | PDF dir: %s | Output: %s", args.pdf_dir, output_dir)
    else:
        log.info("Query: %s | Sources: %s | Max PDFs: %d | Output: %s",
                 args.query, sources, args.max_pdfs, output_dir)

    steps: list[tuple[str, bool, dict]] = []
    report: dict = {"project": project, "query": args.query, "mode": args.mode, "steps": []}

    if args.mode == "local":
        # Local mode: skip retrieval/dedup/fetch, go straight to parse
        pdf_dir = args.pdf_dir or settings.data_dir / "manual_uploads"
        # Exclude non-review PDFs (cli-demo-paper.pdf is a demo artifact)
        exclude_names = {"cli-demo-paper"}
        pdf_paths = sorted([p for p in Path(pdf_dir).glob("*.pdf") if p.stem not in exclude_names])
        if args.max_papers:
            pdf_paths = pdf_paths[:args.max_papers]
        log.info("Found %d local PDFs in %s", len(pdf_paths), pdf_dir)

        fetched = [{"paper_id": p.stem, "title": p.stem, "pdf_path": str(p)} for p in pdf_paths]
        ok4, res4 = step_parse_and_extract(fetched)
        steps.append(("extract", ok4, res4))
        report["steps"].append({"name": "extract", "ok": ok4, **_strip(res4)})
        profiles = res4.get("profiles", [])
    else:
        # Online mode: full pipeline
        if not args.query:
            log.error("--query is required for online mode")
            sys.exit(1)

        # Step 1: Retrieval
        ok, res = step_retrieval(args.query, args.max, sources)
        steps.append(("retrieval", ok, res))
        report["steps"].append({"name": "retrieval", "ok": ok, **res})
        if not ok or not res.get("candidates"):
            log.error("Retrieval failed or returned no candidates: %s", res)
            print(json.dumps(report, indent=2, ensure_ascii=False))
            sys.exit(1)

        # Step 2: Dedup
        candidates = res["candidates"]
        ok2, res2 = step_dedup(candidates)
        steps.append(("dedup", ok2, res2))
        report["steps"].append({"name": "dedup", "ok": ok2, **res2})
        deduped = res2.get("deduped", candidates)

        # Step 3: Fetch PDFs
        ok3, res3 = step_fetch_pdfs(deduped, limit=args.max_pdfs)
        steps.append(("fetch", ok3, res3))
        report["steps"].append({"name": "fetch", "ok": ok3, **res3})

        # Step 4: Parse + Extract
        ok4, res4 = step_parse_and_extract(res3.get("fetched", []))
        steps.append(("extract", ok4, res4))
        report["steps"].append({"name": "extract", "ok": ok4, **_strip(res4)})
        profiles = res4.get("profiles", [])

    if not profiles:
        log.error("No profiles extracted. Check PDF fetch step.")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        sys.exit(1)

    # Step 5: Analysis + Gap
    ok5, res5 = step_analysis(profiles)
    steps.append(("analysis", ok5, res5))
    report["steps"].append({"name": "analysis", "ok": ok5, **res5})

    gaps = res5.get("gaps", []) if ok5 else []
    matrix = res5.get("matrix", []) if ok5 else []
    synthesis_map = res5.get("synthesis_map", {}) if ok5 else {}
    organization = select_organization(synthesis_map, matrix) if synthesis_map else {}
    if synthesis_map:
        report["synthesis_map"] = _strip(synthesis_map)
    if organization:
        report["organization"] = organization

    # Step 6: Writing
    compile_pdf = not args.no_compile
    ok6, res6 = step_write(
        gaps,
        res5.get("verified_gaps", []) if ok5 else [],
        matrix,
        args.title,
        compile_pdf,
        profiles=profiles,
        synthesis_map=synthesis_map,
        organization=organization,
    )
    steps.append(("writing", ok6, res6))
    report["steps"].append({"name": "writing", "ok": ok6, **res6})
    if ok6 and res6.get("validation"):
        report["validation"] = _strip(res6["validation"])

    # Save outputs
    if ok6 and res6:
        (output_dir / "outline.json").write_text(json.dumps(res6["outline"], ensure_ascii=False, indent=2))
        (output_dir / "section_plans.json").write_text(json.dumps(res6.get("section_plans", []), ensure_ascii=False, indent=2))
        (output_dir / "paragraph_plans.json").write_text(json.dumps(res6.get("paragraph_plans", []), ensure_ascii=False, indent=2))
        (output_dir / "sections.json").write_text(json.dumps(res6["sections"], ensure_ascii=False, indent=2))
        (output_dir / "bib.json").write_text(json.dumps(res6["bib"], ensure_ascii=False, indent=2))
        (output_dir / "abstract.json").write_text(json.dumps(res6.get("abstract", {}), ensure_ascii=False, indent=2))
        (output_dir / "abstract.txt").write_text(str((res6.get("abstract") or {}).get("text", "")), encoding="utf-8")
        (output_dir / "keywords.json").write_text(json.dumps(res6.get("keywords", {}), ensure_ascii=False, indent=2), encoding="utf-8")
        (output_dir / "keywords.txt").write_text("\n".join((res6.get("keywords") or {}).get("keywords", [])), encoding="utf-8")
        (output_dir / "appendix.json").write_text(json.dumps(res6.get("appendix", {}), ensure_ascii=False, indent=2))
        (output_dir / "evidence_table.json").write_text(json.dumps(res6.get("evidence_table", []), ensure_ascii=False, indent=2))
        export_markdown_table(output_dir / "evidence_table.md", res6.get("evidence_table", []))
        (output_dir / "review.md").write_text(res6.get("markdown", ""), encoding="utf-8")
        (output_dir / "review.tex").write_text(res6["tex"], encoding="utf-8")
        (output_dir / "validation_report.json").write_text(json.dumps(res6.get("validation_report", {}), ensure_ascii=False, indent=2))
        log.info("  LaTeX saved to %s/review.tex", output_dir)
        if compile_pdf:
            compile_result = LatexCompiler().compile(output_dir / "review.tex")
            res6["compile_result"] = compile_result
            report["steps"][-1]["compile_result"] = compile_result
            report["compile_result"] = compile_result

        # Save analysis results
    if ok5 and res5:
        (output_dir / "matrix.json").write_text(json.dumps(res5["matrix"], ensure_ascii=False, indent=2))
        (output_dir / "coverage.json").write_text(json.dumps(res5["coverage"], ensure_ascii=False, indent=2))
        (output_dir / "candidate_gaps.json").write_text(json.dumps(res5.get("candidate_gaps", []), ensure_ascii=False, indent=2))
        (output_dir / "verified_gaps.json").write_text(json.dumps(res5.get("verified_gaps", []), ensure_ascii=False, indent=2))
        (output_dir / "gaps.json").write_text(json.dumps(res5["gaps"], ensure_ascii=False, indent=2))
        (output_dir / "synthesis_map.json").write_text(json.dumps(res5.get("synthesis_map", {}), ensure_ascii=False, indent=2))
        (output_dir / "organization.json").write_text(json.dumps(organization, ensure_ascii=False, indent=2))

    # Save report — strip Pydantic objects before JSON serialization
    report_copy = _strip(report)
    if ok6 and res6.get("validation_report"):
        report_copy["validation"] = _strip(res6["validation_report"].get("summary", res6["validation_report"]))
    (output_dir / "report.json").write_text(json.dumps(report_copy, indent=2, ensure_ascii=False))

    # Summary
    log.info("")
    log.info("=== Summary ===")
    for name, ok, _ in steps:
        status = "✅" if ok else "❌"
        log.info("  %s %s", status, name)
    log.info("  Output: %s", output_dir)

    print(json.dumps(report_copy, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
