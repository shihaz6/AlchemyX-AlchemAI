import time

from chromadb import Documents, EmbeddingFunction, Embeddings
import voyageai

try:
    from ..config import (
        VOYAGE_MAX_RETRIES,
        VOYAGE_MODEL,
        VOYAGE_RETRY_BASE_SECONDS,
    )
except ImportError:
    from src.alchemyx.config import VOYAGE_MODEL
    from src.alchemyx.config import (
        VOYAGE_MAX_RETRIES,
        VOYAGE_RETRY_BASE_SECONDS,
    )


class VoyageEmbeddingFunction(EmbeddingFunction):
    def __init__(
        self,
        api_key,
        model=VOYAGE_MODEL,
        input_type="document",
        max_retries=VOYAGE_MAX_RETRIES,
        retry_base_seconds=VOYAGE_RETRY_BASE_SECONDS,
    ):
        self.client = voyageai.Client(api_key=api_key)
        self.model = model
        self.input_type = input_type
        self.max_retries = max_retries
        self.retry_base_seconds = retry_base_seconds

    def __call__(self, input: Documents) -> Embeddings:
        for attempt in range(self.max_retries + 1):
            try:
                result = self.client.embed(
                    input,
                    model=self.model,
                    input_type=self.input_type,
                )
                return result.embeddings
            except Exception:
                if attempt >= self.max_retries:
                    raise
                time.sleep(self.retry_base_seconds * (2 ** attempt))
