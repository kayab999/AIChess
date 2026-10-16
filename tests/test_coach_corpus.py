"""Corpus de aceptación del coach (20 casos): veredictos, mates, hints, prompts.
Criterio Fase 2: el híbrido no contradice al motor; el mate nunca es blunder."""
import chess

import coach
from coach import build_coach_prompt, classify_loss, evaluate_move


def test_01_bien_cero():
    assert classify_loss(0)[0] == "bien"


def test_02_bien_limite():
    assert classify_loss(29.9)[0] == "bien"


def test_03_imprecision_limite():
    assert classify_loss(30)[0] == "imprecisión"


def test_04_error_medio():
    assert classify_loss(100)[0] == "error"


def test_05_blunder():
    assert classify_loss(200)[0] == "blunder"


def test_06_grave_explicito():
    assert classify_loss(9999, mate_lost=True) == ("grave", "💀")


def test_07_mate_dado_no_es_blunder():
    b = chess.Board()
    for san in ("e4", "e5", "Bc4", "Nc6", "Qh5", "Nf6"):
        b.push_san(san)
    before = b.copy()
    b.push_san("Qxf7#")
    fb = evaluate_move(before, b, 2.0, 10000.0, "Qxf7#", 4)
    assert fb["veredicto"] == "mate" and fb["cp_loss"] == 0.0


def test_08_mate_perdido_es_grave():
    b = chess.Board()
    fb = evaluate_move(b, b, 10000.0, 400.0, "Ke2??", 20)
    assert fb["veredicto"] == "grave"


def test_09_mate_rival_no_es_grave():
    b = chess.Board()
    fb = evaluate_move(b, b, -10000.0, -10000.0, "a3", 20)
    assert fb["veredicto"] != "grave"


def test_10_colgada_simple():
    b = chess.Board("rnbqkbnr/ppp1pppp/8/3p4/4N3/8/PPPPPPPP/RNBQKB1R w KQkq - 0 1")
    assert coach.detect_hanging(b, chess.WHITE) == ["caballo en e4 colgada/o"]


def test_11_rey_no_es_colgada():
    b = chess.Board("4k3/4Q3/8/8/8/8/4K3/8 b - - 0 1")
    assert coach.detect_hanging(b, chess.BLACK) == []


def test_12_ataque_pieza_menor():
    b = chess.Board("rnbqkbnr/ppp1pppp/8/3p4/4N3/8/PPPPPPPP/RNBQKB1R w KQkq - 0 1")
    assert any("menor" in m for m in coach.detect_lesser_attack(b, chess.WHITE))


def test_13_desarrollo_calla_movidas_1_3():
    b = chess.Board()
    assert coach.detect_development(b, 2, chess.WHITE) == []
    assert coach.detect_development(b, 5, chess.WHITE) != []


def test_14_hint_l2_promocion():
    assert coach.hint_level([], 2, "exd8=Q+", "+6.0", "d8").endswith("de d8 como candidata.")


def test_15_explain_blunder_habla_de_peones():
    txt = coach.explain("Bc4??", 250.0, [], "blunder")
    assert "peones" in txt


def test_16_pov_mate_signo():
    from chess_engine import pov_cp
    assert pov_cp(chess.engine.PovScore(chess.engine.Mate(3), chess.WHITE), chess.WHITE) == 10000.0
    assert pov_cp(chess.engine.PovScore(chess.engine.Mate(-2), chess.WHITE), chess.WHITE) == -10000.0


def test_17_prompt_con_ancla_y_eval():
    p = build_coach_prompt(
        {"veredicto": "error", "cp_loss": 150.0, "best_move": "d4", "motivos": ["caballo sin desarrollar"]},
        "fen-x", "blancas", "Nf3")
    assert "manda" in p and "fen-x" in p and "d4" in p


def test_18_prompt_mate():
    p = build_coach_prompt(
        {"veredicto": "mate", "cp_loss": 0.0, "best_move": None, "motivos": []},
        "fen-y", "negras", "Qxf7#")
    assert "mate" in p.lower() and "—" in p


def test_19_flujo_engine_prompt_con_fen_real():
    from chess_engine import ChessEngine
    e = ChessEngine(seed=11)
    try:
        e.player_move("e4")
        res = e.build_coach_context()
        assert "FEN" in res["prompt"] and e.board.fen() in res["prompt"]
        assert res["context"]["veredicto"] in ("bien", "imprecisión", "error", "blunder", "grave", "mate")
    finally:
        e.close()


def test_20_sin_jugada_previa_es_error():
    from chess_engine import ChessEngine
    e = ChessEngine(seed=12)
    try:
        assert "error" in e.build_coach_context()
    finally:
        e.close()
