"""CLI entry point: builds data/trivia_{es,en}.{tsv,idx} from Open Trivia DB.

Usage:
    python build_pack.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from trivia_pack.opentdb import OpenTdbClient
from trivia_pack.pipeline import run_pipeline
from trivia_pack.translate import translator_from_env

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DATA_DIR = _REPO_ROOT / "data"
_CACHE_DIR = _DATA_DIR / "_cache"
_BLACKLIST = _DATA_DIR / "blacklist.txt"


def main() -> int:
    if not _BLACKLIST.exists():
        print(f"error: blacklist not found at {_BLACKLIST}", file=sys.stderr)
        return 1

    opentdb = OpenTdbClient(cache_dir=_CACHE_DIR / "opentdb")
    translator = translator_from_env(cache_path=_CACHE_DIR / "translations.json")

    run_pipeline(
        opentdb=opentdb,
        translator=translator,
        blacklist_path=_BLACKLIST,
        out_dir=_DATA_DIR,
    )
    print("ok: pack written to data/trivia_{es,en}.{tsv,idx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
