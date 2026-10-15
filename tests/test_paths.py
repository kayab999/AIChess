"""Rutas sandbox: sin escapes de games//boards/ (auditoría C4)."""
import os
from pathlib import Path

import pytest

from chess_engine import ChessEngine


@pytest.mark.parametrize("evil", [
    "/tmp/test-evil.pgn", "/etc/test-evil.pgn", "../test-evil.pgn",
    "sub/../test-evil.pgn", "sub/dir/test-evil.pgn",
])
def test_save_rejects_escape(engine: ChessEngine, evil):
    with pytest.raises(ValueError):
        engine.save_game(evil)
    assert not Path("/tmp/test-evil.pgn").exists()


@pytest.mark.parametrize("evil", ["/etc/hosts", "../cli_test.py", "sub/x.pgn"])
def test_load_rejects_escape(engine: ChessEngine, evil):
    r = engine.load_game(evil)
    assert "error" in r and engine.state.status == "in_progress"


def test_symlink_escape_blocked(engine: ChessEngine):
    link = Path("games/test-link.pgn")
    try:
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to("/tmp/test-outside-target")
        with pytest.raises(ValueError):
            engine.save_game("test-link.pgn")
    finally:
        if link.is_symlink():
            link.unlink()
    assert not Path("/tmp/test-outside-target").exists()


def test_boards_sandbox(engine: ChessEngine):
    with pytest.raises(ValueError):
        engine.save_board_image("/tmp/test-evil.svg")
    with pytest.raises(ValueError):
        engine.save_board_png("../test-evil.png")
    ok = engine.save_board_image("test-ok")
    assert ok["path"].endswith("test-ok.svg")
    Path(ok["path"]).unlink()
