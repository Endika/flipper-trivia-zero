# Trivia Zero — Design Spec

**Date:** 2026-04-28
**Author:** Endika
**Status:** Draft, pending user review

> Note: written in English to match the project rule from `workspace/CLAUDE.md` ("English only for code, comments, and documentation"). The working brainstorm (`BRAINSTORM.md`) remains in Spanish and is the source from which this spec was distilled.

---

## 1. Overview

Trivia Zero is a Flipper Zero application (FAP) that displays trivia questions in a flashcard style: one question on screen, press OK to reveal the answer, press right to advance to the next random question. No scoring, no timers, no multi-choice, no game loop. The product value is variety of content in two languages.

It is the second member of the user's "Zero" FAP family (sister to `flipper-avocado-zero`) and follows the architectural conventions of the rest of the user's FAPs (`flipper-impostor-game`, `flipper-habit-flow`, `flipper-sub-dup`, etc.).

## 2. Identity

| Field | Value |
|-------|-------|
| `name` | `Trivia Zero` |
| `appid` | `flipper_trivia_zero` |
| `entry_point` | `trivia_zero_app` |
| `fap_category` | `Games` |
| Repo dir | `flipper-trivia-zero` |
| SD data path | `/ext/apps_data/flipper_trivia_zero/` |

## 3. User experience

### 3.1 Languages

- Spanish and English, both shipped by default.
- A session uses a single language; languages do not mix within a session.
- The selected language is persisted on SD. On launch, the app reads `lang` from settings and goes straight to the question screen — the language selector only appears on the very first run (or when the settings file is missing or corrupt).
- Language switch during use: `BACK → menu → "Cambiar idioma" / "Change language"`.

### 3.2 Categories

Each question shows its category on screen, but categories do **not** filter the pool. The user always sees a random question drawn from the full pool.

- Display: inverted-video header bar (~10 px) at the top of the question screen with the category name in the active language.
- Taxonomy: the 6 classic Trivial Pursuit categories plus a 7th "Cultura General" / "General Knowledge" bucket for OpenTDB's `General Knowledge` items (which do not map cleanly to any of the 6).

| `category_id` | ES | EN |
|----|----|----|
| 1 | Geografía | Geography |
| 2 | Entretenimiento | Entertainment |
| 3 | Historia | History |
| 4 | Arte y Literatura | Arts & Literature |
| 5 | Ciencia y Naturaleza | Science & Nature |
| 6 | Deportes y Ocio | Sports & Leisure |
| 7 | Cultura General | General Knowledge |

### 3.3 Layout and controls

128×64 monochrome screen, three regions stacked vertically:

1. **Header (inverted, ~10 px):** category name in the active language.
2. **Body (scrollable):** question text. When more text exists below the visible area, a `▼` indicator is drawn in the bottom-right of the body. After OK, the body is replaced (or appended below) by the answer.
3. **Footer (1 line):** action hint — `OK: revelar` / `OK: reveal` before reveal, `→: siguiente` / `→: next` after.

Buttons:

| Button | Action |
|--------|--------|
| OK (center) | Reveal answer |
| → (right) | Next question — random from the unseen pool |
| ← (left) | Previous question — from a ring buffer of the last 5 |
| ↑ / ↓ | Vertical scroll on long question or answer |
| BACK | Open menu: `{Cambiar idioma / Change language, Salir / Exit}` |

### 3.4 Anti-repetition

- In-memory only: a `Set<id>` of question ids already shown in the current session.
- When the pool is exhausted, the set resets and any question can appear again.
- **Not** persisted across sessions. Relaunching the app may, by chance, repeat a recently-seen question. This was an explicit decision favoring simplicity over cross-session uniqueness.

### 3.5 Resume

- On launch, the app reads `last_id` from settings and shows that question, so the user picks up where they left off.
- The resumed question is added to the in-session `seen_set` (§3.4) immediately, so `→` advances cleanly.
- Fallback: if `last_id` is missing, malformed, or out of range for the current pack (e.g., pack was rebuilt with different `count`), the app silently picks a fresh random id and proceeds — no error screen.
- After the first `→` press, normal random selection takes over.

## 4. Data pipeline (off-Flipper)

A Python pipeline, executed once before each release of the FAP, builds the question packs that ship with the installer. It lives under `tools/` in the repo. The output (`data/`) is committed to the repo.

### 4.1 Steps

