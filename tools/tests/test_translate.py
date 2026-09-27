from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from trivia_pack.models import Lang
from trivia_pack.translate import StubTranslator, Translator, backend_from_env, translator_for


@pytest.fixture
def cache_path(tmp_path: Path) -> Path:
    return tmp_path / "translations.json"


def test_stub_translator_round_trip(cache_path: Path) -> None:
    t: Translator = StubTranslator(cache_path=cache_path)

    assert t.translate("Hello", source=Lang.EN, target=Lang.ES) == "[es] Hello"
    assert t.translate("Hola", source=Lang.ES, target=Lang.EN) == "[en] Hola"


def test_translator_caches_on_disk(cache_path: Path) -> None:
    t1 = StubTranslator(cache_path=cache_path)
    t1.translate("Hello", source=Lang.EN, target=Lang.ES)
    t1.flush()
    assert cache_path.exists()

    # New translator, same cache file → second call should not re-translate.
    t2 = StubTranslator(cache_path=cache_path)
    assert t2.translate("Hello", source=Lang.EN, target=Lang.ES) == "[es] Hello"
    assert t2.cache_hits == 1
    assert t2.cache_misses == 0


def test_same_input_distinct_target_caches_separately(cache_path: Path) -> None:
    t = StubTranslator(cache_path=cache_path)
    a = t.translate("Hello", source=Lang.EN, target=Lang.ES)
    b = t.translate("Hello", source=Lang.EN, target=Lang.EN)  # identity
    assert a == "[es] Hello"
    assert b == "Hello"  # translating to source language is identity


def test_empty_string_translates_to_empty(cache_path: Path) -> None:
    t = StubTranslator(cache_path=cache_path)
    assert t.translate("", source=Lang.EN, target=Lang.ES) == ""


def test_unknown_backend_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TZ_TRANSLATOR", "antropic")
    with pytest.raises(ValueError, match="antropic"):
        backend_from_env()


def test_backend_defaults_to_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TZ_TRANSLATOR", raising=False)
    assert backend_from_env() == "stub"


class _FakeMessages:
    def create(self, **_: object) -> SimpleNamespace:
        return SimpleNamespace(content=[SimpleNamespace(text="Hola")])


def test_stub_cache_is_never_served_by_anthropic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stub = translator_for("stub", cache_dir=tmp_path)
    stub.translate("Hello", source=Lang.EN, target=Lang.ES)
    stub.flush()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(
        "trivia_pack.translate.anthropic.Anthropic",
        lambda **_: SimpleNamespace(messages=_FakeMessages()),
    )
    real = translator_for("anthropic", cache_dir=tmp_path)
    assert real.translate("Hello", source=Lang.EN, target=Lang.ES) == "Hola"


def test_override_wins_over_cache_and_backend(cache_path: Path) -> None:
    cached = StubTranslator(cache_path=cache_path)
    cached.translate("Jerk", source=Lang.EN, target=Lang.ES)
    cached.flush()

    t = StubTranslator(cache_path=cache_path, overrides={"en->es|Jerk": "Sobreaceleracion"})
    assert t.translate("Jerk", source=Lang.EN, target=Lang.ES) == "Sobreaceleracion"
    assert t.translate("Jerk ", source=Lang.EN, target=Lang.ES) == "Sobreaceleracion"
    assert t.translate("Jerk", source=Lang.ES, target=Lang.EN) == "[en] Jerk"
