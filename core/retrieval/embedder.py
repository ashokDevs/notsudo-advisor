from __future__ import annotations

import asyncio
import hashlib
import os
from typing import Any

from core.observability.logging import get_logger

logger = get_logger(__name__)


class Embedder:
    """
    Embedding client. Loads BGE-M3 when available; otherwise uses a
    deterministic hash embedding so local demos still run offline.
    """

    def __init__(self, model_name: str = "BAAI/bge-m3", dim: int = 1024) -> None:
        self.model_name = model_name
        self.dim = dim
        self.model: Any | None = None
        self._use_hash = os.getenv("NOTSUDO_HASH_EMBEDDINGS", "").lower() in {"1", "true", "yes"}
        if not self._use_hash:
            try:
                from sentence_transformers import SentenceTransformer

                logger.info("loading embedding model", model=model_name)
                self.model = SentenceTransformer(model_name)
            except Exception as exc:
                logger.warning("sentence-transformers unavailable; using hash embeddings", error=str(exc))
                self._use_hash = True

    async def embed_batch(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        if not texts:
            return []
        if self._use_hash or self.model is None:
            return [self._hash_embed(t) for t in texts]

        def _embed() -> list[list[float]]:
            embeddings = self.model.encode(texts, batch_size=batch_size, show_progress_bar=False)
            return embeddings.tolist()  # type: ignore[no-any-return]

        return await asyncio.to_thread(_embed)

    def _hash_embed(self, text: str) -> list[float]:
        """Deterministic pseudo-embedding for offline / CI use (unit length)."""
        vec = [0.0] * self.dim
        tokens = text.lower().split()
        if not tokens:
            tokens = [text or "empty"]
        for tok in tokens:
            digest = hashlib.sha256(tok.encode("utf-8")).digest()
            for i in range(0, min(len(digest), 32)):
                idx = (digest[i] + i * 17) % self.dim
                vec[idx] += (digest[i] / 255.0) - 0.5
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]