1. **Fetch** OpenTDB ES and EN corpora via the public API.
2. **Apply blacklist** to both languages: keywords flagging culturally-anglo content (`NFL`, `NBA`, `MLB`, `Premier League`, `royal`, `Tudor`, `Super Bowl`, `Hollywood`, …) drop the question on **both** sides to keep the pool symmetric.
3. **Map** OpenTDB's 24 native categories to the 7-bucket taxonomy (see §3.2 and the mapping table in §4.4).
4. **Translate** entries that lack a counterpart in the other language using an LLM (Haiku is the recommended default; concrete model + prompt finalized during plan). The prompt enforces UTF-8 output without tabs or newlines.
5. **Sanitize** all fields: strip any residual tabs and newlines as a safety net.
6. **Emit** four files: `trivia_es.tsv`, `trivia_es.idx`, `trivia_en.tsv`, `trivia_en.idx`.

### 4.2 Symmetry

After step 5, the pack contains the same set of question concepts in both languages: for every question that survives the pipeline, both `trivia_es.tsv` and `trivia_en.tsv` carry an entry sharing the same `id` and `category_id`, differing only in the language of `question` and `answer`.

### 4.3 Estimated volume

~1500–2000 entries per language after filtering.

### 4.4 Category mapping (OpenTDB → 7 buckets)

Draft mapping. Rows marked ⚠️ are debatable and the user should validate during spec review:

| OpenTDB category | Bucket |
|---------|--------|
| General Knowledge | 7 — Cultura General |
| Entertainment: Books | 4 — Arte y Literatura |
| Entertainment: Film | 2 — Entretenimiento |
| Entertainment: Music | 2 — Entretenimiento |
| Entertainment: Musicals & Theatres | 2 — Entretenimiento ⚠️ (alt: Arte y Literatura) |
| Entertainment: Television | 2 — Entretenimiento |
| Entertainment: Video Games | 2 — Entretenimiento |
| Entertainment: Board Games | 2 — Entretenimiento |
| Entertainment: Comics | 2 — Entretenimiento ⚠️ (alt: Arte y Literatura) |
| Entertainment: Japanese Anime & Manga | 2 — Entretenimiento |
| Entertainment: Cartoon & Animations | 2 — Entretenimiento |
| Celebrities | 2 — Entretenimiento |
| Science & Nature | 5 — Ciencia y Naturaleza |
| Science: Computers | 5 — Ciencia y Naturaleza |
| Science: Mathematics | 5 — Ciencia y Naturaleza |
| Science: Gadgets | 5 — Ciencia y Naturaleza |
| Animals | 5 — Ciencia y Naturaleza |
| Vehicles | 5 — Ciencia y Naturaleza ⚠️ (alt: Deportes y Ocio) |
| Geography | 1 — Geografía |
| History | 3 — Historia |
| Politics | 3 — Historia |
| Mythology | 4 — Arte y Literatura ⚠️ (alt: Historia) |
| Art | 4 — Arte y Literatura |
| Sports | 6 — Deportes y Ocio |

## 5. On-device file formats

### 5.1 Question pack — TSV

Each `trivia_<lang>.tsv` line:

```
id<TAB>category_id<TAB>question<TAB>answer<LF>
```

- All fields UTF-8.
- Pipeline guarantees no tab or newline characters inside any field.
- `id` is a stable monotonic integer, identical across `trivia_es.tsv` and `trivia_en.tsv` for the same question concept.
- `category_id` is `1`–`7` per §3.2.
- The pipeline reassigns `id` so that the final pack contains ids `0`..`count-1` contiguously, sorted ascending. **Consequence:** `id == position in the .idx array`, which keeps the `.idx` tiny and lookup O(1) with no extra mapping.

No header row. No CRLF.

### 5.2 Question pack — sidecar index

Each `trivia_<lang>.idx` is a small binary sidecar that enables random access by entry index:

```
[ magic       (4 bytes)     ]  ASCII "TRVI"
[ version     (uint16 LE)   ]  currently 1
[ count       (uint32 LE)   ]  number of entries
[ offsets[count] (uint32 LE × count) ]  byte offset of each entry's line in the .tsv
```

Lookup of entry with `id == i`: read `offsets[i]`, `lseek` to that offset in the TSV, read until `\n`, split on `\t`. (Recall §5.1: ids are dense `0`..`count-1`, so `id` == index in this array.)

The `.idx` is rebuilt deterministically from the `.tsv` by `tools/build_idx.py`.

