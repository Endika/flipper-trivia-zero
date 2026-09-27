# Trivia Zero — Data Pipeline

Off-Flipper Python tooling that builds the question packs the FAP consumes.

## Install (host, one-time)

```
cd tools
uv sync --all-groups
```

## Build the pack

From the repo root:

```
make pack
```

This pulls Open Trivia DB (cached locally), applies the blacklist, maps categories, runs translations through the configured backend (stub by default), and writes:

- `data/trivia_es.tsv` + `data/trivia_es.idx`
- `data/trivia_en.tsv` + `data/trivia_en.idx`
- `src/data/embedded_pack_es.c` + `src/data/embedded_pack_en.c` (the pack compiled into the FAP)

Only `TZ_TRANSLATOR=anthropic` writes those committed files. The stub writes the same outputs to `data/_cache/stub_pack/` instead. `make fap` never runs the pipeline; it builds the committed pack.

## Translation backends

| `TZ_TRANSLATOR` | Behavior |
|-----------------|----------|
| unset / `stub` (default) | Deterministic stub — prefixes `[es]`/`[en]` markers. Useful for development; output is valid but not human-grade. Cached to `data/_cache/translations_stub.json`. |
| `anthropic` | Real translation via Anthropic Haiku. Requires `ANTHROPIC_API_KEY` env var. Cached on disk to `data/_cache/translations_anthropic.json` so reruns are free. |

Any other value is an error.

`data/translation_overrides.json` holds hand-reviewed fixes keyed like the caches (`"en->es|<source text>"`). They win over the cache and the backend, so a fix survives any rerun.

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
