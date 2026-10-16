"""Fidelidad ELO: mismo seed, ELOs distintos deben jugar distinto (auditoría H2)."""
import pytest

from chess_engine import ChessEngine


def _seq(elo, seed):
    e = ChessEngine(elo=elo, seed=seed)
    e.toggle_coach(False)
    try:
        for mv in ("e4", "Nf3", "Bc4", "d3"):
            if "error" in e.player_move(mv):
                break
        return list(e.state.moves_history)
    finally:
        e.close()


@pytest.mark.parametrize("seed", [42, 7])
def test_elo_changes_play(seed):
    assert _seq(1320, seed) != _seq(3190, seed)
