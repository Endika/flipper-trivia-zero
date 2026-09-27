"""CLI entry point: builds the bilingual question pack from Open Trivia DB.

Outputs (TZ_TRANSLATOR=anthropic):
- data/trivia_{es,en}.{tsv,idx}        — binary pack for review/debug.
- src/data/embedded_pack_{es,en}.c     — C source compiled into the FAP.

The stub backend writes both to data/_cache/stub_pack/ instead, so its
placeholder text can never replace the committed pack.

The pack size is capped via TZ_PACK_LIMIT (default 1000). EN is the
canonical source; ES is produced by translating each EN question.

Usage:
    python build_pack.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from trivia_pack.opentdb import OpenTdbClient
from trivia_pack.pipeline import run_pipeline
from trivia_pack.translate import backend_from_env, translator_for

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DATA_DIR = _REPO_ROOT / "data"
_CACHE_DIR = _DATA_DIR / "_cache"
_BLACKLIST = _DATA_DIR / "blacklist.txt"
_C_OUT_DIR = _REPO_ROOT / "src" / "data"
_STUB_OUT_DIR = _CACHE_DIR / "stub_pack"
_DEFAULT_LIMIT = 1000


def output_dirs(backend: str) -> tuple[Path, Path]:
    """Returns (pack_dir, c_dir) for a backend."""
    if backend == "anthropic":
        return _DATA_DIR, _C_OUT_DIR
    return _STUB_OUT_DIR, _STUB_OUT_DIR


def main() -> int:
    if not _BLACKLIST.exists():
        print(f"error: blacklist not found at {_BLACKLIST}", file=sys.stderr)
        return 1

    limit_env = os.environ.get("TZ_PACK_LIMIT")
    limit = int(limit_env) if limit_env else _DEFAULT_LIMIT

    try:
        backend = backend_from_env()
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    out_dir, c_out_dir = output_dirs(backend)

    opentdb = OpenTdbClient(cache_dir=_CACHE_DIR / "opentdb")
    translator = translator_for(backend, cache_dir=_CACHE_DIR)

    run_pipeline(
        opentdb=opentdb,
        translator=translator,
        blacklist_path=_BLACKLIST,
        out_dir=out_dir,
        c_out_dir=c_out_dir,
        limit=limit,
    )
    print(f"ok: pack written to {out_dir.relative_to(_REPO_ROOT)}/trivia_{{es,en}}.{{tsv,idx}}")
    print(
        f"ok: embedded pack written to "
        f"{c_out_dir.relative_to(_REPO_ROOT)}/embedded_pack_{{es,en}}.c",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
