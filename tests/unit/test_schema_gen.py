from typing import Any

import httpx
import pytest
from crawl4ai import LLMConfig as C4ALLMConfig

from phd_searcher.pipeline import schema_gen

SAFE_SCHEMA: dict[str, object] = {
    "name": "vacancies",
    "baseSelector": "li.job",
    "fields": [
        {"name": "title", "selector": "h2", "type": "text"},
        {"name": "url", "selector": "a", "type": "attribute", "attribute": "href"},
    ],
}


def test_schema_cache_is_scoped_by_normalized_host_and_listing_kind() -> None:
    assert schema_gen._schema_cache_key("https://Jobs.Example.test/open", "university") == (
        "university",
        "jobs.example.test",
    )
    assert schema_gen._schema_cache_key("https:///broken", "university") is None
    assert schema_gen._schema_cache_key("mailto:jobs@example.test", "university") is None


def test_cached_schema_is_reused_only_after_target_html_validation() -> None:
    valid_html = """
        <ul>
          <li class="job"><a href="/jobs/1"><h2>PhD one</h2></a></li>
          <li class="job"><a href="/jobs/2"><h2>PhD two</h2></a></li>
        </ul>
    """
    unrelated_html = "<main><h1>About the university</h1></main>"

    reused = schema_gen._validated_reusable_schema(
        valid_html,
        [SAFE_SCHEMA],
        expected_fields=["title", "url"],
    )
    assert reused == SAFE_SCHEMA
    assert reused is not SAFE_SCHEMA
    assert (
        schema_gen._validated_reusable_schema(
            unrelated_html,
            [SAFE_SCHEMA],
            expected_fields=["title", "url"],
        )
        is None
    )


def test_schema_cache_deduplicates_equal_schemas_and_keeps_copies() -> None:
    cache: dict[tuple[str, str], list[dict[str, object]]] = {}
    key = ("university", "jobs.example.test")
    schema_gen._remember_schema(cache, key, SAFE_SCHEMA)
    schema_gen._remember_schema(cache, key, dict(SAFE_SCHEMA))

    assert len(cache[key]) == 1
    assert cache[key][0] == SAFE_SCHEMA
    assert cache[key][0] is not SAFE_SCHEMA


async def test_exhausted_tool_feedback_has_a_typed_non_transport_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    async def no_tool_calls(
        *_args: object,
        **_kwargs: object,
    ) -> tuple[dict[str, Any], list[Any], bool]:
        nonlocal calls
        calls += 1
        return {"role": "assistant", "content": "no schema"}, [], True

    monkeypatch.setattr(schema_gen, "_complete_with_tools", no_tool_calls)
    with pytest.raises(schema_gen.SchemaGenerationExhaustedError, match=r"after 2 attempts.*without a tool call"):
        await schema_gen._generate_schema_with_tools(
            "<main>No listing here</main>",
            "Extract jobs",
            C4ALLMConfig(
                provider="ollama/test",
                api_token="none",
                base_url="http://ollama.test",
            ),
        )

    assert calls == 2


async def test_native_ollama_schema_generation_caps_only_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, Any] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"message": {"role": "assistant", "tool_calls": []}}

    class FakeClient:
        def __init__(self, *, timeout: int) -> None:
            observed["timeout"] = timeout

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, url: str, *, json: dict[str, Any]) -> FakeResponse:
            observed["url"] = url
            observed["payload"] = json
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    await schema_gen._complete_with_tools(
        C4ALLMConfig(
            provider="ollama/test-model",
            api_token="none",
            base_url="http://ollama.test/v1",
        ),
        [{"role": "user", "content": "extract"}],
    )

    payload = observed["payload"]
    assert isinstance(payload, dict)
    assert payload["options"] == {
        "temperature": 0,
        "num_ctx": 65536,
        "num_predict": 8192,
    }
    assert payload["model"] == "test-model"
    assert observed["url"] == "http://ollama.test/api/chat"


@pytest.mark.parametrize("sequence", [
    ["missing", "valid"],
    ["invalid", "invalid", "invalid", "valid"],
    ["missing", "invalid", "missing", "valid"],
])
async def test_tool_progress_retains_schema_correction_budget(monkeypatch, sequence):
    responses = iter(sequence)
    calls = 0

    async def complete(*args, **kwargs):
        nonlocal calls
        calls += 1
        response = next(responses)
        if response == "missing":
            return {"role": "assistant", "content": "working"}, [], True
        schema = SAFE_SCHEMA if response == "valid" else {**SAFE_SCHEMA, "baseSelector": ".absent"}
        call = {"function": {"name": "submit_extraction_schema", "arguments": schema}}
        return {"role": "assistant", "tool_calls": [call]}, [call], True

    monkeypatch.setattr(schema_gen, "_complete_with_tools", complete)
    result = await schema_gen._generate_schema_with_tools(
        '<ul><li class="job"><h2>PhD one</h2><a href="/1">Apply</a></li>'
        '<li class="job"><h2>PhD two</h2><a href="/2">Apply</a></li></ul>',
        "Extract jobs",
        C4ALLMConfig(provider="ollama/test", api_token="none", base_url="http://ollama.test"),
    )
    assert result == SAFE_SCHEMA
    assert calls == len(sequence)
