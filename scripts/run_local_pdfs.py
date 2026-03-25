#!/usr/bin/env python3
"""
run_local_pdfs.py — ARIS-Lit pipeline for locally-uploaded PDFs.

Usage:
    python3 scripts/run_local_pdfs.py \
        --input-dir data/manual_uploads/ \
        --output-dir data/generated/review_2026_03_22/

Steps:
    1. Parse PDFs  → FallbackTextExtractor + chunker
    2. Extract     → PaperExtractor (PaperProfile + claims)
    3. Analysis    → coverage_report + matrix + contradictions
    4. Gap         → gap_generator + gap_verifier + gap_scorer
    5. Writing     → outline_planner + section_writer + citation_grounder
    6. LaTeX       → compose_latex
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import signal
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.models import PaperChunk, PaperProfile
from services.analysis.coverage_analyzer import build_coverage_report
from services.analysis.contradiction_analyzer import detect_contradictions
from services.analysis.gap_generator import generate_candidate_gaps
from services.analysis.gap_scorer import score_gaps
from services.analysis.gap_verifier import verify_gaps
from services.analysis.matrix_builder import build_claims_evidence_matrix
from services.bib.bib_manager import build_bib_entries, prune_bib_entries
from services.extraction.extractor import PaperExtractor
from services.latex.latex_composer import compose_latex
from services.parsing.chunker import chunk_sections
from services.parsing.pymupdf_fallback import FallbackTextExtractor
from services.writing.citation_grounder import ground_citations
from services.writing.outline_planner import build_outline
from services.writing.section_planner import build_section_plans
from services.writing.paragraph_planner import build_paragraph_plans
from services.writing.section_writer import write_sections
from services.writing.style_rewriter import rewrite_style

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("run_local_pdfs")


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


def extract_paper_id_from_filename(filename: str) -> str:
    """Extract paper ID from filename like '01_2001_hamed_safety_science.pdf'"""
    return Path(filename).stem


def load_checkpoint(checkpoint_dir: Path, paper_id: str) -> Optional[PaperProfile]:
    checkpoint_file = checkpoint_dir / f"{paper_id}.json"
    if not checkpoint_file.exists():
        return None
    try:
        data = json.loads(checkpoint_file.read_text(encoding="utf-8"))
        return PaperProfile.model_validate(data)
    except Exception:
        return None


def save_checkpoint(checkpoint_dir: Path, profile: PaperProfile) -> None:
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_file = checkpoint_dir / f"{profile.paper_id}.json"
    checkpoint_file.write_text(
        json.dumps(profile.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_profiles_snapshot(output_dir: Path, profiles: list[PaperProfile]) -> None:
    profiles_data = [p.model_dump() for p in profiles]
    (output_dir / "profiles.json").write_text(
        json.dumps(profiles_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def process_pdf(pdf_path: Path, extractor_llm: PaperExtractor, timeout: int = 60) -> Optional[PaperProfile]:
    """Parse a PDF and extract PaperProfile."""
    try:
        fallback = FallbackTextExtractor()
        parsed = with_timeout(timeout, fallback.extract, str(pdf_path))
        if parsed.get("status") != "ok":
            log.warning("  Parse failed for %s: %s", pdf_path.name, parsed.get("status"))
            return None

        full_text = parsed.get("full_text", "")
        page_count = parsed.get("page_count", 0)

        # Chunk
        sections = [{"title": "Body", "text": full_text, "page_start": 1, "page_end": page_count}]
        chunk_dicts = chunk_sections(pdf_path.stem, sections)
        paper_chunks = [PaperChunk(**c) for c in chunk_dicts]

        # Extract
        def do_extract():
            return extractor_llm.extract(pdf_path.stem, paper_chunks)

        profile, _ = with_timeout(timeout, do_extract)
        if profile is not None:
            if hasattr(profile, "model_dump"):
                profile = PaperProfile.model_validate(profile.model_dump())
        return profile
    except StepTimeout:
        log.warning("  Timeout processing %s", pdf_path.name)
        return None
    except Exception as exc:
        log.warning("  Error processing %s: %s", pdf_path.name, exc)
        return None


def main():
    parser = argparse.ArgumentParser(description="ARIS-Lit pipeline for local PDFs")
    parser.add_argument("--input-dir", required=True, help="Directory containing PDF files")
    parser.add_argument("--output-dir", required=True, help="Output directory for generated files")
    parser.add_argument("--title", default="ARIS-Lit Literature Review", help="Review title")
    parser.add_argument("--max-pdfs", type=int, default=0, help="Max PDFs to process (0=all)")
    parser.add_argument("--parse-timeout", type=int, default=30, help="Timeout per PDF parsing (seconds)")
    parser.add_argument("--extract-timeout", type=int, default=90, help="Timeout per LLM extraction (seconds)")
    parser.add_argument("--no-compile", action="store_true", help="Skip LaTeX compilation")
    parser.add_argument("--resume", action="store_true", help="Resume from per-paper checkpoints")
    args = parser.parse_args()

    input_dir = Path(args.input_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    checkpoint_dir = output_dir / "checkpoints"
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # Find PDFs: only numbered batch files, exclude demo PDFs
    pdf_files = sorted(
        p for p in input_dir.glob("*.pdf")
        if re.match(r"^\d{2}_.+\.pdf$", p.name)
    )
    if not pdf_files:
        log.error("No PDF files found in %s", input_dir)
        sys.exit(1)

    if args.max_pdfs > 0:
        pdf_files = pdf_files[:args.max_pdfs]

    log.info("=== ARIS-Lit Local PDF Pipeline ===")
    log.info("Input: %s (%d PDFs)", input_dir, len(pdf_files))
    log.info("Output: %s", output_dir)

    report: dict = {"input_dir": str(input_dir), "output_dir": str(output_dir), "pdfs": []}

    # ── Step 1+2: Parse + Extract ───────────────────────────────────────────
    log.info("\n[Step 1+2] Parse PDFs + Extract PaperProfiles...")
    extractor_llm = PaperExtractor()
    profiles: list[PaperProfile] = []
    parse_errors: list[dict] = []

    for pdf_path in pdf_files:
        paper_id = pdf_path.stem
        if args.resume:
            existing = load_checkpoint(checkpoint_dir, paper_id)
            if existing is not None:
                profiles.append(existing)
                log.info("  ↻ Resumed: %s | %s | %d claims",
                         existing.paper_id, existing.title or "(no title)",
                         len(existing.main_claims))
                continue

        log.info("  Processing: %s", pdf_path.name)
        profile = process_pdf(pdf_path, extractor_llm, timeout=args.extract_timeout)
        if profile:
            profiles.append(profile)
            save_checkpoint(checkpoint_dir, profile)
            save_profiles_snapshot(output_dir, profiles)
            log.info("  ✓ Extracted: %s | %s | %d claims",
                     profile.paper_id, profile.title or "(no title)",
                     len(profile.main_claims))
        else:
            parse_errors.append({"file": pdf_path.name, "error": "extraction failed or timeout"})
            log.warning("  ✗ Failed: %s", pdf_path.name)

    log.info("\n  Profiles extracted: %d / %d", len(profiles), len(pdf_files))

    if not profiles:
        log.error("No profiles extracted. Aborting.")
        sys.exit(1)

    save_profiles_snapshot(output_dir, profiles)

    # ── Step 3: Analysis ─────────────────────────────────────────────────────
    log.info("\n[Step 3] Analysis: coverage + matrix + contradictions...")
    try:
        matrix = build_claims_evidence_matrix(profiles)
        log.info("  Matrix: %d rows", len(matrix))

        coverage = build_coverage_report(profiles)
        log.info("  Coverage: %d papers, methods=%s, tasks=%s",
                 coverage["paper_count"],
                 list(coverage["method_family_distribution"].keys())[:3],
                 list(coverage["task_distribution"].keys())[:3])

        contradictions = detect_contradictions(profiles)
        log.info("  Contradictions: %d pairs found", len(contradictions))
    except Exception as exc:
        log.error("  Analysis failed: %s", exc)
        matrix, coverage, contradictions = [], {}, []

    # Save analysis
    (output_dir / "matrix.json").write_text(json.dumps(matrix, ensure_ascii=False, indent=2))
    (output_dir / "coverage.json").write_text(json.dumps(coverage, ensure_ascii=False, indent=2))
    (output_dir / "contradictions.json").write_text(json.dumps(contradictions, ensure_ascii=False, indent=2))

    # ── Step 4: Gap Analysis ─────────────────────────────────────────────────
    log.info("\n[Step 4] Gap analysis: generate + verify + score...")
    try:
        gaps_candidates = generate_candidate_gaps(matrix, coverage, contradictions)
        log.info("  Candidates: %d", len(gaps_candidates))

        gaps_verified = verify_gaps(gaps_candidates, coverage, matrix)
        log.info("  Verified: %d", len(gaps_verified))

        gaps_scored = score_gaps(gaps_verified)
        log.info("  Scored: %d", len(gaps_scored))
    except Exception as exc:
        log.error("  Gap analysis failed: %s", exc)
        gaps_candidates = []
        gaps_verified = []
        gaps_scored = []

    if gaps_scored:
        (output_dir / "gaps.json").write_text(json.dumps(gaps_scored, ensure_ascii=False, indent=2))
    else:
        log.warning("  No gaps generated; using empty list for writing step")

    # ── Step 5: Writing ───────────────────────────────────────────────────────
    log.info("\n[Step 5] Writing: outline + sections + citation grounding...")
    try:
        outline = with_timeout(60, build_outline, gaps_verified or gaps_scored, matrix)
        log.info("  Outline: %d sections", len(outline))
        section_plans = with_timeout(30, build_section_plans, outline, matrix, gaps_verified or gaps_scored)
        paragraph_plans = with_timeout(30, build_paragraph_plans, section_plans, matrix, gaps_verified or gaps_scored)

        sections = with_timeout(120, write_sections, outline, matrix, gaps_verified or gaps_scored)
        log.info("  Sections written: %d", len(sections))

        grounded = with_timeout(60, ground_citations, sections, matrix)
        log.info("  Citations grounded: %d sections", len(grounded))

        rewritten = with_timeout(60, rewrite_style, grounded)
        log.info("  Style rewritten: %d sections", len(rewritten))
    except StepTimeout:
        log.error("  Writing step timed out")
        outline, section_plans, paragraph_plans, sections, grounded, rewritten = [], [], [], [], [], []
    except Exception as exc:
        log.error("  Writing failed: %s", exc)
        outline, section_plans, paragraph_plans, sections, grounded, rewritten = [], [], [], [], [], []

    if rewritten:
        (output_dir / "outline.json").write_text(json.dumps(outline, ensure_ascii=False, indent=2))
        (output_dir / "section_plans.json").write_text(json.dumps(section_plans, ensure_ascii=False, indent=2))
        (output_dir / "paragraph_plans.json").write_text(json.dumps(paragraph_plans, ensure_ascii=False, indent=2))
        (output_dir / "sections.json").write_text(json.dumps(rewritten, ensure_ascii=False, indent=2))
    else:
        log.warning("  No written sections; skipping writing output files")

    # ── Step 6: LaTeX ─────────────────────────────────────────────────────────
    log.info("\n[Step 6] LaTeX composition...")
    if rewritten:
        try:
            bib = build_bib_entries(matrix)
            used_keys = []
            for s in grounded:
                used_keys.extend(s.get("citation_keys", []))
            pruned_bib = prune_bib_entries(bib, used_keys)
            log.info("  Bib entries: %d total, %d used", len(bib), len(pruned_bib))

            from services.bib.bib_manager import prune_bib_entries as _prune
            pruned_bib = _prune(bib, used_keys)

            tex = compose_latex(args.title, rewritten, pruned_bib)
            (output_dir / "review.tex").write_text(tex, encoding="utf-8")
            log.info("  LaTeX saved: %d chars", len(tex))

            compile_result = {}
            if not args.no_compile:
                try:
                    from services.latex.compiler import LatexCompiler
                    compile_result = with_timeout(30, LatexCompiler().compile, tex)
                    log.info("  Compile: %s", compile_result.get("status", "unknown"))
                except Exception as exc:
                    log.warning("  Compile failed: %s", exc)
                    compile_result = {"status": "error", "log": str(exc)}
        except Exception as exc:
            log.error("  LaTeX composition failed: %s", exc)
            tex = ""
            compile_result = {}
    else:
        log.warning("  Skipping LaTeX (no sections written)")
        tex = ""
        compile_result = {}

    # ── Final Report ──────────────────────────────────────────────────────────
    report["steps"] = {
        "parse_extract": {"ok": len(profiles) > 0, "profiles": len(profiles), "errors": len(parse_errors)},
        "analysis": {"ok": bool(matrix), "matrix_rows": len(matrix)},
        "gap": {"ok": bool(gaps_scored), "gaps": len(gaps_scored)},
        "writing": {"ok": bool(rewritten), "sections": len(rewritten)},
        "latex": {"ok": bool(tex), "chars": len(tex)},
    }
    report["profiles_errors"] = parse_errors

    (output_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))

    log.info("\n=== Pipeline Complete ===")
    log.info("  Output: %s", output_dir)
    log.info("  Profiles: %d | Matrix rows: %d | Gaps: %d | Sections: %d",
             len(profiles), len(matrix), len(gaps_scored), len(rewritten))
    log.info("  Files: %s", [f.name for f in sorted(output_dir.iterdir())])

    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
