import pytest

from src.alchemyx.agent.openrouter_client import OpenRouterClient


class FakeResponse:
    def __init__(self, payload, status_code=200, text=None, ok=True):
        self.payload = payload
        self.status_code = status_code
        self.text = text if text is not None else "{\"error\": {\"message\": \"provider failed\"}}"
        self.ok = ok

    def json(self):
        return self.payload


def make_client(monkeypatch, response):
    captured_request = {}
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "test-model")
    client = OpenRouterClient()

    def fake_post(*args, **kwargs):
        captured_request.update(kwargs)
        return response

    monkeypatch.setattr(
        "src.alchemyx.agent.openrouter_client.requests.post",
        fake_post,
    )
    return client, captured_request


def test_openrouter_reports_provider_error_without_keyerror(monkeypatch):
    client, _captured_request = make_client(
        monkeypatch,
        FakeResponse({"error": {"message": "provider failed"}}),
    )

    with pytest.raises(RuntimeError, match="did not contain any choices"):
        client.ask("test")


def test_openrouter_extracts_valid_completion(monkeypatch):
    response = FakeResponse({"choices": [{"message": {"content": "answer"}}]})
    client, captured_request = make_client(monkeypatch, response)

    assert client.ask("test") == "answer"
    assert captured_request["json"]["temperature"] == 0


def test_openrouter_falls_back_when_free_model_slug_is_unavailable(monkeypatch):
    calls = []
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "unavailable/model:free")
    client = OpenRouterClient()

    def fake_post(*args, **kwargs):
        calls.append(kwargs["json"]["model"])
        if len(calls) == 1:
            return FakeResponse(
                {},
                status_code=404,
                text='{"error":{"message":"This model is unavailable for free."}}',
                ok=False,
            )
        return FakeResponse({"choices": [{"message": {"content": "fallback answer"}}]})

    monkeypatch.setattr(
        "src.alchemyx.agent.openrouter_client.requests.post",
        fake_post,
    )

    assert client.ask("test") == "fallback answer"
    assert calls == ["unavailable/model:free", "openrouter/free"]


def test_openrouter_does_not_fallback_to_paid_suggested_slug(monkeypatch):
    calls = []
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "unavailable/model:free")
    client = OpenRouterClient()

    def fake_post(*args, **kwargs):
        calls.append(kwargs["json"]["model"])
        return FakeResponse(
            {},
            status_code=404,
            text=(
                '{"error":{"message":"This model is unavailable for free. '
                'The paid version is available now - use this slug instead: '
                'unavailable/model"}}'
            ),
            ok=False,
        )

    monkeypatch.setattr(
        "src.alchemyx.agent.openrouter_client.requests.post",
        fake_post,
    )

    with pytest.raises(RuntimeError, match="configured free model"):
        client.ask("test")
    assert calls == ["unavailable/model:free", "openrouter/free"]
