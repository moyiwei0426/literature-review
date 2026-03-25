from __future__ import annotations

import json
import signal
import time
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Optional, Callable, Any

from core.models import PaperChunk, PaperProfile
from infra.settings import get_settings
from services.analysis.coverage_analyzer import build_coverage_report
from services.analysis.contradiction_analyzer import detect_contradictions
from services.analysis.gap_generator import generate_candidate_gaps
from services.analysis.gap_scorer import score_gaps
from services.analysis.gap_verifier import verify_gaps
from services.analysis.matrix_builder import build_claims_evidence_matrix
from services.extraction.extractor import PaperExtractor
from services.parsing.chunker import chunk_sections
from services.parsing.pymupdf_fallback import FallbackTextExtractor
from services.parsing.section_splitter import split_sections
from services.writing.citation_grounder import ground_citations
from services.writing.outline_planner import build_outline
from services.writing.section_writer import write_sections


class TimeoutError(Exception):
    """Raised when a step exceeds its time budget."""


def _timeout_handler(signum, frame):
    raise TimeoutError()


def _run_with_timeout(func: Callable[..., Any], *args: Any, timeout_secs: int = 30, **kwargs: Any) -> Any:
    """Run func with a SIGALRM timeout. On timeout, raises TimeoutError."""
    old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(timeout_secs)
    try:
        result = func(*args, **kwargs)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
    return result


def _safe_call(func: Callable[..., Any], fallback: Any, timeout_secs: int = 30, **kwargs: Any) -> Any:
    """Call func with timeout; return fallback on timeout or exception."""
    try:
        return _run_with_timeout(func, timeout_secs=timeout_secs, **kwargs)
    except (TimeoutError, Exception) as exc:
        print(f"    [timeout/warn] {func.__name__}: {exc}")
        return fallback


