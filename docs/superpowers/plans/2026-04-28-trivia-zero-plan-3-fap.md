# Trivia Zero — Plan 3: The FAP

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Trivia Zero FAP itself, layer by layer following Clean Architecture: domain (pure logic) → i18n → infrastructure (SD card I/O) → platform (Flipper RNG) → UI (custom View) → app composition root. End state: an installable `.fap` that reads a TSV+idx pack from `/ext/apps_data/flipper_trivia_zero/`, displays random questions with an inverted-header category label and scrollable body, persists language and last-question-id, and supports the full button map from the spec.

**Architecture:** Same as the spec §6 — `ViewDispatcher` + `Views` (no `SceneManager`), three views (`AppViewLangSelect` builtin submenu, `AppViewQuestion` custom, `AppViewMenu` builtin submenu), pure domain modules with no Furi dependency, infrastructure modules split into a pure parser (host-testable) + a Furi I/O wrapper (hardware-only).

**Tech Stack:** C11, Flipper Furi APIs (`furi.h`, `gui/`, `storage/`, `furi_hal_random`), gcc + cppcheck + clang-format on host.

**Reference projects (read-only siblings to mirror when in doubt):**
- `/home/endikaiglesias/workspace/flipper/flipper-impostor-game/` — closest in shape (multi-view, i18n, settings, random selection from a pool).
- `/home/endikaiglesias/workspace/flipper/flipper-habit-flow/` — for date/time persistence patterns if needed.
- `/home/endikaiglesias/workspace/flipper/flipper-avocado-zero/` — for the "Zero" family conventions.

**Prerequisites:**
- Plan 1 (scaffolding) is complete: `Makefile`, `application.fam`, `version.h`, `tests/test_version.c`, `src/app/trivia_zero_app.c` (stub) exist.
- The repo root is `/home/endikaiglesias/workspace/flipper-trivia-zero/`. All paths in this plan are relative to that root.
- `gcc`, `cppcheck`, `clang-format` are installed on the host.
- A real question pack (Plan 2 output) is **not** required to develop or test this FAP. Tests use fixture data created inline; manual hardware testing uses either a Plan 2 pack or a small hand-written fixture pack (see Task 11).
- The user runs `git init` / commits manually. **No subagent should run `git add`, `git commit`, or any git mutation.** The "Commit" step in each task is overridden — skip it silently.

---

## Conventions used throughout this plan

- Each module adds: `include/<layer>/<module>.h`, `src/<layer>/<module>.c`, and (when host-testable) `tests/test_<module>.c`.
- Each module task ends with three Makefile/manifest updates:
  1. Append the new test (if any) to the `test:` aggregator and add per-test `.o` rules.
  2. Append the new `.c` file(s) to the `linter` target's cppcheck source list.
  3. Append the new `src/<layer>/<module>.c` to the `sources=[…]` list in `application.fam`.
- Do **not** commit. Leave changes in the working tree at the end of each task.
- Module name prefixes: every public symbol starts with `tz_` (Trivia Zero) or with the layer name (e.g. `category_`, `pack_`, `settings_`, `question_view_`). Pick the layer prefix when the module is layer-scoped; otherwise `tz_`.
- All public types and functions use `int32_t`/`uint32_t`/`uint16_t`/`uint8_t` from `<stdint.h>`; never raw `int`/`long` for sized data.

---

### Task 1: `domain/category` — id → localized name lookup (TDD)

**Files:**
- Create: `include/domain/category.h`
- Create: `src/domain/category.c`
- Create: `tests/test_category.c`
- Modify: `Makefile`
- Modify: `application.fam`

Pure data lookup. Inputs: `category_id` (1–7) and `Lang` (es|en). Output: `const char *` localized name. No globals, no Furi.

- [ ] **Step 1: Write the failing test**

Create `tests/test_category.c`:

```c
#include "include/domain/category.h"
#include <assert.h>
#include <string.h>

int main(void) {
    /* Spanish names */
    assert(strcmp(category_name(1, LangEs), "Geografía") == 0);
    assert(strcmp(category_name(2, LangEs), "Entretenimiento") == 0);
    assert(strcmp(category_name(3, LangEs), "Historia") == 0);
    assert(strcmp(category_name(4, LangEs), "Arte y Literatura") == 0);
    assert(strcmp(category_name(5, LangEs), "Ciencia y Naturaleza") == 0);
    assert(strcmp(category_name(6, LangEs), "Deportes y Ocio") == 0);
    assert(strcmp(category_name(7, LangEs), "Cultura General") == 0);

    /* English names */
    assert(strcmp(category_name(1, LangEn), "Geography") == 0);
    assert(strcmp(category_name(2, LangEn), "Entertainment") == 0);
    assert(strcmp(category_name(3, LangEn), "History") == 0);
    assert(strcmp(category_name(4, LangEn), "Arts & Literature") == 0);
    assert(strcmp(category_name(5, LangEn), "Science & Nature") == 0);
    assert(strcmp(category_name(6, LangEn), "Sports & Leisure") == 0);
    assert(strcmp(category_name(7, LangEn), "General Knowledge") == 0);

    /* Out-of-range falls back to a sentinel */
    assert(strcmp(category_name(0, LangEs), "?") == 0);
    assert(strcmp(category_name(8, LangEn), "?") == 0);
    assert(strcmp(category_name(255, LangEs), "?") == 0);

    return 0;
}
```

- [ ] **Step 2: Verify it fails**

Run: `gcc -Wall -Wextra -std=c11 -I. tests/test_category.c -o test_category 2>&1 | head`
Expected: compile error (`category.h: No such file or directory`).

- [ ] **Step 3: Create the header**

Create `include/domain/category.h`:

```c
#pragma once

#include <stdint.h>

typedef enum {
    LangEs = 0,
    LangEn = 1,
} Lang;

/* Returns the localized name for category_id (1-7) in the given language.
 * Out-of-range ids return the sentinel string "?". The returned pointer
 * is a static, NUL-terminated string and must not be freed. */
const char *category_name(uint8_t category_id, Lang lang);
```

- [ ] **Step 4: Create the implementation**

Create `src/domain/category.c`:

```c
#include "include/domain/category.h"

static const char *const k_es[8] = {
    "?",
    "Geografía",
    "Entretenimiento",
    "Historia",
    "Arte y Literatura",
    "Ciencia y Naturaleza",
    "Deportes y Ocio",
    "Cultura General",
};

static const char *const k_en[8] = {
    "?",
    "Geography",
    "Entertainment",
    "History",
    "Arts & Literature",
    "Science & Nature",
    "Sports & Leisure",
    "General Knowledge",
};

const char *category_name(uint8_t category_id, Lang lang) {
    if (category_id < 1u || category_id > 7u) {
        return "?";
    }
    return (lang == LangEs) ? k_es[category_id] : k_en[category_id];
}
```

- [ ] **Step 5: Update the Makefile**

Edit `Makefile`:

1. Update the `test:` line:
   ```
   test: test_version test_category
   ```
2. After the existing `test_version` rules, append:
   ```
   test_category: category.o tests/test_category.o
   	$(CC) $(CFLAGS) -o test_category category.o tests/test_category.o
   	./test_category

   category.o: src/domain/category.c include/domain/category.h
   	$(CC) $(CFLAGS) -c src/domain/category.c -o category.o

   tests/test_category.o: tests/test_category.c include/domain/category.h
   	$(CC) $(CFLAGS) -c tests/test_category.c -o tests/test_category.o
   ```
3. Update the `clean` recipe:
   ```
   clean:
   	rm -f *.o tests/*.o test_version test_category
   ```
4. Update the `.PHONY` line:
   ```
   .PHONY: all help test test_version test_category prepare fap clean clean_firmware format linter
   ```
5. Append `src/domain/category.c` to the cppcheck source list inside the `linter:` recipe (one space-separated continuation line — match the existing style).

All recipe lines use TAB indentation.

- [ ] **Step 6: Verify `make test` passes**

Run: `make clean && make test`
Expected: both `test_version` and `test_category` compile and run, exit 0.

- [ ] **Step 7: Verify `make linter` passes**

Run: `make linter`
Expected: cppcheck completes without errors over the new file too.

- [ ] **Step 8: Update `application.fam`**

Append `"src/domain/category.c"` to the `sources` list in `application.fam`:

```python
    sources=[
        "main.c",
        "src/app/trivia_zero_app.c",
        "src/domain/category.c",
    ],
```

- [ ] **Step 9: Verify `make format` is a no-op**

Run: `make format && git diff --exit-code`
Expected: exit 0.

- [ ] **Step 10: Skipped commit.**

---

### Task 2: `domain/anti_repeat` — bitset of seen ids (TDD)

**Files:**
- Create: `include/domain/anti_repeat.h`
- Create: `src/domain/anti_repeat.c`
- Create: `tests/test_anti_repeat.c`
- Modify: `Makefile`, `application.fam`

A fixed-size bitset (capacity = `ANTI_REPEAT_MAX = 4096`) tracking which question ids have been seen in the current session. Operations: `mark`, `is_marked`, `reset`, `count`. No globals.

- [ ] **Step 1: Write the failing test**

Create `tests/test_anti_repeat.c`:

```c
#include "include/domain/anti_repeat.h"
#include <assert.h>

int main(void) {
    AntiRepeat ar;
    anti_repeat_init(&ar);

    assert(anti_repeat_count(&ar) == 0u);
    assert(anti_repeat_is_marked(&ar, 0u) == false);
    assert(anti_repeat_is_marked(&ar, 100u) == false);
    assert(anti_repeat_is_marked(&ar, ANTI_REPEAT_MAX - 1u) == false);

    anti_repeat_mark(&ar, 0u);
    anti_repeat_mark(&ar, 100u);
    anti_repeat_mark(&ar, 100u); /* idempotent */
    anti_repeat_mark(&ar, ANTI_REPEAT_MAX - 1u);

    assert(anti_repeat_is_marked(&ar, 0u) == true);
    assert(anti_repeat_is_marked(&ar, 100u) == true);
    assert(anti_repeat_is_marked(&ar, 99u) == false);
    assert(anti_repeat_is_marked(&ar, ANTI_REPEAT_MAX - 1u) == true);
    assert(anti_repeat_count(&ar) == 3u);

    /* Out-of-range mark is a no-op; out-of-range query returns false. */
    anti_repeat_mark(&ar, ANTI_REPEAT_MAX);
    anti_repeat_mark(&ar, ANTI_REPEAT_MAX + 50u);
    assert(anti_repeat_is_marked(&ar, ANTI_REPEAT_MAX) == false);
    assert(anti_repeat_count(&ar) == 3u);

    anti_repeat_reset(&ar);
    assert(anti_repeat_count(&ar) == 0u);
    assert(anti_repeat_is_marked(&ar, 0u) == false);
    assert(anti_repeat_is_marked(&ar, 100u) == false);

    return 0;
}
```

