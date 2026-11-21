import pytest

from ai_automation_agents.fakes import FakeChatProvider, FakeEmbedder, FakeHttpClient
from ai_automation_agents.providers import HttpFetchError, extract_json
from ai_automation_agents.retrieval import cosine_similarity


def test_fake_chat_provider_first_matching_rule_wins() -> None:
    provider = FakeChatProvider(
        rules=[("hello", "first"), ("hello world", "second")], default="fallback"
    )
    assert provider.complete("say hello world") == "first"
    assert provider.complete("unrelated") == "fallback"
    assert provider.prompts == ["say hello world", "unrelated"]


def test_fake_http_client_serves_pages_and_records_requests() -> None:
    client = FakeHttpClient({"https://x.example": "<p>hi</p>"})
    assert client.get("https://x.example") == "<p>hi</p>"
    assert client.requested == ["https://x.example"]


def test_fake_http_client_missing_page_raises() -> None:
    client = FakeHttpClient()
    with pytest.raises(HttpFetchError):
        client.get("https://missing.example")


def test_fake_embedder_is_deterministic_and_similar_for_shared_words() -> None:
    embedder = FakeEmbedder()
    first = embedder.embed("approval gates keep humans in charge")
    second = embedder.embed("approval gates keep humans in charge")
    other = embedder.embed("zebra quantum banana smoothie")
    assert first == second
    assert cosine_similarity(first, second) == pytest.approx(1.0)
    assert cosine_similarity(first, other) < 0.5


def test_extract_json_plain_fenced_and_prose() -> None:
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json("Here is the result: [1, 2, 3] — hope that helps") == [1, 2, 3]


def test_extract_json_rejects_garbage() -> None:
    with pytest.raises(ValueError):
        extract_json("no structured output here")
