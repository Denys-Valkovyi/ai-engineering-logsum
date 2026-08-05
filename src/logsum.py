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


def summarise(input_path: Path, output_path: Path) -> int:
    """Read input_path, write grouped summary to output_path.

    Returns count of rows with unparseable timestamps.
    Raises OSError on I/O problems.
    """
    groups: dict[tuple[str, str], list] = {}
    skipped = 0

    with input_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row_num, row in enumerate(reader, start=2):  # row 1 = header
            service = (row.get("service") or "").strip().lower();
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
            if key not in groups:
                groups[key] = [0, None, None]       # count, first_seen, last_seen
            groups[key][0] += 1
            if ts is not None:
                first, last = groups[key][1], groups[key][2]
                groups[key][1] = ts if first is None else min(first, ts)
                groups[key][2] = ts if last is None else max(last, ts)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_OUTPUT_HEADERS)
        writer.writeheader()
        for (svc, lvl), (cnt, first, last) in sorted(groups.items()):
            writer.writerow({
                "service": svc,
                "level": lvl,
                "count": cnt,
                "first_seen": first.isoformat() if first else "",
                "last_seen": last.isoformat() if last else "",
            })

    return skipped


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) > 2:
        print("Usage: python -m src.logsum [INPUT [OUTPUT]]", file=sys.stderr)
        return 2
    input_path = Path(args[0]) if len(args) >= 1 else _DEFAULT_INPUT
    output_path = Path(args[1]) if len(args) >= 2 else _DEFAULT_OUTPUT
    try:
        skipped = summarise(input_path, output_path)
    except OSError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if skipped:
        print(f"Skipped {skipped} row(s) with unparseable timestamps.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
