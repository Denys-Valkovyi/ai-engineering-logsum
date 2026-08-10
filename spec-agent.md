# logsum – Specification (agent replay)

## Purpose

Summarise a structured event log (`events.csv`) into an aggregated summary file
(`summary.csv`). Each row in the output represents one unique `(service, level)` group
with occurrence counts and time boundaries.

## Input

CSV file with the following columns (in any order):

| Column      | Type   | Required |
|-------------|--------|----------|
| `timestamp` | string | yes      |
| `level`     | string | no       |
| `service`   | string | yes      |
| `message`   | string | no       |

## Output

CSV file with one row per `(service, level)` group, sorted by `service` then `level`:

| Column       | Type    | Description                              |
|--------------|---------|------------------------------------------|
| `service`    | string  | Normalised service name                  |
| `level`      | string  | Normalised log level                     |
| `count`      | integer | Number of matching events                |
| `first_seen` | string  | Earliest timestamp in the group          |
| `last_seen`  | string  | Latest timestamp in the group            |

## Normalisation

| Field     | Rule                                                         |
|-----------|--------------------------------------------------------------|
| `service` | Strip surrounding whitespace; convert to lowercase           |
| `level`   | Strip surrounding whitespace; convert to uppercase           |
| `level`   | If blank or column absent: set to `UNKNOWN`                  |

## Edge cases

| Scenario                                          | Behaviour                                               |
|---------------------------------------------------|---------------------------------------------------------|
| Malformed timestamp                               | Include row; use raw string for first_seen / last_seen  |
| Empty input file (0 bytes)                        | Write output with headers only; exit 0                  |
| Input has headers but no data rows                | Write output with headers only; exit 0                  |
| `timestamp` or `service` column missing from row  | Skip row; emit WARNING to stderr                        |
| No rows survive filters                           | Write output with headers only; exit 0                  |

## CLI

```
python -m src.logsum_agent [INPUT [OUTPUT]] [--min-count N]
```

| Argument      | Default            | Description                                 |
|---------------|--------------------|---------------------------------------------|
| `INPUT`       | `data/events.csv`  | Path to input CSV                           |
| `OUTPUT`      | `data/summary.csv` | Path to output CSV (parent dirs created)    |
| `--min-count` | `0`                | Exclude groups with count strictly below N  |

Exit code `0` on success, `1` if the input file cannot be opened.
