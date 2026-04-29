# Trivia Zero — Plan 1: Repository Scaffolding

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bootstrap the `flipper-trivia-zero` repository as a production-ready FAP skeleton — minimal-but-complete app entry point, full release-please + dependabot + CI/release workflows, Makefile with `format`/`linter`/`test` targets, and a passing smoke test — matching the conventions used by `flipper-avocado-zero` and `flipper-impostor-game` exactly.

**Architecture:** Replicate the sibling scaffolding pattern. Thin `main.c` calls into `src/app/trivia_zero_app.c` (stub returning 0). Host-only unit tests compiled with `gcc -std=c11`, no test framework — each test is its own `int main(void)` calling `assert`. `cppcheck` for static analysis, `clang-format` for formatting (LLVM base, IndentWidth 4, ColumnLimit 100). `release-please` (`release-type: simple`) tracks `version.h` and `application.fam`. Releases trigger a `ufbt`-built `.fap` upload to the GitHub Release.

**Tech Stack:** C11, gcc (host), cppcheck, clang-format, GitHub Actions (`actions/checkout@v6`), `googleapis/release-please-action@v4`, `flipperdevices/flipperzero-ufbt-action@v0.1`.

**Reference projects (read-only siblings to mirror when in doubt):**
- `/home/endikaiglesias/workspace/flipper/flipper-avocado-zero/`
- `/home/endikaiglesias/workspace/flipper/flipper-impostor-game/`

**Prerequisites:**
- `git init` has been run in the repo root by the user.
- `BRAINSTORM.md` and `docs/superpowers/specs/2026-04-28-trivia-zero-design.md` are already tracked in git.
- The repo root is `/home/endikaiglesias/workspace/flipper-trivia-zero/`. All paths in this plan are relative to that root.

---

### Task 1: Repository skeleton — docs and format config

**Files:**
- Create: `.gitignore`
- Create: `LICENSE`
- Create: `README.md`
- Create: `.clang-format`

- [ ] **Step 1: Create `.gitignore`**

```
# Host unit tests (make test)
*.o
tests/*.o
test_version

# ufbt / GitHub Actions release build
dist/
.ufbt/

# OS
.DS_Store
Thumbs.db

# Editor / swap
*.swp
*~
.idea/
```

- [ ] **Step 2: Create `LICENSE`**

Copy the exact 13-line stub used by `flipper-avocado-zero` and `flipper-impostor-game` verbatim:

```
                    GNU GENERAL PUBLIC LICENSE
                       Version 3, 29 June 2007

 Copyright (C) 2007 Free Software Foundation, Inc. <https://fsf.org/>
 Everyone is permitted to copy and distribute verbatim copies of this license
 document, but changing it is not allowed.

                            Preamble

  The GNU General Public License is a free, copyleft license for software
and other kinds of works.

  ... [Text omitted for brevity - Standard GPLv3] ...
```

(This is intentionally a stub — the siblings do the same. If a full GPLv3 text is needed later, that is a separate, explicit decision rolled out across all sibling FAPs together.)

- [ ] **Step 3: Create `README.md`**

```markdown
# Trivia Zero

**Flipper Zero** external application (**FAP**). Install it on the **microSD** of your Flipper and run it from **Apps → Games → Trivia Zero**.

Flashcard-style trivia: a question is displayed on screen, press OK to reveal the answer, press right to advance to the next random question. Two languages (Spanish and English) shipped by default. No score, no timer — just variety.

## Features

- **Bilingual** UI and content (ES + EN), language selection persisted on SD.
- **6 + 1 categories** (the classic 6 Trivial Pursuit categories plus "Cultura General"), shown as an inverted-video header above each question.
- **Random pool** with in-session anti-repetition.
- **Resume on relaunch** — the app remembers the last question you saw.

## Install on Flipper Zero

1. Build or download the `.fap` for this app.
2. Copy `flipper_trivia_zero.fap` to the SD card (e.g. `apps/Games/`).
3. On the Flipper: **Apps → Games → Trivia Zero**.

## Build

- **Host tests**: `make test` (gcc, no Flipper SDK).
- **FAP**: set `FLIPPER_FIRMWARE_PATH` to your firmware checkout, then `make prepare` and `make fap`.

## Requirements

- [flipperzero-firmware](https://github.com/flipperdevices/flipperzero-firmware) and `./fbt` for device builds.
```

