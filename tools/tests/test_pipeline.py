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


def test_pipeline_emits_symmetric_files(tmp_path: Path) -> None:
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
            ],
            Lang.ES: [
                RawQuestion(Lang.ES, "History", "¿Quién pintó La Mona Lisa?", "Da Vinci"),
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
    assert len(es_lines) == 2  # Geography + History (NFL+Super Bowl filtered out)
    assert len(en_lines) == 2

    # Same id and category on both sides
    for es, en in zip(es_lines, en_lines, strict=True):
        es_parts = es.split("\t")
        en_parts = en.split("\t")
        assert es_parts[0] == en_parts[0]  # id
        assert es_parts[1] == en_parts[1]  # category_id

    # Stub fills missing translations
    es_content = "\n".join(es_lines)
    assert "[es] Capital of Spain?" in es_content  # EN→ES via stub
    en_content = "\n".join(en_lines)
    assert "[en] ¿Quién pintó La Mona Lisa?" in en_content  # ES→EN via stub
