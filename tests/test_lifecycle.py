"""Ciclo de vida: resign/undo/mate/turnos/fallo del bot (auditoría C2, H1, H5)."""
import chess

from chess_engine import ChessEngine


def test_resign_then_undo_reopens_with_moves(engine: ChessEngine):
    engine.player_move("e4")
    r = engine.resign()
    assert (r["status"], r["result"]) == ("resigned", "0-1")
    r = engine.undo()
    assert r["status"] == "in_progress" and r["result"] is None
    assert len(r["moves"]) == 2 and r["turn"] == "blancas"


def test_undo_roundtrip_restores_fen(engine: ChessEngine):
    engine.player_move("e4")
    before = engine.board.fen()
    engine.player_move("Nf3")
    engine.undo()
    assert engine.board.fen() == before
    assert engine.get_state()["result"] is None


def test_undo_empty_is_error(engine: ChessEngine):
    assert engine.undo().get("error") == "Nada que deshacer"


def test_mate_then_undo_pops_one(engine: ChessEngine):
    for san in ["e4", "e5", "Bc4", "Nc6", "Qh5", "Nf6"]:
        engine.board.push_san(san)
    engine._rebuild_history()
    r = engine.player_move("Qxf7#")
    assert r["status"] == "checkmate" and r["result"] == "1-0"
    n = len(engine.board.move_stack)
    r = engine.undo()
    assert len(engine.board.move_stack) == n - 1
    assert r["status"] == "in_progress" and r["result"] is None


def test_wrong_turn_rejected(engine: ChessEngine):
    engine.player_move("e4")
    engine.board.pop()  # simula respuesta perdida: turno negras
    engine.state.moves_history.pop()
    engine._update_status()
    r = engine.player_move("Nf3")
    assert r.get("error", "").startswith("No es tu turno")


def test_bot_failure_rolls_back(engine: ChessEngine, monkeypatch):
    engine.player_move("e4")
    fen_before = engine.board.fen()
    moves_before = list(engine.state.moves_history)
    monkeypatch.setattr(engine, "_get_bot_move", lambda: None)
    r = engine.player_move("Nf3")
    assert "error" in r and "revertido" in r["error"]
    assert engine.board.fen() == fen_before
    assert engine.state.moves_history == moves_before


def test_claim_draw_unavailable(engine: ChessEngine):
    engine.player_move("e4")
    assert "error" in engine.claim_draw()


def test_claim_draw_threefold(engine: ChessEngine):
    for _ in range(3):
        for san in ["Nf3", "Nf6", "Ng1", "Ng8"]:
            engine.board.push_san(san)
    engine._rebuild_history()
    r = engine.claim_draw()
    assert r["status"] == "draw" and r["result"] == "1/2-1/2"
    assert "triple" in r.get("claim", "")
    assert engine.player_move("e4").get("error") == "La partida ya terminó"


def test_checkmate_and_stalemate_status():
    e = ChessEngine(seed=1)
    e.toggle_coach(False)
    try:
        e.board.set_fen("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1")  # Qg7#: mate al negro
        e._update_status()
        assert (e.state.status, e.state.result) == ("checkmate", "1-0")
        e.board.set_fen("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")  # Qf7: ahogado
        e.state.status = "in_progress"
        e.state.result = None
        e._update_status()
        assert (e.state.status, e.state.result) == ("stalemate", "1/2-1/2")
    finally:
        e.close()


def test_finished_import_blocks_play(engine: ChessEngine):
    from pathlib import Path
    Path("games/test-fin.pgn").write_text('[Event "x"]\n[Result "1-0"]\n\n1. e4 e5 1-0\n')
    r = engine.load_game("test-fin.pgn")
    assert r["status"] == "finished" and r["result"] == "1-0"
    assert engine.player_move("Nf3").get("error") == "La partida ya terminó"
