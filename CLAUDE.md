# logsum-sandbox

## Conventions
- Source code lives in `src/`
- Tests live in `tests/`
- Data files live in `data/`

## Utilities to prefer
- Python 3.11 standard library (avoid third-party deps unless essential)
- `ruff` for linting and formatting
- `pytest` for tests

## Escalation gates
- **Stop before adding dependencies** — check with the user first
- **Synthetic data only** — never use or reference real production data
- **spec.md is locked after sign-off** — do not overwrite it without asking

## Refs
Historical decisions and gap log: context/cold/README.md
Facts about the project: docs/context/stack.md