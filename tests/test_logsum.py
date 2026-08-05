"""
Tests derived exclusively from spec.md.  No implementation code was read.

Coverage map (spec section → test class):
  §1 + §3  Grouping & output columns  → TestGrouping, TestOutputColumns
  §2       Normalisation              → TestNormalisation
  §4       Missing level              → TestMissingLevel
  §5       Malformed timestamp        → TestMalformedTimestamp
  §6       Empty input                → TestEmptyInput
  §7       CLI / exit codes           → TestCLI
"""

import csv
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_csv(path, rows, fieldnames=None):
    if fieldnames is None:
        fieldnames = ["timestamp", "level", "service", "message"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _read_header(path):
    with open(path, newline="", encoding="utf-8") as f:
        return next(csv.reader(f))


# ---------------------------------------------------------------------------
# §3 – Output columns
# ---------------------------------------------------------------------------

class TestOutputColumns:
    def test_exactly_five_columns(self, run, tmp_path):
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        _write_csv(inp, [
            {"timestamp": "2024-01-01T10:00:00", "level": "INFO",
             "service": "svc", "message": "m"},
        ])
        assert run([str(inp), str(out)]).returncode == 0
        assert list(_read_csv(out)[0].keys()) == [
            "service", "level", "count", "first_seen", "last_seen"
        ]

    def test_column_order_in_header(self, run, tmp_path):
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        _write_csv(inp, [
            {"timestamp": "2024-01-01T10:00:00", "level": "INFO",
             "service": "svc", "message": "m"},
        ])
        run([str(inp), str(out)])
        assert _read_header(out) == [
            "service", "level", "count", "first_seen", "last_seen"
        ]

    def test_count_is_integer_string(self, run, tmp_path):
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        _write_csv(inp, [
            {"timestamp": "2024-01-01T10:00:00", "level": "INFO",
             "service": "svc", "message": "m"},
        ])
        run([str(inp), str(out)])
        rows = _read_csv(out)
        assert rows[0]["count"].isdigit()


# ---------------------------------------------------------------------------
# §1 + §3 – Grouping
# ---------------------------------------------------------------------------

class TestGrouping:
    def test_three_rows_same_pair_gives_count_three(self, run, tmp_path):
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        _write_csv(inp, [
            {"timestamp": "2024-01-01T08:00:00", "level": "INFO",
             "service": "svc", "message": "a"},
            {"timestamp": "2024-01-01T09:00:00", "level": "INFO",
             "service": "svc", "message": "b"},
            {"timestamp": "2024-01-01T10:00:00", "level": "INFO",
             "service": "svc", "message": "c"},
        ])
        run([str(inp), str(out)])
        rows = _read_csv(out)
        assert len(rows) == 1
        assert rows[0]["count"] == "3"

    def test_three_distinct_pairs_gives_three_rows(self, run, tmp_path):
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        _write_csv(inp, [
            {"timestamp": "2024-01-01T08:00:00", "level": "INFO",
             "service": "svc-a", "message": ""},
            {"timestamp": "2024-01-01T09:00:00", "level": "ERROR",
             "service": "svc-a", "message": ""},
            {"timestamp": "2024-01-01T10:00:00", "level": "INFO",
             "service": "svc-b", "message": ""},
        ])
        run([str(inp), str(out)])
        assert len(_read_csv(out)) == 3

    def test_first_seen_is_earliest_timestamp(self, run, tmp_path):
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        _write_csv(inp, [
            {"timestamp": "2024-01-01T12:00:00", "level": "INFO",
             "service": "svc", "message": ""},
            {"timestamp": "2024-01-01T06:00:00", "level": "INFO",
             "service": "svc", "message": ""},
            {"timestamp": "2024-01-01T09:00:00", "level": "INFO",
             "service": "svc", "message": ""},
        ])
        run([str(inp), str(out)])
        assert _read_csv(out)[0]["first_seen"].startswith("2024-01-01T06:00:00")

    def test_last_seen_is_latest_timestamp(self, run, tmp_path):
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        _write_csv(inp, [
            {"timestamp": "2024-01-01T06:00:00", "level": "INFO",
             "service": "svc", "message": ""},
            {"timestamp": "2024-01-01T12:00:00", "level": "INFO",
             "service": "svc", "message": ""},
            {"timestamp": "2024-01-01T09:00:00", "level": "INFO",
             "service": "svc", "message": ""},
        ])
        run([str(inp), str(out)])
        assert _read_csv(out)[0]["last_seen"].startswith("2024-01-01T12:00:00")

    def test_first_seen_equals_last_seen_for_single_row(self, run, tmp_path):
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        _write_csv(inp, [
            {"timestamp": "2024-03-10T14:30:00", "level": "WARN",
             "service": "svc", "message": ""},
        ])
        run([str(inp), str(out)])
        row = _read_csv(out)[0]
        assert row["first_seen"].startswith("2024-03-10T14:30:00")
        assert row["last_seen"].startswith("2024-03-10T14:30:00")

    def test_basic_fixture_group_counts(self, run, fixture_path, tmp_path):
        """basic.csv: checkout-service/INFO×2, checkout-service/ERROR×1,
        cart-api/INFO×1, cart-api/WARN×2 → 4 output rows."""
        inp = fixture_path("basic.csv")
        out = tmp_path / "s.csv"
        run([str(inp), str(out)])
        rows = _read_csv(out)
        by_key = {(r["service"], r["level"]): int(r["count"]) for r in rows}
        assert by_key[("checkout-service", "INFO")] == 2
        assert by_key[("checkout-service", "ERROR")] == 1
        assert by_key[("cart-api", "INFO")] == 1
        assert by_key[("cart-api", "WARN")] == 2


# ---------------------------------------------------------------------------
# §2 – Normalisation
# ---------------------------------------------------------------------------

class TestNormalisation:
    def test_service_is_lowercased(self, run, tmp_path):
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        _write_csv(inp, [
            {"timestamp": "2024-01-01T10:00:00", "level": "INFO",
             "service": "CHECKOUT-SERVICE", "message": ""},
        ])
        run([str(inp), str(out)])
        assert _read_csv(out)[0]["service"] == "checkout-service"

    def test_service_whitespace_is_stripped(self, run, tmp_path):
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        _write_csv(inp, [
            {"timestamp": "2024-01-01T10:00:00", "level": "INFO",
             "service": "  my-service  ", "message": ""},
        ])
        run([str(inp), str(out)])
        assert _read_csv(out)[0]["service"] == "my-service"

    def test_level_is_uppercased(self, run, tmp_path):
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        _write_csv(inp, [
            {"timestamp": "2024-01-01T10:00:00", "level": "info",
             "service": "svc", "message": ""},
        ])
        run([str(inp), str(out)])
        assert _read_csv(out)[0]["level"] == "INFO"

    def test_level_whitespace_is_stripped(self, run, tmp_path):
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        _write_csv(inp, [
            {"timestamp": "2024-01-01T10:00:00", "level": "  warn  ",
             "service": "svc", "message": ""},
        ])
        run([str(inp), str(out)])
        assert _read_csv(out)[0]["level"] == "WARN"

    def test_info_info_Info_all_in_same_group(self, run, tmp_path):
        """spec §2 example: INFO, info, '  Info  ' map to same group key."""
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        _write_csv(inp, [
            {"timestamp": "2024-01-01T08:00:00", "level": "INFO",
             "service": "svc", "message": ""},
            {"timestamp": "2024-01-01T09:00:00", "level": "info",
             "service": "svc", "message": ""},
            {"timestamp": "2024-01-01T10:00:00", "level": "  Info  ",
             "service": "svc", "message": ""},
        ])
        run([str(inp), str(out)])
        rows = _read_csv(out)
        assert len(rows) == 1
        assert rows[0]["count"] == "3"
        assert rows[0]["level"] == "INFO"

    def test_mixed_case_services_same_group(self, run, tmp_path):
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        _write_csv(inp, [
            {"timestamp": "2024-01-01T08:00:00", "level": "INFO",
             "service": "SVC", "message": ""},
            {"timestamp": "2024-01-01T09:00:00", "level": "INFO",
             "service": "svc", "message": ""},
            {"timestamp": "2024-01-01T10:00:00", "level": "INFO",
             "service": "  Svc  ", "message": ""},
        ])
        run([str(inp), str(out)])
        rows = _read_csv(out)
        assert len(rows) == 1
        assert rows[0]["count"] == "3"

    def test_normalisation_fixture_collapses_to_one_group(self, run, fixture_path, tmp_path):
        """normalisation.csv has 3 rows that all normalise to checkout-service/INFO."""
        inp = fixture_path("normalisation.csv")
        out = tmp_path / "s.csv"
        run([str(inp), str(out)])
        rows = _read_csv(out)
        assert len(rows) == 1
        assert rows[0]["service"] == "checkout-service"
        assert rows[0]["level"] == "INFO"
        assert rows[0]["count"] == "3"


# ---------------------------------------------------------------------------
# §4 – Missing level
# ---------------------------------------------------------------------------

class TestMissingLevel:
    def test_blank_level_becomes_UNKNOWN(self, run, tmp_path):
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        _write_csv(inp, [
            {"timestamp": "2024-01-01T10:00:00", "level": "",
             "service": "svc", "message": "m"},
        ])
        run([str(inp), str(out)])
        assert _read_csv(out)[0]["level"] == "UNKNOWN"

    def test_blank_level_row_is_not_dropped(self, run, tmp_path):
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        _write_csv(inp, [
            {"timestamp": "2024-01-01T10:00:00", "level": "",
             "service": "svc", "message": "a"},
            {"timestamp": "2024-01-01T11:00:00", "level": "",
             "service": "svc", "message": "b"},
        ])
        run([str(inp), str(out)])
        rows = _read_csv(out)
        unknown = [r for r in rows if r["level"] == "UNKNOWN"]
        assert len(unknown) == 1
        assert unknown[0]["count"] == "2"

    def test_UNKNOWN_and_INFO_are_separate_groups(self, run, tmp_path):
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        _write_csv(inp, [
            {"timestamp": "2024-01-01T10:00:00", "level": "INFO",
             "service": "svc", "message": ""},
            {"timestamp": "2024-01-01T11:00:00", "level": "",
             "service": "svc", "message": ""},
        ])
        run([str(inp), str(out)])
        rows = _read_csv(out)
        levels = {r["level"] for r in rows}
        assert "INFO" in levels
        assert "UNKNOWN" in levels
        assert len(rows) == 2

    def test_missing_level_fixture(self, run, fixture_path, tmp_path):
        """missing_level.csv: 2 blank-level rows → UNKNOWN/count=2; INFO/count=1."""
        inp = fixture_path("missing_level.csv")
        out = tmp_path / "s.csv"
        run([str(inp), str(out)])
        rows = _read_csv(out)
        by_level = {r["level"]: int(r["count"]) for r in rows}
        assert by_level["UNKNOWN"] == 2
        assert by_level["INFO"] == 1

    def test_whitespace_only_level_is_UNKNOWN(self, run, tmp_path):
        """Whitespace strip of '   ' produces '' → UNKNOWN."""
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        _write_csv(inp, [
            {"timestamp": "2024-01-01T10:00:00", "level": "   ",
             "service": "svc", "message": ""},
        ])
        run([str(inp), str(out)])
        assert _read_csv(out)[0]["level"] == "UNKNOWN"


# ---------------------------------------------------------------------------
# §5 – Malformed timestamp
# ---------------------------------------------------------------------------

class TestMalformedTimestamp:
    def test_bad_ts_row_included_in_count(self, run, tmp_path):
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        _write_csv(inp, [
            {"timestamp": "not-a-date", "level": "INFO",
             "service": "svc", "message": ""},
            {"timestamp": "2024-01-01T10:00:00", "level": "INFO",
             "service": "svc", "message": ""},
        ])
        run([str(inp), str(out)])
        assert _read_csv(out)[0]["count"] == "2"

    def test_bad_ts_does_not_affect_first_last_seen(self, run, tmp_path):
        """first_seen/last_seen must reflect only the parseable row."""
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        _write_csv(inp, [
            {"timestamp": "not-a-date", "level": "INFO",
             "service": "svc", "message": ""},
            {"timestamp": "2024-06-15T09:00:00", "level": "INFO",
             "service": "svc", "message": ""},
        ])
        run([str(inp), str(out)])
        row = _read_csv(out)[0]
        assert row["first_seen"].startswith("2024-06-15T09:00:00")
        assert row["last_seen"].startswith("2024-06-15T09:00:00")

    def test_one_warning_per_bad_row(self, run, tmp_path):
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        _write_csv(inp, [
            {"timestamp": "bad1", "level": "INFO", "service": "svc", "message": ""},
            {"timestamp": "bad2", "level": "INFO", "service": "svc", "message": ""},
            {"timestamp": "bad3", "level": "INFO", "service": "svc", "message": ""},
        ])
        result = run([str(inp), str(out)])
        warnings = [l for l in result.stderr.splitlines()
                    if l.startswith("WARNING:")]
        assert len(warnings) == 3

    def test_warning_format_contains_row_number_and_value(self, run, tmp_path):
        """spec §5: WARNING: skipping unparseable timestamp on row <n>: "<raw_value>" """
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        _write_csv(inp, [
            {"timestamp": "BADVAL", "level": "INFO",
             "service": "svc", "message": ""},
        ])
        result = run([str(inp), str(out)])
        assert "WARNING: skipping unparseable timestamp on row" in result.stderr
        assert '"BADVAL"' in result.stderr

    def test_warnings_go_to_stderr_not_stdout(self, run, tmp_path):
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        _write_csv(inp, [
            {"timestamp": "bad", "level": "INFO", "service": "svc", "message": ""},
        ])
        result = run([str(inp), str(out)])
        assert "WARNING" not in result.stdout

    def test_skipped_summary_on_stderr_with_correct_count(self, run, tmp_path):
        """spec §5: 'Skipped <k> row(s) with unparseable timestamps.' on stderr."""
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        _write_csv(inp, [
            {"timestamp": "bad1", "level": "INFO", "service": "svc", "message": ""},
            {"timestamp": "bad2", "level": "INFO", "service": "svc", "message": ""},
        ])
        result = run([str(inp), str(out)])
        assert "Skipped 2 row(s) with unparseable timestamps." in result.stderr

    def test_no_skipped_summary_when_all_timestamps_valid(self, run, tmp_path):
        """spec §5: summary line is omitted when k == 0."""
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        _write_csv(inp, [
            {"timestamp": "2024-01-01T10:00:00", "level": "INFO",
             "service": "svc", "message": ""},
        ])
        result = run([str(inp), str(out)])
        assert "Skipped" not in result.stderr

    def test_all_bad_ts_first_last_seen_empty(self, run, tmp_path):
        """When every row in a group has a bad timestamp, first_seen/last_seen are empty."""
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        _write_csv(inp, [
            {"timestamp": "bad1", "level": "INFO", "service": "svc", "message": ""},
            {"timestamp": "bad2", "level": "INFO", "service": "svc", "message": ""},
        ])
        run([str(inp), str(out)])
        row = _read_csv(out)[0]
        assert not row["first_seen"]
        assert not row["last_seen"]

    def test_mixed_good_bad_ts_count_includes_bad(self, run, tmp_path):
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        _write_csv(inp, [
            {"timestamp": "2024-01-01T08:00:00", "level": "INFO",
             "service": "svc", "message": ""},
            {"timestamp": "bad", "level": "INFO",
             "service": "svc", "message": ""},
            {"timestamp": "2024-01-01T20:00:00", "level": "INFO",
             "service": "svc", "message": ""},
        ])
        run([str(inp), str(out)])
        row = _read_csv(out)[0]
        assert row["count"] == "3"
        assert row["first_seen"].startswith("2024-01-01T08:00:00")
        assert row["last_seen"].startswith("2024-01-01T20:00:00")

    def test_malformed_ts_fixture(self, run, fixture_path, tmp_path):
        """malformed_ts.csv: 2 bad rows → 2 warnings + 'Skipped 2 row(s)…'."""
        inp = fixture_path("malformed_ts.csv")
        out = tmp_path / "s.csv"
        result = run([str(inp), str(out)])
        warnings = [l for l in result.stderr.splitlines()
                    if l.startswith("WARNING:")]
        assert len(warnings) == 2
        assert "Skipped 2 row(s) with unparseable timestamps." in result.stderr


# ---------------------------------------------------------------------------
# §6 – Empty input
# ---------------------------------------------------------------------------

class TestEmptyInput:
    def test_headers_only_exits_zero(self, run, fixture_path, tmp_path):
        inp = fixture_path("headers_only.csv")
        out = tmp_path / "s.csv"
        assert run([str(inp), str(out)]).returncode == 0

    def test_headers_only_writes_summary_with_correct_header(self, run, fixture_path, tmp_path):
        inp = fixture_path("headers_only.csv")
        out = tmp_path / "s.csv"
        run([str(inp), str(out)])
        assert out.exists()
        assert _read_header(out) == [
            "service", "level", "count", "first_seen", "last_seen"
        ]

    def test_headers_only_writes_zero_data_rows(self, run, fixture_path, tmp_path):
        inp = fixture_path("headers_only.csv")
        out = tmp_path / "s.csv"
        run([str(inp), str(out)])
        assert _read_csv(out) == []

    def test_completely_empty_file_exits_zero(self, run, tmp_path):
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        inp.write_text("", encoding="utf-8")
        assert run([str(inp), str(out)]).returncode == 0

    def test_completely_empty_file_writes_output(self, run, tmp_path):
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        inp.write_text("", encoding="utf-8")
        run([str(inp), str(out)])
        assert out.exists()

    def test_completely_empty_file_zero_data_rows(self, run, tmp_path):
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        inp.write_text("", encoding="utf-8")
        run([str(inp), str(out)])
        content = out.read_text(encoding="utf-8").strip()
        data_lines = [l for l in content.splitlines()[1:] if l.strip()]
        assert data_lines == []


# ---------------------------------------------------------------------------
# §7 – CLI interface and exit codes
# ---------------------------------------------------------------------------

class TestCLI:
    def test_exit_zero_on_success(self, run, tmp_path):
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        _write_csv(inp, [
            {"timestamp": "2024-01-01T10:00:00", "level": "INFO",
             "service": "svc", "message": ""},
        ])
        assert run([str(inp), str(out)]).returncode == 0

    def test_output_written_to_given_path(self, run, tmp_path):
        inp = tmp_path / "in.csv"
        out = tmp_path / "subdir" / "out.csv"
        out.parent.mkdir()
        _write_csv(inp, [
            {"timestamp": "2024-01-01T10:00:00", "level": "INFO",
             "service": "svc", "message": ""},
        ])
        run([str(inp), str(out)])
        assert out.exists()

    def test_no_csv_on_stdout(self, run, tmp_path):
        """spec §7: only CSV goes to the output file, not stdout."""
        inp, out = tmp_path / "e.csv", tmp_path / "s.csv"
        _write_csv(inp, [
            {"timestamp": "2024-01-01T10:00:00", "level": "INFO",
             "service": "svc", "message": ""},
        ])
        result = run([str(inp), str(out)])
        assert result.stdout == ""

    def test_exit_one_when_input_not_found(self, run, tmp_path):
        out = tmp_path / "s.csv"
        result = run([str(tmp_path / "nonexistent.csv"), str(out)])
        assert result.returncode == 1

    def test_exit_one_error_message_on_stderr(self, run, tmp_path):
        out = tmp_path / "s.csv"
        result = run([str(tmp_path / "nonexistent.csv"), str(out)])
        assert result.stderr.strip() != ""

    def test_missing_output_directory_is_created(self, run, tmp_path):
        inp = tmp_path / "e.csv"
        _write_csv(inp, [
            {"timestamp": "2024-01-01T10:00:00", "level": "INFO",
             "service": "svc", "message": ""},
        ])
        out = tmp_path / "no_such_dir" / "s.csv"
        result = run([str(inp), str(out)])
        assert result.returncode == 0
        assert out.exists()

    def test_exit_two_on_too_many_positional_args(self, run):
        result = run(["a.csv", "b.csv", "c.csv"])
        assert result.returncode == 2

    def test_no_args_uses_default_input_and_output(self, tmp_path):
        """spec §7 default: data/events.csv → data/summary.csv.

        CWD is tmp_path so default paths resolve to the temp tree; PYTHONPATH
        points to PROJECT_ROOT so `python -m src.logsum` resolves the module.
        """
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        _write_csv(data_dir / "events.csv", [
            {"timestamp": "2024-01-01T10:00:00", "level": "INFO",
             "service": "svc", "message": ""},
        ])
        env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
        result = subprocess.run(
            [sys.executable, "-m", "src.logsum"],
            capture_output=True, text=True,
            cwd=str(tmp_path), env=env,
        )
        assert result.returncode == 0
        assert (data_dir / "summary.csv").exists()

    def test_one_arg_uses_default_output_path(self, tmp_path):
        """spec §7: supplying only INPUT writes to data/summary.csv.

        CWD is tmp_path so the default output resolves to tmp_path/data/summary.csv;
        PYTHONPATH points to PROJECT_ROOT so the module is found.
        """
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        inp = tmp_path / "custom_in.csv"
        _write_csv(inp, [
            {"timestamp": "2024-01-01T10:00:00", "level": "INFO",
             "service": "svc", "message": ""},
        ])
        env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
        result = subprocess.run(
            [sys.executable, "-m", "src.logsum", str(inp)],
            capture_output=True, text=True,
            cwd=str(tmp_path), env=env,
        )
        assert result.returncode == 0
        assert (data_dir / "summary.csv").exists()