- [ ] **Step 4: Create `.clang-format`**

```yaml
BasedOnStyle: LLVM
IndentWidth: 4
ColumnLimit: 100
AllowShortFunctionsOnASingleLine: None
IndentCaseLabels: true
```

- [ ] **Step 5: Verify all four files exist and are non-empty**

Run: `ls -la .gitignore LICENSE README.md .clang-format && wc -l .gitignore LICENSE README.md .clang-format`
Expected: all four exist with non-zero line counts.

- [ ] **Step 6: Commit**

```bash
git add .gitignore LICENSE README.md .clang-format
git commit -m "chore: bootstrap repository docs and format config"
```

---

### Task 2: Version header, Makefile, and smoke test (TDD)

**Files:**
- Create: `version.h`
- Create: `tests/test_version.c`
- Create: `Makefile`

This task uses the TDD cycle: write the failing test, prove it fails, write the version header, prove the test passes, then add the Makefile that wraps everything.

- [ ] **Step 1: Write the failing test**

Create `tests/test_version.c`:

```c
#include "version.h"
#include <assert.h>
#include <string.h>

int main(void) {
    /* APP_VERSION must be defined and equal "0.1.0" at scaffolding time. */
    assert(strcmp(APP_VERSION, "0.1.0") == 0);
    return 0;
}
```

- [ ] **Step 2: Run the test directly with gcc and verify it fails**

Run: `gcc -Wall -Wextra -std=c11 -I. tests/test_version.c -o test_version`
Expected: compile error — `version.h: No such file or directory`.

- [ ] **Step 3: Create `version.h`**

```c
#pragma once

#define APP_VERSION "0.1.0" // x-release-please-version
```

- [ ] **Step 4: Recompile and run the test, verify it passes**

Run: `gcc -Wall -Wextra -std=c11 -I. tests/test_version.c -o test_version && ./test_version && echo OK`
Expected: prints `OK` and exits 0.

- [ ] **Step 5: Create `Makefile`**

```makefile
# Host tests + FAP via fbt. Symlink under applications_user (matches apps_data path).
PROJECT_NAME = trivia_zero

FAP_APPID = flipper_trivia_zero

FLIPPER_FIRMWARE_PATH ?= /home/<YOUR_PATH>/flipperzero-firmware
PWD = $(shell pwd)

CC = gcc
CFLAGS = -Wall -Wextra -std=c11 -I.

.PHONY: all help test test_version prepare fap clean clean_firmware format

all: test

help:
	@echo "Targets for $(PROJECT_NAME):"
	@echo "  make test           - Host unit tests"
	@echo "  make prepare        - Symlink app into firmware applications_user"
	@echo "  make fap            - Clean firmware build + compile .fap"
	@echo "  make format         - clang-format"
	@echo "  make clean          - Remove local objects"
	@echo "  make clean_firmware - rm firmware build dir"

FORMAT_FILES := $(shell git ls-files '*.c' '*.h' 2>/dev/null)
ifeq ($(strip $(FORMAT_FILES)),)
FORMAT_FILES := $(shell find . -type f \( -name '*.c' -o -name '*.h' \) ! -path './.git/*' | sort)
endif

format:
	clang-format -i $(FORMAT_FILES)

test: test_version

test_version: tests/test_version.o
	$(CC) $(CFLAGS) -o test_version tests/test_version.o
	./test_version

tests/test_version.o: tests/test_version.c version.h
	$(CC) $(CFLAGS) -c tests/test_version.c -o tests/test_version.o

prepare:
	@if [ -d "$(FLIPPER_FIRMWARE_PATH)" ]; then \
		mkdir -p $(FLIPPER_FIRMWARE_PATH)/applications_user; \
		ln -sfn $(PWD) $(FLIPPER_FIRMWARE_PATH)/applications_user/$(PROJECT_NAME); \
		echo "Linked to $(FLIPPER_FIRMWARE_PATH)/applications_user/$(PROJECT_NAME)"; \
	else \
		echo "Firmware not found at $(FLIPPER_FIRMWARE_PATH)"; \
	fi

clean_firmware:
	@if [ -d "$(FLIPPER_FIRMWARE_PATH)/build" ]; then \
		rm -rf $(FLIPPER_FIRMWARE_PATH)/build; \
	fi

fap: prepare clean_firmware clean
	@if [ -d "$(FLIPPER_FIRMWARE_PATH)" ]; then \
		cd $(FLIPPER_FIRMWARE_PATH) && ./fbt fap_$(FAP_APPID); \
	fi

clean:
	rm -f *.o tests/*.o test_version
```

