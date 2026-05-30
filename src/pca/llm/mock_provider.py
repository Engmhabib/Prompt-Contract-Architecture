"""Deterministic mock LLM provider used for tests and offline demos.

Classification: keyword scoring against contract ``intent_examples``.
Extraction: heuristic regexes for common fields (name, email, phone, kind, rows).
"""

from __future__ import annotations

import re
from typing import Any

from pca.llm.base import ClassificationResult

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_NAME_RE = re.compile(r"\bnamed?\s+([A-Z][\w'-]*(?:\s+[A-Z][\w'-]*)*)")
_PHONE_RE = re.compile(r"\+?\d[\d\s().-]{6,}\d")
_ROWS_RE = re.compile(r"\b(\d{1,6})\s+(?:rows?|records?|entries)\b", re.I)


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z]+", text.lower()) if len(t) > 2}


class MockLLMProvider:
    """Deterministic LLM stub."""

    name = "mock"

    async def classify(
        self, prompt: str, candidates: list[dict[str, Any]]
    ) -> ClassificationResult:
        prompt_tokens = _tokens(prompt)
        best_id = "unknown"
        best_score = 0.0
        for cand in candidates:
            corpus = " ".join([cand.get("description", ""), *cand.get("examples", [])])
            cand_tokens = _tokens(corpus)
            if not cand_tokens:
                continue
            overlap = len(prompt_tokens & cand_tokens)
            score = overlap / max(len(cand_tokens), 1)
            if score > best_score:
                best_score = score
                best_id = cand["contract_id"]
        return ClassificationResult(
            contract_id=best_id, confidence=best_score, rationale="mock keyword match"
        )

    async def extract(
        self, prompt: str, input_schema: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        out: dict[str, Any] = {}
        lower = prompt.lower()

        for field_name, spec in input_schema.items():
            ftype = spec.get("type", "string") if isinstance(spec, dict) else "string"

            if field_name == "email":
                m = _EMAIL_RE.search(prompt)
                if m:
                    out["email"] = m.group(0)
                continue
            if field_name == "name":
                m = _NAME_RE.search(prompt)
                if m:
                    out["name"] = m.group(1).strip()
                continue
            if field_name == "phone":
                m = _PHONE_RE.search(prompt)
                if m:
                    out["phone"] = m.group(0).strip()
                continue
            if field_name == "kind":
                for k in ("summary", "detailed", "monthly", "weekly", "daily"):
                    if k in lower:
                        out["kind"] = k
                        break
                continue
            if field_name == "rows":
                m = _ROWS_RE.search(prompt)
                if m:
                    out["rows"] = int(m.group(1))
                continue

            # Generic fallback for ints
            if ftype == "integer":
                m = re.search(rf"{field_name}\s*[:=]?\s*(\d+)", lower)
                if m:
                    out[field_name] = int(m.group(1))

        return out
