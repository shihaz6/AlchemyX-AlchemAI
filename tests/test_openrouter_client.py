import pytest

from src.alchemyx.agent.openrouter_client import OpenRouterClient


class FakeResponse:
    status_code = 200
    text = "{\"error\": {\"message\": \"provider failed\"}}"
    ok = True

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


def make_client(monkeypatch, response):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "test-model")
    client = OpenRouterClient()
    monkeypatch.setattr(
        "src.alchemyx.agent.openrouter_client.requests.post",
        lambda *args, **kwargs: response,
    )
    return client


def test_openrouter_reports_provider_error_without_keyerror(monkeypatch):
    client = make_client(monkeypatch, FakeResponse({"error": {"message": "provider failed"}}))

    with pytest.raises(RuntimeError, match="did not contain any choices"):
        client.ask("test")


def test_openrouter_extracts_valid_completion(monkeypatch):
    response = FakeResponse({"choices": [{"message": {"content": "answer"}}]})
    client = make_client(monkeypatch, response)

    assert client.ask("test") == "answer"
