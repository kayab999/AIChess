"""Coach S4: mate como veredicto propio, hint L2 por casilla, colgadas (auditoría H4, M1, M2)."""
import chess

import coach
from chess_engine import ChessEngine, pov_cp


def _mate_in_one():
    b = chess.Board()
    for san in ("e4", "e5", "Bc4", "Nc6", "Qh5", "Nf6"):
        b.push_san(san)
    return b  # blancas dan Qxf7#


def test_delivered_mate_is_not_blunder():
    b = _mate_in_one()
    before = b.copy()
    b.push_san("Qxf7#")
    assert b.is_checkmate()
    fb = coach.evaluate_move(before, b, 0.5, 10000.0, "Qxf7#", 4)
    assert fb["veredicto"] == "mate" and fb["cp_loss"] == 0.0
    assert "mate" in fb["consejo"].lower()


def test_mate_flow_via_engine():
    e = ChessEngine(seed=9)
    e.toggle_coach(False)
    e.toggle_coach(True)
    for san in ("e4", "e5", "Bc4", "Nc6", "Qh5", "Nf6"):
        e.board.push_san(san)
    e._rebuild_history()
    r = e.player_move("Qxf7#")
    assert r["status"] == "checkmate"
    assert r["coach"]["veredicto"] == "mate"
    e.close()


def test_hint_level2_uses_real_square():
    assert coach.hint_level([], 2, "Qxf7#", "+5.0", "f7") == "Mira la zona de f7 como candidata."
    # SAN con +/# ya no produce zonas imposibles: fallback genérico honesto
    assert coach.hint_level([], 2, "Nf3+", "+0.3") == "Busca jugadas que mejoren tu control central."
    assert coach.hint_level([], 2, "O-O", "+0.2") != "Mira la zona de -O como candidata."


def test_hanging_excludes_king_and_pawns():
    # Rey en jaque sin defensores NO es "pieza colgada"
    b = chess.Board("4k3/4Q3/8/8/8/8/4K3/8 b - - 0 1")
    assert b.is_check()
    assert coach.detect_hanging(b, chess.BLACK) == []
    assert coach.detect_hanging(chess.Board(), chess.WHITE) == []


def test_lesser_attack_warning():
    # Caballo atacado por peón (aunque defendido): aviso, no colgada
    b = chess.Board("rnbqkbnr/ppp1pppp/8/3p4/4N3/8/PPPPPPPP/RNBQKB1R w KQkq - 0 1")
    assert any("menor" in m for m in coach.detect_lesser_attack(b, chess.WHITE))


def test_development_quiet_in_first_moves():
    b = chess.Board()
    assert coach.detect_development(b, 1, chess.WHITE) == []
    assert coach.detect_development(b, 3, chess.WHITE) == []
    assert coach.detect_development(b, 4, chess.WHITE) != []


def test_pov_cp_shared():
    from tournament import Rival  # noqa: F401  (importa el helper común)
    import chess_engine
    assert chess_engine.pov_cp(None, chess.WHITE) == 0.0
