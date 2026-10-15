"""Fixtures compartidas: motor real (Stockfish) y limpieza de artefactos."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from chess_engine import ChessEngine  # noqa: E402


@pytest.fixture()
def engine():
    e = ChessEngine(seed=1234)
    e.toggle_coach(False)
    yield e
    e.close()


@pytest.fixture(autouse=True)
def _clean_test_artifacts():
    yield
    for d in ("games", "boards"):
        p = ROOT / d
        if p.exists():
            for f in p.glob("test-*"):
                try:
                    f.unlink()
                except OSError:
                    pass
