"""Composition root for the off-Flipper data pipeline."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from trivia_pack.blacklist import Blacklist
from trivia_pack.category_map import map_opentdb_to_bucket
from trivia_pack.models import BilingualQuestion, Lang, MappedQuestion, RawQuestion
from trivia_pack.pack_writer import write_embedded_pack, write_pack
from trivia_pack.translate import Translator


class _OpenTdbSource(Protocol):
    def iter_all(self, lang: Lang) -> Iterable[RawQuestion]: ...


@dataclass(frozen=True)
class _DedupeKey:
    bucket_id: int
    source_lang: Lang
    question_normalized: str


def _normalize(s: str) -> str:
    return " ".join(s.lower().strip().split())


def _filter_and_map(
    raw: Iterable[RawQuestion],
    blacklist: Blacklist,
) -> list[MappedQuestion]:
    out: list[MappedQuestion] = []
    for q in raw:
        if blacklist.is_blacklisted(q.question, q.answer):
            continue
        try:
            bucket = map_opentdb_to_bucket(q.opentdb_category)
        except KeyError:
            print(
                f"warn: unknown OpenTDB category {q.opentdb_category!r}, dropping question.",
            )
            continue
        out.append(
            MappedQuestion(
                source_lang=q.source_lang,
                bucket_id=int(bucket),
                question=q.question,
                answer=q.answer,
            ),
        )
    return out


def _build_bilingual(
    mapped: list[MappedQuestion],
    translator: Translator,
) -> list[BilingualQuestion]:
    seen: set[_DedupeKey] = set()
    out: list[BilingualQuestion] = []
    for q in mapped:
        key = _DedupeKey(
            bucket_id=q.bucket_id,
            source_lang=q.source_lang,
            question_normalized=_normalize(q.question),
        )
        if key in seen:
            continue
        seen.add(key)

        if q.source_lang == Lang.EN:
            question_en = q.question
            answer_en = q.answer
            question_es = translator.translate(q.question, source=Lang.EN, target=Lang.ES)
            answer_es = translator.translate(q.answer, source=Lang.EN, target=Lang.ES)
        else:
            question_es = q.question
            answer_es = q.answer
            question_en = translator.translate(q.question, source=Lang.ES, target=Lang.EN)
            answer_en = translator.translate(q.answer, source=Lang.ES, target=Lang.EN)

        out.append(
            BilingualQuestion(
                bucket_id=q.bucket_id,
                question_es=question_es,
                answer_es=answer_es,
                question_en=question_en,
                answer_en=answer_en,
            ),
        )
    return out


def run_pipeline(
    *,
    opentdb: _OpenTdbSource,
    translator: Translator,
    blacklist_path: Path,
    out_dir: Path,
    c_out_dir: Path | None = None,
) -> None:
    """Runs the full pipeline.

    Always emits the binary pack to `out_dir` (data/trivia_*.{tsv,idx}) for
    review and debugging. If `c_out_dir` is provided, also emits the
    embedded C source files (src/data/embedded_pack_*.c) which the FAP
    compiles into its binary.
    """
    blacklist = Blacklist.from_file(blacklist_path)
    raw_en = list(opentdb.iter_all(Lang.EN))
    raw_es = list(opentdb.iter_all(Lang.ES))
    mapped = _filter_and_map([*raw_en, *raw_es], blacklist)
    bilingual = _build_bilingual(mapped, translator)
    bilingual.sort(key=lambda q: (q.bucket_id, q.question_en))
    write_pack(bilingual, out_dir=out_dir)
    if c_out_dir is not None:
        write_embedded_pack(bilingual, c_out_dir=c_out_dir)
    translator.flush()
