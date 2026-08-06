# Provenance – logsum agent replay

## Replay date

2026-08-05

## Source of intended behaviour

`spec.md` on branch `replay/logsum` (intended behaviour only — no code was read or copied).

## What was replayed

A clean re-implementation of the full logsum feature lifecycle from specification through CI,
using only brand-new files. No existing files were read or modified.

## Files created

| File | Purpose |
|------|---------|
| `spec-agent.md` | Fresh specification document |
| `src/normalise_agent.py` | Extracted normalisation utilities (refactor) |
| `src/logsum_agent.py` | Main CLI implementation |
| `tests/fixtures_agent/basic_agent.csv` | Happy-path fixture |
| `tests/fixtures_agent/normalisation_agent.csv` | Mixed-case / whitespace fixture |
| `tests/fixtures_agent/malformed_ts_agent.csv` | Malformed timestamp fixture |
| `tests/fixtures_agent/empty_agent.csv` | Empty file fixture |
| `tests/fixtures_agent/headers_only_agent.csv` | Headers-only fixture |
| `tests/fixtures_agent/missing_level_agent.csv` | Absent level column fixture |
| `tests/fixtures_agent/missing_col_agent.csv` | Wrong column names fixture |
| `tests/test_logsum_agent.py` | Full pytest test suite |
| `.github/workflows/ci-agent.yml` | CI workflow (lint + format + test) |
| `provenance-agent.md` | This file |

## What was intentionally excluded

- No third-party runtime dependencies (stdlib only)
- No mutation of existing source files or test fixtures
- No reference to synthetic `data/events.csv` beyond its schema
