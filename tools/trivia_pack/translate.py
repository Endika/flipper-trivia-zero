"""Translation backends for the data pipeline.

The Translator protocol defines the contract every backend implements. Two
concrete backends are shipped:

  StubTranslator     — deterministic, network-free, default.
  AnthropicTranslator — real Claude Haiku translations behind an env var.

Each backend keeps its own on-disk JSON cache, so stub placeholders can
never be served as real translations. Hand-reviewed fixes live in a
committed overrides file (same key format as the caches) that wins over
both the cache and the backend.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

import anthropic

from trivia_pack.models import Lang


def _key(text: str, source: Lang, target: Lang) -> str:
    s = "es" if source == Lang.ES else "en"
    t = "es" if target == Lang.ES else "en"
    return f"{s}->{t}|{text}"


class Translator(Protocol):
    cache_hits: int
    cache_misses: int

    def translate(self, text: str, *, source: Lang, target: Lang) -> str: ...

    def flush(self) -> None: ...


def load_overrides(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    data: dict[str, str] = json.loads(path.read_text(encoding="utf-8"))
    return data


class _CachedTranslator:
    def __init__(self, cache_path: Path, overrides: Mapping[str, str] | None = None) -> None:
        self._cache_path = cache_path
        self._overrides = overrides or {}
        self._cache: dict[str, str] = {}
        if cache_path.exists():
            self._cache = json.loads(cache_path.read_text(encoding="utf-8"))
        self.cache_hits = 0
        self.cache_misses = 0

    def translate(self, text: str, *, source: Lang, target: Lang) -> str:
        if not text:
            return ""
        if source == target:
            return text
        override = self._overrides.get(_key(text.strip(), source, target))
        if override is not None:
            return override
        k = _key(text, source, target)
        cached = self._cache.get(k)
        if cached is not None:
            self.cache_hits += 1
            return cached
        self.cache_misses += 1
        out = self._translate_uncached(text, source=source, target=target)
        self._cache[k] = out
        return out

    def flush(self) -> None:
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache_path.write_text(
            json.dumps(self._cache, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _translate_uncached(self, text: str, *, source: Lang, target: Lang) -> str:
        raise NotImplementedError


class StubTranslator(_CachedTranslator):
    def _translate_uncached(self, text: str, *, source: Lang, target: Lang) -> str:
        del source
        prefix = "[es]" if target == Lang.ES else "[en]"
        return f"{prefix} {text}"


class AnthropicTranslator(_CachedTranslator):
    """Real translations via Claude Haiku.

    Activated when `TZ_TRANSLATOR=anthropic`. Requires `ANTHROPIC_API_KEY`.
    """

    _MODEL = "claude-haiku-4-5-20251001"
    _SYSTEM_PROMPT = (
        "You translate trivia questions or short answers between Spanish and English. "
        "Return only the translation, with no commentary, no quotes, and no surrounding "
        "whitespace. Output must not contain tab or newline characters."
    )

    def __init__(self, cache_path: Path, overrides: Mapping[str, str] | None = None) -> None:
        super().__init__(cache_path=cache_path, overrides=overrides)
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is required for AnthropicTranslator.")
        self._client = anthropic.Anthropic(api_key=api_key)

    def _translate_uncached(self, text: str, *, source: Lang, target: Lang) -> str:
        target_name = "Spanish" if target == Lang.ES else "English"
        source_name = "Spanish" if source == Lang.ES else "English"
        # The system prompt is far below the minimum cacheable length, so this
        # cache_control marker doesn't cache anything.
        system_block: dict[str, object] = {
            "type": "text",
            "text": self._SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }
        msg = self._client.messages.create(
            model=self._MODEL,
            max_tokens=400,
            system=[system_block],  # type: ignore[list-item]
            messages=[
                {
                    "role": "user",
                    "content": f"Translate from {source_name} to {target_name}:\n{text}",
                },
            ],
        )
        parts: list[str] = []
        for block in msg.content:
            text_attr = getattr(block, "text", None)
            if isinstance(text_attr, str):
                parts.append(text_attr)
        return "".join(parts).strip().replace("\t", " ").replace("\n", " ")


_BACKENDS: dict[str, type[_CachedTranslator]] = {
    "stub": StubTranslator,
    "anthropic": AnthropicTranslator,
}


def backend_from_env() -> str:
    """Reads TZ_TRANSLATOR (defaults to stub) and rejects unknown values."""
    backend = os.environ.get("TZ_TRANSLATOR", "stub").lower()
    if backend not in _BACKENDS:
        valid = ", ".join(sorted(_BACKENDS))
        raise ValueError(f"unknown TZ_TRANSLATOR {backend!r}; expected one of: {valid}")
    return backend


def translator_for(
    backend: str, cache_dir: Path, overrides: Mapping[str, str] | None = None
) -> Translator:
    return _BACKENDS[backend](
        cache_path=cache_dir / f"translations_{backend}.json",
        overrides=overrides,
    )
