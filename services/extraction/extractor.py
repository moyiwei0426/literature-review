from __future__ import annotations

import json
import time
from pathlib import Path

from core.models import PaperChunk, PaperProfile
from infra.settings import get_settings
from services.llm.adapter import LLMAdapter

from .normalizers import normalize_profile_payload
from .validators import validate_profile_payload


class PaperExtractor:
    def __init__(self, llm: LLMAdapter | None = None) -> None:
        self.llm = llm or LLMAdapter()
        project_root = Path(__file__).resolve().parents[2]
        self.system_prompt = (project_root / "prompts" / "extraction" / "system.txt").read_text(encoding="utf-8")
        self.user_prompt_template = (project_root / "prompts" / "extraction" / "user.txt").read_text(encoding="utf-8")
        self.settings = get_settings()

    def extract(self, paper_id: str, chunks: list[PaperChunk], *, max_attempts: int = 3) -> tuple[PaperProfile, dict]:
        context = self._build_context(chunks)
        last_error: str | None = None
        total_latency_ms = 0
        last_response = None

        for attempt in range(1, max_attempts + 1):
            user_prompt = self._build_user_prompt(paper_id, context, attempt=attempt, previous_error=last_error)
            response = self.llm.generate_json(
                self.system_prompt,
                user_prompt,
                metadata={"paper_id": paper_id, "chunk_ids": [chunk.chunk_id for chunk in chunks]},
            )
            last_response = response
            total_latency_ms += response.latency_ms
            normalized_payload = normalize_profile_payload(response.content, paper_id=paper_id)

            try:
                profile = validate_profile_payload(normalized_payload)
                self._validate_required_content(profile)
                report = {
                    "provider": response.provider,
                    "model": response.model,
                    "latency_ms": total_latency_ms,
                    "usage": response.usage,
                    "chunk_count": len(chunks),
                    "attempts": attempt,
                    "recovered_after_retry": attempt > 1,
                }
                return profile, report
            except Exception as exc:
                last_error = str(exc)
                self._write_failure_snapshot(
                    paper_id=paper_id,
                    attempt=attempt,
                    error=last_error,
                    response=response.raw_text,
                    normalized_payload=normalized_payload,
                    chunk_count=len(chunks),
                )
                if attempt == max_attempts:
                    raise

        raise RuntimeError(f"Extraction failed for {paper_id}: {last_error or 'unknown error'}")

    def _build_user_prompt(self, paper_id: str, context: str, *, attempt: int, previous_error: str | None) -> str:
        prompt = f"{self.user_prompt_template}\n\nPaper ID: {paper_id}\n\nChunks:\n{context}"
        if attempt > 1:
            prompt += (
                "\n\nPrevious extraction attempt failed validation. "
                "Regenerate the FULL JSON object from scratch, not a partial patch."
                f"\nValidation failure: {previous_error or 'unknown'}"
                "\nRequirements reminder: research_problem and method_summary must be non-empty strings; "
                "method_family must be a non-empty list when inferable; each main_claim must include evidence_chunk_ids."
            )
        return prompt

    def _validate_required_content(self, profile: PaperProfile) -> None:
        if not profile.research_problem or not profile.research_problem.strip():
            raise ValueError("research_problem is empty")
        if not profile.method_summary or not profile.method_summary.strip():
            raise ValueError("method_summary is empty")
        if not profile.method_family:
            raise ValueError("method_family is empty")
        if not profile.main_claims:
            raise ValueError("main_claims is empty")

    def _write_failure_snapshot(self, *, paper_id: str, attempt: int, error: str, response: str, normalized_payload: dict, chunk_count: int) -> None:
        failure_dir = self.settings.data_dir / "generated" / "extraction_failures"
        failure_dir.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        path = failure_dir / f"{paper_id}_attempt{attempt}_{timestamp}.json"
        payload = {
            "paper_id": paper_id,
            "attempt": attempt,
            "error": error,
            "chunk_count": chunk_count,
            "normalized_payload": normalized_payload,
            "raw_response": response,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _build_context(self, chunks: list[PaperChunk]) -> str:
        lines = []
        for chunk in chunks:
            lines.append(f"[{chunk.chunk_id}] ({chunk.section}) {chunk.text}")
        return "\n".join(lines)