The `linter` target is added in Task 3, when there are real source files to lint.

- [ ] **Step 6: Verify `make test` passes**

Run: `make clean && make test`
Expected: compilation succeeds, `./test_version` runs and exits 0.

- [ ] **Step 7: Verify `make format` is a no-op (no diffs)**

Run: `make format && git diff --exit-code`
Expected: exits 0 (no formatting changes needed).

- [ ] **Step 8: Commit**

```bash
git add version.h tests/test_version.c Makefile
git commit -m "feat: add version header, Makefile, and smoke test"
```

---

### Task 3: FAP entry point and application manifest

**Files:**
- Create: `include/app/trivia_zero_app.h`
- Create: `src/app/trivia_zero_app.c`
- Create: `main.c`
- Create: `application.fam`
- Modify: `Makefile` (add `linter` target)

The empty app stub returns `0` from `trivia_zero_app_run`. Real behavior is added in Plan 3.

- [ ] **Step 1: Create `include/app/trivia_zero_app.h`**

```c
#pragma once

#include <stdint.h>

int32_t trivia_zero_app_run(void);
```

- [ ] **Step 2: Create `src/app/trivia_zero_app.c`**

```c
#include "include/app/trivia_zero_app.h"

int32_t trivia_zero_app_run(void) {
    /* Stub. Real implementation lives in Plan 3 (the FAP itself). */
    return 0;
}
```

- [ ] **Step 3: Create `main.c`**

```c
#include "include/app/trivia_zero_app.h"
#include <furi.h>

int32_t trivia_zero_app(void *p) {
    UNUSED(p);
    return trivia_zero_app_run();
}
```

- [ ] **Step 4: Create `application.fam`**

```python
App(
    appid="flipper_trivia_zero",
    name="Trivia Zero",
    apptype=FlipperAppType.EXTERNAL,
    sources=[
        "main.c",
        "src/app/trivia_zero_app.c",
    ],
    entry_point="trivia_zero_app",
    stack_size=4 * 1024,
    fap_version="0.1.0",  # x-release-please-version
    fap_icon="icons/icon.icon",
    fap_category="Games",
    fap_author="Endika",
    fap_description="Bilingual flashcard trivia: random questions with reveal-on-OK, two languages shipped.",
)
```

- [ ] **Step 5: Add the `linter` target to `Makefile`**

Edit `Makefile`:

1. Update the `.PHONY` line to include `linter`:

   ```makefile
   .PHONY: all help test test_version prepare fap clean clean_firmware format linter
   ```

2. Add a help line for `linter` in the `help` block. Insert immediately after the `make format` line:

   ```makefile
   	@echo "  make linter         - cppcheck"
   ```

3. Add the `linter` target itself, immediately after the `format:` target block:

   ```makefile
   linter:
   	cppcheck --enable=all --inline-suppr -I. \
   		--suppress=missingIncludeSystem \
   		--suppress=unusedFunction:main.c \
   		src/app/trivia_zero_app.c main.c \
   		tests/test_version.c
   ```

- [ ] **Step 6: Verify `make linter` runs cleanly**

Run: `make linter`
Expected: cppcheck completes without errors. Do not blanket-suppress any warning that surfaces — investigate and fix.

- [ ] **Step 7: Verify `make format` is still a no-op**

Run: `make format && git diff --exit-code`
Expected: exits 0.

- [ ] **Step 8: Verify `make test` still passes**

Run: `make clean && make test`
Expected: `test_version` runs, exit code 0.

