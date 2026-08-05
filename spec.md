# logsum — CLI Specification

## 1. Group Key

Each output row represents a unique `(service, level)` pair after normalisation.
Both fields are derived from the input CSV columns of the same names.

## 2. Normalisation Rules

| Field | Rule |
|---|---|
| `service` | Strip leading/trailing whitespace; convert to **lowercase** |
| `level` | Strip leading/trailing whitespace; convert to **UPPERCASE** |
| `timestamp` | Parse as ISO-8601; timezone-naive values are treated as UTC |

Normalisation is applied before grouping, so `INFO`, `info`, and `  Info  ` all map
to the same group key.

## 3. Aggregated Output Columns

`summary.csv` contains exactly five columns in this order:

| Column | Type | Description |
|---|---|---|
| `service` | string | Normalised service name |
| `level` | string | Normalised log level |
| `count` | integer | Number of input rows in this group |
| `first_seen` | ISO-8601 string | Earliest timestamp in the group (UTC) |
| `last_seen` | ISO-8601 string | Latest timestamp in the group (UTC) |

`first_seen`/`last_seen` are derived only from rows whose `timestamp` parsed
successfully (see §5).

## 4. Missing Level Behaviour

A row with a blank or absent `level` field is **not dropped**. It is assigned the
literal level string `UNKNOWN` and grouped accordingly. This avoids silent data
loss and makes coverage gaps visible in the output.

## 5. Malformed Timestamp Behaviour

A row whose `timestamp` cannot be parsed as ISO-8601:

- Is **included** in its `(service, level)` group and increments `count`.
- Does **not** contribute to `first_seen` or `last_seen` for that group.
- Causes exactly one warning line on **stderr** per bad row:
  `WARNING: skipping unparseable timestamp on row <n>: "<raw_value>"`
- After processing, a single summary line is printed to stderr:
  `Skipped <k> row(s) with unparseable timestamps.` (omitted when `k == 0`).

## 6. Empty Input Behaviour

If `events.csv` exists but contains zero data rows (headers only, or a completely
empty file), the tool writes `summary.csv` with the five header columns and zero
data rows, then exits with code **0**. This is not treated as an error.

## 7. CLI Interface and Exit Codes

```
Usage: python -m src.logsum [--min-count N] [INPUT [OUTPUT]]

Arguments:
  INPUT   Path to input CSV   [default: data/events.csv]
  OUTPUT  Path to output CSV  [default: data/summary.csv]

Options:
  --min-count N  Only output groups with count >= N  [default: 1]
```

Both arguments are optional positional args. Supplying only `INPUT` uses the
default output path. Supplying neither uses both defaults.

| Exit code | Meaning |
|---|---|
| `0` | Success (output written, even if empty) |
| `1` | I/O error (input not found, unreadable, output not writable) |
| `2` | Bad arguments (too many positional args) |

All user-facing error messages go to **stderr**; normal progress output (if any)
also goes to stderr. Only the CSV content itself is written to the output file.

If the output directory does not exist, the tool creates it (including any
intermediate directories). This is not treated as an error.

## 8. --min-count Filter

When `--min-count N` is supplied, only groups whose `count` is **≥ N** are
written to the output. Groups below the threshold are silently omitted.

| N | Effect |
|---|---|
| omitted (default) | All groups are written (equivalent to `--min-count 1`) |
| `1` | All groups are written |
| `> 1` | Groups with `count < N` are excluded from output |

This filter is applied after all grouping and aggregation; timestamps and counts
are computed over the full input before any group is dropped.

## 9. Explicit Out-of-Scope Items

The following are **not** part of this specification and must not be implemented
without a separate spec:

- Analysis, deduplication, or search of the `message` field
- Filtering rows by service, level, or time range
- Real-time / tail mode for streaming logs
- Output formats other than CSV (JSON, Parquet, etc.)
- Third-party library dependencies (stdlib only)
- Support for input formats other than UTF-8 CSV
- Database or remote storage output targets

## Signed off
03-08-2026 Denys V 

## Implementation notes
AI added `src/__init__.py` unprompted â needed to make `src` a package so `python -m src.logsum` works.