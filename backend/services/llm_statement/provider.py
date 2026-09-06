"""Narrow Anthropic Messages API adapter for statement transcription."""

import asyncio
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Dict, Optional


class ProviderError(RuntimeError):
    def __init__(self, status: str, message: str) -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class ProviderConfig:
    api_key: str
    model: str
    max_output_tokens: int
    timeout_seconds: float
    transport_retries: int = 2


@dataclass(frozen=True)
class ModelResponse:
    extraction: Dict[str, Any]
    request_id: str
    input_tokens: int
    output_tokens: int
    stop_reason: Optional[str]


class AnthropicStatementProvider:
    def __init__(self, config: ProviderConfig, prompt_path: Path, schema_path: Path) -> None:
        if not config.api_key:
            raise ProviderError("provider_unavailable", "Anthropic API key is not configured")
        if not config.model:
            raise ProviderError("provider_unavailable", "Anthropic model is not configured")
        try:
            import anthropic
        except ImportError as exc:
            raise ProviderError("provider_unavailable", "The Anthropic SDK is not installed") from exc

        self._anthropic = anthropic
        self._client = anthropic.AsyncAnthropic(api_key=config.api_key, timeout=config.timeout_seconds)
        self._config = config
        self._prompt = prompt_path.read_text(encoding="utf-8")
        self._schema = json.loads(schema_path.read_text(encoding="utf-8"))
        # This annotation is useful locally but is not part of the constrained
        # subset accepted by every Messages API model.
        self._schema.pop("$schema", None)

    async def extract(self, document_id: str, page_text: str, retry_instruction: Optional[str] = None) -> ModelResponse:
        user_content = self._prompt
        if retry_instruction:
            user_content += "\n\nSecond-pass instruction:\n" + retry_instruction
        user_content += "\n\n" + page_text

        last_error: Optional[Exception] = None
        for attempt in range(self._config.transport_retries + 1):
            try:
                response = await self._client.messages.create(
                    model=self._config.model,
                    max_tokens=self._config.max_output_tokens,
                    metadata={"user_id": document_id},
                    messages=[{"role": "user", "content": user_content}],
                    output_config={"format": {"type": "json_schema", "schema": self._schema}},
                )
                stop_reason = getattr(response, "stop_reason", None)
                if stop_reason == "max_tokens":
                    raise ProviderError("unparseable", "Model output was truncated")
                if stop_reason in {"refusal", "model_context_window_exceeded"}:
                    raise ProviderError("unparseable", "Model did not complete statement extraction")
                blocks = [block for block in response.content if getattr(block, "type", None) == "text"]
                if len(blocks) != 1:
                    raise ProviderError("unparseable", "Model returned unexpected content blocks")
                try:
                    extraction = json.loads(blocks[0].text)
                except (TypeError, json.JSONDecodeError) as exc:
                    raise ProviderError("unparseable", "Model returned invalid JSON") from exc
                usage = getattr(response, "usage", None)
                return ModelResponse(
                    extraction=extraction,
                    request_id=str(getattr(response, "id", "")),
                    input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
                    output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
                    stop_reason=stop_reason,
                )
            except ProviderError:
                raise
            except Exception as exc:
                last_error = exc
                status_code = getattr(exc, "status_code", None)
                retryable = status_code in {408, 409, 429, 500, 502, 503, 504} or status_code is None
                if not retryable or attempt >= self._config.transport_retries:
                    break
                await asyncio.sleep(min(2 ** attempt, 4))
        raise ProviderError("provider_unavailable", "Statement extraction provider is unavailable") from last_error
