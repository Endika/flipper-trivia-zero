# Trivia Zero — Plan 2: Off-Flipper Python Data Pipeline

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the off-Flipper Python pipeline under `tools/` that produces the question packs the FAP consumes. End state: running `make pack` ingests OpenTDB (cached locally), filters culturally-anglo content with a versioned blacklist, maps OpenTDB's 24 categories to the 7-bucket Trivia Zero taxonomy, fills missing translations via an LLM (stub by default, Anthropic Haiku when `TZ_TRANSLATOR=anthropic`), and emits a symmetric pack: `data/trivia_es.tsv` + `.idx` and `data/trivia_en.tsv` + `.idx` — same `id` and `category_id` across languages, only the question/answer text differs.

**Architecture:** Python 3.11+ package `trivia_pack` under `tools/`. Pure modules (models, category_map, blacklist, pack_writer) are unit-tested with `pytest`. The OpenTDB client and translator both write through to file caches in `data/` so reruns don't hammer the network or burn tokens. The orchestrator composes these modules; an end-to-end test verifies the output is consumable by the existing C `test_pack_integration` binary.

**Tech Stack:** Python 3.11+, `httpx` (HTTP client), `anthropic` (LLM SDK, optional via env var), `pytest` (tests), `ruff` (lint+format), `mypy --strict` (type-check). Configured through `tools/pyproject.toml`. No Poetry — `pip install -r requirements.txt` is enough for a one-shot pipeline.

**Reference:**
- Spec sections §4 (data pipeline), §4.4 (category mapping table), §5.1/§5.2 (TSV+IDX format).
- The C `pack_reader` already implemented in Plan 3 is the **consumer** of the output and is the source of truth for the byte layout.
- The user's `backend-api/pyproject.toml` is the conventional reference for ruff/mypy/pytest configuration in this workspace (`/home/endikaiglesias/workspace/backend-api/pyproject.toml`).

**Prerequisites:**
- Plans 1 (scaffolding) and 3 (FAP) are complete. The C-side test suite (10 host tests) is green.
- Repo root is `/home/endikaiglesias/workspace/flipper-trivia-zero/`. All paths in this plan are relative to that root.
- Python 3.11+ is available on the host (`python3 --version`).
- `gcc`, `make`, `cppcheck`, `clang-format` from Plan 1 remain installed.
- The user runs `git init` / commits manually. **No subagent should run `git add`/`git commit`/any git mutation.** Each task's "Commit" step is overridden — skip it silently.

---

## Conventions used throughout this plan

- All Python sources live under `tools/`. The package itself is `tools/trivia_pack/`. Tests are `tools/tests/`. CLI entry points are flat scripts under `tools/` (e.g. `tools/build_pack.py`).
- Every module: full type hints, no `Any` (per workspace CLAUDE.md), passes `ruff check`, formatted by `ruff format`, passes `mypy --strict`. Tests use `pytest`.
- `data/blacklist.txt` is the versioned keyword blacklist (committed). The OpenTDB cache lives under `data/_cache/opentdb/` and is **not** committed (added to `.gitignore`). The translation cache `data/_cache/translations.json` is **not** committed (large, regenerable).
- The output `data/trivia_*.tsv` and `data/trivia_*.idx` **are** committed (per spec §10 default; cheap, reviewable).
- Network access is mocked in unit tests (no live OpenTDB calls). The translator defaults to a deterministic stub; the real Anthropic path is exercised only when `TZ_TRANSLATOR=anthropic` and `ANTHROPIC_API_KEY` are both set.

---

### Task 1: Python project bootstrap

**Files:**
- Create: `tools/pyproject.toml`
- Create: `tools/requirements.txt`
- Create: `tools/requirements-dev.txt`
- Create: `tools/README.md`
- Create: `tools/trivia_pack/__init__.py`
- Create: `tools/tests/__init__.py`
- Create: `tools/tests/test_smoke.py`
- Modify: `Makefile` (add `pack`, `py-test`, `py-lint`, `py-format`, `py-typecheck` targets)
- Modify: `.github/workflows/ci.yml` (add Python lint+test job)
- Modify: `.github/dependabot.yml` (add `pip` ecosystem)
- Modify: `.gitignore` (add Python cruft + `data/_cache/`)

- [ ] **Step 1: Create `tools/pyproject.toml`**

```toml
[project]
name = "trivia-pack"
version = "0.1.0"
description = "Off-Flipper data pipeline for Trivia Zero. Pulls Open Trivia DB, filters, translates, emits the TSV+IDX packs the FAP consumes."
requires-python = ">=3.11"
authors = [{ name = "Endika" }]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["ALL"]
ignore = [
    "ANN401",  # Dynamic Any
    "S101",    # assert in tests
    "D",       # docstrings only for public API
    "TRY003",  # long exception messages
    "EM101",   # exception string literal
    "EM102",
    "COM812",  # trailing-comma — conflicts with formatter
    "ISC001",  # implicit string concat — conflicts with formatter
    "PLR0913", # too many args
    "T201",    # allow print() in CLI scripts
]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101", "PLR2004", "ARG", "ANN", "INP001"]
"build_pack.py" = ["INP001"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true

[tool.pytest.ini_options]
minversion = "8.0"
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = ["-ra", "--strict-markers", "--tb=short"]
```

- [ ] **Step 2: Create `tools/requirements.txt`**

```
httpx==0.28.1
anthropic==0.40.0
```

- [ ] **Step 3: Create `tools/requirements-dev.txt`**

```
-r requirements.txt
pytest==8.3.4
ruff==0.8.4
mypy==1.13.0
respx==0.21.1
```

- [ ] **Step 4: Create `tools/README.md`**

