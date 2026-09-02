from src.alchemyx.retrieval import embeddings as embeddings_module
from src.alchemyx.retrieval import voyage_diagnostics
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


def test_embedding_logs_authoritative_usage(monkeypatch):
    logs = []

    class FakeResult:
        embeddings = [[1.0, 0.0, 0.0]]
        usage = {"total_tokens": 14}

    class FakeClient:
        def embed(self, *args, **kwargs):
            return FakeResult()

    monkeypatch.setattr(embeddings_module.voyageai, "Client", lambda api_key: FakeClient())
    monkeypatch.setattr(voyage_diagnostics, "log", logs.append)

    function = VoyageEmbeddingFunction(api_key="test-key", input_type="query")
    function(["hello world"])

    assert "[Voyage Embedding]" in logs
    assert "model=voyage-4-lite" in logs
    assert "input_type=query" in logs
    assert "inputs=1" in logs
    assert "tokens=14" in logs
    assert not any("tokens_estimate" in entry for entry in logs)


def test_embedding_logs_estimated_usage_when_sdk_usage_is_missing(monkeypatch):
    logs = []

    class FakeResult:
        embeddings = [[1.0, 0.0, 0.0]]

    class FakeClient:
        def embed(self, *args, **kwargs):
            return FakeResult()

    monkeypatch.setattr(embeddings_module.voyageai, "Client", lambda api_key: FakeClient())
    monkeypatch.setattr(voyage_diagnostics, "log", logs.append)

    function = VoyageEmbeddingFunction(api_key="test-key", input_type="document")
    function(["one two", "three four five"])

    assert "tokens_estimate=5" in logs