Rationale: ~500 KB of pack does not fit in the Flipper's 256 KB SRAM; on-demand seek+read with an index is the only viable path.

### 5.3 Settings file

Path: `/ext/apps_data/flipper_trivia_zero/settings`

Format: line-based key=value, UTF-8.

```
# trivia v1
lang=es
last_id=1234
```

Parser rules:

- First line is a versioned comment (`# trivia vN`).
- Lines starting with `#` are skipped.
- Unknown keys are skipped (forward compatibility).
- Malformed lines are skipped (resilience to partial corruption).
- Future keys can be added without breaking older builds.

Confirmed keys:

| Key | Type | Meaning |
|-----|------|---------|
| `lang` | `es` \| `en` | Active language |
| `last_id` | uint32 | Id of the last question shown (for resume) |

## 6. Application architecture

### 6.1 Pattern

`ViewDispatcher` + `Views` (no `SceneManager`), matching `flipper-impostor-game` and `flipper-habit-flow`.

### 6.2 Screens

Three views:

| Enum | Type | Purpose |
|------|------|---------|
| `AppViewLangSelect` | builtin `submenu` | First-run language picker |
| `AppViewQuestion` | custom `question_view` | Header + scrollable body + footer |
| `AppViewMenu` | builtin `submenu` | BACK menu: `Cambiar idioma`, `Salir` |

### 6.3 Source layout

```
flipper-trivia-zero/
├── application.fam
├── main.c
├── version.h                       # autogenerated; # x-release-please-version
├── icons/
│   └── icon.icon
├── include/                        # mirrors src/, public headers per module
│   ├── app/
│   ├── domain/
│   ├── infrastructure/
│   ├── platform/
│   ├── i18n/
│   └── ui/
├── src/
│   ├── app/
│   │   └── trivia_zero_app.c       # composition root + ViewDispatcher wiring
│   ├── domain/
│   │   ├── question_pool.c         # picks a random unseen id
│   │   ├── history_buffer.c        # ring buffer of last 5 ids for ←
│   │   ├── anti_repeat.c           # bitset/Set<id> of seen ids in session
│   │   └── category.c              # category id → localized name
│   ├── infrastructure/
│   │   ├── pack_reader.c           # opens .tsv + .idx, reads entry by index
│   │   └── settings_storage.c      # parse/write key=value settings
│   ├── platform/
│   │   └── random_port.c           # thin wrapper over furi rng
│   ├── i18n/
│   │   └── strings.c               # localized labels (buttons, menus, categories)
│   └── ui/
│       └── question_view.c         # custom View
├── tests/                          # host-runnable, stubbing furi where needed
│   ├── test_question_pool.c
│   ├── test_history_buffer.c
│   ├── test_anti_repeat.c
│   ├── test_category.c
│   ├── test_pack_reader.c          # uses fixture .tsv + .idx
│   └── test_settings_storage.c
├── data/                           # generated pack, committed to repo
│   ├── trivia_es.tsv
│   ├── trivia_es.idx
│   ├── trivia_en.tsv
│   ├── trivia_en.idx
│   └── blacklist.txt
├── tools/                          # off-Flipper Python pipeline
│   ├── build_pack.py
│   ├── build_idx.py
│   └── translate.py
├── Makefile
├── README.md
├── CHANGELOG.md
├── LICENSE
└── release-please-config.json
```

### 6.4 Module boundaries

- `domain/` is pure: no `furi.h`, no I/O, no globals. Trivially unit-testable on host.
- `infrastructure/` opens files, reads bytes, parses. Testable on host with fixture files.
- `platform/` is the only place that touches Flipper hardware APIs (RNG, RTC, etc.) directly.
- `ui/` knows how to draw and interpret input but never reads files or talks to RNG directly — it consumes data prepared by `app/`.
- `app/` is the composition root: builds wires, owns the `ViewDispatcher`, holds the current `Question` cache, calls into `domain/` and `infrastructure/`.

### 6.5 Runtime data flow