```markdown
# Trivia Zero — Data Pipeline

Off-Flipper Python tooling that builds the question packs the FAP consumes.

## Install (host, one-time)

```
cd tools
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Build the pack

From the repo root:

```
make pack
```

This pulls Open Trivia DB (cached locally), applies the blacklist, maps categories, runs translations through the configured backend (stub by default), and writes:

- `data/trivia_es.tsv` + `data/trivia_es.idx`
- `data/trivia_en.tsv` + `data/trivia_en.idx`

## Translation backends

| `TZ_TRANSLATOR` | Behavior |
|-----------------|----------|
| unset / `stub` (default) | Deterministic stub — appends `[es]`/`[en]` markers. Useful for development; output is valid but not human-grade. |
| `anthropic` | Real translation via Anthropic Haiku. Requires `ANTHROPIC_API_KEY` env var. Cached on disk to `data/_cache/translations.json` so reruns are free. |

## Test

```
make py-test
```

## Lint, format, type-check

```
make py-lint
make py-format
make py-typecheck
```
```

- [ ] **Step 5: Create the Python package skeletons**

`tools/trivia_pack/__init__.py`:

```python
"""Off-Flipper data pipeline for Trivia Zero."""

__version__ = "0.1.0"
```

`tools/tests/__init__.py`:

```python
```

`tools/tests/test_smoke.py`:

```python
from trivia_pack import __version__


def test_package_version_exposed() -> None:
    assert __version__ == "0.1.0"
```

- [ ] **Step 6: Update the root `Makefile`**

Edit `Makefile`:

1. Add to the `.PHONY` line: `pack py-install py-test py-lint py-format py-typecheck`.
2. Add to the `help:` block (insert near the existing format/linter lines):

```
	@echo "  make py-install     - pip install Python pipeline deps (in tools/.venv)"
	@echo "  make py-test        - pytest the Python pipeline"
	@echo "  make py-lint        - ruff check the Python pipeline"
	@echo "  make py-format      - ruff format the Python pipeline"
	@echo "  make py-typecheck   - mypy --strict the Python pipeline"
	@echo "  make pack           - build data/trivia_{es,en}.{tsv,idx}"
```

3. Append after the existing `clean` recipe:

```
PY_VENV = tools/.venv
PY = $(PY_VENV)/bin/python
PIP = $(PY_VENV)/bin/pip

