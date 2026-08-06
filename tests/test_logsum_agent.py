import csv
import subprocess
import sys
from pathlib import Path

import src.logsum_agent as mod
from src.logsum_agent import main
from src.normalise_agent import normalise_level, normalise_service

FIXTURES = Path(__file__).parent / "fixtures_agent"


# ---------------------------------------------------------------------------
# normalise_agent unit tests
# ---------------------------------------------------------------------------


def test_normalise_service_strips_and_lowercases():
    assert normalise_service("  Checkout-Service  ") == "checkout-service"


def test_normalise_level_strips_and_uppercases():
    assert normalise_level("  info  ") == "INFO"


def test_normalise_level_blank_string_becomes_unknown():
    assert normalise_level("") == "UNKNOWN"


def test_normalise_level_whitespace_becomes_unknown():
    assert normalise_level("   ") == "UNKNOWN"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_csv(path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _fieldnames(path) -> set[str]:
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return set(reader.fieldnames or [])


# ---------------------------------------------------------------------------
# Happy-path / basic output
# ---------------------------------------------------------------------------


def test_basic_output_row_count(tmp_path):
    out = tmp_path / "out.csv"
    rc = main([str(FIXTURES / "basic_agent.csv"), str(out)])
    assert rc == 0
    rows = _read_csv(out)
    assert len(rows) == 5  # cart-api×3 + checkout-service×2


def test_basic_output_services(tmp_path):
    out = tmp_path / "out.csv"
    main([str(FIXTURES / "basic_agent.csv"), str(out)])
    services = {r["service"] for r in _read_csv(out)}
    assert services == {"checkout-service", "cart-api"}


def test_basic_output_counts(tmp_path):
    out = tmp_path / "out.csv"
    main([str(FIXTURES / "basic_agent.csv"), str(out)])
    by_key = {(r["service"], r["level"]): int(r["count"]) for r in _read_csv(out)}
    assert by_key[("checkout-service", "INFO")] == 2
    assert by_key[("checkout-service", "ERROR")] == 1
    assert by_key[("cart-api", "WARN")] == 1


def test_basic_output_columns(tmp_path):
    out = tmp_path / "out.csv"
    main([str(FIXTURES / "basic_agent.csv"), str(out)])
    assert _fieldnames(out) == {"service", "level", "count", "first_seen", "last_seen"}


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------


def test_normalisation_service(tmp_path):
    out = tmp_path / "out.csv"
    main([str(FIXTURES / "normalisation_agent.csv"), str(out)])
    services = {r["service"] for r in _read_csv(out)}
    assert services == {"checkout-service", "cart-api"}


def test_normalisation_level(tmp_path):
    out = tmp_path / "out.csv"
    main([str(FIXTURES / "normalisation_agent.csv"), str(out)])
    levels = {r["level"] for r in _read_csv(out)}
    assert levels <= {"INFO", "ERROR", "WARN", "UNKNOWN"}
    assert "INFO" in levels


def test_blank_level_becomes_unknown(tmp_path):
    src = tmp_path / "blank_level.csv"
    src.write_text(
        "timestamp,level,service,message\n2024-01-01T00:00:00,  ,checkout-service,msg\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.csv"
    main([str(src), str(out)])
    levels = {r["level"] for r in _read_csv(out)}
    assert "UNKNOWN" in levels


def test_absent_level_col_becomes_unknown(tmp_path):
    out = tmp_path / "out.csv"
    main([str(FIXTURES / "missing_level_agent.csv"), str(out)])
    rows = _read_csv(out)
    assert len(rows) == 1
    assert rows[0]["level"] == "UNKNOWN"
    assert int(rows[0]["count"]) == 2


# ---------------------------------------------------------------------------
# Malformed timestamp
# ---------------------------------------------------------------------------


def test_malformed_timestamp_row_is_included(tmp_path):
    out = tmp_path / "out.csv"
    main([str(FIXTURES / "malformed_ts_agent.csv"), str(out)])
    rows = _read_csv(out)
    assert len(rows) == 1
    assert int(rows[0]["count"]) == 2  # both rows counted


def test_malformed_timestamp_fields_are_strings(tmp_path):
    out = tmp_path / "out.csv"
    main([str(FIXTURES / "malformed_ts_agent.csv"), str(out)])
    rows = _read_csv(out)
    assert rows[0]["first_seen"] != ""
    assert rows[0]["last_seen"] != ""


# ---------------------------------------------------------------------------
# Empty / headers-only input
# ---------------------------------------------------------------------------


def test_empty_input_writes_headers_only(tmp_path):
    out = tmp_path / "out.csv"
    rc = main([str(FIXTURES / "empty_agent.csv"), str(out)])
    assert rc == 0
    assert _fieldnames(out) == {"service", "level", "count", "first_seen", "last_seen"}
    assert _read_csv(out) == []


def test_headers_only_input_writes_headers_only(tmp_path):
    out = tmp_path / "out.csv"
    rc = main([str(FIXTURES / "headers_only_agent.csv"), str(out)])
    assert rc == 0
    assert _fieldnames(out) == {"service", "level", "count", "first_seen", "last_seen"}
    assert _read_csv(out) == []


# ---------------------------------------------------------------------------
# --min-count
# ---------------------------------------------------------------------------


def test_min_count_filters_low_groups(tmp_path):
    out = tmp_path / "out.csv"
    main([str(FIXTURES / "basic_agent.csv"), str(out), "--min-count", "2"])
    rows = _read_csv(out)
    assert rows  # at least one group survives
    assert all(int(r["count"]) >= 2 for r in rows)


def test_min_count_zero_keeps_all(tmp_path):
    out = tmp_path / "out.csv"
    main([str(FIXTURES / "basic_agent.csv"), str(out), "--min-count", "0"])
    assert len(_read_csv(out)) == 5


# ---------------------------------------------------------------------------
# Missing required columns
# ---------------------------------------------------------------------------


def test_missing_required_cols_skips_all_rows(tmp_path, capsys):
    out = tmp_path / "out.csv"
    rc = main([str(FIXTURES / "missing_col_agent.csv"), str(out)])
    assert rc == 0
    assert _read_csv(out) == []


def test_missing_required_cols_emits_warning(tmp_path, capsys):
    out = tmp_path / "out.csv"
    main([str(FIXTURES / "missing_col_agent.csv"), str(out)])
    captured = capsys.readouterr()
    assert "WARNING" in captured.err


# ---------------------------------------------------------------------------
# Default paths
# ---------------------------------------------------------------------------


def test_default_input_path():
    assert mod._DEFAULT_INPUT == "data/events.csv"


def test_default_output_path():
    assert mod._DEFAULT_OUTPUT == "data/summary.csv"


# ---------------------------------------------------------------------------
# CLI roundtrip (subprocess)
# ---------------------------------------------------------------------------


def test_cli_roundtrip(tmp_path):
    out = tmp_path / "out.csv"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.logsum_agent",
            str(FIXTURES / "basic_agent.csv"),
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    rows = _read_csv(out)
    assert len(rows) == 5
    assert _fieldnames(out) == {"service", "level", "count", "first_seen", "last_seen"}
