from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from infra.settings import get_settings
from services.auth import OAuthClient


@dataclass
class LLMResponse:
    content: Any
    raw_text: str
    model: str
    provider: str
    latency_ms: int
    usage: dict[str, Any]


class LLMAdapter:
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None) -> None:
        settings = get_settings()
        self.settings = settings
        self.provider = provider or settings.llm_provider or "stub"
        self.model = model or settings.llm_model or "stub-model"
        self.base_url = settings.llm_base_url.rstrip("/") if settings.llm_base_url else ""
        self.api_key = settings.llm_api_key
        self.timeout = settings.llm_timeout_seconds
        self._oauth_client: OAuthClient | None = None

    def generate_json(self, system_prompt: str, user_prompt: str, *, metadata: Optional[dict[str, Any]] = None) -> LLMResponse:
        start = time.time()

        if self._should_force_stub():
            payload = self._stub_response(user_prompt, metadata or {})
            raw_text = json.dumps(payload, ensure_ascii=False)
            response = LLMResponse(
                content=payload,
                raw_text=raw_text,
                model=self.model,
                provider="stub",
                latency_ms=0,
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            )
        elif self.provider in {"openai_compatible", "openai-compatible", "oauth_openai_compatible"} and self.base_url and self._has_auth():
            response = self._generate_openai_compatible(system_prompt, user_prompt)
        elif self.provider in {"minimaxi", "minimax"} and self.base_url and self.api_key:
            response = self._generate_minimaxi(system_prompt, user_prompt)
        else:
            payload = self._stub_response(user_prompt, metadata or {})
            raw_text = json.dumps(payload, ensure_ascii=False)
            response = LLMResponse(
                content=payload,
                raw_text=raw_text,
                model=self.model,
                provider="stub",
                latency_ms=0,
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            )

        response.latency_ms = int((time.time() - start) * 1000)
        return response

    def _generate_openai_compatible(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        if self.base_url.endswith("/chat/completions"):
            url = self.base_url
        else:
            url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._get_bearer_token()}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }

        with httpx.Client(timeout=self.timeout) as client:
            http_response = client.post(url, headers=headers, json=payload)
            http_response.raise_for_status()
            data = http_response.json()

        raw_text = data["choices"][0]["message"]["content"]
        content = self._safe_load_json(raw_text)
        usage = data.get("usage", {})
        return LLMResponse(
            content=content,
            raw_text=raw_text,
            model=data.get("model", self.model),
            provider=self.provider,
            latency_ms=0,
            usage=usage,
        )

    def _generate_minimaxi(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        url = f"{self.base_url}/v1/text/chatcompletion_v2"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt + "\n\nReturn ONLY valid JSON."},
            ],
            "temperature": 0.2,
        }

        with httpx.Client(timeout=self.timeout) as client:
            http_response = client.post(url, headers=headers, json=payload)
            http_response.raise_for_status()
            data = http_response.json()

        raw_text = self._extract_message_content(data)
        content = self._safe_load_json(raw_text)
        usage = data.get("usage", {})
        return LLMResponse(
            content=content,
            raw_text=raw_text,
            model=data.get("model", self.model),
            provider=self.provider,
            latency_ms=0,
            usage=usage,
        )

    @property
    def oauth_client(self) -> OAuthClient:
        if self._oauth_client is None:
            self._oauth_client = OAuthClient(provider=self.provider)
        return self._oauth_client

    def _should_force_stub(self) -> bool:
        return bool(os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("ARIS_LIT_FORCE_STUB"))

    def _has_auth(self) -> bool:
        if self.api_key:
            return True
        if self.provider != "oauth_openai_compatible":
            return False
        return self.oauth_client.is_configured() and self.oauth_client.store.exists(self.provider)

    def _get_bearer_token(self) -> str:
        if self.api_key:
            return self.api_key
        if self.provider == "oauth_openai_compatible":
            return self.oauth_client.get_valid_access_token()
        raise ValueError("No API key or OAuth access token available")

    def _extract_message_content(self, data: dict[str, Any]) -> str:
        choices = data.get("choices") or []
        if not choices:
            raise ValueError(f"No choices returned from provider: {data}")
        message = choices[0].get("message") or {}
        content = message.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts = []
            for item in content:
                if isinstance(item, dict):
                    texts.append(str(item.get("text") or item.get("content") or ""))
                else:
                    texts.append(str(item))
            return "\n".join(texts).strip()
        return str(content)

    def _safe_load_json(self, raw_text: str) -> Any:
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            fenced = re.findall(r"```json\s*([\[{].*?[\]}])\s*```", raw_text, flags=re.DOTALL | re.IGNORECASE)
            if fenced:
                return json.loads(fenced[-1])
            obj_start = raw_text.find("{")
            obj_end = raw_text.rfind("}")
            arr_start = raw_text.find("[")
            arr_end = raw_text.rfind("]")
            candidates = []
            if obj_start != -1 and obj_end != -1 and obj_end > obj_start:
                candidates.append(raw_text[obj_start:obj_end + 1])
            if arr_start != -1 and arr_end != -1 and arr_end > arr_start:
                candidates.append(raw_text[arr_start:arr_end + 1])
            for candidate in candidates:
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    continue
            raise

    def _stub_response(self, user_prompt: str, metadata: dict[str, Any]) -> dict[str, Any]:
        paper_id = metadata.get("paper_id", "unknown-paper")
        chunk_ids = metadata.get("chunk_ids", [])
        sample_evidence = chunk_ids[:2] if chunk_ids else []
        return {
            "paper_id": paper_id,
            "research_problem": "Automatically extract structured literature review signals from academic papers.",
            "problem_type": "information_extraction",
            "domain": "scholarly_nlp",
            "language_scope": "english",
            "method_summary": "A pipeline that combines retrieval, PDF parsing, chunking, and structured extraction.",
            "method_family": ["pipeline", "llm-assisted-extraction"],
            "datasets": [],
            "tasks": ["literature_review", "information_extraction"],
            "metrics": [],
            "baselines": [],
            "main_claims": [
                {
                    "claim_id": "claim-1",
                    "claim_text": "The pipeline can transform parsed paper chunks into a structured paper profile.",
                    "claim_type": "methodological",
                    "evidence_chunk_ids": sample_evidence[:1],
                    "confidence": 0.7,
                },
                {
                    "claim_id": "claim-2",
                    "claim_text": "The system supports downstream gap analysis by preserving evidence links.",
                    "claim_type": "application",
                    "evidence_chunk_ids": sample_evidence[1:2] or sample_evidence[:1],
                    "confidence": 0.68,
                },
            ],
            "limitations": [
                {
                    "text": "The current output may rely on stubbed model behavior before real LLM integration.",
                    "source": "inferred",
                    "evidence_chunk_ids": sample_evidence[:1],
                }
            ],
            "future_work": ["Integrate real LLM provider", "Improve claim grounding"],
            "notes": "Stub extraction response for local development."
        }
