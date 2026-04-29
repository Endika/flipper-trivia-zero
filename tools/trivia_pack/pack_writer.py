"""Writes the (TSV, IDX) pair per language. Format mirrors the C pack_reader."""

from __future__ import annotations

import struct
from collections.abc import Sequence
from pathlib import Path

from trivia_pack.models import BilingualQuestion

_MAGIC = b"TRVI"
_VERSION = 1
_MIN_BUCKET_ID = 1
_MAX_BUCKET_ID = 7


def _sanitize(field: str) -> str:
    """Replace tabs and newlines with single spaces — the runtime parser cannot
    handle them in fields, so the pipeline must scrub them defensively."""
    return field.replace("\t", " ").replace("\n", " ").replace("\r", " ")


def write_pack(questions: Sequence[BilingualQuestion], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for q in questions:
        if not (_MIN_BUCKET_ID <= q.bucket_id <= _MAX_BUCKET_ID):
            raise ValueError(f"bucket_id {q.bucket_id} is out of range 1..7")

    _write_one(
        out_dir / "trivia_es.tsv",
        out_dir / "trivia_es.idx",
        [(_sanitize(q.question_es), _sanitize(q.answer_es), q.bucket_id) for q in questions],
    )
    _write_one(
        out_dir / "trivia_en.tsv",
        out_dir / "trivia_en.idx",
        [(_sanitize(q.question_en), _sanitize(q.answer_en), q.bucket_id) for q in questions],
    )


def _write_one(
    tsv_path: Path,
    idx_path: Path,
    rows: list[tuple[str, str, int]],
) -> None:
    offsets: list[int] = []
    cursor = 0
    with tsv_path.open("wb") as fh:
        for i, (question, answer, bucket_id) in enumerate(rows):
            line = f"{i}\t{bucket_id}\t{question}\t{answer}\n".encode()
            offsets.append(cursor)
            fh.write(line)
            cursor += len(line)

    count = len(rows)
    blob = bytearray()
    blob += _MAGIC
    blob += struct.pack("<H", _VERSION)
    blob += struct.pack("<I", count)
    for off in offsets:
        blob += struct.pack("<I", off)
    idx_path.write_bytes(bytes(blob))
