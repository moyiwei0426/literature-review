from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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
from services.bib.bib_manager import build_bib_entries, prune_bib_entries
from services.extraction.claim_linker import build_claim_evidence_links
from services.extraction.extractor import PaperExtractor
from services.extraction.storage import ExtractionStorage
from services.parsing.chunker import chunk_sections
from services.parsing.pdf_fetcher import PDFFetcher
from services.parsing.pymupdf_fallback import FallbackTextExtractor
from services.parsing.quality_scorer import score_parse_quality
from services.parsing.section_splitter import split_sections
from services.parsing.storage import ParsingStorage
from services.retrieval.aggregator import RetrievalAggregator
from services.retrieval.local_watcher import LocalPDFWatcher
from services.retrieval.deduper import dedupe_candidates
from services.retrieval.query_builder import QueryInput, build_query_plan
from services.writing.citation_grounder import ground_citations
from services.writing.outline_planner import build_outline
from services.writing.section_writer import write_sections
from services.writing.style_rewriter import rewrite_style
from services.latex.latex_composer import compose_latex
from services.latex.compiler import LatexCompiler
from storage.repositories.entities import PapersRepository, ChunksRepository, ProfilesRepository, GapsRepository, DraftsRepository


def cmd_run_local_review(args: argparse.Namespace) -> None:
    import subprocess, sys
    cmd = [sys.executable, str(PROJECT_ROOT / "scripts" / "run_local_review.py")]
    if args.pdf_dir:
        cmd += ["--pdf-dir", str(args.pdf_dir)]
    if args.title:
        cmd += ["--title", args.title]
    if args.output_dir:
        cmd += ["--output-dir", str(args.output_dir)]
    if args.no_compile:
        cmd += ["--no-compile"]
    if args.max_papers:
        cmd += ["--max-papers", str(args.max_papers)]
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    sys.exit(result.returncode)


def cmd_init_project(args: argparse.Namespace) -> None:
    target = PROJECT_ROOT / "data" / "generated" / args.name
    target.mkdir(parents=True, exist_ok=True)
    print(f"Initialized project workspace: {target}")


def cmd_show_status(args: argparse.Namespace) -> None:
    status_path = PROJECT_ROOT / "progress" / "STATUS.md"
    if status_path.exists():
        print(status_path.read_text(encoding="utf-8"))
    else:
        print("STATUS.md not found")


def cmd_run_retrieval(args: argparse.Namespace) -> None:
    plan = build_query_plan(QueryInput(query=args.query, max_results=args.max_results))
    result = RetrievalAggregator().run(plan)
    print(json.dumps({
        "count": result["count"],
        "sources": result["sources"],
        "titles": [item.title for item in result["candidates"][:5]],
    }, ensure_ascii=False, indent=2))


def _load_candidates(path: str) -> list[PaperCandidate]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return [PaperCandidate.model_validate(item) for item in payload]


def _load_chunks(path: str) -> list[PaperChunk]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return [PaperChunk.model_validate(item) for item in payload]


def _load_profiles(path: str) -> list[PaperProfile]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = [payload]
    return [PaperProfile.model_validate(item) for item in payload]


