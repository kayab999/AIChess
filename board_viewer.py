"""
board_viewer.py — Visor HTML para AI Chess.
Genera un monofichero autocontenido (splash + icono en base64, SVG inline):
funciona con file:// sin servidor. Auto-refresh vía <meta refresh>.
"""

from __future__ import annotations

import base64
import html
from pathlib import Path
from typing import Optional

import chess

ASSETS_DIR = Path(__file__).parent / "assets"
BOARDS_DIR = Path(__file__).parent / "boards"


def _data_uri(path: Path) -> str:
    raw = path.read_bytes()
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


def render_viewer(
    board: chess.Board,
    svg: str,
    moves: list[str],
    status: str,
    turn: str,
    elo: int,
    coach: Optional[dict] = None,
    refresh: int = 5,
    generated: str = "",
) -> str:
    """Compón el HTML completo del visor."""
    splash = _data_uri(ASSETS_DIR / "splash.png")
    icon = _data_uri(ASSETS_DIR / "icon.png")

    moves_txt = " ".join(moves[-12:]) if moves else "(vacío)"
    coach_html = ""
    if coach:
        coach_html = (
            f"<div class='coach'><span class='emoji'>{html.escape(coach.get('emoji', ''))}</span> "
            f"<b>{html.escape(coach.get('veredicto', ''))}</b> "
            f"<span class='cp'>({coach.get('cp_loss', 0):.0f}cp)</span><br>"
            f"{html.escape(coach.get('consejo', ''))}</div>"
        )

    try:
        refresh = int(refresh)
    except (TypeError, ValueError):
        refresh = 5
    refresh = max(0, min(60, refresh))
    meta = f'<meta http-equiv="refresh" content="{refresh}">' if refresh else ""

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{meta}
<title>♟️ AI Chess</title>
<link rel="icon" href="{icon}">
<style>
  :root {{ --bg: #0a1628; --panel: #10233f; --accent: #35e0ff; --txt: #d7e6f5; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--bg); color: var(--txt);
         font-family: system-ui, sans-serif; display: flex; min-height: 100vh; }}
  #splash {{ position: fixed; inset: 0; z-index: 10; display: flex;
            align-items: center; justify-content: center; background: #050b16;
            animation: splashout 0.8s ease 1.5s forwards; pointer-events: none; }}
  #splash img {{ max-width: 90vw; max-height: 90vh; border-radius: 12px; }}
  @keyframes splashout {{ to {{ opacity: 0; visibility: hidden; }} }}
  main {{ display: flex; gap: 24px; padding: 24px; margin: auto;
         flex-wrap: wrap; align-items: flex-start; justify-content: center; }}
  .board svg {{ width: min(90vmin, 640px); height: auto; border-radius: 8px;
               box-shadow: 0 0 40px rgba(53,224,255,.25); }}
  aside {{ background: var(--panel); border-radius: 12px; padding: 20px;
          min-width: 280px; max-width: 360px; }}
  h1 {{ color: var(--accent); margin: 0 0 12px; font-size: 1.4em; }}
  .row {{ margin: 8px 0; }}
  .moves {{ font-family: monospace; background: #081426; padding: 10px;
           border-radius: 8px; line-height: 1.7; }}
  .coach {{ margin-top: 12px; background: #0d2b1d; border-left: 4px solid #4ade80;
           padding: 10px; border-radius: 0 8px 8px 0; }}
  .cp {{ color: #9fb3c8; }}
  footer {{ color: #5b7288; font-size: .8em; margin-top: 12px; }}
</style>
</head>
<body>
<div id="splash"><img src="{splash}" alt="AI Chess"></div>
<main>
  <div class="board">{svg}</div>
  <aside>
    <h1>♟️ AI Chess</h1>
    <div class="row">Turno: <b>{html.escape(turn)}</b> · Estado: <b>{html.escape(status)}</b></div>
    <div class="row">Rival: Stockfish ELO {elo}</div>
    <div class="row moves">{html.escape(moves_txt)}</div>
    {coach_html}
    <footer>Actualizado: {html.escape(generated)} · refresh {refresh}s</footer>
  </aside>
</main>
</body>
</html>
"""


def save_viewer(
    board: chess.Board,
    svg: str,
    moves: list[str],
    status: str,
    turn: str,
    elo: int,
    coach: Optional[dict] = None,
    path: Optional[str] = None,
    refresh: int = 5,
) -> dict:
    """Guarda el visor en boards/viewer.html (nombre fijo, sobrescribe)."""
    import datetime
    BOARDS_DIR.mkdir(parents=True, exist_ok=True)
    if path:
        dest = Path(path)
        if not dest.is_absolute():
            dest = BOARDS_DIR / dest
    else:
        dest = BOARDS_DIR / "viewer.html"
    if dest.suffix != ".html":
        dest = dest.with_suffix(".html")
    generated = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dest.write_text(
        render_viewer(board, svg, moves, status, turn, elo, coach, refresh, generated),
        encoding="utf-8",
    )
    return {"path": str(dest)}
