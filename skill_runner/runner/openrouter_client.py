"""OpenRouter API client using OpenAI SDK (OpenRouter is OpenAI-compatible)."""

import time
import openai
from typing import Callable, TypeVar

T = TypeVar("T")


def create_openrouter_client(api_key: str, base_url: str = "https://openrouter.ai/api/v1") -> openai.OpenAI:
    """Create an OpenAI client configured for OpenRouter."""
    return openai.OpenAI(
        base_url=base_url,
        api_key=api_key,
    )


def call_with_retry(fn: Callable[[], T], max_retries: int = 3, base_delay: float = 2.0) -> T:
    """
    Call a function with exponential backoff retry for rate limits.

    Args:
        fn: Callable that makes the API request (no arguments).
        max_retries: Maximum number of retry attempts.
        base_delay: Base delay in seconds (doubles each retry).

    Returns:
        Return value of fn().

    Raises:
        openai.RateLimitError: If all retries are exhausted.
        openai.APIError: If a non-retryable API error occurs.
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            return fn()
        except openai.RateLimitError as e:
            last_exc = e
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            time.sleep(delay)
        except openai.APIStatusError as e:
            last_exc = e
            # Only retry on 5xx server errors
            if e.status_code and e.status_code < 500:
                raise
            if attempt == max_retries - 1:
                raise
            time.sleep(base_delay)
        except openai.APIConnectionError as e:
            last_exc = e
            if attempt == max_retries - 1:
                raise
            time.sleep(base_delay)

    raise RuntimeError(f"All {max_retries} retries failed") from last_exc