- [ ] **Step 9: Commit**

```bash
git add include/app/trivia_zero_app.h src/app/trivia_zero_app.c main.c application.fam Makefile
git commit -m "feat: add FAP entry point stub and Flipper manifest"
```

---

### Task 4: Icon placeholder

**Files:**
- Create: `icons/icon.icon` (placeholder copied from a sibling)

The `.icon` format is a Flipper-specific binary asset (compiled by `fbt` at build time from a small `.png`). For scaffolding purposes a working icon from a sibling is sufficient — the user can swap it for a Trivia-specific icon in a later, dedicated task.

- [ ] **Step 1: Copy the icon from a sibling FAP**

Run: `mkdir -p icons && cp /home/endikaiglesias/workspace/flipper/flipper-avocado-zero/icons/icon.icon icons/icon.icon`
Expected: file copied.

- [ ] **Step 2: Verify the file exists and is non-empty**

Run: `ls -la icons/icon.icon && wc -c icons/icon.icon`
Expected: file exists, byte count > 0.

- [ ] **Step 3: Commit**

```bash
git add icons/icon.icon
git commit -m "chore: add placeholder icon copied from flipper-avocado-zero"
```

---

### Task 5: release-please configuration and initial CHANGELOG

**Files:**
- Create: `release-please-config.json`
- Create: `.release-please-manifest.json`
- Create: `CHANGELOG.md`

`release-please` will manage `CHANGELOG.md` automatically going forward; we just commit an empty seed.

- [ ] **Step 1: Create `release-please-config.json`**

```json
{
  "packages": {
    ".": {
      "release-type": "simple",
      "bump-minor-pre-major": true,
      "bump-patch-for-minor-pre-major": true,
      "extra-files": [
        "version.h",
        {
          "type": "generic",
          "path": "application.fam"
        }
      ]
    }
  }
}
```

- [ ] **Step 2: Create `.release-please-manifest.json`**

```json
{
  ".": "0.1.0"
}
```

- [ ] **Step 3: Create `CHANGELOG.md`**

```markdown
# Changelog
```

(Empty seed. release-please will append entries here on each release.)

- [ ] **Step 4: Verify the version is `0.1.0` in all three places**

Run: `grep -E '0\.1\.0' version.h .release-please-manifest.json application.fam`
Expected: each file contains `0.1.0`.

- [ ] **Step 5: Commit**

```bash
git add release-please-config.json .release-please-manifest.json CHANGELOG.md
git commit -m "chore: configure release-please for semver and changelog automation"
```

---

### Task 6: Dependabot and PR template

**Files:**
- Create: `.github/dependabot.yml`
- Create: `.github/PULL_REQUEST_TEMPLATE.md`

- [ ] **Step 1: Create `.github/dependabot.yml`**

```yaml
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

(Python dependency tracking is added in Plan 2 when `tools/` is created.)

- [ ] **Step 2: Create `.github/PULL_REQUEST_TEMPLATE.md`**

```markdown
## Description
Please include a summary of the change and which issue is fixed.

## Type of change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)

## How Has This Been Tested?
Please describe the tests that you ran to verify your changes.
- [ ] Ran `make test`
- [ ] Ran `make linter`
- [ ] Compiled with `make fap`

## Checklist:
- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] My changes generate no new warnings
```

- [ ] **Step 3: Commit**

```bash
git add .github/dependabot.yml .github/PULL_REQUEST_TEMPLATE.md
git commit -m "ci: add dependabot config and PR template"
```

---

### Task 7: CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create `.github/workflows/ci.yml`**

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
```

- [ ] **Step 2: Sanity-check the YAML parses**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('ok')"`
Expected: prints `ok`. (If `pyyaml` is unavailable on the host, skip this step — GitHub will surface YAML errors when the workflow runs for the first time.)

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add CI workflow with linter, format check, and tests"
```

---

### Task 8: Release workflow

**Files:**
- Create: `.github/workflows/release.yml`

- [ ] **Step 1: Create `.github/workflows/release.yml`**

```yaml
# Release assets are only built when release-please opens a GitHub Release
# (release_created == true). Pushes to main that are not a release do not upload a .fap.

