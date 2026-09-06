import asyncio
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from services.llm_statement.provider import AnthropicStatementProvider, ProviderConfig


class _Block:
    type = "text"
    text = '{"document_type":"not_a_statement"}'


class _Usage:
    input_tokens = 12
    output_tokens = 3


class _Response:
    id = "msg_test"
    stop_reason = "end_turn"
    content = [_Block()]
    usage = _Usage()


class _Messages:
    def __init__(self):
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return _Response()


class _Client:
    latest = None

    def __init__(self, **_kwargs):
        self.messages = _Messages()
        _Client.latest = self


class ProviderTests(unittest.TestCase):
    def test_uses_structured_output_without_optional_storage_features(self):
        fake_module = types.SimpleNamespace(AsyncAnthropic=_Client)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prompt = root / "prompt.md"
            schema = root / "schema.json"
            prompt.write_text("Transcribe.", encoding="utf-8")
            schema.write_text(json.dumps({
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "additionalProperties": False,
                "properties": {"document_type": {"type": "string"}},
                "required": ["document_type"],
            }), encoding="utf-8")
            with patch.dict(sys.modules, {"anthropic": fake_module}):
                provider = AnthropicStatementProvider(
                    ProviderConfig("key", "exact-model-id", 1000, 30, 0), prompt, schema
                )
                response = asyncio.run(provider.extract("opaque-id", "<page>data</page>"))

        kwargs = _Client.latest.messages.kwargs
        self.assertEqual("exact-model-id", kwargs["model"])
        self.assertEqual("json_schema", kwargs["output_config"]["format"]["type"])
        self.assertNotIn("$schema", kwargs["output_config"]["format"]["schema"])
        self.assertNotIn("tools", kwargs)
        self.assertNotIn("cache_control", str(kwargs))
        self.assertEqual("msg_test", response.request_id)


if __name__ == "__main__":
    unittest.main()
