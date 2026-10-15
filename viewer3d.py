"""
viewer3d.py — Genera el visor 3D (Three.js) con la posición actual embebida.
Estilos: clasico (Staunton), antiguo (Lewis), cyberpunk (neón), wizard (fantasía).
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Optional

import chess

from chess_engine import BOARDS_DIR, sandboxed

STYLES_3D = ["clasico", "antiguo", "cyberpunk", "wizard"]

TEMPLATE = Path(__file__).parent / "assets3d" / "viewer3d.html"


def save_viewer3d(
    board: chess.Board,
    moves_uci: list[str],
    moves_san: list[str],
    status: str,
    turn: str,
    elo: int,
    style: str = "clasico",
    path: Optional[str] = None,
    refresh: int = 5,
) -> dict:
    """Rellena la plantilla y guarda boards/viewer3d-<style>.html."""
    style = (style or "clasico").strip().lower()
    if style not in STYLES_3D:
        raise KeyError(f"Estilo desconocido: {style!r}. Válidos: {', '.join(STYLES_3D)}")
    try:
        refresh = max(0, min(60, int(refresh)))
    except (TypeError, ValueError):
        refresh = 5

    check_sq = None
    if board.is_check():
        king = board.king(board.turn)
        if king is not None:
            check_sq = chess.square_name(king)

    data = {
        "fen": board.fen(),
        "movesUci": moves_uci,
        "style": style,
        "checkSq": check_sq,
        "turn": turn,
    }
    tpl = TEMPLATE.read_text(encoding="utf-8")
    meta = f'<meta http-equiv="refresh" content="{refresh}">' if refresh else ""
    moves_txt = " ".join(moves_san[-10:]) if moves_san else "(vacío)"
    out = (tpl.replace("__STYLE__", style)
              .replace("__REFRESH_META__", meta)
              .replace("__DATA_JSON__", json.dumps(data))
              .replace("__STATUS__", html.escape(status))
              .replace("__TURN__", html.escape(turn))
              .replace("__ELO__", str(elo))
              .replace("__MOVES__", html.escape(moves_txt)))

    BOARDS_DIR.mkdir(parents=True, exist_ok=True)
    from chess_engine import sandboxed
    # Sandbox: siempre dentro de boards/, luego las rutas ../assets valen
    dest = sandboxed(BOARDS_DIR, path or f"viewer3d-{style}.html", ".html", "viewer3d")
    dest.write_text(out, encoding="utf-8")
    return {"path": str(dest), "style": style}
