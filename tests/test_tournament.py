"""Torneo: ucinewgame por partida y harness mínimo (auditoría M10)."""
import subprocess
import sys
from pathlib import Path

import chess.engine

ROOT = Path(__file__).parent.parent
PY = sys.executable


def test_rival_reseeds_and_renews():
    sys.path.insert(0, str(ROOT))
    from tournament import Rival
    r = Rival("novato", 0.1, seed=7)
    try:
        first_engine = r.engine
        r.new_game(0)
        assert r.engine is not first_engine  # proceso fresco: hash limpio
        r.new_game(1)
        a = r.rng.random()
        r.new_game(1)
        assert r.rng.random() == a  # misma partida -> misma secuencia
    finally:
        r.close()


def test_mini_tournament_end_to_end():
    proc = subprocess.run(
        [PY, "tournament.py", "--players", "novato,stanley",
         "--games", "1", "--time", "0.1", "--max-ply", "60"],
        capture_output=True, text=True, cwd=str(ROOT), timeout=300,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "Tabla:" in proc.stdout
    made = sorted((ROOT / "games").glob("tour-*.pgn"))
    assert made, "el torneo debe guardar PGNs"
    for f in made:
        f.unlink()
