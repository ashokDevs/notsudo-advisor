from __future__ import annotations

import asyncio
from typing import Any

from sentence_transformers import SentenceTransformer

from core.observability.logging import get_logger

logger = get_logger(__name__)

class Embedder:
    def __init__(self, model_name: str = "BAAI/bge-m3") -> None:
        logger.info("loading embedding model", model=model_name)
        self.model = SentenceTransformer(model_name)

    async def embed_batch(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        if not texts:
            return []

        def _embed() -> list[list[float]]:
            # encode returns a numpy array or tensor, we convert to list of floats
            embeddings = self.model.encode(texts, batch_size=batch_size, show_progress_bar=False)
            return embeddings.tolist() # type: ignore

        return await asyncio.to_thread(_embed)