class LocalPDFWatcher:
    """Monitor a local directory for new PDFs and process them through the full pipeline.

    Usage:
        watcher = LocalPDFWatcher()
        watcher.scan()           # Run once (cron-friendly)
        watcher.watch(interval=5) # Loop indefinitely (blocks)
    """

    def __init__(self, watch_dir: Optional[Path] = None) -> None:
        settings = get_settings()
        self.watch_dir = watch_dir or settings.local_watch_dir
        self.watch_dir.mkdir(parents=True, exist_ok=True)
        self.processed_marker = self.watch_dir / ".processed"
        self._load_processed()

    def _load_processed(self) -> None:
        if self.processed_marker.exists():
            self.processed: set[str] = set(json.loads(self.processed_marker.read_text()))
        else:
            self.processed = set()
        self._save_processed()

    def _save_processed(self) -> None:
        self.processed_marker.write_text(json.dumps(sorted(self.processed)))

    def _paper_id_from_path(self, path: Path) -> str:
        return path.stem.replace(" ", "_").replace(",", "")

    def process_pdf(self, pdf_path: Path) -> dict:
        """Process a single local PDF: parse → extract → analysis → gap → writing."""
        paper_id = self._paper_id_from_path(pdf_path)
        print(f"  Processing: {paper_id} from {pdf_path.name}")

        # Step 1: Parse (PyMuPDF fallback)
        extractor = FallbackTextExtractor()
        parsed = extractor.extract(str(pdf_path))
        if parsed.get("status") != "ok":
            return {"paper_id": paper_id, "step": "parse", "status": "failed", "error": parsed.get("status")}

        full_text = parsed.get("full_text", "")
        page_count = parsed.get("page_count", 0)

        # Step 2: Section split + Chunk
        pseudo_parsed = {
            "abstract": None,
            "sections": [
                {
                    "title": "Body",
                    "text": full_text,
                    "page_start": 1,
                    "page_end": page_count,
                }
            ],
        }
        sections = split_sections(pseudo_parsed)
        chunk_dicts = chunk_sections(paper_id, sections)

        # Step 3: Extract profile (LLM) — 60s budget
        paper_chunks = [PaperChunk(**c) for c in chunk_dicts]
        extractor_llm = PaperExtractor()

        def _do_extract():
            return extractor_llm.extract(paper_id, paper_chunks)

        profile, extraction_report = _safe_call(_do_extract, fallback=(None, {}), timeout_secs=60)

        profile_pydantic: Optional[PaperProfile] = None
        profile_dict: dict = {}
        if profile is not None:
            if hasattr(profile, "model_dump"):
                profile_pydantic = profile
                profile_dict = profile.model_dump()
            else:
                profile_dict = dict(profile)
        else:
            profile_dict = {"paper_id": paper_id, "error": "extraction returned None"}

        # Step 4: Analysis — rule-based components are fast; LLM gaps get a budget
        analysis_result: dict = {"paper_id": paper_id}
        if profile_pydantic is not None:
            try:
                profiles = [profile_pydantic]
                matrix = build_claims_evidence_matrix(profiles)
                coverage = build_coverage_report(profiles)
                contradictions = detect_contradictions(profiles)
                # Gap generation/verification use LLM; give them 30s each
                gaps = _safe_call(generate_candidate_gaps, [], timeout_secs=30,
                                  matrix=matrix, coverage=coverage, contradiction=contradictions)
                verified = _safe_call(verify_gaps, gaps, timeout_secs=30,
                                      candidate_gaps=gaps, coverage=coverage, matrix=matrix)
                scored = _safe_call(score_gaps, verified, timeout_secs=10, gaps=verified)
                analysis_result = {
                    "paper_id": paper_id,
                    "matrix": matrix,
                    "coverage": coverage,
                    "contradictions": contradictions,
                    "gaps": scored,
                }
            except Exception as exc:
                analysis_result["analysis_error"] = str(exc)

        # Step 5: Writing — 60s budget
        writing_result: dict = {}
        matrix = analysis_result.get("matrix", [])
        gaps = analysis_result.get("gaps", [])
        if matrix and gaps:
            try:
                def _do_writing():
                    outline = build_outline(gaps, matrix)
                    sections_w = write_sections(outline, matrix, gaps)
                    grounded = ground_citations(sections_w, matrix)
                    return {"outline": outline, "sections": grounded}
                writing_result = _safe_call(_do_writing, fallback={}, timeout_secs=60)
            except Exception as exc:
                writing_result = {"writing_error": str(exc)}

        # Save all results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = get_settings().data_dir / "generated" / f"local_{paper_id}"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"parsed_{timestamp}.json").write_text(
            json.dumps(parsed, ensure_ascii=False, indent=2)
        )
        (out_dir / "profile.json").write_text(
            json.dumps(profile_dict, ensure_ascii=False, indent=2)
        )
        (out_dir / "analysis.json").write_text(
            json.dumps(analysis_result, ensure_ascii=False, indent=2)
        )
        if writing_result:
            (out_dir / "writing.json").write_text(
                json.dumps(writing_result, ensure_ascii=False, indent=2)
            )

        self.processed.add(pdf_path.name)
        self._save_processed()

        return {
            "paper_id": paper_id,
            "status": "done",
            "pages": page_count,
            "text_chars": len(full_text),
            "chunks": len(chunk_dicts),
            "has_profile": "error" not in profile_dict,
            "has_analysis": "analysis_error" not in analysis_result,
            "has_writing": bool(writing_result) and "writing_error" not in writing_result,
        }

    def scan(self) -> list[dict]:
        """Scan watch directory once and process new PDFs."""
        results = []
        pdf_files = sorted(
            f for f in self.watch_dir.iterdir()
            if f.suffix.lower() == ".pdf" and f.name not in self.processed
        )
        if not pdf_files:
            print(f"No new PDFs in {self.watch_dir}")
            return []

        print(f"Found {len(pdf_files)} new PDF(s) in {self.watch_dir}")
        for pdf_path in pdf_files:
            try:
                result = self.process_pdf(pdf_path)
                results.append(result)
                status = "✅" if result.get("status") == "done" else "❌"
                print(f"  {status} {result.get('paper_id')}: {result.get('status')}")
            except Exception as exc:
                print(f"  ❌ {pdf_path.name}: {exc}")
                results.append({"paper_id": pdf_path.stem, "status": "error", "error": str(exc)})

        return results

    def watch(self, interval: int = 10) -> None:
        """Run indefinitely as a background daemon, scanning every `interval` seconds.

        This method is designed to be run as a subprocess (e.g. via nohup or &).
        It blocks forever, printing progress to stdout/stderr.
        """
        import logging
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
        logger = logging.getLogger("pdf_watcher")

        logger.info(f"Starting PDF watcher on {self.watch_dir} (interval={interval}s)")
        logger.info("Press Ctrl+C or send SIGTERM to stop")

        while True:
            try:
                results = self.scan()
                if results:
                    logger.info(f"Processed {len(results)} PDF(s): {results}")
                else:
                    logger.debug("No new PDFs found")
            except Exception as exc:
                logger.error(f"Scan error: {exc}")

            try:
                time.sleep(interval)
            except KeyboardInterrupt:
                logger.info("Stopped by SIGINT")
                break
