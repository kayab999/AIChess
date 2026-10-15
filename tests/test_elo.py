"""Fidelidad ELO: mismo seed, ELOs distintos deben jugar distinto (auditoría H2)."""
from chess_engine import ChessEngine


def _seq(elo):
    e = ChessEngine(elo=elo, seed=42)
    e.toggle_coach(False)
    try:
        for mv in ("e4", "Nf3", "Bc4", "d3"):
            if "error" in e.player_move(mv):
                break
        return list(e.state.moves_history)
    finally:
        e.close()


def test_elo_changes_play():
    assert _seq(1320) != _seq(3190)
