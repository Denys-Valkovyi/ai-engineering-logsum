"""Summarise events.csv → summary.csv grouped by (service, level)."""

from __future__ import annotations

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

_DEFAULT_INPUT = Path("data/events.csv")
_DEFAULT_OUTPUT = Path("data/summary.csv")
_OUTPUT_HEADERS = ["service", "level", "count", "first_seen", "last_seen"]


def _parse_ts(raw: str) -> datetime | None:
    """Return a UTC-aware datetime, or None if unparseable."""
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def summarise(input_path: Path, output_path: Path, *, min_count: int = 1) -> int:
    """Read input_path, write grouped summary to output_path.

    Returns count of rows with unparseable timestamps.
    Raises OSError on I/O problems.
    """
    groups: dict[tuple[str, str], dict] = {}
    skipped = 0

    with input_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row_num, row in enumerate(reader, start=2):  # row 1 = header
            service = (row.get("service") or "").strip().lower()
            level_raw = (row.get("level") or "").strip().upper()
            level = level_raw or "UNKNOWN"          # § 4: missing level → UNKNOWN
            ts_raw = (row.get("timestamp") or "").strip()

            ts = _parse_ts(ts_raw)
            if ts is None and ts_raw:               # § 5: malformed, not merely absent
                print(
                    f'WARNING: skipping unparseable timestamp on row {row_num}: "{ts_raw}"',
                    file=sys.stderr,
                )
                skipped += 1

            key = (service, level)
            entry = groups.setdefault(key, {"count": 0, "first_seen": None, "last_seen": None})
            entry["count"] += 1
            if ts is not None:
                entry["first_seen"] = ts if entry["first_seen"] is None else min(entry["first_seen"], ts)
                entry["last_seen"] = ts if entry["last_seen"] is None else max(entry["last_seen"], ts)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_OUTPUT_HEADERS)
        writer.writeheader()
        for (svc, lvl), entry in sorted(groups.items()):
            if entry["count"] < min_count:
                continue
            writer.writerow({
                "service": svc,
                "level": lvl,
                "count": entry["count"],
                "first_seen": entry["first_seen"].isoformat() if entry["first_seen"] else "",
                "last_seen": entry["last_seen"].isoformat() if entry["last_seen"] else "",
            })

    return skipped


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)

    min_count = 1
    positional: list[str] = []
    i = 0
    while i < len(raw):
        if raw[i] == "--min-count":
            if i + 1 >= len(raw):
                print("Usage: python -m src.logsum [--min-count N] [INPUT [OUTPUT]]", file=sys.stderr)
                return 2
            try:
                min_count = int(raw[i + 1])
            except ValueError:
                print("Usage: python -m src.logsum [--min-count N] [INPUT [OUTPUT]]", file=sys.stderr)
                return 2
            i += 2
        else:
            positional.append(raw[i])
            i += 1

    if len(positional) > 2:
        print("Usage: python -m src.logsum [--min-count N] [INPUT [OUTPUT]]", file=sys.stderr)
        return 2
    input_path = Path(positional[0]) if len(positional) >= 1 else _DEFAULT_INPUT
    output_path = Path(positional[1]) if len(positional) >= 2 else _DEFAULT_OUTPUT
    try:
        skipped = summarise(input_path, output_path, min_count=min_count)
    except OSError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if skipped:
        print(f"Skipped {skipped} row(s) with unparseable timestamps.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
