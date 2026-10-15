"""PGN: round-trip, FEN custom, malformados, personalidad (auditoría H2, H5/M3)."""
from pathlib import Path

import chess.pgn

from chess_engine import ChessEngine, chess


def _play_two_rounds(engine: ChessEngine):
    for mv in ("e4", "Nf3"):
        r = engine.player_move(mv)
        assert "error" not in r
    return list(engine.state.moves_history)


def test_save_load_roundtrip(engine: ChessEngine):
    moves = _play_two_rounds(engine)
    fen = engine.board.fen()
    res = engine.save_game("test-rt")
    assert res["path"].endswith("test-rt.pgn")
    engine.reset()
    assert engine.state.moves_history == []
    loaded = engine.load_game("test-rt.pgn")
    assert "error" not in loaded
    assert loaded["moves"] == moves and engine.board.fen() == fen
    # re-export estable
    assert f"1. {moves[0]}" in engine.to_pgn()


def test_personality_header_restored(engine: ChessEngine):
    _play_two_rounds(engine)
    engine.set_personality("tal")
    engine.save_game("test-pers")
    engine.set_personality("muro")
    engine.load_game("test-pers.pgn")
    assert engine.personality_key == "tal"


def test_custom_fen_root_roundtrip(engine: ChessEngine):
    fen = "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3"
    game = chess.pgn.Game.from_board(chess.Board(fen))
    game.headers["Result"] = "*"
    game.add_variation(chess.Move.from_uci("f3e5"))
    Path("games/test-fen.pgn").write_text(
        game.accept(chess.pgn.StringExporter()), encoding="utf-8")
    r = engine.load_game("test-fen.pgn")
    assert "error" not in r and r["moves"] == ["Nxe5"]
    assert "FEN" in engine.to_pgn() and "SetUp" in engine.to_pgn()
    engine.undo()
    assert engine.board.fen().split()[0] == chess.Board(fen).board_fen()


def test_malformed_and_missing(engine: ChessEngine):
    Path("games/test-bad.pgn").write_text("esto no es un pgn válido (((\n", encoding="utf-8")
    assert "error" in engine.load_game("test-bad.pgn")
    assert "error" in engine.load_game("test-noexiste.pgn")
    assert engine.state.status == "in_progress"


def test_parse_san_and_uci(engine: ChessEngine):
    assert engine._parse_move("e4") == chess.Move.from_uci("e2e4")
    assert engine._parse_move("e2e4") == chess.Move.from_uci("e2e4")
    assert engine._parse_move("Nf3") == chess.Move.from_uci("g1f3")
    assert engine._parse_move("e5") is None  # ilegal en inicial
    assert engine._parse_move("zzz") is None
