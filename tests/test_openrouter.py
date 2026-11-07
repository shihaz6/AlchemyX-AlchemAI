from unittest.mock import Mock

import pytest

from alchemyx.agent.openrouter_client import OpenRouterClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only-not-a-real-key")
    return OpenRouterClient()


def test_valid_completion(client):
    response = Mock(ok=True)
    response.json.return_value = {"choices": [{"message": {"content": "Answer"}}]}
    assert client._parse_completion(response) == "Answer"


@pytest.mark.parametrize("payload", [{}, {"choices": []},
    {"choices": [{"message": {"content": ""}}]}])
def test_invalid_completion(client, payload):
    response = Mock(ok=True)
    response.json.return_value = payload
    with pytest.raises(RuntimeError):
        client._parse_completion(response)


def test_free_model_fallback(client, monkeypatch):
    client.model = "first"
    client.fallback_models = ["second"]
    unavailable = Mock(ok=False, status_code=404, text="unavailable for free")
    success = Mock(ok=True, status_code=200)
    success.json.return_value = {"choices": [{"message": {"content": "Answer"}}]}
    post = Mock(side_effect=[unavailable, success])
    monkeypatch.setattr(client, "_post", post)
    assert client.ask("Question") == "Answer"
    assert [call.args[1] for call in post.call_args_list] == ["first", "second"]
