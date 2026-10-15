"""
board_svg.py — Tablero 2D para AI Chess.
SVG nítido con chess.svg (sin dependencias) + PNG raster vía cairosvg.
El SVG es la única fuente de verdad: misma posición, tema y resaltados.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import chess
import chess.svg


BOARDS_DIR = Path(__file__).parent / "boards"

DEFAULT_PNG_SIZE = 960
MIN_PNG_SIZE = 256
MAX_PNG_SIZE = 2048

# Tema lichess marrón, coordinado con el ANSI (grises) en espíritu:
# claras cálidas, oscuras tierra, última jugada amarilla, jaque rojo.
THEME = {
    "square light": "#f0d9b5",
    "square dark": "#b58863",
    "square light lastmove": "#cdd26a",
    "square dark lastmove": "#aaa23a",
}


def parse_orientation(value: str = "blancas") -> chess.Color:
    """Acepta blancas/negras/white/black/w/b (case-insensitive)."""
    v = (value or "blancas").strip().lower()
    if v in ("negras", "negro", "black", "b", "n"):
        return chess.BLACK
    return chess.WHITE


def to_svg(
    board: chess.Board,
    orientation: str = "blancas",
    lastmove: bool = True,
    check: bool = True,
) -> str:
    """Renderiza el tablero a string SVG."""
    last = board.peek() if (lastmove and board.move_stack) else None
    king = board.king(board.turn) if (check and board.is_check()) else None
    return chess.svg.board(
        board,
        orientation=parse_orientation(orientation),
        lastmove=last,
        check=king,
        coordinates=True,
        colors=dict(THEME),
    )


def clamp_size(size: int) -> int:
    try:
        size = int(size)
    except (TypeError, ValueError):
        size = DEFAULT_PNG_SIZE
    return max(MIN_PNG_SIZE, min(MAX_PNG_SIZE, size))


def to_png(
    board: chess.Board,
    orientation: str = "blancas",
    size: int = DEFAULT_PNG_SIZE,
) -> bytes:
    """Renderiza el tablero a bytes PNG (vía SVG, misma fuente de verdad)."""
    try:
        import cairosvg
    except ImportError as exc:
        raise RuntimeError(
            "Falta cairosvg. Instálalo con: .venv/bin/pip install -r requirements.txt"
        ) from exc
    svg = to_svg(board, orientation=orientation)
    return cairosvg.svg2png(bytestring=svg.encode("utf-8"), output_width=clamp_size(size))


def save_board_png(
    board: chess.Board,
    path: Optional[str] = None,
    orientation: str = "blancas",
    size: int = DEFAULT_PNG_SIZE,
) -> dict:
    """Guarda el PNG en boards/. Auto-nombre si no se da ruta."""
    import datetime
    size = clamp_size(size)
    BOARDS_DIR.mkdir(parents=True, exist_ok=True)
    if path:
        dest = Path(path)
        if not dest.is_absolute():
            dest = BOARDS_DIR / dest
    else:
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        dest = BOARDS_DIR / f"board-{stamp}.png"
    if dest.suffix != ".png":
        dest = dest.with_suffix(".png")
    dest.write_bytes(to_png(board, orientation=orientation, size=size))
    return {"path": str(dest), "size": size}


def save_board_svg(
    board: chess.Board,
    path: Optional[str] = None,
    orientation: str = "blancas",
) -> dict:
    """Guarda el SVG en boards/. Auto-nombre si no se da ruta."""
    import datetime
    BOARDS_DIR.mkdir(parents=True, exist_ok=True)
    if path:
        dest = Path(path)
        if not dest.is_absolute():
            dest = BOARDS_DIR / dest
    else:
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        dest = BOARDS_DIR / f"board-{stamp}.svg"
    if dest.suffix != ".svg":
        dest = dest.with_suffix(".svg")
    dest.write_text(to_svg(board, orientation=orientation), encoding="utf-8")
    return {"path": str(dest)}
