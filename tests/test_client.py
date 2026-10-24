from __future__ import annotations

import httpx
import pytest
import respx

from schemaforge.client import OpenAICompatibleClient
from schemaforge.config import Settings
from schemaforge.errors import ModelAPIError


@respx.mock
def test_complete_json_sends_guided_schema() -> None:
    route = respx.post("https://model.test/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [{"message": {"content": '{"x":1}'}}]})
    )
    settings = Settings(base_url="https://model.test/v1", api_key="secret", model="test")
    with OpenAICompatibleClient(settings) as client:
        assert client.complete_json([], {"type": "object"}) == '{"x":1}'
    request = route.calls.last.request
    payload = __import__("json").loads(request.content)
    assert payload["response_format"]["type"] == "json_schema"
    assert request.headers["authorization"] == "Bearer secret"


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500, text="failure"),
        httpx.Response(200, json={"choices": []}),
        httpx.Response(200, json={"choices": [{"message": {"content": ""}}]}),
    ],
)
def test_complete_json_wraps_bad_responses(response: httpx.Response) -> None:
    transport = httpx.MockTransport(lambda request: response)
    with OpenAICompatibleClient(Settings(), transport) as client, pytest.raises(ModelAPIError):
        client.complete_json([], {})


def test_health() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"data": []}))
    with OpenAICompatibleClient(Settings(), transport) as client:
        assert client.health()
