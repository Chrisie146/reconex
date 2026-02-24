"""
PostHog server-side analytics tracker.
Provides a thin wrapper around the PostHog Python SDK so that any router can
capture events without worrying about initialization or graceful shutdown.
"""

import logging
import threading
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_client = None


def _get_client():
    """Lazy-initialize the PostHog client (thread-safe)."""
    global _client
    if _client is not None:
        return _client

    with _lock:
        if _client is not None:
            return _client  # Double-check after acquiring lock

        try:
            from config import Config
            api_key = getattr(Config, "POSTHOG_API_KEY", "")
            host = getattr(Config, "POSTHOG_HOST", "https://us.i.posthog.com")
            enabled = getattr(Config, "POSTHOG_ENABLED", False)

            if not enabled or not api_key:
                _client = None
                return None

            from posthog import Posthog
            _client = Posthog(
                project_api_key=api_key,
                host=host,
                on_error=lambda e, _: logger.warning(f"[PostHog] Error: {e}"),
            )
            logger.info("[PostHog] Server-side client initialized")
        except Exception as exc:
            logger.warning(f"[PostHog] Failed to initialize: {exc}")
            _client = None

    return _client


def capture(
    distinct_id: str,
    event: str,
    properties: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Capture a server-side event.  Fire-and-forget — never raises.

    Args:
        distinct_id: User identifier (use str(user.id)).
        event:       Event name, e.g. 'statement_parsed_success'.
        properties:  Optional dict of additional properties.
    """
    try:
        client = _get_client()
        if client is None:
            return
        client.capture(distinct_id=distinct_id, event=event, properties=properties or {})
    except Exception as exc:
        logger.warning(f"[PostHog] capture({event}) failed: {exc}")