1. `trivia_zero_app` allocates the app context, creates the `ViewDispatcher` and Views.
2. `settings_storage_load()` returns `{lang, last_id}` (or `{none, 0}` on first run).
3. If `lang` is missing/invalid, switch to `AppViewLangSelect`. After the user picks, `settings_storage_save()` and continue.
4. `pack_reader_open(lang)` mmap-or-seek-opens the appropriate `.tsv` and `.idx`.
5. If `last_id` is valid, `pack_reader_get_by_id(last_id, &question)` and display it. Otherwise pick a fresh random index via `question_pool_next(seen_set)`.
6. `question_view`'s input callback emits semantic events back to `app/`: `Reveal`, `Next`, `Prev`, `ScrollUp`, `ScrollDown`, `OpenMenu`. `app/` updates state and tells the view to redraw.
7. On exit (BACK from menu → Salir), persist `last_id` via `settings_storage_save()`.

## 7. Testing strategy

Following the user's project standards (≥80 % coverage, no mocking of business logic):

- **Unit tests** (host, no Flipper hardware): all of `domain/*`, plus the pure-parsing parts of `infrastructure/*`. Includes pack parsing with fixture TSV+IDX files.
- **Integration tests** (host): end-to-end question retrieval driven by a real fixture pack.
- **Manual tests on hardware** before release: scroll, language switch, BACK menu navigation, resume on relaunch, behavior when SD is missing/corrupt.

What is **not** mocked: domain logic, category mapping, anti-repetition state, history buffer, parsing.
What may be stubbed: `furi.h` symbols when running tests on host (already a pattern in the user's other FAPs).

## 8. Repository conventions

The conventions below match the **actual** patterns used by `flipper-avocado-zero` and `flipper-impostor-game` (verified by reading both repos). Anything that is not in either sibling is explicitly out of scope for now to preserve family consistency.

These are part of the MVP, not deferred:

- **Versioning & changelog:** `release-please` (`release-type: simple`) drives semver and `CHANGELOG.md`. `application.fam` carries `fap_version="X.Y.Z"  # x-release-please-version` and `version.h` (at the repo root, mirroring `flipper-avocado-zero`) carries `#define APP_VERSION "X.Y.Z" // x-release-please-version`. `release-please-config.json` lists both as `extra-files`.
- **Dependencies:** `.github/dependabot.yml` watching `github-actions` weekly. (Python deps are introduced in Plan 2 when `tools/` is added; `dependabot` will be extended then.)
- **Linting:** `cppcheck --enable=all --inline-suppr` driven from `make linter` over the project's source files. (No `clang-tidy`; siblings do not use it.)
- **Formatting:** `clang-format` driven from `make format`, configured via `.clang-format` (LLVM base, IndentWidth 4, ColumnLimit 100, IndentCaseLabels). CI checks formatting with `clang-format --dry-run --Werror`.
- **CI** (GitHub Actions, `actions/checkout@v6`):
  - `ci.yml`: install `build-essential cppcheck clang-format`, run `make linter`, format check, `make test`. Triggers: push, pull_request, workflow_call.
  - `release.yml`: triggered on push to `main`. Runs CI as a reusable workflow, then `googleapis/release-please-action@v4`. On `release_created == true`, builds the `.fap` with `flipperdevices/flipperzero-ufbt-action@v0.1` (channel `dev`) and uploads `dist/*.fap` to the GitHub Release via `gh release upload`.
- **Makefile** exposing `make test` (host unit tests), `make format` (clang-format -i), `make linter` (cppcheck), `make prepare` (symlink into firmware checkout), `make fap` (build .fap via local `./fbt`), `make clean`, `make clean_firmware`, `make help`.
- **LICENSE:** the same 13-line GPLv3 stub used by the sibling FAPs.
- **PR template:** `.github/PULL_REQUEST_TEMPLATE.md` matching the sibling pattern (Description / Type of change / How tested / Checklist).

Out of scope for the family right now (do not add to Trivia Zero unilaterally):

- `.editorconfig`, `.pre-commit-config.yaml`, `clang-tidy`, `pyproject.toml`. None of the sibling FAPs use these. If we want to upgrade the family later, that should be a separate, explicit decision rolled out across all the FAPs at once for consistency.

## 9. Out of scope (explicit non-goals)

- Multi-choice, scoring, timers, multiplayer.
- Cross-session anti-repetition.
- Filtering or browsing by category.
- Live online updates of the pack.
- More than two languages.

## 10. Open items to confirm before plan

- Validate the ⚠️ rows in the category mapping table (§4.4).
- Confirm LLM model + prompt for translation (current default: Haiku).
- Confirm policy for committing `data/*.tsv`/`*.idx` to git vs. attaching as release artifacts (current default: commit).
- Confirm sort order of the `.idx` (current default: ascending by `id`).
