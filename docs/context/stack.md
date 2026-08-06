## Project context
Tiny CLI that summarises synthetic `events.csv` logs. Log data covers two
services: `checkout-service` and `cart-api`.

# Stack

| Dimension | Value |
|---|---|
| Language | Python 3.11 |
| Framework | None — plain stdlib CLI (`argparse`, `csv`, `pathlib`) |
| Build tool | None — no `pyproject.toml`; dev dependencies installed directly via `pip install ruff pytest` |
| Test runner | pytest (invoked as `pytest -v` in CI) |
| Architectural constraint | No third-party runtime dependencies; `ruff` and `pytest` are dev-only tools, never imported by `src/` |

## Verified claim

`src/logsum.py:12` defines the output schema as a literal list:

```python
_OUTPUT_HEADERS = ["service", "level", "count", "first_seen", "last_seen"]
```

This matches the columns written to `data/summary.csv` and is the authoritative shape for any downstream consumer of the summary file.
