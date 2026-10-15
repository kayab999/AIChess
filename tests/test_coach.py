"""Coach estable: clasificación, colgadas, UCI caído (S4 añadirá mate/hints)."""
import chess

import coach
from chess_engine import ChessEngine


def test_classify_loss_boundaries():
    assert coach.classify_loss(0)[0] == "bien"
    assert coach.classify_loss(29.9)[0] == "bien"
    assert coach.classify_loss(30)[0] == "imprecisión"
    assert coach.classify_loss(69.9)[0] == "imprecisión"
    assert coach.classify_loss(70)[0] == "error"
    assert coach.classify_loss(179.9)[0] == "error"
    assert coach.classify_loss(180)[0] == "blunder"
    assert coach.classify_loss(0, mate_lost=True)[0] == "grave"


def test_hanging_ignores_pawns_and_counts_attackers():
    b = chess.Board("rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1")
    assert coach.detect_hanging(b, chess.WHITE) == []
    # d5 atacado por e4, defendido por dama: 1 vs 1 -> no colgada
    b2 = chess.Board("rnbqkbnr/ppp1pppp/8/3p4/3PP3/8/PPP2PPP/RNBQKBNR b KQkq - 0 1")
    assert coach.detect_hanging(b2, chess.BLACK) == []


def test_analyze_engine_failure_returns_error(engine: ChessEngine, monkeypatch):
    def boom(*a, **k):
        raise chess.engine.EngineError("motor caído")
    monkeypatch.setattr(engine.engine, "analyse", boom)
    assert "error" in engine.analyze()
    # la partida sigue jugable: _quick_eval falla en silencio y el bot usa play
    monkeypatch.setattr(engine.engine, "play",
                        lambda *a, **k: (_ for _ in ()).throw(chess.engine.EngineError("x")))
    # a4 sale del libro: el bot debe tirar de UCI (caído) -> rollback
    r = engine.player_move("a4")
    assert "revertido" in r.get("error", "")
    assert r["moves"] == []


def test_eco_known_openings():
    from eco import opening_name
    assert opening_name(["e4", "c5", "Nf3", "d6", "d4", "cxd4",
                         "Nxd4", "Nf6", "Nc3", "a6"])[0] == "Siciliana Najdorf"
    assert opening_name([])[0] == "Posición inicial"