- [ ] **Step 2: Verify it fails**

Run: `gcc -Wall -Wextra -std=c11 -I. tests/test_anti_repeat.c -o test_anti_repeat 2>&1 | head`
Expected: compile error.

- [ ] **Step 3: Create the header**

Create `include/domain/anti_repeat.h`:

```c
#pragma once

#include <stdbool.h>
#include <stdint.h>

#define ANTI_REPEAT_MAX 4096u
#define ANTI_REPEAT_WORDS (ANTI_REPEAT_MAX / 32u)

typedef struct {
    uint32_t bits[ANTI_REPEAT_WORDS];
    uint32_t count;
} AntiRepeat;

void anti_repeat_init(AntiRepeat *ar);
void anti_repeat_reset(AntiRepeat *ar);
void anti_repeat_mark(AntiRepeat *ar, uint32_t id);
bool anti_repeat_is_marked(const AntiRepeat *ar, uint32_t id);
uint32_t anti_repeat_count(const AntiRepeat *ar);
```

- [ ] **Step 4: Create the implementation**

Create `src/domain/anti_repeat.c`:

```c
#include "include/domain/anti_repeat.h"
#include <string.h>

void anti_repeat_init(AntiRepeat *ar) {
    if (!ar) {
        return;
    }
    memset(ar, 0, sizeof(*ar));
}

void anti_repeat_reset(AntiRepeat *ar) {
    anti_repeat_init(ar);
}

void anti_repeat_mark(AntiRepeat *ar, uint32_t id) {
    if (!ar || id >= ANTI_REPEAT_MAX) {
        return;
    }
    const uint32_t word = id >> 5u;
    const uint32_t mask = 1u << (id & 31u);
    if ((ar->bits[word] & mask) == 0u) {
        ar->bits[word] |= mask;
        ar->count++;
    }
}

bool anti_repeat_is_marked(const AntiRepeat *ar, uint32_t id) {
    if (!ar || id >= ANTI_REPEAT_MAX) {
        return false;
    }
    const uint32_t word = id >> 5u;
    const uint32_t mask = 1u << (id & 31u);
    return (ar->bits[word] & mask) != 0u;
}

uint32_t anti_repeat_count(const AntiRepeat *ar) {
    return ar ? ar->count : 0u;
}
```

- [ ] **Step 5: Wire into Makefile** (same shape as Task 1)

1. Add `test_anti_repeat` to the `test:` aggregator and to `.PHONY`.
2. Add the per-test rules:
   ```
   test_anti_repeat: anti_repeat.o tests/test_anti_repeat.o
   	$(CC) $(CFLAGS) -o test_anti_repeat anti_repeat.o tests/test_anti_repeat.o
   	./test_anti_repeat

   anti_repeat.o: src/domain/anti_repeat.c include/domain/anti_repeat.h
   	$(CC) $(CFLAGS) -c src/domain/anti_repeat.c -o anti_repeat.o

   tests/test_anti_repeat.o: tests/test_anti_repeat.c include/domain/anti_repeat.h
   	$(CC) $(CFLAGS) -c tests/test_anti_repeat.c -o tests/test_anti_repeat.o
   ```
3. Append `test_anti_repeat` to the `clean` recipe's `rm -f` list.
4. Append `src/domain/anti_repeat.c` to the `linter` cppcheck source list.

- [ ] **Step 6: Update `application.fam`** — add `"src/domain/anti_repeat.c"` to `sources`.

- [ ] **Step 7: Verify** — `make clean && make test && make linter && make format && git diff --exit-code` all exit 0.

- [ ] **Step 8: Skipped commit.**

---

### Task 3: `domain/history_buffer` — last-N ring buffer (TDD)

**Files:**
- Create: `include/domain/history_buffer.h`
- Create: `src/domain/history_buffer.c`
- Create: `tests/test_history_buffer.c`
- Modify: `Makefile`, `application.fam`

Ring buffer of the last 5 question ids, used by the `←` button to walk back through recent questions. Capacity = `HISTORY_CAPACITY = 5`. Operations: `push`, `peek_back(steps)`, `clear`, `len`. Older entries are dropped when the buffer is full.

- [ ] **Step 1: Write the failing test**

Create `tests/test_history_buffer.c`:

```c
#include "include/domain/history_buffer.h"
#include <assert.h>

int main(void) {
    HistoryBuffer h;
    history_buffer_init(&h);

    uint32_t out;
    assert(history_buffer_len(&h) == 0u);
    assert(history_buffer_peek_back(&h, 0u, &out) == false);

    history_buffer_push(&h, 10u);
    assert(history_buffer_len(&h) == 1u);
    assert(history_buffer_peek_back(&h, 0u, &out) == true && out == 10u);
    assert(history_buffer_peek_back(&h, 1u, &out) == false);

    history_buffer_push(&h, 20u);
    history_buffer_push(&h, 30u);
    assert(history_buffer_len(&h) == 3u);
    assert(history_buffer_peek_back(&h, 0u, &out) == true && out == 30u);
    assert(history_buffer_peek_back(&h, 1u, &out) == true && out == 20u);
    assert(history_buffer_peek_back(&h, 2u, &out) == true && out == 10u);
    assert(history_buffer_peek_back(&h, 3u, &out) == false);

    /* Fill and overflow */
    history_buffer_push(&h, 40u);
    history_buffer_push(&h, 50u);
    history_buffer_push(&h, 60u); /* drops 10 */
    history_buffer_push(&h, 70u); /* drops 20 */
    assert(history_buffer_len(&h) == HISTORY_CAPACITY);
    assert(history_buffer_peek_back(&h, 0u, &out) == true && out == 70u);
    assert(history_buffer_peek_back(&h, 4u, &out) == true && out == 30u);
    assert(history_buffer_peek_back(&h, 5u, &out) == false);

    history_buffer_clear(&h);
    assert(history_buffer_len(&h) == 0u);
    assert(history_buffer_peek_back(&h, 0u, &out) == false);

    return 0;
}
```

- [ ] **Step 2: Verify it fails** (compile error).

- [ ] **Step 3: Header**

Create `include/domain/history_buffer.h`:

```c
#pragma once

#include <stdbool.h>
#include <stdint.h>

#define HISTORY_CAPACITY 5u

typedef struct {
    uint32_t ids[HISTORY_CAPACITY];
    uint8_t head; /* index of next slot to write */
    uint8_t len;  /* count of valid entries (<= HISTORY_CAPACITY) */
} HistoryBuffer;

void history_buffer_init(HistoryBuffer *h);
void history_buffer_clear(HistoryBuffer *h);
void history_buffer_push(HistoryBuffer *h, uint32_t id);

/* Peek `steps` positions back from the most-recent entry.
 * steps == 0 returns the most recent. Returns false if steps >= len. */
bool history_buffer_peek_back(const HistoryBuffer *h, uint8_t steps, uint32_t *out);

uint8_t history_buffer_len(const HistoryBuffer *h);
```

- [ ] **Step 4: Implementation**

Create `src/domain/history_buffer.c`:

```c
#include "include/domain/history_buffer.h"
#include <string.h>

void history_buffer_init(HistoryBuffer *h) {
    if (!h) {
        return;
    }
    memset(h, 0, sizeof(*h));
}

void history_buffer_clear(HistoryBuffer *h) {
    history_buffer_init(h);
}

void history_buffer_push(HistoryBuffer *h, uint32_t id) {
    if (!h) {
        return;
    }
    h->ids[h->head] = id;
    h->head = (uint8_t)((h->head + 1u) % HISTORY_CAPACITY);
    if (h->len < HISTORY_CAPACITY) {
        h->len++;
    }
}

bool history_buffer_peek_back(const HistoryBuffer *h, uint8_t steps, uint32_t *out) {
    if (!h || !out || steps >= h->len) {
        return false;
    }
    /* head points to next-write slot. The most recent entry is at (head - 1). */
    const uint8_t idx = (uint8_t)((h->head + HISTORY_CAPACITY - 1u - steps) % HISTORY_CAPACITY);
    *out = h->ids[idx];
    return true;
}

uint8_t history_buffer_len(const HistoryBuffer *h) {
    return h ? h->len : 0u;
}
```

- [ ] **Step 5: Wire into Makefile** (same shape as Task 1: add to `test:`, `.PHONY`, per-test rules, `clean`, `linter`).

- [ ] **Step 6: Update `application.fam`** — add `"src/domain/history_buffer.c"`.

- [ ] **Step 7: Verify** — full make sequence exits 0.

- [ ] **Step 8: Skipped commit.**

---

### Task 4: `domain/question_pool` — random unseen id selection (TDD)

**Files:**
- Create: `include/domain/question_pool.h`
- Create: `src/domain/question_pool.c`
- Create: `tests/test_question_pool.c`
- Modify: `Makefile`, `application.fam`

Picks a random id from `[0, count)` that is not yet in `seen_set`. Resets the seen set when the pool is exhausted (so the user keeps seeing questions even after going through the whole pool). RNG is injected as a function pointer so tests can use a deterministic stub.

- [ ] **Step 1: Failing test**

Create `tests/test_question_pool.c`:

