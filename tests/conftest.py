import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _run(args, cwd=None):
    return subprocess.run(
        [sys.executable, "-m", "src.logsum"] + list(args),
        capture_output=True,
        text=True,
        cwd=str(cwd or PROJECT_ROOT),
        check=False,
    )


@pytest.fixture
def run():
    """Invoke python -m src.logsum; returns a callable(*args, cwd=None)."""
    return _run


@pytest.fixture
def fixture_path(tmp_path):
    """Copy a named fixture file into tmp_path and return its Path."""
    def _copy(name):
        src = FIXTURES_DIR / name
        dst = tmp_path / name
        shutil.copy(src, dst)
        return dst
    return _copy
