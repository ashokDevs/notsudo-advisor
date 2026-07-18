from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class EvidenceQuote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_path: str
    line_start: int
    line_end: int
    quote: str


class EvidenceQuoteValidator:
    """
    Post-hoc grounding check: every evidence quote must appear in the cited source.
    Hallucinated quotes fail validation.
    """

    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = repo_root

    def quote_matches(self, source: str, quote: str) -> bool:
        if not quote or not quote.strip():
            return False
        norm_source = self._normalize(source)
        norm_quote = self._normalize(quote)
        if not norm_quote:
            return False
        if norm_quote in norm_source:
            return True
        # allow contiguous substring of significant tokens
        tokens = [t for t in re.split(r"\s+", norm_quote) if len(t) > 2]
        if len(tokens) < 3:
            return norm_quote in norm_source
        # require at least 70% of significant tokens present in order
        pos = 0
        hits = 0
        for t in tokens:
            idx = norm_source.find(t, pos)
            if idx >= 0:
                hits += 1
                pos = idx + len(t)
        return hits / len(tokens) >= 0.7

    def validate(
        self,
        quotes: list[EvidenceQuote],
        file_contents: dict[str, str] | None = None,
    ) -> tuple[bool, list[EvidenceQuote], list[str]]:
        """
        Returns (all_valid, valid_quotes, failures).
        """
        valid: list[EvidenceQuote] = []
        failures: list[str] = []
        for q in quotes:
            source = self._load_source(q.file_path, file_contents)
            if source is None:
                failures.append(f"missing source file: {q.file_path}")
                continue
            # Prefer the cited line range when present
            lines = source.splitlines()
            if 1 <= q.line_start <= len(lines):
                window = "\n".join(lines[max(0, q.line_start - 3) : min(len(lines), q.line_end + 3)])
            else:
                window = source
            if self.quote_matches(window, q.quote) or self.quote_matches(source, q.quote):
                valid.append(q)
            else:
                failures.append(f"quote not found in {q.file_path}:{q.line_start}")
        return (len(failures) == 0 and len(valid) > 0) or (len(quotes) == 0), valid, failures

    def validate_advisory_quote(self, advisory_text: str, quote: str) -> bool:
        return self.quote_matches(advisory_text, quote)

    def _load_source(self, file_path: str, file_contents: dict[str, str] | None) -> str | None:
        if file_contents and file_path in file_contents:
            return file_contents[file_path]
        if self.repo_root is None:
            return None
        path = self.repo_root / file_path
        if not path.is_file():
            return None
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return None

    @staticmethod
    def _normalize(text: str) -> str:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"\s+", " ", text).strip().lower()
        return text


class ReachabilityVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict: str = Field(pattern="^(exposed|safe|unsure)$")
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    evidence_quotes: list[EvidenceQuote] = Field(default_factory=list)
    entrypoints: list[str] = Field(default_factory=list)
    nodes: list[str] = Field(default_factory=list)