name: Release

on:
  push:
    branches: [main]

permissions:
  contents: write
  pull-requests: write

jobs:
  ci:
    uses: ./.github/workflows/ci.yml

  release:
    needs: ci
    runs-on: ubuntu-latest
    steps:
      - uses: googleapis/release-please-action@v4
        id: release
        with:
          config-file: release-please-config.json
          manifest-file: .release-please-manifest.json

      - uses: actions/checkout@v6
        if: ${{ steps.release.outputs.release_created }}

      - name: Build FAP
        id: ufbt
        if: ${{ steps.release.outputs.release_created }}
        uses: flipperdevices/flipperzero-ufbt-action@v0.1
        with:
          sdk-channel: dev

      - name: Upload FAP to release
        if: ${{ steps.release.outputs.release_created }}
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          shopt -s nullglob
          faps=(dist/*.fap)
          if [ ${#faps[@]} -eq 0 ]; then
            echo "::error::No .fap in dist/. ufbt output was:"
            echo "${{ steps.ufbt.outputs.fap-artifacts }}"
            ls -la dist/ 2>&1 || true
            find . -name '*.fap' -print 2>/dev/null || true
            exit 1
          fi
          gh release upload "${{ steps.release.outputs.tag_name }}" "${faps[@]}"
```

- [ ] **Step 2: Sanity-check the YAML parses**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml')); print('ok')"`
Expected: prints `ok`.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: add release workflow with release-please and ufbt FAP build"
```

---

### Task 9: End-to-end local verification

**Files:** none — this task only runs commands.

A final sanity check across all the make targets and the directory structure.

- [ ] **Step 1: Confirm `make help` lists all expected targets**

Run: `make help`
Expected output includes lines for `make test`, `make prepare`, `make fap`, `make format`, `make linter`, `make clean`, `make clean_firmware`.

- [ ] **Step 2: Confirm `make clean` leaves the tree clean**

Run: `make clean && git status --short`
Expected: `git status --short` prints nothing.

- [ ] **Step 3: Confirm `make test` passes**

Run: `make test`
Expected: `test_version` compiles and runs, exit code 0.

- [ ] **Step 4: Confirm `make linter` passes**

Run: `make linter`
Expected: cppcheck completes without errors.

- [ ] **Step 5: Confirm `make format` is a no-op**

Run: `make format && git diff --exit-code`
Expected: exits 0.

- [ ] **Step 6: Confirm the directory inventory matches the spec**

Run:
```bash
find . -type f \
  -not -path './.git/*' \
  -not -name '*.o' \
  -not -name 'test_version' \
  | sort
```

Expected output (set, order may vary slightly):

```
./.clang-format
./.github/PULL_REQUEST_TEMPLATE.md
./.github/dependabot.yml
./.github/workflows/ci.yml
./.github/workflows/release.yml
./.gitignore
./.release-please-manifest.json
./BRAINSTORM.md
./CHANGELOG.md
./LICENSE
./Makefile
./README.md
./application.fam
./docs/superpowers/plans/2026-04-28-trivia-zero-plan-1-scaffolding.md
./docs/superpowers/specs/2026-04-28-trivia-zero-design.md
./icons/icon.icon
./include/app/trivia_zero_app.h
./main.c
./release-please-config.json
./src/app/trivia_zero_app.c
./tests/test_version.c
./version.h
```

- [ ] **Step 7: No commit (read-only verification task)**

If any step above fails, stop, fix the issue, and re-run from Step 1.

---

## Out of scope for this plan

Explicitly **not** done in Plan 1 (covered later):

- Real domain code (`src/domain/`, `src/infrastructure/`, `src/platform/`, `src/i18n/`, `src/ui/`) — Plan 3.
- The off-Flipper Python pipeline (`tools/`) and the `data/` content — Plan 2. Dependabot will be extended at that point to watch Python deps.
- Building the `.fap` end-to-end on the user's machine (`make fap` requires the firmware checkout). The release workflow exercises this via `ufbt` once a release is cut.
- A real Trivia Zero icon. The placeholder is copied from `flipper-avocado-zero`.
