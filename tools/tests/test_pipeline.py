from __future__ import annotations

from pathlib import Path

from trivia_pack.models import Lang, RawQuestion
from trivia_pack.pipeline import run_pipeline
from trivia_pack.translate import StubTranslator


class _FakeOpenTdb:
    def __init__(self, by_lang: dict[Lang, list[RawQuestion]]) -> None:
        self._by_lang = by_lang

    def iter_all(self, lang: Lang) -> list[RawQuestion]:
        return list(self._by_lang.get(lang, []))


def test_pipeline_translates_en_source_to_spanish(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    out_dir = tmp_path / "out"
    blacklist_path = tmp_path / "bl.txt"
    blacklist_path.write_text("NFL\nSuper Bowl\n", encoding="utf-8")

    fake = _FakeOpenTdb(
        by_lang={
            Lang.EN: [
                RawQuestion(Lang.EN, "Geography", "Capital of Spain?", "Madrid"),
                RawQuestion(Lang.EN, "Sports", "Who won Super Bowl XII?", "Cowboys"),  # blacklist
                RawQuestion(Lang.EN, "Sports", "Who won the NFL MVP?", "X"),  # blacklist
                RawQuestion(Lang.EN, "History", "Who painted the Mona Lisa?", "Da Vinci"),
            ],
        }
    )
    translator = StubTranslator(cache_path=cache_dir / "translations.json")

    run_pipeline(
        opentdb=fake,
        translator=translator,
        blacklist_path=blacklist_path,
        out_dir=out_dir,
    )

    es_lines = (out_dir / "trivia_es.tsv").read_text(encoding="utf-8").splitlines()
    en_lines = (out_dir / "trivia_en.tsv").read_text(encoding="utf-8").splitlines()
    assert len(es_lines) == 2
    assert len(en_lines) == 2

    for es, en in zip(es_lines, en_lines, strict=True):
        es_parts = es.split("\t")
        en_parts = en.split("\t")
        assert es_parts[0] == en_parts[0]  # id
        assert es_parts[1] == en_parts[1]  # category_id

    en_content = "\n".join(en_lines)
    es_content = "\n".join(es_lines)
    assert "Capital of Spain?" in en_content  # EN preserved verbatim (after sanitize)
    assert "[es] Capital of Spain?" in es_content  # ES is the EN→ES stub translation


def test_pipeline_respects_limit(tmp_path: Path) -> None:
    blacklist_path = tmp_path / "bl.txt"
    blacklist_path.write_text("", encoding="utf-8")
    fake = _FakeOpenTdb(
        by_lang={
            Lang.EN: [RawQuestion(Lang.EN, "Geography", f"Q{i}?", f"A{i}") for i in range(50)],
        }
    )
    translator = StubTranslator(cache_path=tmp_path / "cache" / "translations.json")
    out_dir = tmp_path / "out"

    run_pipeline(
        opentdb=fake,
        translator=translator,
        blacklist_path=blacklist_path,
        out_dir=out_dir,
        limit=10,
    )
    assert len((out_dir / "trivia_en.tsv").read_text(encoding="utf-8").splitlines()) == 10
