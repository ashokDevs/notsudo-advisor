import pytest

from core.retrieval.embedder import Embedder

pytestmark = pytest.mark.asyncio

@pytest.fixture(scope="module")
def embedder() -> Embedder:
    # Use a tiny model for tests instead of bge-m3
    return Embedder(model_name="all-MiniLM-L6-v2")

async def test_embed_returns_vectors(embedder: Embedder) -> None:
    texts = ["hello world", "test string"]
    vectors = await embedder.embed_batch(texts)
    
    assert len(vectors) == 2
    assert len(vectors[0]) == 384  # MiniLM dimension
    assert all(isinstance(x, float) for x in vectors[0])