```c
#include "include/domain/anti_repeat.h"
#include "include/domain/question_pool.h"
#include <assert.h>

static uint32_t g_seq[8];
static uint32_t g_seq_idx;

static uint32_t stub_rng(void *ctx) {
    (void)ctx;
    const uint32_t v = g_seq[g_seq_idx];
    g_seq_idx = (g_seq_idx + 1u) % 8u;
    return v;
}

int main(void) {
    AntiRepeat seen;
    anti_repeat_init(&seen);

    /* count=4. RNG returns values that mod-4 to 0,1,2,3 in order. */
    g_seq[0] = 0u;
    g_seq[1] = 1u;
    g_seq[2] = 2u;
    g_seq[3] = 3u;
    g_seq[4] = 0u;
    g_seq[5] = 1u;
    g_seq_idx = 0u;

    uint32_t id;
    bool reset_happened;

    /* First pick: 0, not seen → returned. */
    assert(question_pool_next(4u, &seen, stub_rng, NULL, &id, &reset_happened) == true);
    assert(id == 0u && reset_happened == false);
    anti_repeat_mark(&seen, id);

    /* Next: 1, 2, 3 — not seen → returned in order. */
    assert(question_pool_next(4u, &seen, stub_rng, NULL, &id, &reset_happened) && id == 1u && !reset_happened);
    anti_repeat_mark(&seen, id);
    assert(question_pool_next(4u, &seen, stub_rng, NULL, &id, &reset_happened) && id == 2u && !reset_happened);
    anti_repeat_mark(&seen, id);
    assert(question_pool_next(4u, &seen, stub_rng, NULL, &id, &reset_happened) && id == 3u && !reset_happened);
    anti_repeat_mark(&seen, id);

    /* All 4 are now seen → next call must reset and return a fresh id. */
    assert(question_pool_next(4u, &seen, stub_rng, NULL, &id, &reset_happened) == true);
    assert(reset_happened == true);
    assert(id < 4u);

    /* count == 0 → returns false. */
    AntiRepeat empty;
    anti_repeat_init(&empty);
    assert(question_pool_next(0u, &empty, stub_rng, NULL, &id, &reset_happened) == false);

    return 0;
}
```

- [ ] **Step 2: Verify it fails.**

- [ ] **Step 3: Header**

Create `include/domain/question_pool.h`:

```c
#pragma once

#include "include/domain/anti_repeat.h"
#include <stdbool.h>
#include <stdint.h>

typedef uint32_t (*RngFn)(void *ctx);

/* Picks a random id in [0, count) that is not in `seen`. If every id is seen,
 * resets `seen` and picks again (sets *reset_happened to true).
 * Returns false if count == 0. */
bool question_pool_next(uint32_t count, AntiRepeat *seen, RngFn rng, void *rng_ctx,
                        uint32_t *id_out, bool *reset_happened);
```

- [ ] **Step 4: Implementation**

Create `src/domain/question_pool.c`:

```c
#include "include/domain/question_pool.h"

bool question_pool_next(uint32_t count, AntiRepeat *seen, RngFn rng, void *rng_ctx,
                        uint32_t *id_out, bool *reset_happened) {
    if (count == 0u || !seen || !rng || !id_out || !reset_happened) {
        return false;
    }

    *reset_happened = false;

    if (anti_repeat_count(seen) >= count) {
        anti_repeat_reset(seen);
        *reset_happened = true;
    }

    /* Linear probe from a random start. Worst case scans the whole pool, which
     * is fine — the pool is small (~2000) and we only do this on user input. */
    const uint32_t start = rng(rng_ctx) % count;
    for (uint32_t i = 0u; i < count; ++i) {
        const uint32_t cand = (start + i) % count;
        if (!anti_repeat_is_marked(seen, cand)) {
            *id_out = cand;
            return true;
        }
    }

    /* Should not happen: we just reset above if everything was seen. */
    return false;
}
```

- [ ] **Step 5: Wire into Makefile.** Note: `test_question_pool` depends on **two** `.o` files: `question_pool.o` and `anti_repeat.o`. The recipe is:

```
test_question_pool: question_pool.o anti_repeat.o tests/test_question_pool.o
	$(CC) $(CFLAGS) -o test_question_pool question_pool.o anti_repeat.o tests/test_question_pool.o
	./test_question_pool

question_pool.o: src/domain/question_pool.c include/domain/question_pool.h include/domain/anti_repeat.h
	$(CC) $(CFLAGS) -c src/domain/question_pool.c -o question_pool.o

tests/test_question_pool.o: tests/test_question_pool.c include/domain/question_pool.h include/domain/anti_repeat.h
	$(CC) $(CFLAGS) -c tests/test_question_pool.c -o tests/test_question_pool.o
```

Add to `test:` aggregator, `.PHONY`, `clean`, `linter`.

- [ ] **Step 6: Update `application.fam`** — add `"src/domain/question_pool.c"`.

- [ ] **Step 7: Verify** — full make sequence exits 0.

- [ ] **Step 8: Skipped commit.**

---

### Task 5: `i18n/strings` — localized UI strings (TDD)

**Files:**
- Create: `include/i18n/strings.h`
- Create: `src/i18n/strings.c`
- Create: `tests/test_strings.c`
- Modify: `Makefile`, `application.fam`

