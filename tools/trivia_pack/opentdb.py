"""Open Trivia DB API client with on-disk JSON cache.

The cache is a single JSON file per language (cache_dir/opentdb_{lang}.json).
On first call, fetches all available questions in batches of 50 until the
API returns response_code != 0 (no more results). Subsequent calls of the
same language skip the network entirely.
"""

from __future__ import annotations

import html
import json
import time
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

from trivia_pack.models import Lang, RawQuestion

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

_API_URL = "https://opentdb.com/api.php"
_PAGE_SIZE = 50
_REQUEST_DELAY_SECONDS = 5.0


class OpenTdbClient:
    def __init__(self, cache_dir: Path, *, sleep_between: float = _REQUEST_DELAY_SECONDS) -> None:
        self._cache_dir = cache_dir
        self._sleep_between = sleep_between

    def iter_all(self, lang: Lang) -> Iterator[RawQuestion]:
        cache_file = self._cache_path(lang)
        if cache_file.exists():
            yield from self._load_cache(cache_file)
            return

        questions = list(self._fetch_all(lang))
        self._save_cache(cache_file, questions)
        yield from questions

    def _cache_path(self, lang: Lang) -> Path:
        suffix = "es" if lang == Lang.ES else "en"
        return self._cache_dir / f"opentdb_{suffix}.json"

    def _fetch_all(self, lang: Lang) -> Iterable[RawQuestion]:
        suffix = "es" if lang == Lang.ES else "en"
        first = True
        with httpx.Client(timeout=30.0) as client:
            while True:
                if not first:
                    time.sleep(self._sleep_between)
                first = False

                resp = client.get(
                    _API_URL,
                    params={"amount": str(_PAGE_SIZE), "language": suffix},
                )
                resp.raise_for_status()
                payload = resp.json()
                if payload.get("response_code", 0) != 0:
                    return
                results = payload.get("results", [])
                if not results:
                    return
                for r in results:
                    yield RawQuestion(
                        source_lang=lang,
                        opentdb_category=html.unescape(r["category"]),
                        question=html.unescape(r["question"]),
                        answer=html.unescape(r["correct_answer"]),
                    )

    def _save_cache(self, path: Path, questions: list[RawQuestion]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        serializable = [
            {
                "source_lang": "ES" if q.source_lang == Lang.ES else "EN",
                "opentdb_category": q.opentdb_category,
                "question": q.question,
                "answer": q.answer,
            }
            for q in questions
        ]
        path.write_text(
            json.dumps(serializable, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_cache(self, path: Path) -> Iterator[RawQuestion]:
        for entry in json.loads(path.read_text(encoding="utf-8")):
            yield RawQuestion(
                source_lang=Lang.ES if entry["source_lang"] == "ES" else Lang.EN,
                opentdb_category=entry["opentdb_category"],
                question=entry["question"],
                answer=entry["answer"],
            )
