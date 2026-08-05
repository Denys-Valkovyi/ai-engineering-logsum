# Provenance Note

**Model:** claude-sonnet-4-6

**Context loaded:**
- `src/logsum.py` (full, 95 lines)
- `tests/test_logsum.py` (full, 584 lines)
- `spec.md` (full, 99 lines)
- `CLAUDE.md` (project conventions)

**Files changed:**

| File | Change |
|---|---|
| `src/logsum.py` | Added `min_count: int = 1` keyword param to `summarise()`; added `if entry["count"] < min_count: continue` guard in write loop; replaced 4-line manual parser in `main()` with 20-line loop that strips `--min-count N` before processing remaining positional args |
| `spec.md` | Updated CLI usage block to show `[--min-count N]`; inserted new §8 `--min-count Filter`; renumbered old §8 → §9 |
| `tests/test_logsum.py` | Added `§8 --min-count filter → TestMinCount` to docstring coverage map; added `TestMinCount` class with 5 tests |

**Plan deviations:** None. The only revision was user-directed: the initial plan proposed switching to `argparse`, which was rejected in favour of extending the existing manual parser. The final implementation followed the revised plan exactly.

**Untested items:** Tests were written but not executed — the test run was interrupted before `pytest` could confirm passing. Items not covered by `TestMinCount` that could be worth adding: invalid non-integer value for `--min-count` (e.g. `--min-count foo`, expected exit 2); `--min-count` with missing value at end of args (e.g. `--min-count` alone, expected exit 2); `--min-count` placed after positional args rather than before.
