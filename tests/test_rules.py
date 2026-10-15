"""Reglas: terminales, 75 jugadas, 50 reclamables (auditoría H6)."""
import chess

from chess_engine import ChessEngine


def _set(engine: ChessEngine, fen: str):
    engine.board.set_fen(fen)
    engine.state.status = "in_progress"
    engine.state.result = None
    engine._update_status()
    return engine.state


def test_insufficient_material(engine: ChessEngine):
    s = _set(engine, "8/8/4k3/8/8/4K3/8/8 w - - 0 1")
    assert (s.status, s.result) == ("draw", "1/2-1/2")


def test_seventyfive_moves_auto(engine: ChessEngine):
    s = _set(engine, "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 150 90")
    assert (s.status, s.result) == ("draw", "1/2-1/2")


def test_fifty_moves_claimable_not_auto(engine: ChessEngine):
    # python-chess: is_fifty_moves() == reclamable (>=100); la automática es 150.
    engine.board.set_fen("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 100 60")
    assert engine.board.is_fifty_moves()
    assert not engine.board.is_seventyfive_moves()
    engine._rebuild_history()
    assert engine.state.status == "in_progress"  # no es automática
    r = engine.claim_draw()
    assert r["status"] == "draw" and "50" in r.get("claim", "")


def test_result_cleared_when_reopened(engine: ChessEngine):
    engine.board.set_fen("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1")
    engine._update_status()
    assert engine.state.result == "1-0"  # negras mateadas: ganan blancas
    engine.board.set_fen(chess.STARTING_FEN)
    engine.state.status = "in_progress"
    engine._update_status()
    assert engine.state.result is None