def cmd_run_dedup(args: argparse.Namespace) -> None:
    candidates = _load_candidates(args.input)
    masters, report = dedupe_candidates(candidates)
    output_dir = PROJECT_ROOT / "data" / "generated" / "dedup"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "masters.json").write_text(
        json.dumps([item.model_dump() for item in masters], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "dedup_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


def cmd_run_parsing_demo(args: argparse.Namespace) -> None:
    paper = PaperMaster(
        paper_id=args.paper_id,
        canonical_title=args.title or args.paper_id,
        normalized_title=(args.title or args.paper_id).lower(),
        authors=[],
        sources=["cli"],
        pdf_candidates=[args.pdf_url],
    )
    fetch_result = PDFFetcher().fetch(paper)
    print("fetch_result:", json.dumps(fetch_result, ensure_ascii=False, indent=2))
    if fetch_result.get("status") != "downloaded":
        return

    parsed = FallbackTextExtractor().extract(fetch_result["path"])
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
    chunks = chunk_sections(paper.paper_id, sections)
    report = score_parse_quality({**pseudo_parsed, "sections": sections}, chunks)

    storage = ParsingStorage()
    storage.save_parsed(paper.paper_id, parsed)
    storage.save_chunks(paper.paper_id, chunks)
    storage.save_quality_report(paper.paper_id, report)

    PapersRepository().save(paper.paper_id, paper.model_dump(mode="json"))
    ChunksRepository().save(paper.paper_id, chunks)

    print(json.dumps({
        "paper_id": paper.paper_id,
        "page_count": parsed.get("page_count"),
        "chunk_count": len(chunks),
        "quality": report,
    }, ensure_ascii=False, indent=2))


def cmd_run_extraction_demo(args: argparse.Namespace) -> None:
    chunks = _load_chunks(args.input)
    paper_id = args.paper_id or (chunks[0].paper_id if chunks else "demo-paper")
    profile, report = PaperExtractor().extract(paper_id, chunks)
    links = build_claim_evidence_links(profile)
    storage = ExtractionStorage()
    storage.save_profile(paper_id, profile.model_dump(mode="json"))
    storage.save_claims(paper_id, [claim.model_dump(mode="json") for claim in profile.main_claims])
    storage.save_links(paper_id, [link.model_dump(mode="json") for link in links])
    storage.save_report(paper_id, report)
    ProfilesRepository().save(paper_id, profile.model_dump(mode="json"))
    print(json.dumps({
        "paper_id": paper_id,
        "claim_count": len(profile.main_claims),
        "link_count": len(links),
        "report": report,
    }, ensure_ascii=False, indent=2))


def cmd_run_analysis_demo(args: argparse.Namespace) -> None:
    profiles = _load_profiles(args.input)
    coverage = build_coverage_report(profiles)
    matrix = build_claims_evidence_matrix(profiles)
    contradiction = detect_contradictions(profiles)
    out_dir = PROJECT_ROOT / "data" / "generated" / "analysis_cli"
    out_dir.mkdir(parents=True, exist_ok=True)
    export_json(out_dir / "coverage.json", coverage)
    export_json(out_dir / "matrix.json", matrix)
    export_csv(out_dir / "matrix.csv", matrix)
    export_markdown_table(out_dir / "matrix.md", matrix)
    export_json(out_dir / "contradiction.json", contradiction)
    for profile in profiles:
        ProfilesRepository().save(profile.paper_id, profile.model_dump(mode="json"))
    print(json.dumps({
        "paper_count": coverage["paper_count"],
        "matrix_rows": len(matrix),
        "contradiction_count": contradiction["contradiction_count"],
    }, ensure_ascii=False, indent=2))


def cmd_run_gap_demo(args: argparse.Namespace) -> None:
    coverage = json.loads(Path(args.coverage).read_text(encoding="utf-8"))
    contradiction = json.loads(Path(args.contradiction).read_text(encoding="utf-8"))
    # matrix can be json exported manually; for csv users should convert first. keep MVP simple.
    matrix = json.loads(Path(args.matrix).read_text(encoding="utf-8"))
    candidates = generate_candidate_gaps(matrix, coverage, contradiction)
    verified = verify_gaps(candidates, coverage, matrix)
    scored = score_gaps(verified)
    out_dir = PROJECT_ROOT / "data" / "generated" / "gap_cli"
    out_dir.mkdir(parents=True, exist_ok=True)
    export_json(out_dir / "candidate_gaps.json", candidates)
    export_json(out_dir / "verified_gaps.json", verified)
    export_json(out_dir / "scored_gaps.json", scored)
    GapsRepository().save("latest", {"candidate_gaps": candidates, "verified_gaps": verified, "scored_gaps": scored})
    print(json.dumps({
        "candidate_count": len(candidates),
        "verified_count": len(verified),
        "scored_count": len(scored),
    }, ensure_ascii=False, indent=2))


def cmd_run_writing_demo(args: argparse.Namespace) -> None:
    verified_gaps = json.loads(Path(args.gaps).read_text(encoding="utf-8"))
    matrix = json.loads(Path(args.matrix).read_text(encoding="utf-8"))
    outline = build_outline(verified_gaps, matrix)
    sections = write_sections(outline, matrix, verified_gaps)
    grounded = ground_citations(sections, matrix)
    rewritten = rewrite_style(grounded)
    bib_entries = build_bib_entries(matrix)
    used_keys = []
    for section in grounded:
        used_keys.extend(section.get("citation_keys", []))
    pruned = prune_bib_entries(bib_entries, used_keys)
    tex = compose_latex(args.title, rewritten, pruned)
    out_dir = PROJECT_ROOT / "data" / "generated" / "writing_cli"
    out_dir.mkdir(parents=True, exist_ok=True)
    tex_path = out_dir / "review.tex"
    tex_path.write_text(tex, encoding="utf-8")
    compile_result = LatexCompiler().compile(tex_path)
    DraftsRepository().save("latest", {"outline": outline, "sections": rewritten, "bib_entries": pruned, "tex": tex, "compile_result": compile_result})
    print(json.dumps({
        "outline_sections": len(outline),
        "written_sections": len(rewritten),
        "bib_entries": len(pruned),
        "compile_result": compile_result,
    }, ensure_ascii=False, indent=2))


def cmd_watch_local_pdfs(args: argparse.Namespace) -> None:
    watch_dir = Path(args.watch_dir) if args.watch_dir else None
    watcher = LocalPDFWatcher(watch_dir=watch_dir)
    watcher.watch(interval=args.interval)


def cmd_scan_local_pdfs(args: argparse.Namespace) -> None:
    watch_dir = Path(args.watch_dir) if args.watch_dir else None
    watcher = LocalPDFWatcher(watch_dir=watch_dir)
    results = watcher.scan()
    print(json.dumps({
        "processed": len(results),
        "results": results,
    }, ensure_ascii=False, indent=2))


def cmd_run_review(args: argparse.Namespace) -> None:
    """Delegates to scripts/run_review.py."""
    import subprocess, sys
    cmd = [sys.executable, str(PROJECT_ROOT / "scripts" / "run_review.py")]
    # Forward relevant args
    if args.mode:
        cmd += ["--mode", args.mode]
    if args.query:
        cmd += ["--query", args.query]
    if args.max:
        cmd += ["--max", str(args.max)]
    if args.max_pdfs:
        cmd += ["--max-pdfs", str(args.max_pdfs)]
    if args.title:
        cmd += ["--title", args.title]
    if args.project:
        cmd += ["--project", args.project]
    if args.no_compile:
        cmd += ["--no-compile"]
    if args.output_dir:
        cmd += ["--output-dir", str(args.output_dir)]
    if args.pdf_dir:
        cmd += ["--pdf-dir", str(args.pdf_dir)]
    if args.max_papers:
        cmd += ["--max-papers", str(args.max_papers)]
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    sys.exit(result.returncode)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aris-lit")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_init = subparsers.add_parser("init-project", help="Initialize a local project workspace")
    p_init.add_argument("name", help="Project name")
    p_init.set_defaults(func=cmd_init_project)

    p_status = subparsers.add_parser("show-status", help="Show current project status")
    p_status.set_defaults(func=cmd_show_status)

    p_retrieval = subparsers.add_parser("run-retrieval", help="Run retrieval")
    p_retrieval.add_argument("--query", required=True, help="Search query")
    p_retrieval.add_argument("--max-results", type=int, default=20)
    p_retrieval.set_defaults(func=cmd_run_retrieval)

    p_dedup = subparsers.add_parser("run-dedup", help="Run dedup on a candidates JSON file")
    p_dedup.add_argument("--input", required=True, help="Path to candidate JSON file")
    p_dedup.set_defaults(func=cmd_run_dedup)

    p_parse = subparsers.add_parser("run-parsing-demo", help="Download a PDF and run fallback parsing")
    p_parse.add_argument("--paper-id", required=True)
    p_parse.add_argument("--pdf-url", required=True)
    p_parse.add_argument("--title", default=None)
    p_parse.set_defaults(func=cmd_run_parsing_demo)

    p_extract = subparsers.add_parser("run-extraction-demo", help="Run extraction on a chunk JSON file")
    p_extract.add_argument("--input", required=True)
    p_extract.add_argument("--paper-id", default=None)
    p_extract.set_defaults(func=cmd_run_extraction_demo)

    p_analysis = subparsers.add_parser("run-analysis-demo", help="Run analysis on a profile JSON file")
    p_analysis.add_argument("--input", required=True)
    p_analysis.set_defaults(func=cmd_run_analysis_demo)

    p_gap = subparsers.add_parser("run-gap-demo", help="Run gap generation on JSON analysis outputs")
    p_gap.add_argument("--coverage", required=True)
    p_gap.add_argument("--matrix", required=True)
    p_gap.add_argument("--contradiction", required=True)
    p_gap.set_defaults(func=cmd_run_gap_demo)

    p_writing = subparsers.add_parser("run-writing-demo", help="Run writing demo from verified gaps and matrix JSON")
    p_writing.add_argument("--gaps", required=True)
    p_writing.add_argument("--matrix", required=True)
    p_writing.add_argument("--title", default="ARIS-Lit Demo Review")
    p_writing.set_defaults(func=cmd_run_writing_demo)

    p_watch = subparsers.add_parser("watch-local-pdfs", help="Watch local PDF folder and process new files (blocks indefinitely)")
    p_watch.add_argument("--watch-dir", default=None, help="Path to watch for new PDFs")
    p_watch.add_argument("--interval", type=int, default=10, help="Scan interval in seconds")
    p_watch.set_defaults(func=cmd_watch_local_pdfs)

    p_scan = subparsers.add_parser("scan-local-pdfs", help="Scan local PDF folder once (cron-friendly)")
    p_scan.add_argument("--watch-dir", default=None, help="Path to watch for new PDFs")
    p_scan.set_defaults(func=cmd_scan_local_pdfs)

    p_local = subparsers.add_parser("run-local-review", help="End-to-end from LOCAL PDFs: parse → extract → analysis → gaps → writing")
    p_local.add_argument("--pdf-dir", "-i", required=True, help="Directory containing PDFs")
    p_local.add_argument("--title", "-t", default="Local Literature Review", help="Review title")
    p_local.add_argument("--output-dir", "-o", default=None, help="Output directory")
    p_local.add_argument("--no-compile", action="store_true", help="Skip LaTeX compilation")
    p_local.add_argument("--max-papers", "-m", type=int, default=None, help="Max papers to process")
    p_local.set_defaults(func=cmd_run_local_review)

    p_review = subparsers.add_parser("run-review", help="End-to-end: retrieval → parse → extract → writing")
    p_review.add_argument("--query", "-q", default=None, help="Search query (required for online mode, optional for local)")
    p_review.add_argument("--max", "-m", type=int, default=5, help="Max candidates to retrieve (default 5)")
    p_review.add_argument("--max-pdfs", type=int, default=5, help="Max PDFs to download (default 5)")
    p_review.add_argument("--title", default="ARIS-Lit Literature Review", help="Review title")
    p_review.add_argument("--project", default=None, help="Project name (output dir)")
    p_review.add_argument("--no-compile", action="store_true", help="Skip LaTeX compilation")
    p_review.add_argument("--output-dir", default=None, help="Override output directory")
    p_review.add_argument("--mode", default="online", choices=["online", "local"], help="Pipeline mode: online (retrieve) or local (existing PDFs)")
    p_review.add_argument("--pdf-dir", default=None, help="Directory containing local PDFs (for --mode local)")
    p_review.add_argument("--max-papers", type=int, default=None, help="Max papers to process locally")
    p_review.set_defaults(func=cmd_run_review)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