$(PY_VENV)/bin/activate: tools/requirements-dev.txt
	python3 -m venv $(PY_VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r tools/requirements-dev.txt
	@touch $(PY_VENV)/bin/activate

py-install: $(PY_VENV)/bin/activate

py-test: py-install
	cd tools && ../$(PY) -m pytest

py-lint: py-install
	cd tools && ../$(PY) -m ruff check .

py-format: py-install
	cd tools && ../$(PY) -m ruff format .

py-typecheck: py-install
	cd tools && ../$(PY) -m mypy --strict trivia_pack

pack: py-install
	cd tools && ../$(PY) build_pack.py
```

(Use TAB indentation for recipe lines.)

- [ ] **Step 7: Update `.gitignore`**

Append:

```
# Python
tools/.venv/
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Pipeline caches (regenerable, not committed)
data/_cache/
```

- [ ] **Step 8: Update `.github/workflows/ci.yml`**

Add a second job after `test`. The full file becomes:

```yaml
name: CI

on:
  push:
  pull_request:
  workflow_call:

jobs:
  test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: .
    steps:
      - uses: actions/checkout@v6
      - name: Install dependencies
        run: sudo apt-get update && sudo apt-get install -y build-essential cppcheck clang-format
      - name: Run linter
        run: make linter
      - name: Check format
        run: git ls-files '*.c' '*.h' | xargs clang-format --dry-run --Werror
      - name: Run tests
        run: make test

  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install Python deps
        run: |
          python -m pip install --upgrade pip
          pip install -r tools/requirements-dev.txt
      - name: Ruff check
        run: cd tools && python -m ruff check .
      - name: Ruff format check
        run: cd tools && python -m ruff format --check .
      - name: Mypy
        run: cd tools && python -m mypy --strict trivia_pack
      - name: Pytest
        run: cd tools && python -m pytest
```

(This file is created via `bash heredoc` because the `Write` tool's GitHub-Actions security hook flags any workflow edit. The content above does not use any untrusted GitHub event input — it is safe.)

- [ ] **Step 9: Update `.github/dependabot.yml`**

```yaml
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
  - package-ecosystem: "pip"
    directory: "/tools"
    schedule:
      interval: "weekly"
```

- [ ] **Step 10: Verify the smoke test passes end-to-end**

Run:

```
make py-install
make py-test
make py-lint
make py-format && git diff --exit-code
make py-typecheck
```

Expected:
- `py-install` creates `tools/.venv/` and installs deps (slow first time, ~30s).
- `py-test` runs `tests/test_smoke.py::test_package_version_exposed` and exits 0 (1 passed).
- `py-lint` exits 0 with no findings.
- `py-format` is a no-op; `git diff --exit-code` exits 0.
- `py-typecheck` exits 0 with no errors.

Also confirm the C side did not regress: `make test` from the root still passes all 10 binaries.

- [ ] **Step 11: Skipped commit.**

---

### Task 2: Domain models + category mapper (TDD)

**Files:**
- Create: `tools/trivia_pack/models.py`
- Create: `tools/trivia_pack/category_map.py`
- Create: `tools/tests/test_category_map.py`

`models.py` defines the dataclasses passed between modules. `category_map.py` is the OpenTDB-string → bucket-id table from spec §4.4 plus a small helper.

- [ ] **Step 1: Write `tools/tests/test_category_map.py` (failing test)**

```python
from trivia_pack.category_map import (
    BucketId,
    CATEGORY_MAP,
    map_opentdb_to_bucket,
)


def test_general_knowledge_maps_to_cultura_general() -> None:
    assert map_opentdb_to_bucket("General Knowledge") == BucketId.CULTURA_GENERAL


def test_geography_maps_to_geografia() -> None:
    assert map_opentdb_to_bucket("Geography") == BucketId.GEOGRAFIA


def test_sports_maps_to_deportes_y_ocio() -> None:
    assert map_opentdb_to_bucket("Sports") == BucketId.DEPORTES_Y_OCIO


def test_entertainment_subcategories_map_to_entretenimiento() -> None:
    for sub in (
        "Entertainment: Books",
        "Entertainment: Film",
        "Entertainment: Music",
        "Entertainment: Television",
        "Entertainment: Video Games",
        "Entertainment: Comics",
        "Entertainment: Japanese Anime & Manga",
    ):
        bucket = map_opentdb_to_bucket(sub)
        # Books map to Arts & Literature; the rest go to Entertainment
        if sub == "Entertainment: Books":
            assert bucket == BucketId.ARTE_Y_LITERATURA
        else:
            assert bucket == BucketId.ENTRETENIMIENTO


def test_science_subcategories_map_to_ciencia_y_naturaleza() -> None:
    for sub in (
        "Science & Nature",
        "Science: Computers",
        "Science: Mathematics",
        "Science: Gadgets",
        "Animals",
        "Vehicles",
    ):
        assert map_opentdb_to_bucket(sub) == BucketId.CIENCIA_Y_NATURALEZA


def test_history_and_politics_map_to_historia() -> None:
    assert map_opentdb_to_bucket("History") == BucketId.HISTORIA
    assert map_opentdb_to_bucket("Politics") == BucketId.HISTORIA


def test_mythology_and_art_map_to_arte_y_literatura() -> None:
    assert map_opentdb_to_bucket("Mythology") == BucketId.ARTE_Y_LITERATURA
    assert map_opentdb_to_bucket("Art") == BucketId.ARTE_Y_LITERATURA


def test_unknown_opentdb_category_raises() -> None:
    import pytest

    with pytest.raises(KeyError):
        map_opentdb_to_bucket("Some Future Category")


def test_full_table_covers_all_24_opentdb_categories() -> None:
    # Spec §4.4: 24 OpenTDB categories must each have a bucket.
    expected = {
        "General Knowledge",
        "Entertainment: Books",
        "Entertainment: Film",
        "Entertainment: Music",
        "Entertainment: Musicals & Theatres",
        "Entertainment: Television",
        "Entertainment: Video Games",
        "Entertainment: Board Games",
        "Entertainment: Comics",
        "Entertainment: Japanese Anime & Manga",
        "Entertainment: Cartoon & Animations",
        "Celebrities",
        "Science & Nature",
        "Science: Computers",
        "Science: Mathematics",
        "Science: Gadgets",
        "Animals",
        "Vehicles",
        "Geography",
        "History",
        "Politics",
        "Mythology",
        "Art",
        "Sports",
    }
    assert set(CATEGORY_MAP.keys()) == expected
```

- [ ] **Step 2: Verify it fails** with `cd tools && ../.venv/bin/python -m pytest tests/test_category_map.py` — expect `ImportError: trivia_pack.category_map`.

- [ ] **Step 3: Create `tools/trivia_pack/models.py`**

```python
"""Pure dataclasses passed between pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Lang(IntEnum):
    ES = 0
    EN = 1


@dataclass(frozen=True)
class RawQuestion:
    """A question as it arrives from Open Trivia DB, before mapping/filtering."""

    source_lang: Lang
    opentdb_category: str
    question: str
    answer: str


@dataclass(frozen=True)
class MappedQuestion:
    """A RawQuestion after blacklist + category mapping survived. Still single-language."""

    source_lang: Lang
    bucket_id: int
    question: str
    answer: str


@dataclass
class BilingualQuestion:
    """A question with both ES and EN text, ready to be packed."""

    bucket_id: int
    question_es: str
    answer_es: str
    question_en: str
    answer_en: str
```

- [ ] **Step 4: Create `tools/trivia_pack/category_map.py`**

```python
"""OpenTDB (24 native categories) → 7-bucket Trivia Zero taxonomy.

Source of truth: docs/superpowers/specs/2026-04-28-trivia-zero-design.md §4.4.
The four ⚠️ rows in the spec are resolved here; if user review changes any of
those, update both this table AND the spec.
"""

from __future__ import annotations

from enum import IntEnum


class BucketId(IntEnum):
    GEOGRAFIA = 1
    ENTRETENIMIENTO = 2
    HISTORIA = 3
    ARTE_Y_LITERATURA = 4
    CIENCIA_Y_NATURALEZA = 5
    DEPORTES_Y_OCIO = 6
    CULTURA_GENERAL = 7


CATEGORY_MAP: dict[str, BucketId] = {
    # General
    "General Knowledge": BucketId.CULTURA_GENERAL,
    # Geography
    "Geography": BucketId.GEOGRAFIA,
    # History / Politics / Mythology (Mythology lives here per spec §4.4)
    "History": BucketId.HISTORIA,
    "Politics": BucketId.HISTORIA,
    "Mythology": BucketId.ARTE_Y_LITERATURA,
    # Arts & Literature
    "Entertainment: Books": BucketId.ARTE_Y_LITERATURA,
    "Art": BucketId.ARTE_Y_LITERATURA,
    # Entertainment (films/music/games/celebs/etc.)
    "Entertainment: Film": BucketId.ENTRETENIMIENTO,
    "Entertainment: Music": BucketId.ENTRETENIMIENTO,
    "Entertainment: Musicals & Theatres": BucketId.ENTRETENIMIENTO,
    "Entertainment: Television": BucketId.ENTRETENIMIENTO,
    "Entertainment: Video Games": BucketId.ENTRETENIMIENTO,
    "Entertainment: Board Games": BucketId.ENTRETENIMIENTO,
    "Entertainment: Comics": BucketId.ENTRETENIMIENTO,
    "Entertainment: Japanese Anime & Manga": BucketId.ENTRETENIMIENTO,
    "Entertainment: Cartoon & Animations": BucketId.ENTRETENIMIENTO,
    "Celebrities": BucketId.ENTRETENIMIENTO,
    # Science & Nature
    "Science & Nature": BucketId.CIENCIA_Y_NATURALEZA,
    "Science: Computers": BucketId.CIENCIA_Y_NATURALEZA,
    "Science: Mathematics": BucketId.CIENCIA_Y_NATURALEZA,
    "Science: Gadgets": BucketId.CIENCIA_Y_NATURALEZA,
    "Animals": BucketId.CIENCIA_Y_NATURALEZA,
    "Vehicles": BucketId.CIENCIA_Y_NATURALEZA,
    # Sports
    "Sports": BucketId.DEPORTES_Y_OCIO,
}


def map_opentdb_to_bucket(opentdb_category: str) -> BucketId:
    """Returns the 7-bucket id for an OpenTDB category string.

    Raises KeyError if the category is not in the table — the pipeline should
    surface unknown categories as a hard failure rather than silently dropping
    them (we want OpenTDB additions to be a visible event, not data loss).
    """
    return CATEGORY_MAP[opentdb_category]
```

- [ ] **Step 5: Run the tests, verify pass**

`cd tools && ../.venv/bin/python -m pytest tests/test_category_map.py -v`
Expected: 8 passed.

- [ ] **Step 6: Run full Python suite, lint, type-check**

```
make py-test
make py-lint
make py-format && git diff --exit-code
make py-typecheck
```

All exit 0.

- [ ] **Step 7: Skipped commit.**

---

### Task 3: Blacklist filter (TDD)

**Files:**
- Create: `data/blacklist.txt`
- Create: `tools/trivia_pack/blacklist.py`
- Create: `tools/tests/test_blacklist.py`

The blacklist is a plain-text file, one keyword per line, lines starting with `#` are comments, case-insensitive. A question is dropped if the question text OR the answer text contains any keyword as a whole word.

- [ ] **Step 1: Failing test**

`tools/tests/test_blacklist.py`:

```python
from pathlib import Path

from trivia_pack.blacklist import Blacklist


def test_keyword_match_drops_question(tmp_path: Path) -> None:
    f = tmp_path / "bl.txt"
    f.write_text("NFL\nSuper Bowl\n# comment\n\nroyal\n", encoding="utf-8")
    bl = Blacklist.from_file(f)

    assert bl.is_blacklisted("Who won Super Bowl XII?", "Cowboys") is True
    assert bl.is_blacklisted("Capital of France?", "Paris") is False
    # case insensitive
    assert bl.is_blacklisted("the nfl is popular", "?") is True
    # word boundary — "rfl" in the middle of a word should NOT match "NFL"
    assert bl.is_blacklisted("trflactor", "?") is False


def test_match_in_answer_also_drops(tmp_path: Path) -> None:
    f = tmp_path / "bl.txt"
    f.write_text("Tudor\n", encoding="utf-8")
    bl = Blacklist.from_file(f)
    assert bl.is_blacklisted("Which dynasty?", "The Tudor dynasty") is True


def test_empty_file_drops_nothing(tmp_path: Path) -> None:
    f = tmp_path / "bl.txt"
    f.write_text("", encoding="utf-8")
    bl = Blacklist.from_file(f)
    assert bl.is_blacklisted("anything goes", "any answer") is False


def test_comment_and_empty_lines_ignored(tmp_path: Path) -> None:
    f = tmp_path / "bl.txt"
    f.write_text("# a comment\n\n   \nNBA\n", encoding="utf-8")
    bl = Blacklist.from_file(f)
    assert bl.size == 1
    assert bl.is_blacklisted("the NBA finals", "anything") is True


def test_multi_word_phrase_matches(tmp_path: Path) -> None:
    f = tmp_path / "bl.txt"
    f.write_text("Premier League\n", encoding="utf-8")
    bl = Blacklist.from_file(f)
    assert bl.is_blacklisted("Premier League winner?", "Liverpool") is True
    # individual words should not match alone
    assert bl.is_blacklisted("the premier of china", "?") is False
    assert bl.is_blacklisted("league of nations", "?") is False
```

- [ ] **Step 2: Verify it fails.**

- [ ] **Step 3: Create `data/blacklist.txt`**

```
# Trivia Zero blacklist — keywords that drop a question on either side.
# Lines starting with '#' are comments. Empty lines are ignored.
# Match is case-insensitive and whole-word.
# Multi-word entries are matched as exact phrases.

# US sports
NFL
NBA
MLB
Super Bowl
World Series

# UK / British-specific
Premier League
royal
Tudor
House of Commons

# Hollywood / very-anglo pop culture
Hollywood
Oscars
Grammys
```

- [ ] **Step 4: Implementation `tools/trivia_pack/blacklist.py`**

```python
"""Keyword blacklist for filtering culturally-anglo questions in both languages."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Blacklist:
    keywords: tuple[str, ...]
    _regex: re.Pattern[str]

    @classmethod
    def from_file(cls, path: Path) -> Blacklist:
        keywords: list[str] = []
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            keywords.append(line)

        if not keywords:
            # An impossible-to-match regex so .search always returns None.
            pattern = re.compile(r"(?!x)x")
        else:
            # Word-boundary, case-insensitive alternation.
            escaped = [re.escape(k) for k in keywords]
            pattern = re.compile(
                r"(?<!\w)(?:" + "|".join(escaped) + r")(?!\w)",
                flags=re.IGNORECASE,
            )

        return cls(keywords=tuple(keywords), _regex=pattern)

    @property
    def size(self) -> int:
        return len(self.keywords)

    def is_blacklisted(self, question: str, answer: str) -> bool:
        return bool(self._regex.search(question) or self._regex.search(answer))
```

- [ ] **Step 5: Run the test, verify pass.**

- [ ] **Step 6: Full Python suite green** — `make py-test py-lint py-typecheck`, `make py-format && git diff --exit-code`.

- [ ] **Step 7: Skipped commit.**

---

### Task 4: OpenTDB API client + on-disk cache (TDD)

**Files:**
- Create: `tools/trivia_pack/opentdb.py`
- Create: `tools/tests/test_opentdb.py`

Pulls questions from `https://opentdb.com/api.php` with retry + on-disk JSON cache so reruns are free. The API returns `response_code` + `results` array per request; up to 50 questions per call. Tests mock the HTTP layer with `respx` (already in dev requirements).

- [ ] **Step 1: Failing test**

`tools/tests/test_opentdb.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from trivia_pack.models import Lang, RawQuestion
from trivia_pack.opentdb import OpenTdbClient

API = "https://opentdb.com/api.php"


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    return tmp_path / "cache"


@respx.mock
def test_fetch_pages_until_response_code_nonzero(cache_dir: Path) -> None:
    page1 = {
        "response_code": 0,
        "results": [
            {
                "category": "Geography",
                "type": "multiple",
                "question": "Capital of Spain?",
                "correct_answer": "Madrid",
                "incorrect_answers": ["Lisbon", "Rome", "Paris"],
            }
        ],
    }
    page2 = {"response_code": 1, "results": []}
    respx.get(API, params={"amount": "50", "language": "en"}).mock(
        side_effect=[
            httpx.Response(200, json=page1),
            httpx.Response(200, json=page2),
        ]
    )

    client = OpenTdbClient(cache_dir=cache_dir)
    out: list[RawQuestion] = list(client.iter_all(Lang.EN))

    assert len(out) == 1
    assert out[0].source_lang == Lang.EN
    assert out[0].opentdb_category == "Geography"
    assert out[0].question == "Capital of Spain?"
    assert out[0].answer == "Madrid"


@respx.mock
def test_html_entities_are_decoded(cache_dir: Path) -> None:
    page = {
        "response_code": 0,
        "results": [
            {
                "category": "History",
                "type": "multiple",
                "question": "What does &quot;C&apos;est la vie&quot; mean?",
                "correct_answer": "That&#039;s life",
                "incorrect_answers": [],
            }
        ],
    }
    end = {"response_code": 1, "results": []}
    respx.get(API).mock(side_effect=[httpx.Response(200, json=page), httpx.Response(200, json=end)])

    client = OpenTdbClient(cache_dir=cache_dir)
    out = list(client.iter_all(Lang.EN))
    assert out[0].question == 'What does "C\'est la vie" mean?'
    assert out[0].answer == "That's life"


@respx.mock
def test_cached_responses_are_replayed_without_network(cache_dir: Path) -> None:
    page = {
        "response_code": 0,
        "results": [
            {
                "category": "Sports",
                "type": "multiple",
                "question": "Q?",
                "correct_answer": "A",
                "incorrect_answers": [],
            }
        ],
    }
    end = {"response_code": 1, "results": []}
    route = respx.get(API).mock(
        side_effect=[httpx.Response(200, json=page), httpx.Response(200, json=end)]
    )

    client = OpenTdbClient(cache_dir=cache_dir)
    first = list(client.iter_all(Lang.EN))
    assert len(first) == 1
    network_calls_after_first = route.call_count

    # Second pass: cache populated → no extra HTTP calls
    second = list(client.iter_all(Lang.EN))
    assert second == first
    assert route.call_count == network_calls_after_first


def test_cache_file_is_human_readable_json(cache_dir: Path) -> None:
    cache_dir.mkdir()
    sample = [
        {
            "source_lang": "EN",
            "opentdb_category": "Geography",
            "question": "Q?",
            "answer": "A",
        }
    ]
    (cache_dir / "opentdb_en.json").write_text(json.dumps(sample), encoding="utf-8")

    client = OpenTdbClient(cache_dir=cache_dir)
    cached = list(client.iter_all(Lang.EN))
    assert len(cached) == 1
    assert cached[0].question == "Q?"
```

- [ ] **Step 2: Verify it fails.**

- [ ] **Step 3: Implementation**

```python
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
from collections.abc import Iterable, Iterator
from pathlib import Path

import httpx

from trivia_pack.models import Lang, RawQuestion

_API_URL = "https://opentdb.com/api.php"
_PAGE_SIZE = 50
_REQUEST_DELAY_SECONDS = 5.0  # OpenTDB asks for 5s between requests


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
```

- [ ] **Step 4: Test passes** (`make py-test`).

- [ ] **Step 5: Lint + format + typecheck pass.**

- [ ] **Step 6: Skipped commit.**

---

### Task 5: Translator with on-disk cache (TDD; stub default + Anthropic optional)

**Files:**
- Create: `tools/trivia_pack/translate.py`
- Create: `tools/tests/test_translate.py`

The translator turns `(text, target_lang)` into the localized string. Default backend (`stub`) returns a deterministic transformation so the pipeline is fully self-contained; the `anthropic` backend issues real calls to Claude Haiku gated on `TZ_TRANSLATOR=anthropic` + `ANTHROPIC_API_KEY`. All translations are cached on disk so reruns are free.

> **Note for the implementer:** This task imports the `anthropic` SDK. When you actually edit `translate.py`, follow the `claude-api` skill conventions (model id `claude-haiku-4-5-20251001`, prompt caching where the system prompt is reused, max_tokens budget). For Plan 2 we only need a single `messages.create` call per translation, no streaming, no tools.

- [ ] **Step 1: Failing test (stub-mode + cache only — Anthropic path is exercised manually)**

`tools/tests/test_translate.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest

from trivia_pack.models import Lang
from trivia_pack.translate import StubTranslator, Translator


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
```

- [ ] **Step 2: Verify it fails.**

- [ ] **Step 3: Implementation**

```python
"""Translation backends for the data pipeline.

The Translator protocol defines the contract every backend implements. Two
concrete backends are shipped:

  StubTranslator     — deterministic, network-free, default.
  AnthropicTranslator — real Claude Haiku translations behind an env var.

Both share the same on-disk JSON cache so switching between them mid-build
preserves any work already done.
"""

from __future__ import annotations

import json
import os
from collections.abc import MutableMapping
from pathlib import Path
from typing import Protocol

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


class _CachedTranslator:
    def __init__(self, cache_path: Path) -> None:
        self._cache_path = cache_path
        self._cache: MutableMapping[str, str] = {}
        if cache_path.exists():
            self._cache = json.loads(cache_path.read_text(encoding="utf-8"))
        self.cache_hits = 0
        self.cache_misses = 0

    def translate(self, text: str, *, source: Lang, target: Lang) -> str:
        if not text:
            return ""
        if source == target:
            return text
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
        prefix = "[es]" if target == Lang.ES else "[en]"
        return f"{prefix} {text}"


class AnthropicTranslator(_CachedTranslator):
    """Real translations via Claude Haiku.

    Activated when `TZ_TRANSLATOR=anthropic`. Requires `ANTHROPIC_API_KEY`.
    """

    _MODEL = "claude-haiku-4-5-20251001"

    def __init__(self, cache_path: Path) -> None:
        super().__init__(cache_path=cache_path)
        # Lazy import so the package works without the SDK installed for stub-only use.
        import anthropic  # noqa: PLC0415

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is required for AnthropicTranslator.")
        self._client = anthropic.Anthropic(api_key=api_key)

    def _translate_uncached(self, text: str, *, source: Lang, target: Lang) -> str:
        target_name = "Spanish" if target == Lang.ES else "English"
        source_name = "Spanish" if source == Lang.ES else "English"
        msg = self._client.messages.create(
            model=self._MODEL,
            max_tokens=400,
            system=(
                "You translate trivia questions or short answers between Spanish and English. "
                "Return only the translation, with no commentary, no quotes, and no surrounding "
                "whitespace. Output must not contain tab or newline characters."
            ),
            messages=[
                {
                    "role": "user",
                    "content": f"Translate from {source_name} to {target_name}:\n{text}",
                },
            ],
        )
        # The Anthropic SDK returns content as a list of typed blocks.
        parts: list[str] = []
        for block in msg.content:
            text_attr = getattr(block, "text", None)
            if isinstance(text_attr, str):
                parts.append(text_attr)
        return "".join(parts).strip().replace("\t", " ").replace("\n", " ")


def translator_from_env(cache_path: Path) -> Translator:
    """Picks the backend based on TZ_TRANSLATOR (defaults to stub)."""
    backend = os.environ.get("TZ_TRANSLATOR", "stub").lower()
    if backend == "anthropic":
        return AnthropicTranslator(cache_path=cache_path)
    return StubTranslator(cache_path=cache_path)
```

- [ ] **Step 4: Test passes.** Lint + typecheck pass.

- [ ] **Step 5: Skipped commit.**

---

### Task 6: Pack writer (TSV + IDX, TDD against the on-device byte layout)

**Files:**
- Create: `tools/trivia_pack/pack_writer.py`
- Create: `tools/tests/test_pack_writer.py`

Emits the pair of files per language. Format must match the C `pack_reader` exactly:

- TSV line: `id\tcategory_id\tquestion\tanswer\n`, UTF-8.
- Pipeline guarantees no `\t` / `\n` in any field (sanitize before emit).
- IDX: 4 magic "TRVI" + 2 LE version + 4 LE count + count×4 LE offsets.
- ids are dense `0..count-1` ascending, so `id == index` in the IDX array.

- [ ] **Step 1: Failing test**

`tools/tests/test_pack_writer.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest

from trivia_pack.models import BilingualQuestion
from trivia_pack.pack_writer import write_pack


def _read_idx_header(blob: bytes) -> tuple[int, int]:
    assert blob[:4] == b"TRVI"
    version = int.from_bytes(blob[4:6], "little")
    count = int.from_bytes(blob[6:10], "little")
    return version, count


def _read_idx_offset(blob: bytes, i: int) -> int:
    base = 10 + i * 4
    return int.from_bytes(blob[base : base + 4], "little")


def test_writes_two_tsvs_and_two_idxs(tmp_path: Path) -> None:
    qs = [
        BilingualQuestion(
            bucket_id=1,
            question_es="¿Capital de España?",
            answer_es="Madrid",
            question_en="Capital of Spain?",
            answer_en="Madrid",
        ),
        BilingualQuestion(
            bucket_id=6,
            question_es="¿Año del primer Mundial?",
            answer_es="1930",
            question_en="First World Cup year?",
            answer_en="1930",
        ),
    ]
    write_pack(qs, out_dir=tmp_path)

    for name in ("trivia_es.tsv", "trivia_en.tsv", "trivia_es.idx", "trivia_en.idx"):
        assert (tmp_path / name).exists()


def test_tsv_has_dense_ids_and_correct_fields(tmp_path: Path) -> None:
    qs = [
        BilingualQuestion(1, "Q1es", "A1es", "Q1en", "A1en"),
        BilingualQuestion(7, "Q2es", "A2es", "Q2en", "A2en"),
        BilingualQuestion(3, "Q3es", "A3es", "Q3en", "A3en"),
    ]
    write_pack(qs, out_dir=tmp_path)

    es = (tmp_path / "trivia_es.tsv").read_text(encoding="utf-8").splitlines()
    en = (tmp_path / "trivia_en.tsv").read_text(encoding="utf-8").splitlines()
    assert len(es) == 3 and len(en) == 3

    for i, line in enumerate(es):
        parts = line.split("\t")
        assert parts[0] == str(i)
        # category preserved
        assert parts[1] == str(qs[i].bucket_id)
        assert parts[2] == qs[i].question_es
        assert parts[3] == qs[i].answer_es

    for i, line in enumerate(en):
        parts = line.split("\t")
        assert parts[0] == str(i)
        assert parts[1] == str(qs[i].bucket_id)
        assert parts[2] == qs[i].question_en
        assert parts[3] == qs[i].answer_en


def test_idx_is_consistent_with_tsv_offsets(tmp_path: Path) -> None:
    qs = [BilingualQuestion(1, "AAA", "Madrid", "AAA", "Madrid") for _ in range(5)]
    write_pack(qs, out_dir=tmp_path)

    tsv_bytes = (tmp_path / "trivia_es.tsv").read_bytes()
    idx_blob = (tmp_path / "trivia_es.idx").read_bytes()

    version, count = _read_idx_header(idx_blob)
    assert version == 1
    assert count == 5

    # Verify each offset lands at the start of a line.
    for i in range(count):
        off = _read_idx_offset(idx_blob, i)
        assert off >= 0
        # offset must be 0 or one past a newline
        if off > 0:
            assert tsv_bytes[off - 1 : off] == b"\n"
        # the 4 tab-separated fields starting at this offset must include exactly 3 tabs
        # before the next newline
        line_end = tsv_bytes.index(b"\n", off)
        line = tsv_bytes[off:line_end].decode("utf-8")
        assert line.count("\t") == 3


def test_tabs_and_newlines_in_fields_are_sanitized(tmp_path: Path) -> None:
    q = BilingualQuestion(
        bucket_id=2,
        question_es="hola\tmundo\nlinea2",
        answer_es="ok\nok",
        question_en="hello\tworld\nline2",
        answer_en="ok\nok",
    )
    write_pack([q], out_dir=tmp_path)
    es = (tmp_path / "trivia_es.tsv").read_text(encoding="utf-8")
    assert "\t" in es  # the 3 separator tabs
    # but no stray tabs inside fields → exactly 3 tabs total per line
    assert es.strip("\n").count("\t") == 3
    # no embedded newlines (the file ends with one terminating newline)
    assert es.count("\n") == 1


def test_invalid_bucket_id_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        write_pack(
            [BilingualQuestion(99, "q", "a", "q", "a")],
            out_dir=tmp_path,
        )
    with pytest.raises(ValueError):
        write_pack(
            [BilingualQuestion(0, "q", "a", "q", "a")],
            out_dir=tmp_path,
        )
```

- [ ] **Step 2: Verify it fails.**

- [ ] **Step 3: Implementation**

```python
"""Writes the (TSV, IDX) pair per language. Format mirrors the C pack_reader."""

from __future__ import annotations

import struct
from collections.abc import Sequence
from pathlib import Path

from trivia_pack.models import BilingualQuestion

_MAGIC = b"TRVI"
_VERSION = 1
_HEADER_SIZE = 10  # 4 magic + 2 version + 4 count


def _sanitize(field: str) -> str:
    """Replace tabs and newlines with single spaces — the runtime parser cannot
    handle them in fields, so the pipeline must scrub them defensively."""
    return field.replace("\t", " ").replace("\n", " ").replace("\r", " ")


def write_pack(questions: Sequence[BilingualQuestion], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for q in questions:
        if not (1 <= q.bucket_id <= 7):
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
```

- [ ] **Step 4: Tests pass.** Lint + typecheck green.

- [ ] **Step 5: Skipped commit.**

---

### Task 7: Pipeline orchestrator + CLI entry point

**Files:**
- Create: `tools/trivia_pack/pipeline.py`
- Create: `tools/tests/test_pipeline.py`
- Create: `tools/build_pack.py`

The orchestrator wires every previous module together: fetch raw → blacklist filter → category map → group by `(bucket_id, normalized_text)` so duplicates collapse → fill missing translations → emit. The integration test mocks the OpenTDB client and the translator (stub) and verifies the final files exist with reasonable content.

- [ ] **Step 1: Failing test**

`tools/tests/test_pipeline.py`:

```python
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
    blacklist_path.write_text("NFL\n", encoding="utf-8")

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
```

- [ ] **Step 2: Verify it fails.**

- [ ] **Step 3: Implementation `tools/trivia_pack/pipeline.py`**

```python
"""Composition root for the off-Flipper data pipeline."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from trivia_pack.blacklist import Blacklist
from trivia_pack.category_map import map_opentdb_to_bucket
from trivia_pack.models import BilingualQuestion, Lang, MappedQuestion, RawQuestion
from trivia_pack.pack_writer import write_pack
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
            # Unknown category — surface to user but don't crash the build.
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
) -> None:
    blacklist = Blacklist.from_file(blacklist_path)
    raw_en = list(opentdb.iter_all(Lang.EN))
    raw_es = list(opentdb.iter_all(Lang.ES))
    mapped = _filter_and_map([*raw_en, *raw_es], blacklist)
    bilingual = _build_bilingual(mapped, translator)
    # Sort deterministically by (bucket, EN question text) so reruns produce
    # the same dense ids — important for last_id stability across pack rebuilds.
    bilingual.sort(key=lambda q: (q.bucket_id, q.question_en))
    write_pack(bilingual, out_dir=out_dir)
    translator.flush()
```

- [ ] **Step 4: Implementation `tools/build_pack.py`**

```python
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
```

- [ ] **Step 5: Tests pass.** Lint + typecheck green.

- [ ] **Step 6: Skipped commit.**

---

### Task 8: End-to-end verification — generated pack consumed by the C parser

**Files:**
- Create: `tools/tests/test_e2e_with_c_parser.py`

The Python side has produced a TSV+IDX pair. The C side already has `test_pack_integration` (Task 11 of Plan 3) that exercises pure parsers against an in-memory fixture. This task closes the loop: build a pack with Python from canned input, then write a Python test that runs the actual C `test_pack_reader` binary against that pack on disk via `subprocess`, confirming the generated bytes are consumable.

This task does **not** modify any C code. It only adds a Python test that drives the existing C binary through `subprocess.run`. It catches any drift between writer and parser early.

- [ ] **Step 1: Create the e2e test**

`tools/tests/test_e2e_with_c_parser.py`:

```python
from __future__ import annotations

import struct
import subprocess
from pathlib import Path

import pytest

from trivia_pack.models import BilingualQuestion
from trivia_pack.pack_writer import write_pack

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _ensure_c_binary_built() -> Path:
    """Builds test_pack_reader if it isn't already, returns its path."""
    binary = _REPO_ROOT / "test_pack_reader"
    if not binary.exists():
        result = subprocess.run(
            ["make", "test_pack_reader"],
            cwd=_REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.skip(f"could not build C side: {result.stderr}")
    return binary


def test_python_writer_output_is_consumable_by_c_parser(tmp_path: Path) -> None:
    """Round-trip: write a small pack with Python, parse the TSV+IDX with the
    same byte-level routines used on device.

    The C `test_pack_reader` binary tests pure parsers with hand-crafted bytes;
    here we don't re-run it (it doesn't touch the filesystem). Instead we verify
    bit-level compatibility by:
      1) Writing a pack with Python.
      2) Reading the IDX header back with Python and confirming magic/version/count.
      3) Reading each TSV line at the offset given by the IDX and confirming it
         parses with exactly 3 tabs.

    This catches any layout drift between the Python writer and the C reader's
    expectations without needing on-device execution.
    """
    qs = [
        BilingualQuestion(1, "¿Capital de España?", "Madrid", "Capital of Spain?", "Madrid"),
        BilingualQuestion(6, "¿Año del primer Mundial?", "1930", "First World Cup year?", "1930"),
        BilingualQuestion(7, "¿Qué es el H2O?", "Agua", "What is H2O?", "Water"),
    ]
    write_pack(qs, out_dir=tmp_path)

    for lang in ("es", "en"):
        tsv = (tmp_path / f"trivia_{lang}.tsv").read_bytes()
        idx = (tmp_path / f"trivia_{lang}.idx").read_bytes()

        # Header
        assert idx[:4] == b"TRVI"
        version = struct.unpack_from("<H", idx, 4)[0]
        count = struct.unpack_from("<I", idx, 6)[0]
        assert version == 1
        assert count == len(qs)

        # Each offset lands at the start of a parseable line
        for i in range(count):
            off = struct.unpack_from("<I", idx, 10 + i * 4)[0]
            line_end = tsv.index(b"\n", off)
            line = tsv[off:line_end].decode("utf-8")
            parts = line.split("\t")
            assert len(parts) == 4
            assert parts[0] == str(i)
            assert int(parts[1]) == qs[i].bucket_id


def test_c_test_pack_reader_still_passes() -> None:
    """The existing C `test_pack_reader` should still pass — sanity check that
    Plan 2 has not broken Plan 3."""
    binary = _ensure_c_binary_built()
    result = subprocess.run([str(binary)], cwd=_REPO_ROOT, check=False)
    assert result.returncode == 0
```

- [ ] **Step 2: Verify the test passes** with `make py-test`.

- [ ] **Step 3: Run a real `make pack`** (with the stub translator) and confirm:

```bash
make pack
ls -la data/trivia_es.tsv data/trivia_es.idx data/trivia_en.tsv data/trivia_en.idx
```

The four files exist and are non-empty. The first run hits OpenTDB (slow because of the 5 s rate limit between pages); subsequent runs read from `data/_cache/opentdb/*.json` and finish in seconds.

If you want to skip the live OpenTDB call during plan execution, prepopulate `data/_cache/opentdb/opentdb_en.json` and `opentdb_es.json` with a small canned set of questions and re-run.

- [ ] **Step 4: Skipped commit.**

---

## Out of scope for this plan

Explicitly **not** done in Plan 2:

- Hardware verification of the real pack on a Flipper. That's Task 12 of Plan 3 (manual).
- Per-category quotas / balanced sampling.
- Curating a high-quality ES corpus by hand. The pipeline pulls whatever OpenTDB returns; quality improvements happen by iterating on `data/blacklist.txt` and (optionally) the LLM prompt.
- Streaming / async fetching. Synchronous `httpx.Client` is fine — OpenTDB rate-limits us harder than our network does.
- Internationalization of the pipeline's own logs (English-only — they're for the developer).
