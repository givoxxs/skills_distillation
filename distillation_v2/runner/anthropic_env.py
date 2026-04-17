"""Lightweight env-var swap for Anthropic SDK calls (Teacher + Judge).

Used to scope ANTHROPIC_API_KEY and ANTHROPIC_BASE_URL to a specific call without
spawning a subprocess. Useful when the surrounding shell has polluted env vars
(e.g. pointing at OpenRouter) and we need to force the default Anthropic endpoint.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

_VARS = ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN")


@contextmanager
def anthropic_env(api_key: str, base_url: str | None = None) -> Iterator[None]:
    """Temporarily set ANTHROPIC_API_KEY (+ optional base URL) in os.environ.

    Args:
        api_key:  Anthropic API key to expose for the duration of the block.
        base_url: If provided, overrides ANTHROPIC_BASE_URL; if None, the env var
                  is *removed* so the SDK falls back to the default Anthropic host.

    On exit the previous values are restored exactly (including unset state).
    """
    if not api_key:
        raise ValueError("anthropic_env: api_key must be non-empty")

    previous: dict[str, str | None] = {k: os.environ.get(k) for k in _VARS}

    try:
        os.environ["ANTHROPIC_API_KEY"] = api_key
        if base_url is None:
            os.environ.pop("ANTHROPIC_BASE_URL", None)
        else:
            os.environ["ANTHROPIC_BASE_URL"] = base_url
        os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
        yield
    finally:
        for k, v in previous.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