Localized strings table for menu items and UI hints (categories live in `domain/category` because they're domain content; this module is pure UI chrome). Pattern mirrors `flipper-impostor-game/src/i18n/strings.c` exactly. Locale state is held in a single static (matches sibling).

- [ ] **Step 1: Failing test**

Create `tests/test_strings.c`:

```c
#include "include/i18n/strings.h"
#include <assert.h>
#include <string.h>

int main(void) {
    /* Default locale is EN. */
    assert(tz_locale_get() == LangEn);
    assert(strcmp(tz_str(TzStrMenuChangeLang), "Change language") == 0);
    assert(strcmp(tz_str(TzStrMenuExit), "Exit") == 0);
    assert(strcmp(tz_str(TzStrFooterReveal), "OK: reveal") == 0);
    assert(strcmp(tz_str(TzStrFooterNext), ">: next") == 0);
    assert(strcmp(tz_str(TzStrLangPickHeader), "Language") == 0);
    assert(strcmp(tz_str(TzStrLangSpanish), "Spanish") == 0);
    assert(strcmp(tz_str(TzStrLangEnglish), "English") == 0);

    tz_locale_set(LangEs);
    assert(tz_locale_get() == LangEs);
    assert(strcmp(tz_str(TzStrMenuChangeLang), "Cambiar idioma") == 0);
    assert(strcmp(tz_str(TzStrMenuExit), "Salir") == 0);
    assert(strcmp(tz_str(TzStrFooterReveal), "OK: revelar") == 0);
    assert(strcmp(tz_str(TzStrFooterNext), ">: siguiente") == 0);
    assert(strcmp(tz_str(TzStrLangPickHeader), "Idioma") == 0);
    assert(strcmp(tz_str(TzStrLangSpanish), "Español") == 0);
    assert(strcmp(tz_str(TzStrLangEnglish), "Inglés") == 0);

    /* Out-of-range id falls back to a sentinel. */
    assert(strcmp(tz_str(TzStrCount), "?") == 0);

    /* Invalid locale falls back to EN. */
    tz_locale_set((Lang)99);
    assert(tz_locale_get() == LangEn);

    return 0;
}
```

- [ ] **Step 2: Verify it fails.**

- [ ] **Step 3: Header**

Create `include/i18n/strings.h`:

```c
#pragma once

#include "include/domain/category.h" /* for Lang */

typedef enum {
    TzStrMenuChangeLang = 0,
    TzStrMenuExit,
    TzStrFooterReveal,
    TzStrFooterNext,
    TzStrLangPickHeader,
    TzStrLangSpanish,
    TzStrLangEnglish,
    TzStrCount, /* keep last */
} TzStrId;

Lang tz_locale_get(void);
void tz_locale_set(Lang locale);

const char *tz_str(TzStrId id);
```

- [ ] **Step 4: Implementation**

Create `src/i18n/strings.c`:

```c
#include "include/i18n/strings.h"

static Lang g_locale = LangEn;

static const char *const k_en[TzStrCount] = {
    [TzStrMenuChangeLang] = "Change language",
    [TzStrMenuExit] = "Exit",
    [TzStrFooterReveal] = "OK: reveal",
    [TzStrFooterNext] = ">: next",
    [TzStrLangPickHeader] = "Language",
    [TzStrLangSpanish] = "Spanish",
    [TzStrLangEnglish] = "English",
};

static const char *const k_es[TzStrCount] = {
    [TzStrMenuChangeLang] = "Cambiar idioma",
    [TzStrMenuExit] = "Salir",
    [TzStrFooterReveal] = "OK: revelar",
    [TzStrFooterNext] = ">: siguiente",
    [TzStrLangPickHeader] = "Idioma",
    [TzStrLangSpanish] = "Español",
    [TzStrLangEnglish] = "Inglés",
};

Lang tz_locale_get(void) { return g_locale; }

void tz_locale_set(Lang locale) {
    g_locale = (locale == LangEs) ? LangEs : LangEn;
}

const char *tz_str(TzStrId id) {
    if ((unsigned)id >= (unsigned)TzStrCount) {
        return "?";
    }
    return (g_locale == LangEs) ? k_es[id] : k_en[id];
}
```

- [ ] **Step 5: Makefile** — `test_strings` depends on `strings.o` and `tests/test_strings.o`. (Does **not** need `category.o` because `Lang` is defined in `category.h` as an enum — it has no implementation dependency.)

- [ ] **Step 6: `application.fam`** — add `"src/i18n/strings.c"`.

- [ ] **Step 7: Verify** — full make sequence.

- [ ] **Step 8: Skipped commit.**

---

### Task 6: `infrastructure/settings_storage` — pure parser + Furi I/O

**Files:**
- Create: `include/infrastructure/settings_storage.h`
- Create: `src/infrastructure/settings_storage.c`
- Create: `tests/test_settings_storage.c`
- Modify: `Makefile`, `application.fam`

Loads/saves `lang` and `last_id` from `/ext/apps_data/flipper_trivia_zero/settings`. Format per spec §5.3: line-based key=value, lines starting with `#` are skipped, unknown keys are skipped, malformed lines are skipped. The **parser** is pure C and host-testable (`settings_apply_kv`); the **I/O** wrapper uses Furi's storage API and is verified manually on hardware.

- [ ] **Step 1: Failing test (parser only)**

Create `tests/test_settings_storage.c`:

```c
#include "include/infrastructure/settings_storage.h"
#include <assert.h>
#include <string.h>

int main(void) {
    Settings s = settings_default();

    /* Defaults */
    assert(s.lang == LangEn);
    assert(s.last_id == 0u);
    assert(s.last_id_valid == false);

    /* Apply known kv */
    assert(settings_apply_kv(&s, "lang", "es") == true);
    assert(s.lang == LangEs);

    assert(settings_apply_kv(&s, "lang", "en") == true);
    assert(s.lang == LangEn);

    assert(settings_apply_kv(&s, "last_id", "1234") == true);
    assert(s.last_id == 1234u);
    assert(s.last_id_valid == true);

    /* Unknown key returns false but does not corrupt state */
    Settings before = s;
    assert(settings_apply_kv(&s, "future_key", "anything") == false);
    assert(memcmp(&s, &before, sizeof(s)) == 0);

    /* Malformed values keep prior state */
    assert(settings_apply_kv(&s, "lang", "fr") == false);
    assert(s.lang == LangEn); /* unchanged */
    assert(settings_apply_kv(&s, "last_id", "not-a-number") == false);
    assert(s.last_id == 1234u); /* unchanged */

    /* Line splitter */
    char key[32];
    char value[64];
    assert(settings_split_line("lang=es", key, sizeof(key), value, sizeof(value)) == true);
    assert(strcmp(key, "lang") == 0 && strcmp(value, "es") == 0);

    /* Comment line returns false */
    assert(settings_split_line("# trivia v1", key, sizeof(key), value, sizeof(value)) == false);

    /* Empty/whitespace returns false */
    assert(settings_split_line("", key, sizeof(key), value, sizeof(value)) == false);
    assert(settings_split_line("   ", key, sizeof(key), value, sizeof(value)) == false);

    /* No equals sign returns false */
    assert(settings_split_line("garbage", key, sizeof(key), value, sizeof(value)) == false);

    /* Trailing newline trimmed */
    assert(settings_split_line("last_id=42\n", key, sizeof(key), value, sizeof(value)) == true);
    assert(strcmp(key, "last_id") == 0 && strcmp(value, "42") == 0);

    return 0;
}
```

- [ ] **Step 2: Verify it fails.**

- [ ] **Step 3: Header**

Create `include/infrastructure/settings_storage.h`:

```c
#pragma once

#include "include/domain/category.h" /* for Lang */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef struct {
    Lang lang;
    uint32_t last_id;
    bool last_id_valid;
} Settings;

/* ---- Pure parsing (host-testable) ---- */

Settings settings_default(void);

/* Splits a single settings line into key + value.
 * Returns false for empty, comment (#...), whitespace-only, or lines without '='.
 * Strips leading/trailing whitespace and a single trailing '\n'. */
bool settings_split_line(const char *line,
                         char *key, size_t key_size,
                         char *value, size_t value_size);

/* Applies a known key=value pair to settings. Returns true if the key was
 * recognized AND the value was valid. Unknown keys / invalid values return
 * false and leave settings unchanged. */
bool settings_apply_kv(Settings *s, const char *key, const char *value);

/* ---- Furi I/O (hardware-only; declared here, verified on device) ---- */

bool settings_load(Settings *out);
bool settings_save(const Settings *s);
```

- [ ] **Step 4: Implementation**

Create `src/infrastructure/settings_storage.c`:

```c
#include "include/infrastructure/settings_storage.h"
#include <ctype.h>
#include <stdlib.h>
#include <string.h>

#ifdef __has_include
#if __has_include(<furi.h>)
#include <furi.h>
#include <storage/storage.h>
#define TZ_HAVE_FURI 1
#endif
#endif

#define APPS_DATA_DIR "/ext/apps_data/flipper_trivia_zero"
#define SETTINGS_PATH APPS_DATA_DIR "/settings"
#define SETTINGS_HEADER "# trivia v1\n"

/* ---- Pure parsing ---- */

Settings settings_default(void) {
    return (Settings){.lang = LangEn, .last_id = 0u, .last_id_valid = false};
}

static char *trim_inplace(char *s) {
    if (!s) return s;
    while (*s && isspace((unsigned char)*s)) s++;
    char *end = s + strlen(s);
    while (end > s && isspace((unsigned char)end[-1])) end--;
    *end = '\0';
    return s;
}

bool settings_split_line(const char *line,
                         char *key, size_t key_size,
                         char *value, size_t value_size) {
    if (!line || !key || !value || key_size == 0 || value_size == 0) {
        return false;
    }

    /* Make a working copy and strip a trailing newline */
    char buf[160];
    strncpy(buf, line, sizeof(buf) - 1u);
    buf[sizeof(buf) - 1u] = '\0';
    char *nl = strchr(buf, '\n');
    if (nl) *nl = '\0';

    char *t = trim_inplace(buf);
    if (*t == '\0' || *t == '#') {
        return false;
    }

    char *eq = strchr(t, '=');
    if (!eq) {
        return false;
    }
    *eq = '\0';
    char *k = trim_inplace(t);
    char *v = trim_inplace(eq + 1);

    if (strlen(k) >= key_size || strlen(v) >= value_size) {
        return false;
    }
    strcpy(key, k);
    strcpy(value, v);
    return true;
}

bool settings_apply_kv(Settings *s, const char *key, const char *value) {
    if (!s || !key || !value) {
        return false;
    }
    if (strcmp(key, "lang") == 0) {
        if (strcmp(value, "es") == 0) {
            s->lang = LangEs;
            return true;
        }
        if (strcmp(value, "en") == 0) {
            s->lang = LangEn;
            return true;
        }
        return false;
    }
    if (strcmp(key, "last_id") == 0) {
        char *end = NULL;
        const unsigned long parsed = strtoul(value, &end, 10);
        if (end == value || *end != '\0' || parsed > 0xFFFFFFFFul) {
            return false;
        }
        s->last_id = (uint32_t)parsed;
        s->last_id_valid = true;
        return true;
    }
    return false;
}

/* ---- Furi I/O ---- */

#ifdef TZ_HAVE_FURI

bool settings_load(Settings *out) {
    if (!out) return false;
    *out = settings_default();

    Storage *storage = furi_record_open(RECORD_STORAGE);
    File *file = storage_file_alloc(storage);
    bool ok = false;

    if (storage_file_open(file, SETTINGS_PATH, FSAM_READ, FSOM_OPEN_EXISTING)) {
        char buf[160];
        size_t pos = 0u;
        char ch;
        while (storage_file_read(file, &ch, 1) == 1) {
            if (ch == '\n' || pos == sizeof(buf) - 1u) {
                buf[pos] = '\0';
                char k[32];
                char v[96];
                if (settings_split_line(buf, k, sizeof(k), v, sizeof(v))) {
                    settings_apply_kv(out, k, v);
                }
                pos = 0u;
                if (ch != '\n') {
                    /* line was truncated; reset and skip until next '\n' */
                    while (storage_file_read(file, &ch, 1) == 1 && ch != '\n') {
                        /* drain */
                    }
                }
            } else {
                buf[pos++] = ch;
            }
        }
        if (pos > 0u) {
            buf[pos] = '\0';
            char k[32];
            char v[96];
            if (settings_split_line(buf, k, sizeof(k), v, sizeof(v))) {
                settings_apply_kv(out, k, v);
            }
        }
        ok = true;
    }

    storage_file_close(file);
    storage_file_free(file);
    furi_record_close(RECORD_STORAGE);
    return ok;
}

bool settings_save(const Settings *s) {
    if (!s) return false;
    Storage *storage = furi_record_open(RECORD_STORAGE);
    File *file = storage_file_alloc(storage);
    bool ok = false;

    storage_common_mkdir(storage, APPS_DATA_DIR);
    if (storage_file_open(file, SETTINGS_PATH, FSAM_WRITE, FSOM_CREATE_ALWAYS)) {
        storage_file_write(file, SETTINGS_HEADER, sizeof(SETTINGS_HEADER) - 1u);
        const char *lang = (s->lang == LangEs) ? "lang=es\n" : "lang=en\n";
        storage_file_write(file, lang, strlen(lang));
        if (s->last_id_valid) {
            char line[40];
            const int n = snprintf(line, sizeof(line), "last_id=%lu\n",
                                   (unsigned long)s->last_id);
            if (n > 0 && (size_t)n < sizeof(line)) {
                storage_file_write(file, line, (size_t)n);
            }
        }
        ok = true;
    }

    storage_file_close(file);
    storage_file_free(file);
    furi_record_close(RECORD_STORAGE);
    return ok;
}

#endif /* TZ_HAVE_FURI */
```

The `__has_include(<furi.h>)` guard makes the file safe to compile both on host (host tests link only the parser) and on device.

- [ ] **Step 5: Makefile** — `test_settings_storage` depends on `settings_storage.o` and `tests/test_settings_storage.o`. The Furi I/O block compiles to nothing on host because `<furi.h>` is missing.

- [ ] **Step 6: `application.fam`** — add `"src/infrastructure/settings_storage.c"`.

- [ ] **Step 7: Verify** — full make sequence.

- [ ] **Step 8: Skipped commit.**

---

### Task 7: `infrastructure/pack_reader` — pure TSV/idx parser + Furi I/O

**Files:**
- Create: `include/infrastructure/pack_reader.h`
- Create: `src/infrastructure/pack_reader.c`
- Create: `tests/test_pack_reader.c`
- Modify: `Makefile`, `application.fam`

Reads the question pack from `/ext/apps_data/flipper_trivia_zero/trivia_<lang>.tsv` + `.idx`. Pack format per spec §5.1 and §5.2.

The **pure** surface is host-testable:
- `pack_parse_tsv_line(line, len, &entry)` — splits on `\t`, populates `Question`.
- `pack_idx_header_decode(blob, blob_len, &header)` — verifies `magic="TRVI"` + version + count.
- `pack_idx_offset_at(blob, blob_len, count, i, &offset)` — bounds-checked offset lookup.

The **I/O** surface is Furi-only:
- `pack_open(lang)` / `pack_close()` / `pack_get_by_id(id, &q)`.

- [ ] **Step 1: Failing test**

Create `tests/test_pack_reader.c`:

```c
#include "include/infrastructure/pack_reader.h"
#include <assert.h>
#include <string.h>

int main(void) {
    /* TSV line parsing */
    Question q;
    const char *line = "0\t6\tWhat year was Pelé born?\t1940";
    assert(pack_parse_tsv_line(line, strlen(line), &q) == true);
    assert(q.id == 0u);
    assert(q.category_id == 6u);
    assert(strcmp(q.question, "What year was Pelé born?") == 0);
    assert(strcmp(q.answer, "1940") == 0);

    /* Trailing newline tolerated */
    const char *line_nl = "12\t1\tCapital of Spain?\tMadrid\n";
    assert(pack_parse_tsv_line(line_nl, strlen(line_nl), &q) == true);
    assert(q.id == 12u && q.category_id == 1u);
    assert(strcmp(q.question, "Capital of Spain?") == 0);
    assert(strcmp(q.answer, "Madrid") == 0);

    /* Wrong number of fields */
    const char *bad = "1\t2\tonly three";
    assert(pack_parse_tsv_line(bad, strlen(bad), &q) == false);

    /* Non-numeric id */
    const char *bad_id = "abc\t2\tQ\tA";
    assert(pack_parse_tsv_line(bad_id, strlen(bad_id), &q) == false);

    /* Out-of-range category */
    const char *bad_cat = "1\t99\tQ\tA";
    assert(pack_parse_tsv_line(bad_cat, strlen(bad_cat), &q) == false);

    /* IDX header decoding */
    const uint8_t header_ok[] = {
        'T', 'R', 'V', 'I',     /* magic */
        0x01, 0x00,             /* version 1 LE */
        0x03, 0x00, 0x00, 0x00, /* count = 3 */
    };
    PackIdxHeader h;
    assert(pack_idx_header_decode(header_ok, sizeof(header_ok), &h) == true);
    assert(h.version == 1u);
    assert(h.count == 3u);

    /* Bad magic */
    uint8_t bad_magic[sizeof(header_ok)];
    memcpy(bad_magic, header_ok, sizeof(header_ok));
    bad_magic[0] = 'X';
    assert(pack_idx_header_decode(bad_magic, sizeof(bad_magic), &h) == false);

    /* Truncated */
    assert(pack_idx_header_decode(header_ok, 6u, &h) == false);

    /* Offset lookup with a 3-entry idx */
    const uint8_t idx_blob[] = {
        'T', 'R', 'V', 'I',
        0x01, 0x00,
        0x03, 0x00, 0x00, 0x00,
        0x10, 0x00, 0x00, 0x00, /* offsets[0] = 16 */
        0x40, 0x00, 0x00, 0x00, /* offsets[1] = 64 */
        0xA0, 0x00, 0x00, 0x00, /* offsets[2] = 160 */
    };
    uint32_t off;
    assert(pack_idx_offset_at(idx_blob, sizeof(idx_blob), 3u, 0u, &off) && off == 16u);
    assert(pack_idx_offset_at(idx_blob, sizeof(idx_blob), 3u, 2u, &off) && off == 160u);
    assert(pack_idx_offset_at(idx_blob, sizeof(idx_blob), 3u, 3u, &off) == false); /* OOB */

    return 0;
}
```

- [ ] **Step 2: Verify it fails.**

- [ ] **Step 3: Header**

Create `include/infrastructure/pack_reader.h`:

```c
#pragma once

#include "include/domain/category.h"
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define QUESTION_MAX 320u
#define ANSWER_MAX 96u

typedef struct {
    uint32_t id;
    uint8_t category_id;
    char question[QUESTION_MAX];
    char answer[ANSWER_MAX];
} Question;

typedef struct {
    uint16_t version;
    uint32_t count;
} PackIdxHeader;

/* ---- Pure parsing ---- */

bool pack_parse_tsv_line(const char *line, size_t len, Question *out);

bool pack_idx_header_decode(const uint8_t *blob, size_t len, PackIdxHeader *out);

bool pack_idx_offset_at(const uint8_t *blob, size_t len, uint32_t count,
                        uint32_t i, uint32_t *offset_out);

/* ---- Furi I/O (hardware-only) ---- */

bool pack_open(Lang lang);
void pack_close(void);
uint32_t pack_count(void);
bool pack_get_by_id(uint32_t id, Question *out);
```

- [ ] **Step 4: Implementation**

Create `src/infrastructure/pack_reader.c`:

```c
#include "include/infrastructure/pack_reader.h"
#include <stdlib.h>
#include <string.h>

#ifdef __has_include
#if __has_include(<furi.h>)
#include <furi.h>
#include <storage/storage.h>
#define TZ_HAVE_FURI 1
#endif
#endif

#define IDX_HEADER_SIZE 10u /* 4 magic + 2 version + 4 count */

static uint16_t le_u16(const uint8_t *p) {
    return (uint16_t)(p[0] | ((uint16_t)p[1] << 8));
}

static uint32_t le_u32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}

bool pack_parse_tsv_line(const char *line, size_t len, Question *out) {
    if (!line || !out || len == 0u) {
        return false;
    }
    /* Strip a trailing newline from the effective length. */
    while (len > 0u && (line[len - 1u] == '\n' || line[len - 1u] == '\r')) {
        len--;
    }
    if (len == 0u) {
        return false;
    }

    /* Find the three tab positions. */
    size_t tabs[3];
    size_t found = 0u;
    for (size_t i = 0u; i < len && found < 3u; ++i) {
        if (line[i] == '\t') {
            tabs[found++] = i;
        }
    }
    if (found != 3u) {
        return false;
    }

    /* id */
    char idbuf[16];
    if (tabs[0] >= sizeof(idbuf)) return false;
    memcpy(idbuf, line, tabs[0]);
    idbuf[tabs[0]] = '\0';
    char *end = NULL;
    const unsigned long id = strtoul(idbuf, &end, 10);
    if (end == idbuf || *end != '\0') return false;

    /* category_id */
    const size_t cat_start = tabs[0] + 1u;
    const size_t cat_len = tabs[1] - cat_start;
    char catbuf[8];
    if (cat_len >= sizeof(catbuf)) return false;
    memcpy(catbuf, line + cat_start, cat_len);
    catbuf[cat_len] = '\0';
    const unsigned long cat = strtoul(catbuf, &end, 10);
    if (end == catbuf || *end != '\0' || cat < 1u || cat > 7u) return false;

    /* question */
    const size_t q_start = tabs[1] + 1u;
    const size_t q_len = tabs[2] - q_start;
    if (q_len >= QUESTION_MAX) return false;

    /* answer */
    const size_t a_start = tabs[2] + 1u;
    const size_t a_len = len - a_start;
    if (a_len >= ANSWER_MAX) return false;

    out->id = (uint32_t)id;
    out->category_id = (uint8_t)cat;
    memcpy(out->question, line + q_start, q_len);
    out->question[q_len] = '\0';
    memcpy(out->answer, line + a_start, a_len);
    out->answer[a_len] = '\0';
    return true;
}

bool pack_idx_header_decode(const uint8_t *blob, size_t len, PackIdxHeader *out) {
    if (!blob || !out || len < IDX_HEADER_SIZE) return false;
    if (blob[0] != 'T' || blob[1] != 'R' || blob[2] != 'V' || blob[3] != 'I') {
        return false;
    }
    out->version = le_u16(blob + 4);
    out->count = le_u32(blob + 6);
    return true;
}

bool pack_idx_offset_at(const uint8_t *blob, size_t len, uint32_t count,
                        uint32_t i, uint32_t *offset_out) {
    if (!blob || !offset_out || i >= count) return false;
    const size_t need = (size_t)IDX_HEADER_SIZE + (size_t)count * 4u;
    if (len < need) return false;
    *offset_out = le_u32(blob + IDX_HEADER_SIZE + (size_t)i * 4u);
    return true;
}

#ifdef TZ_HAVE_FURI

static Storage *s_storage = NULL;
static File *s_tsv = NULL;
static File *s_idx = NULL;
static uint32_t s_count = 0u;

static const char *path_tsv(Lang lang) {
    return (lang == LangEs)
               ? "/ext/apps_data/flipper_trivia_zero/trivia_es.tsv"
               : "/ext/apps_data/flipper_trivia_zero/trivia_en.tsv";
}

static const char *path_idx(Lang lang) {
    return (lang == LangEs)
               ? "/ext/apps_data/flipper_trivia_zero/trivia_es.idx"
               : "/ext/apps_data/flipper_trivia_zero/trivia_en.idx";
}

bool pack_open(Lang lang) {
    pack_close();
    s_storage = furi_record_open(RECORD_STORAGE);
    s_tsv = storage_file_alloc(s_storage);
    s_idx = storage_file_alloc(s_storage);

    if (!storage_file_open(s_tsv, path_tsv(lang), FSAM_READ, FSOM_OPEN_EXISTING) ||
        !storage_file_open(s_idx, path_idx(lang), FSAM_READ, FSOM_OPEN_EXISTING)) {
        pack_close();
        return false;
    }

    uint8_t header[IDX_HEADER_SIZE];
    if (storage_file_read(s_idx, header, sizeof(header)) != sizeof(header)) {
        pack_close();
        return false;
    }
    PackIdxHeader h;
    if (!pack_idx_header_decode(header, sizeof(header), &h) || h.version != 1u) {
        pack_close();
        return false;
    }
    s_count = h.count;
    return true;
}

void pack_close(void) {
    if (s_tsv) {
        storage_file_close(s_tsv);
        storage_file_free(s_tsv);
        s_tsv = NULL;
    }
    if (s_idx) {
        storage_file_close(s_idx);
        storage_file_free(s_idx);
        s_idx = NULL;
    }
    if (s_storage) {
        furi_record_close(RECORD_STORAGE);
        s_storage = NULL;
    }
    s_count = 0u;
}

uint32_t pack_count(void) { return s_count; }

bool pack_get_by_id(uint32_t id, Question *out) {
    if (!out || !s_idx || !s_tsv || id >= s_count) return false;

    /* Read offset[id] from idx */
    const uint64_t idx_pos = (uint64_t)IDX_HEADER_SIZE + (uint64_t)id * 4u;
    if (!storage_file_seek(s_idx, idx_pos, true)) return false;
    uint8_t off_bytes[4];
    if (storage_file_read(s_idx, off_bytes, 4) != 4) return false;
    const uint32_t offset =
        (uint32_t)off_bytes[0] | ((uint32_t)off_bytes[1] << 8) |
        ((uint32_t)off_bytes[2] << 16) | ((uint32_t)off_bytes[3] << 24);

    if (!storage_file_seek(s_tsv, offset, true)) return false;

    /* Read line until '\n' or buffer full */
    char line[QUESTION_MAX + ANSWER_MAX + 32u];
    size_t pos = 0u;
    char ch;
    while (pos < sizeof(line) - 1u && storage_file_read(s_tsv, &ch, 1) == 1) {
        if (ch == '\n') break;
        line[pos++] = ch;
    }
    line[pos] = '\0';

    return pack_parse_tsv_line(line, pos, out);
}

#endif /* TZ_HAVE_FURI */
```

- [ ] **Step 5: Makefile** — `test_pack_reader` depends on `pack_reader.o` and `tests/test_pack_reader.o`.

- [ ] **Step 6: `application.fam`** — add `"src/infrastructure/pack_reader.c"`.

- [ ] **Step 7: Verify** — full make sequence.

- [ ] **Step 8: Skipped commit.**

---

### Task 8: `platform/random_port` — Furi RNG wrapper

**Files:**
- Create: `include/platform/random_port.h`
- Create: `src/platform/random_port.c`
- Modify: `Makefile`, `application.fam`

Mirrors `flipper-impostor-game/src/platform/random_port.c` exactly. No host test (the wrapper is a single line of glue; testing it would tautologically test `furi_hal_random_get`).

- [ ] **Step 1: Header**

Create `include/platform/random_port.h`:

```c
#pragma once

#include <stdint.h>

uint32_t tz_rng_u32(void *ctx);
```

- [ ] **Step 2: Implementation**

Create `src/platform/random_port.c`:

```c
#include "include/platform/random_port.h"

#ifdef __has_include
#if __has_include(<furi_hal_random.h>)
#include <furi_hal_random.h>
#define TZ_HAVE_FURI 1
#endif
#endif

uint32_t tz_rng_u32(void *ctx) {
    (void)ctx;
#ifdef TZ_HAVE_FURI
    return furi_hal_random_get();
#else
    /* Host-build fallback: deterministic counter so cppcheck doesn't see
     * an undefined function call. Tests pass an explicit RngFn stub
     * (see Task 4) so this code path is never exercised on host. */
    static uint32_t s = 0u;
    return s++;
#endif
}
```

- [ ] **Step 3: Makefile** — append `src/platform/random_port.c` to the `linter` source list. No new test target.

- [ ] **Step 4: `application.fam`** — add `"src/platform/random_port.c"`.

- [ ] **Step 5: Verify** — `make linter && make format && git diff --exit-code` exit 0. (`make test` is unaffected.)

- [ ] **Step 6: Skipped commit.**

---

### Task 9: `ui/question_view` — custom View with header + scroll body + footer

**Files:**
- Create: `include/ui/question_view.h`
- Create: `src/ui/question_view.c`
- Create: `tests/test_question_view_layout.c`
- Modify: `Makefile`, `application.fam`

Custom `View` for the question screen. Layout: inverted header bar (~10 px) with category name, scrollable body (question OR answer once revealed), single-line footer with action hint.

The **pure** surface is the **wrap-into-lines** helper — given a string and a max-chars-per-line, split it into a sequence of line slices. This is host-testable.

The **Furi-bound** surface (allocate view, draw callback, input callback) is verified manually on hardware.

Key facts about the canvas:
- Default `FontSecondary` is ~5 px wide and ~7 px tall — about **21 chars per line** at 128 px width.
- We reserve 10 px for the header (rows 0-9), 1 px gap (row 10), N rows for body (rows 11 to 54 = 44 px → 6 visible lines), 1 px gap, and ~9 px footer (rows 55-63).
- Visible body capacity: 6 lines × 21 chars ≈ 126 chars per "page".

- [ ] **Step 1: Failing test (layout helper only)**

Create `tests/test_question_view_layout.c`:

```c
#include "include/ui/question_view.h"
#include <assert.h>
#include <string.h>

int main(void) {
    char buf[256];
    LineSlices slices;

    /* Empty input → 0 lines */
    qview_wrap("", 21u, buf, sizeof(buf), &slices);
    assert(slices.count == 0u);

    /* Single short line */
    qview_wrap("Hello world", 21u, buf, sizeof(buf), &slices);
    assert(slices.count == 1u);
    assert(strcmp(slices.lines[0], "Hello world") == 0);

    /* Word wrap */
    qview_wrap("This is a longer string that needs to wrap across lines",
               21u, buf, sizeof(buf), &slices);
    /* Greedy word wrap: each line <= 21 chars, prefer breaking on spaces */
    for (uint8_t i = 0u; i < slices.count; ++i) {
        assert(strlen(slices.lines[i]) <= 21u);
    }
    /* Reassembled (with single spaces between lines) should match the original */
    char joined[128];
    joined[0] = '\0';
    for (uint8_t i = 0u; i < slices.count; ++i) {
        if (i > 0u) strcat(joined, " ");
        strcat(joined, slices.lines[i]);
    }
    assert(strcmp(joined, "This is a longer string that needs to wrap across lines") == 0);

    /* Hard break on a single word longer than max */
    qview_wrap("Supercalifragilisticexpialidocious", 10u, buf, sizeof(buf), &slices);
    /* Should split mid-word at boundary 10 */
    assert(slices.count >= 2u);
    for (uint8_t i = 0u; i < slices.count; ++i) {
        assert(strlen(slices.lines[i]) <= 10u);
    }

    return 0;
}
```

- [ ] **Step 2: Verify it fails.**

- [ ] **Step 3: Header**

Create `include/ui/question_view.h`:

```c
#pragma once

#include "include/infrastructure/pack_reader.h"
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define QVIEW_MAX_LINES 32u

typedef struct {
    const char *lines[QVIEW_MAX_LINES];
    uint8_t count;
} LineSlices;

/* Pure: greedy word wrap into NUL-terminated slices stored inside `buf`.
 * Slices stay valid for the lifetime of `buf`. */
void qview_wrap(const char *text, uint8_t max_cols,
                char *buf, size_t buf_size, LineSlices *out);

/* ---- Furi-bound (hardware-only) ---- */

typedef enum {
    QViewModeQuestion,
    QViewModeAnswer,
} QViewMode;

typedef enum {
    QViewActionReveal,
    QViewActionNext,
    QViewActionPrev,
    QViewActionScrollUp,
    QViewActionScrollDown,
    QViewActionMenu,
} QViewAction;

typedef struct QuestionView QuestionView;

QuestionView *question_view_alloc(void);
void question_view_free(QuestionView *qv);
struct View *question_view_get_view(QuestionView *qv);

void question_view_set_question(QuestionView *qv, const Question *q);
void question_view_set_mode(QuestionView *qv, QViewMode mode);

void question_view_set_callback(QuestionView *qv, void *ctx,
                                void (*on_action)(void *ctx, QViewAction action));
```

- [ ] **Step 4: Implementation**

Create `src/ui/question_view.c`:

```c
#include "include/ui/question_view.h"
#include "include/domain/category.h"
#include "include/i18n/strings.h"
#include <string.h>

#ifdef __has_include
#if __has_include(<furi.h>)
#include <furi.h>
#include <gui/canvas.h>
#include <gui/elements.h>
#include <gui/view.h>
#include <input/input.h>
#include <stdlib.h>
#define TZ_HAVE_FURI 1
#endif
#endif

/* ---- Pure word wrap ---- */

void qview_wrap(const char *text, uint8_t max_cols,
                char *buf, size_t buf_size, LineSlices *out) {
    if (!out) return;
    out->count = 0u;
    if (!text || !buf || buf_size == 0u || max_cols == 0u) return;

    size_t pos = 0u;
    const size_t tlen = strlen(text);
    if (tlen == 0u) return;

    size_t i = 0u;
    while (i < tlen && out->count < QVIEW_MAX_LINES) {
        /* skip leading spaces between lines */
        while (i < tlen && text[i] == ' ') i++;
        if (i >= tlen) break;

        /* find the longest prefix <= max_cols that ends at a space (or EOS) */
        size_t end = i;
        size_t last_space = 0u;
        while (end < tlen && (end - i) < max_cols) {
            if (text[end] == ' ') last_space = end;
            end++;
        }

        size_t cut;
        if (end >= tlen) {
            cut = end;
        } else if (text[end] == ' ') {
            cut = end;
        } else if (last_space > i) {
            cut = last_space;
        } else {
            cut = end; /* hard break */
        }

        const size_t line_len = cut - i;
        if (pos + line_len + 1u > buf_size) break;

        memcpy(buf + pos, text + i, line_len);
        buf[pos + line_len] = '\0';
        out->lines[out->count++] = buf + pos;
        pos += line_len + 1u;
        i = cut;
    }
}

/* ---- Furi-bound View ---- */

#ifdef TZ_HAVE_FURI

#define BODY_VISIBLE_LINES 6u
#define BODY_MAX_COLS 21u
#define WRAP_BUF_SIZE (QUESTION_MAX + ANSWER_MAX)

typedef struct {
    Question q;
    QViewMode mode;
    uint8_t scroll;
    char wrap_buf[WRAP_BUF_SIZE];
    LineSlices slices;
} QViewModel;

struct QuestionView {
    View *view;
    void *ctx;
    void (*on_action)(void *ctx, QViewAction action);
};

static void recompute_slices(QViewModel *m) {
    const char *text =
        (m->mode == QViewModeAnswer) ? m->q.answer : m->q.question;
    qview_wrap(text, BODY_MAX_COLS, m->wrap_buf, sizeof(m->wrap_buf), &m->slices);
    if (m->scroll >= m->slices.count) {
        m->scroll = (m->slices.count == 0u) ? 0u
                                            : (uint8_t)(m->slices.count - 1u);
    }
}

static void qview_draw(Canvas *canvas, void *model) {
    const QViewModel *m = model;
    canvas_clear(canvas);

    /* Inverted header bar: filled rectangle, white text */
    canvas_set_color(canvas, ColorBlack);
    canvas_draw_box(canvas, 0, 0, 128, 10);
    canvas_set_color(canvas, ColorWhite);
    canvas_set_font(canvas, FontSecondary);
    const char *cat = category_name(m->q.category_id, tz_locale_get());
    canvas_draw_str_aligned(canvas, 64, 1, AlignCenter, AlignTop, cat);

    /* Body */
    canvas_set_color(canvas, ColorBlack);
    canvas_set_font(canvas, FontSecondary);
    const uint8_t y0 = 13u;
    for (uint8_t i = 0u; i < BODY_VISIBLE_LINES; ++i) {
        const uint8_t idx = (uint8_t)(m->scroll + i);
        if (idx >= m->slices.count) break;
        canvas_draw_str(canvas, 0, (int)(y0 + i * 8u + 7u), m->slices.lines[idx]);
    }

    /* Scroll indicator */
    if (m->scroll + BODY_VISIBLE_LINES < m->slices.count) {
        canvas_draw_str(canvas, 120, 54, "v");
    }

    /* Footer */
    const char *footer = (m->mode == QViewModeQuestion)
                             ? tz_str(TzStrFooterReveal)
                             : tz_str(TzStrFooterNext);
    canvas_draw_str_aligned(canvas, 64, 56, AlignCenter, AlignTop, footer);
}

static bool qview_input(InputEvent *event, void *context) {
    QuestionView *qv = context;
    if (!qv || !qv->on_action || event->type != InputTypeShort) {
        return false;
    }
    QViewAction a;
    switch (event->key) {
    case InputKeyOk:
        a = QViewActionReveal;
        break;
    case InputKeyRight:
        a = QViewActionNext;
        break;
    case InputKeyLeft:
        a = QViewActionPrev;
        break;
    case InputKeyUp:
        a = QViewActionScrollUp;
        break;
    case InputKeyDown:
        a = QViewActionScrollDown;
        break;
    case InputKeyBack:
        a = QViewActionMenu;
        break;
    default:
        return false;
    }
    qv->on_action(qv->ctx, a);
    return true;
}

QuestionView *question_view_alloc(void) {
    QuestionView *qv = malloc(sizeof(QuestionView));
    if (!qv) return NULL;
    *qv = (QuestionView){0};
    qv->view = view_alloc();
    if (!qv->view) {
        free(qv);
        return NULL;
    }
    view_allocate_model(qv->view, ViewModelTypeLockFree, sizeof(QViewModel));
    QViewModel *m = view_get_model(qv->view);
    memset(m, 0, sizeof(*m));
    m->mode = QViewModeQuestion;
    view_commit_model(qv->view, true);
    view_set_context(qv->view, qv);
    view_set_draw_callback(qv->view, qview_draw);
    view_set_input_callback(qv->view, qview_input);
    return qv;
}

void question_view_free(QuestionView *qv) {
    if (!qv) return;
    view_free(qv->view);
    free(qv);
}

View *question_view_get_view(QuestionView *qv) {
    furi_assert(qv);
    return qv->view;
}

void question_view_set_question(QuestionView *qv, const Question *q) {
    furi_assert(qv);
    if (!q) return;
    QViewModel *m = view_get_model(qv->view);
    m->q = *q;
    m->mode = QViewModeQuestion;
    m->scroll = 0u;
    recompute_slices(m);
    view_commit_model(qv->view, true);
}

void question_view_set_mode(QuestionView *qv, QViewMode mode) {
    furi_assert(qv);
    QViewModel *m = view_get_model(qv->view);
    m->mode = mode;
    m->scroll = 0u;
    recompute_slices(m);
    view_commit_model(qv->view, true);
}

void question_view_set_callback(QuestionView *qv, void *ctx,
                                void (*on_action)(void *ctx, QViewAction action)) {
    furi_assert(qv);
    qv->ctx = ctx;
    qv->on_action = on_action;
}

#endif /* TZ_HAVE_FURI */
```

- [ ] **Step 5: Makefile** — `test_question_view_layout` depends on `question_view.o` and `tests/test_question_view_layout.o`.

- [ ] **Step 6: `application.fam`** — add `"src/ui/question_view.c"`.

- [ ] **Step 7: Verify** — full make sequence.

- [ ] **Step 8: Skipped commit.**

---

### Task 10: `app/trivia_zero_app` — composition root (replaces stub)

**Files:**
- Modify: `include/app/trivia_zero_app.h` (no signature change)
- Modify: `src/app/trivia_zero_app.c` (replace stub with real implementation)
- Modify: `Makefile` (no new tests; just keep linter list current)

This is the meat — wires the ViewDispatcher with three Views, manages app state (current question, history buffer, anti-repeat set, current language), routes events from the question view back into the state machine, and persists settings on exit.

This task does **not** add new public symbols beyond the existing `int32_t trivia_zero_app_run(void)` declaration in the header. The header therefore does not need to change.

- [ ] **Step 1: Replace `src/app/trivia_zero_app.c`**

Overwrite the existing stub with:

```c
#include "include/app/trivia_zero_app.h"
#include "include/domain/anti_repeat.h"
#include "include/domain/category.h"
#include "include/domain/history_buffer.h"
#include "include/domain/question_pool.h"
#include "include/i18n/strings.h"
#include "include/infrastructure/pack_reader.h"
#include "include/infrastructure/settings_storage.h"
#include "include/platform/random_port.h"
#include "include/ui/question_view.h"
#include <furi.h>
#include <gui/gui.h>
#include <gui/modules/submenu.h>
#include <gui/view_dispatcher.h>
#include <stdlib.h>

typedef enum {
    AppViewLangSelect = 0,
    AppViewQuestion,
    AppViewMenu,
} AppView;

typedef enum {
    LangSelectIdEs = 0,
    LangSelectIdEn = 1,
} LangSelectId;

typedef enum {
    MenuIdChangeLang = 0,
    MenuIdExit = 1,
} MenuId;

typedef struct {
    Gui *gui;
    ViewDispatcher *vd;

    Submenu *lang_menu;
    Submenu *back_menu;
    QuestionView *qview;

    Question current;
    AntiRepeat seen;
    HistoryBuffer history;
    Settings settings;
    bool exit_requested;
} App;

static void app_show_question_for_id(App *app, uint32_t id) {
    if (pack_get_by_id(id, &app->current)) {
        anti_repeat_mark(&app->seen, id);
        history_buffer_push(&app->history, id);
        question_view_set_question(app->qview, &app->current);
        app->settings.last_id = id;
        app->settings.last_id_valid = true;
    }
}

static void app_show_random(App *app) {
    uint32_t id;
    bool reset_happened;
    if (question_pool_next(pack_count(), &app->seen, tz_rng_u32, NULL, &id,
                           &reset_happened)) {
        app_show_question_for_id(app, id);
    }
}

static void app_open_pack_for_current_lang(App *app) {
    if (!pack_open(app->settings.lang)) {
        app->exit_requested = true;
        view_dispatcher_stop(app->vd);
    }
}

static void on_lang_pick(void *ctx, uint32_t selected);
static void on_menu_pick(void *ctx, uint32_t selected);

static void app_rebuild_back_menu(App *app) {
    submenu_reset(app->back_menu);
    submenu_add_item(app->back_menu, tz_str(TzStrMenuChangeLang),
                     MenuIdChangeLang, on_menu_pick, app);
    submenu_add_item(app->back_menu, tz_str(TzStrMenuExit), MenuIdExit,
                     on_menu_pick, app);
}

static void app_rebuild_lang_menu(App *app) {
    submenu_reset(app->lang_menu);
    submenu_set_header(app->lang_menu, tz_str(TzStrLangPickHeader));
    submenu_add_item(app->lang_menu, tz_str(TzStrLangSpanish), LangSelectIdEs,
                     on_lang_pick, app);
    submenu_add_item(app->lang_menu, tz_str(TzStrLangEnglish), LangSelectIdEn,
                     on_lang_pick, app);
}

static void app_switch(App *app, AppView v) {
    view_dispatcher_switch_to_view(app->vd, (uint32_t)v);
}

static void on_qview_action(void *ctx, QViewAction action) {
    App *app = ctx;
    switch (action) {
    case QViewActionReveal:
        question_view_set_mode(app->qview, QViewModeAnswer);
        break;
    case QViewActionNext:
        app_show_random(app);
        question_view_set_mode(app->qview, QViewModeQuestion);
        break;
    case QViewActionPrev: {
        uint32_t prev_id;
        if (history_buffer_peek_back(&app->history, 1u, &prev_id)) {
            if (pack_get_by_id(prev_id, &app->current)) {
                question_view_set_question(app->qview, &app->current);
            }
        }
        break;
    }
    case QViewActionScrollUp:
        /* The view itself is responsible for scroll state on the model. */
        break;
    case QViewActionScrollDown:
        break;
    case QViewActionMenu:
        app_rebuild_back_menu(app);
        app_switch(app, AppViewMenu);
        break;
    }
}

static void on_lang_pick(void *ctx, uint32_t selected) {
    App *app = ctx;
    app->settings.lang = (selected == LangSelectIdEs) ? LangEs : LangEn;
    tz_locale_set(app->settings.lang);
    settings_save(&app->settings);
    pack_close();
    app_open_pack_for_current_lang(app);
    anti_repeat_reset(&app->seen);
    history_buffer_clear(&app->history);
    app_show_random(app);
    app_switch(app, AppViewQuestion);
}

static void on_menu_pick(void *ctx, uint32_t selected) {
    App *app = ctx;
    if (selected == MenuIdChangeLang) {
        app_rebuild_lang_menu(app);
        app_switch(app, AppViewLangSelect);
    } else {
        app->exit_requested = true;
        view_dispatcher_stop(app->vd);
    }
}

static bool app_nav(void *context) {
    App *app = context;
    /* Hardware BACK from the question view goes through on_qview_action; this
     * path is for the submenus only — fall through to default (close). */
    (void)app;
    return false;
}

int32_t trivia_zero_app_run(void) {
    App *app = malloc(sizeof(App));
    if (!app) return -1;
    *app = (App){0};

    /* Settings */
    app->settings = settings_default();
    settings_load(&app->settings);
    tz_locale_set(app->settings.lang);
    anti_repeat_init(&app->seen);
    history_buffer_init(&app->history);

    /* GUI plumbing */
    app->gui = furi_record_open(RECORD_GUI);
    app->vd = view_dispatcher_alloc();
    view_dispatcher_attach_to_gui(app->vd, app->gui, ViewDispatcherTypeFullscreen);
    view_dispatcher_set_event_callback_context(app->vd, app);
    view_dispatcher_set_navigation_event_callback(app->vd, app_nav);

    /* Lang submenu — callback is attached per-item by app_rebuild_lang_menu */
    app->lang_menu = submenu_alloc();
    app_rebuild_lang_menu(app);
    view_dispatcher_add_view(app->vd, AppViewLangSelect,
                             submenu_get_view(app->lang_menu));

    /* Question view */
    app->qview = question_view_alloc();
    question_view_set_callback(app->qview, app, on_qview_action);
    view_dispatcher_add_view(app->vd, AppViewQuestion,
                             question_view_get_view(app->qview));

    /* Back menu — callback is attached per-item by app_rebuild_back_menu */
    app->back_menu = submenu_alloc();
    app_rebuild_back_menu(app);
    view_dispatcher_add_view(app->vd, AppViewMenu,
                             submenu_get_view(app->back_menu));

    /* First-run: language not set in settings → show language picker.
     * settings_load() returns false on missing/corrupt → defaults are kept,
     * so we use settings_load's return as the "first run" signal. */
    if (!settings_load(&app->settings)) {
        app_switch(app, AppViewLangSelect);
    } else {
        tz_locale_set(app->settings.lang);
        app_open_pack_for_current_lang(app);
        if (app->settings.last_id_valid &&
            app->settings.last_id < pack_count()) {
            app_show_question_for_id(app, app->settings.last_id);
        } else {
            app_show_random(app);
        }
        app_switch(app, AppViewQuestion);
    }

    view_dispatcher_run(app->vd);

    /* Persist on exit */
    settings_save(&app->settings);
    pack_close();

    /* Teardown */
    view_dispatcher_remove_view(app->vd, AppViewLangSelect);
    view_dispatcher_remove_view(app->vd, AppViewQuestion);
    view_dispatcher_remove_view(app->vd, AppViewMenu);
    submenu_free(app->lang_menu);
    submenu_free(app->back_menu);
    question_view_free(app->qview);
    view_dispatcher_free(app->vd);
    furi_record_close(RECORD_GUI);
    free(app);
    return 0;
}
```

- [ ] **Step 2: Verify `make linter` passes** (no host test for app composition).

Run: `make linter`. The composition root references many Furi symbols that cppcheck cannot resolve; the suppressions `--suppress=missingIncludeSystem` and `--suppress=unusedFunction:main.c` already inherited from siblings should keep the run clean. Fix any genuine issues that surface (e.g. an actually-unused local variable).

- [ ] **Step 3: Verify `make format` is a no-op.**

- [ ] **Step 4: Verify `make test` still passes** (the existing domain/parser tests must not have been broken).

- [ ] **Step 5: Skipped commit.**

---

### Task 11: Host integration smoke test

**Files:**
- Create: `tests/test_pack_integration.c`
- Modify: `Makefile`

A host-runnable test that proves the pure parsers work end-to-end against a tiny fixture pack built in-memory. No binary fixtures are committed to the repo — the test constructs the `.idx` blob and the `.tsv` lines as C string literals.

- [ ] **Step 1: Create `tests/test_pack_integration.c`**

```c
#include "include/infrastructure/pack_reader.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

/* Builds the .idx blob in memory matching the .tsv lines below.
 * Returns the number of bytes used in `out`. */
static size_t build_idx_blob(uint8_t *out, size_t cap, const uint32_t *offsets,
                             uint32_t count) {
    const size_t need = 10u + (size_t)count * 4u;
    if (cap < need) return 0u;
    out[0] = 'T';
    out[1] = 'R';
    out[2] = 'V';
    out[3] = 'I';
    out[4] = 0x01;
    out[5] = 0x00;
    out[6] = (uint8_t)(count & 0xFFu);
    out[7] = (uint8_t)((count >> 8) & 0xFFu);
    out[8] = (uint8_t)((count >> 16) & 0xFFu);
    out[9] = (uint8_t)((count >> 24) & 0xFFu);
    for (uint32_t i = 0u; i < count; ++i) {
        const size_t pos = 10u + (size_t)i * 4u;
        out[pos + 0] = (uint8_t)(offsets[i] & 0xFFu);
        out[pos + 1] = (uint8_t)((offsets[i] >> 8) & 0xFFu);
        out[pos + 2] = (uint8_t)((offsets[i] >> 16) & 0xFFu);
        out[pos + 3] = (uint8_t)((offsets[i] >> 24) & 0xFFu);
    }
    return need;
}

int main(void) {
    /* TSV lines */
    const char *tsv =
        "0\t1\tCapital of Spain?\tMadrid\n"
        "1\t6\tFirst World Cup year?\t1930\n"
        "2\t7\tWhat is H2O?\tWater\n";

    /* Compute offsets */
    uint32_t offsets[3];
    offsets[0] = 0u;
    offsets[1] = (uint32_t)(strchr(tsv, '\n') - tsv) + 1u;
    const char *second_nl = strchr(tsv + offsets[1], '\n');
    offsets[2] = (uint32_t)(second_nl - tsv) + 1u;

    uint8_t idx[64];
    const size_t idx_len = build_idx_blob(idx, sizeof(idx), offsets, 3u);
    assert(idx_len == 22u);

    /* Decode header */
    PackIdxHeader h;
    assert(pack_idx_header_decode(idx, idx_len, &h));
    assert(h.version == 1u && h.count == 3u);

    /* Lookup each offset and parse the line at that offset */
    for (uint32_t i = 0u; i < 3u; ++i) {
        uint32_t off;
        assert(pack_idx_offset_at(idx, idx_len, 3u, i, &off));
        const char *line = tsv + off;
        const char *line_end = strchr(line, '\n');
        assert(line_end != NULL);
        Question q;
        assert(pack_parse_tsv_line(line, (size_t)(line_end - line), &q));
        assert(q.id == i);
    }
    return 0;
}
```

- [ ] **Step 2: Wire into Makefile**

```
test_pack_integration: pack_reader.o tests/test_pack_integration.o
	$(CC) $(CFLAGS) -o test_pack_integration pack_reader.o tests/test_pack_integration.o
	./test_pack_integration

tests/test_pack_integration.o: tests/test_pack_integration.c include/infrastructure/pack_reader.h
	$(CC) $(CFLAGS) -c tests/test_pack_integration.c -o tests/test_pack_integration.o
```

Add to `test:` aggregator, `.PHONY`, `clean`, `linter` (the `tests/test_pack_integration.c` file).

- [ ] **Step 3: Verify** — full make sequence.

- [ ] **Step 4: Skipped commit.**

---

### Task 12: Manual hardware verification

**Files:** none — instruction-only task for the user.

Since the Flipper SDK is not installed on this host, the `.fap` cannot be built or run automatically. This task documents the manual verification steps to perform on real hardware before considering Plan 3 complete.

- [ ] **Step 1: Check out the Flipper firmware locally**

```bash
git clone https://github.com/flipperdevices/flipperzero-firmware.git ~/flipperzero-firmware
```

(Or set `FLIPPER_FIRMWARE_PATH` to an existing checkout.)

- [ ] **Step 2: Symlink and build**

From the Trivia Zero repo root:

```bash
export FLIPPER_FIRMWARE_PATH=~/flipperzero-firmware
make prepare
make fap
```

Expected: a `.fap` is written somewhere under `$FLIPPER_FIRMWARE_PATH/build/.../flipper_trivia_zero.fap`.

- [ ] **Step 3: Create a tiny fixture pack on the SD card**

On the Flipper's SD (via qFlipper or `mkdir`+`cp` over the USB-mounted card), create:

```
/ext/apps_data/flipper_trivia_zero/trivia_es.tsv
/ext/apps_data/flipper_trivia_zero/trivia_es.idx
/ext/apps_data/flipper_trivia_zero/trivia_en.tsv
/ext/apps_data/flipper_trivia_zero/trivia_en.idx
```

A 5-question fixture is enough. The exact byte layout of `.idx` is documented in the spec §5.2; a one-off Python helper to build it can live outside this repo for now (Plan 2 will productize this).

- [ ] **Step 4: Install and run the FAP**

Copy `flipper_trivia_zero.fap` to `/ext/apps/Games/`. From the Flipper UI: **Apps → Games → Trivia Zero**.

- [ ] **Step 5: Smoke checks on hardware**

- [ ] First-run language picker appears and accepts a selection.
- [ ] Question screen renders with inverted header showing the category in the chosen language.
- [ ] Pressing OK reveals the answer in place of the question.
- [ ] Pressing right advances to a different random question.
- [ ] Pressing left walks back through up to the last 5 questions seen.
- [ ] Pressing up/down scrolls long question text (use a fixture entry with text > 126 chars).
- [ ] Pressing BACK opens the menu with `Cambiar idioma`/`Salir`.
- [ ] After exit + relaunch, the app reopens directly on the question screen (no language picker) and shows the question that was last visible.
- [ ] Switching language via the menu rebuilds the pool from the other language and resets the seen set.

- [ ] **Step 6: Bug fixes (if any)**

Any defect surfaced in Step 5 is filed as a small targeted task. Common suspects: scroll math (lines/page count), submenu callback signature mismatch (see Task 10 Step 2), Furi storage path typos.

- [ ] **Step 7: No commit needed** (all bug fixes go through the user's normal git flow).

---

## Out of scope for this plan

Explicitly **not** done in Plan 3 (covered elsewhere or deferred):

- The off-Flipper data pipeline that produces real `data/*.tsv`+`.idx` packs — Plan 2.
- Per-category icons (8×8 monochrome) — out of scope for the spec's MVP.
- Cross-session anti-repetition.
- Screenshots and an updated README features section — add after Plan 2 ships real content.
- Internationalization beyond ES/EN.
