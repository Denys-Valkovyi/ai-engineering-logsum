import argparse
import csv
import sys
from pathlib import Path

from src.normalise_agent import normalise_level, normalise_service

_OUTPUT_FIELDS = ["service", "level", "count", "first_seen", "last_seen"]
_DEFAULT_INPUT = "data/events.csv"
_DEFAULT_OUTPUT = "data/summary.csv"


def parse_rows(path: str):
    """Read input CSV and yield normalised row dicts; skip rows missing required columns."""
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for i, row in enumerate(reader, start=2):
            if "timestamp" not in row or "service" not in row:
                print(
                    f"WARNING: row {i} missing required column(s); skipping",
                    file=sys.stderr,
                )
                continue
            yield {
                "timestamp": row["timestamp"],
                "service": normalise_service(row["service"]),
                "normalised_level": normalise_level(row.get("level", "")),
            }


def aggregate(rows, min_count: int = 0) -> list[dict]:
    """Group rows by (service, level) and compute count, first_seen, last_seen."""
    groups: dict[tuple[str, str], dict] = {}
    for row in rows:
        key = (row["service"], row["normalised_level"])
        ts = row["timestamp"]
        if key not in groups:
            groups[key] = {"count": 0, "first_seen": ts, "last_seen": ts}
        g = groups[key]
        g["count"] += 1
        g["first_seen"] = min(g["first_seen"], ts)
        g["last_seen"] = max(g["last_seen"], ts)

    result = []
    for (service, level), g in sorted(groups.items()):
        if g["count"] >= min_count:
            result.append(
                {
                    "service": service,
                    "level": level,
                    "count": g["count"],
                    "first_seen": g["first_seen"],
                    "last_seen": g["last_seen"],
                }
            )
    return result


def write_summary(path: str, groups: list[dict]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(groups)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Summarise events.csv into summary.csv."
    )
    parser.add_argument("input", nargs="?", default=_DEFAULT_INPUT)
    parser.add_argument("output", nargs="?", default=_DEFAULT_OUTPUT)
    parser.add_argument("--min-count", type=int, default=0, metavar="N")
    args = parser.parse_args(argv)

    try:
        rows = list(parse_rows(args.input))
    except FileNotFoundError:
        print(f"ERROR: input file not found: {args.input}", file=sys.stderr)
        return 1

    groups = aggregate(rows, min_count=args.min_count)
    write_summary(args.output, groups)
    return 0


if __name__ == "__main__":
    sys.exit(main())
