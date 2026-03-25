from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


class LatexCompiler:
    """Real LaTeX compiler using xelatex (with pdflatex fallback).
    Detects available toolchain automatically; falls back to stub gracefully.
    """

    def __init__(self) -> None:
        self._toolchain: str | None = None

    def _detect_toolchain(self) -> str:
        """Detect available LaTeX compiler."""
        if self._toolchain:
            return self._toolchain
        for candidate in ["xelatex", "pdflatex", "lualatex"]:
            if shutil.which(candidate) is not None:
                self._toolchain = candidate
                return candidate
        self._toolchain = "stub"
        return self._toolchain

    def compile(self, tex_path: str | Path) -> dict:
        """Compile a .tex file to PDF using detected LaTeX toolchain.

        Runs xelatex twice (for cross-references) with minimal pipeline.
        Returns stub result if no toolchain is available.
        """
        path = Path(tex_path)
        if not path.exists():
            return self._stub_result(path, "missing_tex")

        toolchain = self._detect_toolchain()
        if toolchain == "stub":
            return self._stub_result(path, "toolchain_not_found")

        work_dir = path.parent.resolve()
        base = path.stem

        try:
            # First pass
            self._run_latex(toolchain, path, work_dir)
            # Second pass for cross-refs / TOC
            self._run_latex(toolchain, path, work_dir)
            pdf_path = work_dir / f"{base}.pdf"
            if pdf_path.exists():
                return {
                    "status": "success",
                    "toolchain": toolchain,
                    "tex_path": str(path),
                    "pdf_path": str(pdf_path),
                    "pdf_size_kb": pdf_path.stat().st_size // 1024,
                }
            return self._stub_result(path, "pdf_not_generated")
        except subprocess.TimeoutExpired:
            return self._stub_result(path, "timeout")
        except Exception as exc:
            return {
                "status": "error",
                "toolchain": toolchain,
                "tex_path": str(path),
                "error": str(exc),
            }

    def _run_latex(self, toolchain: str, tex_path: Path, work_dir: Path) -> None:
        result = subprocess.run(
            [toolchain, "-interaction=batchmode", "-halt-on-error",
             f"-output-directory={work_dir}", str(tex_path)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(work_dir),
        )
        if result.returncode != 0:
            error_snippet = result.stderr[-1000:] if result.stderr else ""
            raise RuntimeError(f"{toolchain} failed: {error_snippet}")

    def _stub_result(self, path: Path, reason: str) -> dict:
        return {
            "status": reason,
            "toolchain": self._toolchain or "unknown",
            "tex_path": str(path),
            "pdf_path": str(path.with_suffix(".pdf")),
        }

    def get_bibtex_engine(self) -> str:
        """Return preferred bibtex command for the detected toolchain."""
        toolchain = self._detect_toolchain()
        if toolchain == "xelatex":
            return "biber"
        return "bibtex"
