# Repository Q&A

## Files read

- `src/logsum.py`
- `spec.md`
- `tests/test_logsum.py`
- `tests/conftest.py`
- `tests/fixtures/missing_level.csv`
- `.github/workflows/ci.yml`

---

## Where is the grouping rule?

The group key is the two-field tuple `(service, level)`. There are no time windows or buckets.

**Normalisation** happens before the key is built (`src/logsum.py:40-42`):

```python
service = (row.get("service") or "").strip().lower()
level_raw = (row.get("level") or "").strip().upper()
level = level_raw or "UNKNOWN"
```

- `service`: stripped of whitespace and lowercased.
- `level`: stripped and uppercased; blank/absent falls back to `"UNKNOWN"`.

**Key construction** (`src/logsum.py:53`):

```python
key = (service, level)
```

**Accumulation** (`src/logsum.py:54-58`): each key gets a `count`, `first_seen`, and
`last_seen`. The timestamp is used only for those two tracking fields — never as
part of the key.

**Output sort** (`src/logsum.py:64`): groups are written in alphabetical order by
`(service, level)`.

The spec confirms the design at `spec.md:5` ("each output row represents a unique
`(service, level)` pair") and `spec.md:9-16` (normalisation table).

Test coverage: `tests/test_logsum.py` — `TestGrouping` (lines 88-165) and
`TestNormalisation` (lines 172-250).

---

## How is missing level handled?

A row with a blank or absent `level` field is **never dropped**. It is assigned the
literal string `"UNKNOWN"` and grouped with other `UNKNOWN` rows.

**Implementation** (`src/logsum.py:41-42`):

```python
level_raw = (row.get("level") or "").strip().upper()
level = level_raw or "UNKNOWN"
```

- `row.get("level") or ""` treats a missing column (`None`) the same as `""`.
- After strip + uppercase, if the result is still empty (blank field, whitespace-only,
  or absent column) `level` is set to `"UNKNOWN"`.

The spec documents this explicitly at `spec.md:35-38`:
> A row with a blank or absent `level` field is not dropped. It is assigned the
> literal level string UNKNOWN and grouped accordingly. This avoids silent data loss
> and makes coverage gaps visible in the output.

The fixture `tests/fixtures/missing_level.csv` has two blank-level rows and one
`INFO` row; they produce two separate groups (`UNKNOWN` count=2, `INFO` count=1).

Test coverage: `tests/test_logsum.py` — `TestMissingLevel` (lines 257-314), five
tests covering blank level, whitespace-only level, row not dropped, distinct groups,
and the fixture end-to-end.

---

## How do I run tests and CI locally?

There is no `Makefile`, `tox.ini`, or `pyproject.toml`. The canonical recipe is in
`.github/workflows/ci.yml:19-25`:

```sh
pip install ruff pytest
ruff check .
pytest -v
```

Run all three commands from the project root. CI runs these on `ubuntu-latest` with
Python 3.11 on every push and pull request.

**Note:** `pytest` must be run from the project root. `tests/conftest.py:13-18` invokes
`python -m src.logsum` with `cwd=PROJECT_ROOT`; tests that call `subprocess.run`
directly set `PYTHONPATH` explicitly (`tests/test_logsum.py:601, 623`).

### Unverified

- There is no `requirements.txt` or lock file; `ruff` and `pytest` version pins used
  in CI are not recorded anywhere in the repo.
- No Windows-specific run instructions exist; the CI workflow targets `ubuntu-latest`
  only.

## Verification
citations are checked 
