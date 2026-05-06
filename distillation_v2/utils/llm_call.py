"""Unified LLM call helper for Teacher, Judge, and RubricGen.

Routes to OpenRouter (via openai SDK) or Anthropic SDK depending on base_url.
- OpenRouter: base_url contains 'openrouter' → use openai.OpenAI client
- Anthropic:  base_url is None → use anthropic.Anthropic client directly
"""

from __future__ import annotations

import logging
from typing import Any

_log = logging.getLogger("distillation.v2.llm_call")

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def call_llm(
    *,
    system: str,
    user: str | list[dict[str, Any]],
    model: str,
    api_key: str,
    max_tokens: int,
    base_url: str | None = None,
) -> tuple[str, dict[str, int]]:
    """Call an LLM and return (text_response, usage_dict).

    Args:
        system:     System prompt string.
        user:       User message — either a plain string or a list of content
                    blocks (text + image) in Anthropic format.
        model:      Model ID (e.g. 'anthropic/claude-haiku-4-5').
        api_key:    API key for the backend.
        max_tokens: Max tokens to generate.
        base_url:   If set to an OpenRouter URL, routes via openai SDK.
                    If None, routes via Anthropic SDK directly.

    Returns:
        (text, {"prompt_tokens": N, "completion_tokens": M})
    """
    if base_url and "openrouter" in base_url:
        return _call_openrouter(
            system=system,
            user=user,
            model=model,
            api_key=api_key,
            max_tokens=max_tokens,
            base_url=base_url,
        )
    return _call_anthropic(
        system=system,
        user=user,
        model=model,
        api_key=api_key,
        max_tokens=max_tokens,
    )


# ── OpenRouter backend (openai SDK) ───────────────────────────────────────────


def _call_openrouter(
    *,
    system: str,
    user: str | list[dict[str, Any]],
    model: str,
    api_key: str,
    max_tokens: int,
    base_url: str,
) -> tuple[str, dict[str, int]]:
    from openai import OpenAI

    client = OpenAI(base_url=base_url, api_key=api_key)

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": _to_openai_content(user)},
    ]
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
    )
    text = resp.choices[0].message.content or ""
    usage = {
        "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
        "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
    }
    return text.strip(), usage


def _to_openai_content(
    user: str | list[dict[str, Any]],
) -> str | list[dict[str, Any]]:
    """Convert Anthropic-style content blocks to OpenAI format."""
    if isinstance(user, str):
        return user

    result: list[dict[str, Any]] = []
    for block in user:
        if block.get("type") == "text":
            result.append({"type": "text", "text": block["text"]})
        elif block.get("type") == "image":
            src = block.get("source", {})
            if src.get("type") == "base64":
                result.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{src['media_type']};base64,{src['data']}"
                        },
                    }
                )
    return result


# ── Anthropic backend (anthropic SDK) ─────────────────────────────────────────


def _call_anthropic(
    *,
    system: str,
    user: str | list[dict[str, Any]],
    model: str,
    api_key: str,
    max_tokens: int,
) -> tuple[str, dict[str, int]]:
    import anthropic

    content = user if isinstance(user, list) else [{"type": "text", "text": user}]
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": content}],
    )
    text = message.content[0].text.strip()
    usage = {
        "prompt_tokens": message.usage.input_tokens,
        "completion_tokens": message.usage.output_tokens,
    }
    return text, usage
