from src.alchemyx.retrieval import embeddings as embeddings_module
from src.alchemyx.retrieval.embeddings import VoyageEmbeddingFunction


def test_embedding_retries_transient_failure(monkeypatch):
    class FakeResult:
        embeddings = [[1.0, 0.0, 0.0]]

    class FakeClient:
        attempts = 0

        def embed(self, *args, **kwargs):
            self.attempts += 1
            if self.attempts < 3:
                raise OSError("temporary network failure")
            return FakeResult()

    client = FakeClient()
    monkeypatch.setattr(embeddings_module.voyageai, "Client", lambda api_key: client)
    monkeypatch.setattr(embeddings_module.time, "sleep", lambda seconds: None)

    function = VoyageEmbeddingFunction(
        api_key="test-key",
        max_retries=2,
        retry_base_seconds=0,
    )

    result = function(["text"])
    assert result[0].tolist() == [1.0, 0.0, 0.0]
    assert client.attempts == 3
