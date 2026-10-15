"""
chess_mcp_server.py — Servidor MCP para AI Chess (MCP SDK 2.x).
Expone herramientas que un agente puede invocar para jugar contra Stockfish.
Transporte: stdio (genérico, compatible con Claude Desktop y otros clientes).

Icono del proyecto: aichess.png
Splash screen: aichesssplashscreen.png
"""

from mcp.server.mcpserver import MCPServer

import chess

from pathlib import Path
from threading import Lock

from chess_engine import get_engine, close_engine


_ENGINE_LOCK = Lock()  # las tools síncronas corren en hilos: mutaciones bajo lock


def _io_guard(fn):
    """Las tools de ficheros nunca devuelven tracebacks al cliente."""
    import functools

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (ValueError, OSError, RuntimeError) as exc:
            return f"❌ {exc}"
    return wrapper


def _locked(fn):
    """Serializa las mutaciones de partida (el SDK ejecuta tools en hilos)."""
    import functools

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        with _ENGINE_LOCK:
            return fn(*args, **kwargs)
    return wrapper


mcp = MCPServer(
    name="ai-chess",
    instructions=(
        "Servidor de ajedrez. El usuario juega blancas, Stockfish (bot) juega negras. "
        "Usa new_game para empezar, make_move para jugar (incluye feedback del entrenador), "
        "get_board/get_status para ver, analyze/hint(level 1-3) para ayuda, "
        "explain_move para entender la última jugada, coach_status para ver problemas, "
        "export_pgn/save_game/load_game/list_games para persistir partidas, "
        "get_board_svg/save_board_image para tablero 2D vectorial, "
        "get_board_png/save_board_png para tablero PNG raster, "
        "get_board_viewer para visor HTML con splash, "
        "list_personalities/set_personality para elegir rival (arquetipos y leyendas), "
        "lookup_history/opening_info/search_classics para la base histórica, "
        "get_board_3d/list_3d_styles para el visor 3D animado, "
        "undo para deshacer, resign para abandonar, claim_draw para tablas."
    ),
)


def _format_state(state: dict) -> str:
    """Formatea el estado tras una jugada (incluye feedback coach si existe)."""
    last_moves = " ".join(state["moves"][-4:]) if state["moves"] else "—"
    status_icons = {
        "checkmate": "🏁 JAQUE MATE",
        "stalemate": "🤝 AHOGADO",
        "draw": "🤝 TABLAS",
        "finished": "🏁 FINAL",
        "check": "⚠️ JAQUE",
        "resigned": "🏳️ ABANDONO",
        "in_progress": "",
    }
    icon = status_icons.get(state["status"], "")

    lines = [state["board_ascii"], ""]
    if icon:
        lines.append(f"{icon} — Resultado: {state['result']}")
    lines.append(f"Últimos movimientos: {last_moves}")
    lines.append(f"Turno: {state['turn']}")

    coach = state.get("coach")
    if coach:
        lines.append("")
        lines.append(f"🎓 Entrenador: {coach.get('emoji','')} {coach.get('veredicto','')} — {coach.get('consejo','')}")
        if coach.get("classic"):
            lines.append(f"📜 Historia: {coach['classic']}")
    return "\n".join(lines)


@mcp.tool(
    name="new_game",
    description=("Inicia una nueva partida contra 'club' (ELO 1600) por defecto. "
                "Con personality se usa su ELO salvo elo explícito distinto de 1600. "
                "Con elo explícito se usa esa fuerza con el estilo de la personalidad."),
)
@_locked
def new_game(elo: int = 1600, personality: str = "club") -> str:
    engine = get_engine()
    try:
        state = engine.reset(
            elo=elo if elo != 1600 else None,
            personality=personality or None,
        )
    except KeyError as exc:
        return f"❌ {exc}"
    return (f"♟️ Nueva partida vs {state['personality_name']} (ELO {state['elo']})\n\n"
            f"{state['board_ascii']}")


@mcp.tool(
    name="make_move",
    description="Juega un movimiento en SAN (e4, Nf3, O-O) o UCI (e2e4). El bot responde automáticamente. Incluye feedback del entrenador.",
)
@_locked
def make_move(move: str) -> str:
    engine = get_engine()
    result = engine.player_move(move)
    if "error" in result:
        legal = ", ".join(result.get("legal_moves", [])[:15])
        return f"❌ {result['error']}\n\nMovimientos legales (primeros 15): {legal}..."
    # Si el visor 2D ya existe, se regenera para el auto-refresh (best effort)
    try:
        if (Path(__file__).parent / "boards" / "viewer.html").exists():
            engine.save_viewer()
    except Exception:
        pass
    return _format_state(result)


@mcp.tool(
    name="get_board",
    description="Muestra el tablero actual en Unicode. Usa color=true para versión ANSI con casillas coloreadas, última jugada y jaque resaltados (ideal para terminales).",
)
def get_board(color: bool = False) -> str:
    return get_engine().get_board_ascii(color=color)


@mcp.tool(
    name="get_status",
    description="Estado completo: turno, jaque, resultado, historial y tablero.",
)
def get_status() -> str:
    state = get_engine().get_state()
    history = " ".join(state["moves"][-10:]) if state["moves"] else "(vacío)"
    return (
        f"Turno: {state['turn']}\n"
        f"Estado: {state['status']}\n"
        f"Resultado: {state['result'] or '—'}\n"
        f"Jaque: {'sí' if state['in_check'] else 'no'}\n"
        f"Movimientos: {history}\n\n"
        f"{state['board_ascii']}"
    )


@mcp.tool(
    name="get_legal_moves",
    description="Lista todos los movimientos legales en notación SAN.",
)
def get_legal_moves() -> str:
    moves = get_engine().get_legal_moves_san()
    return f"{len(moves)} movimientos legales:\n" + ", ".join(moves)


@mcp.tool(
    name="undo",
    description="Deshace la última ronda (la tuya y la del bot). También reabre tras mate o abandono.",
)
@_locked
def undo() -> str:
    state = get_engine().undo()
    if "error" in state:
        return f"❌ {state['error']}"
    return f"↩️ Jugada deshecha.\n\n{state['board_ascii']}"


@mcp.tool(
    name="claim_draw",
    description="Reclama tablas por triple repetición o 50 movimientos, si aplica.",
)
@_locked
def claim_draw() -> str:
    result = get_engine().claim_draw()
    if "error" in result:
        return f"❌ {result['error']}"
    return f"🤝 Tablas por {result.get('claim', '?')}. Resultado: {result['result']}"


@mcp.tool(
    name="resign",
    description="Abandona la partida actual (pierdes 0-1).",
)
@_locked
def resign() -> str:
    state = get_engine().resign()
    return f"🏳️ Has abandonado. Resultado: {state['result']}"


@mcp.tool(
    name="analyze",
    description="Analiza la posición actual con Stockfish. Devuelve evaluación, mejor jugada y profundidad.",
)
def analyze(depth: int = 15) -> str:
    info = get_engine().analyze(depth=depth)
    if "error" in info:
        return f"❌ {info['error']}"
    return (
        f"📊 Análisis (profundidad {info['depth']}):\n"
        f"  Evaluación: {info['evaluation']}\n"
        f"  Mejor jugada: {info['best_move']}\n"
        f"  Turno: {info['turn']}"
    )


@mcp.tool(
    name="hint",
    description="Pista progresiva sin jugarla: nivel 1 idea general, 2 zona candidata, 3 jugada exacta. Repetir en la misma posición auto-escala.",
)
def hint(level: int = 1) -> str:
    info = get_engine().hint_with_level(level=level)
    if "error" in info:
        return f"❌ {info['error']}"
    return f"💡 Nivel {info['level']}: {info['hint']}"


@mcp.tool(
    name="explain_move",
    description="Explica por qué la última jugada del usuario fue buena o mala (veredicto + pérdida + consejo).",
)
def explain_move() -> str:
    info = get_engine().explain_last()
    if "error" in info:
        return f"❌ {info['error']}"
    return (
        f"{info.get('emoji','')} Veredicto: {info.get('veredicto','')}\n"
        f"Pérdida: {info.get('cp_loss',0):.0f} centipeones\n"
        f"Consejo: {info.get('consejo','')}"
    )


@mcp.tool(
    name="coach_status",
    description="Snapshot del entrenador: piezas colgadas, desarrollo y seguridad del rey en la posición actual.",
)
def coach_status() -> str:
    info = get_engine().coach_status()
    issues = info.get("current_issues", {})
    enabled = "✅ activo" if info.get("coach_enabled") else "❌ inactivo"
    lines = [
        f"🎓 Modo entrenador: {enabled}",
        f"Jugada núm: {info.get('move_number',0)} | Turno: {info.get('turn','')}",
        "Problemas actuales:",
        f"  • Piezas colgadas: {issues.get('piezas_colgadas',0)}",
        f"  • Desarrollo: {issues.get('problemas_desarrollo',0)}",
        f"  • Seguridad del rey: {issues.get('seguridad_rey',0)}",
    ]
    detalle = info.get("detalle_colgadas") or []
    if detalle:
        lines.append("Detalle: " + "; ".join(detalle))
    return "\n".join(lines)


@mcp.tool(
    name="toggle_coach",
    description="Activa o desactiva el feedback automático del entrenador tras cada jugada.",
)
def toggle_coach(enabled: bool = True) -> str:
    get_engine().toggle_coach(enabled)
    return f"🎓 Modo entrenador {'activado' if enabled else 'desactivado'}"


@mcp.tool(
    name="export_pgn",
    description="Devuelve la partida actual en formato PGN estándar (headers + movimientos).",
)
def export_pgn() -> str:
    return get_engine().to_pgn()


@mcp.tool(
    name="save_game",
    description="Guarda la partida en games/ (auto-nombre con fecha) o en el nombre dado. Devuelve el path.",
)
@_io_guard
def save_game(path: str = "") -> str:
    res = get_engine().save_game(path or None)
    return f"💾 Partida guardada ({res['moves']} jugadas): {res['path']}"


@mcp.tool(
    name="load_game",
    description="Carga la primera partida de un PGN de games/ y restaura el tablero.",
)
@_io_guard
def load_game(path: str) -> str:
    result = get_engine().load_game(path)
    if "error" in result:
        return f"❌ {result['error']}"
    moves = " ".join(result["moves"][-6:]) if result["moves"] else "(vacía)"
    return f"📂 Cargada desde {result.get('loaded_from')}\nMovimientos: {moves}\n\n{result['board_ascii']}"


@mcp.tool(
    name="list_games",
    description="Lista las partidas PGN guardadas en games/.",
)
def list_games() -> str:
    res = get_engine().list_games()
    if not res["games"]:
        return "Sin partidas guardadas en games/."
    return f"📚 {res['count']} partidas:\n" + "\n".join(f"  • {g}" for g in res["games"])


@mcp.tool(
    name="get_board_svg",
    description="Genera el tablero 2D como SVG (última jugada y jaque resaltados), lo guarda en boards/ y devuelve la ruta. orientation: blancas/negras.",
)
@_io_guard
def get_board_svg(orientation: str = "blancas") -> str:
    res = get_engine().save_board_image(orientation=orientation)
    return f"🖼️ Tablero SVG: {res['path']}"


@mcp.tool(
    name="save_board_image",
    description="Guarda el tablero SVG en la ruta dada (o auto-nombre en boards/). Devuelve el path.",
)
@_io_guard
def save_board_image(path: str = "", orientation: str = "blancas") -> str:
    res = get_engine().save_board_image(path or None, orientation=orientation)
    return f"🖼️ Tablero guardado: {res['path']}"


@mcp.tool(
    name="get_board_png",
    description="Genera el tablero como PNG raster (960px por defecto, 256-2048), lo guarda en boards/ y devuelve la ruta con el tamaño.",
)
@_io_guard
def get_board_png(orientation: str = "blancas", size: int = 960) -> str:
    try:
        res = get_engine().save_board_png(orientation=orientation, size=size)
    except RuntimeError as exc:
        return f"❌ {exc}"
    return f"🖼️ Tablero PNG ({res['size']}px): {res['path']}"


@mcp.tool(
    name="save_board_png",
    description="Guarda el tablero PNG en la ruta dada (o auto-nombre en boards/). orientation: blancas/negras, size 256-2048.",
)
@_io_guard
def save_board_png(path: str = "", orientation: str = "blancas", size: int = 960) -> str:
    try:
        res = get_engine().save_board_png(path or None, orientation=orientation, size=size)
    except RuntimeError as exc:
        return f"❌ {exc}"
    return f"🖼️ Tablero PNG guardado ({res['size']}px): {res['path']}"


@mcp.tool(
    name="get_board_viewer",
    description="Genera el visor HTML (splash de carga + tablero + jugadas + coach, auto-refresh) y devuelve la ruta para abrirlo en el navegador.",
)
@_io_guard
def get_board_viewer(refresh: int = 5) -> str:
    res = get_engine().save_viewer(refresh=refresh)
    return f"🌐 Visor: {res['path']} (ábrelo en el navegador)"


@mcp.tool(
    name="list_3d_styles",
    description="Lista los 4 estilos 3D: clasico, antiguo, cyberpunk, wizard.",
)
def list_3d_styles() -> str:
    return ("🧊 Estilos 3D:\n"
            "  • clasico — Staunton de madera\n"
            "  • antiguo — Lewis, marfil y rojo\n"
            "  • cyberpunk — neón translúcido\n"
            "  • wizard — piedra rúnica con chispas")


@mcp.tool(
    name="get_board_3d",
    description="Genera el visor 3D animado (Three.js, reproduce la partida, jaque pulsante) y devuelve la ruta. style: clasico/antiguo/cyberpunk/wizard.",
)
@_io_guard
def get_board_3d(style: str = "clasico", refresh: int = 5) -> str:
    try:
        res = get_engine().save_viewer3d(style=style, refresh=refresh)
    except KeyError as exc:
        return f"❌ {exc}"
    return f"🧊 Visor 3D ({res['style']}): {res['path']} (ábrelo en el navegador)"


@mcp.tool(
    name="list_personalities",
    description="Lista las 15 personalidades (6 arquetipos + 8 leyendas + socio del club) con ELO y estilo.",
)
def list_personalities() -> str:
    from personalities import list_personalities as _list
    lines = ["🎭 Personalidades AI Chess:"]
    for p in _list():
        lines.append(f"  • {p['key']} — {p['name']} (ELO {p['elo']}): {p['desc']}")
    return "\n".join(lines)


@mcp.tool(
    name="set_personality",
    description="Cambia la personalidad del rival (fija su ELO y estilo) e inicia partida nueva.",
)
@_locked
def set_personality(key: str) -> str:
    from personalities import get_personality
    try:
        engine = get_engine()
        engine.set_personality(key)
        state = engine.reset()
    except KeyError as exc:
        return f"❌ {exc}"
    p = get_personality(state["personality"])
    return (f"🎭 Ahora juegas contra {p.name} (ELO {state['elo']})\n"
            f"{p.desc}\n\n{state['board_ascii']}")


@mcp.tool(
    name="lookup_history",
    description="Qué jugaron Fischer/Tal en la posición actual (base CC0: 162 clásicas).",
)
def lookup_history() -> str:
    from history import get_history
    board = get_engine().board
    refs = get_history().lookup_board(board)[:5]
    if not refs:
        return "📜 Sin referencias clásicas para esta posición."
    lines = [f"📜 {len(refs)} referencia(s) — la primera movida de cada maestro:"]
    for r in refs[:5]:
        mover = r.white if board.turn == chess.WHITE else r.black
        lines.append(f"  • {mover}: {r.move_san} ({r.event}, {r.date[:4]}, {r.result})")
    return "\n".join(lines)


@mcp.tool(
    name="opening_info",
    description="Nombre ECO de la apertura en juego y qué hicieron las leyendas desde aquí.",
)
def opening_info() -> str:
    from eco import opening_name
    from history import get_history
    engine = get_engine()
    name, eco = opening_name(engine.state.moves_history)
    stats = get_history().stats(engine.board)
    lines = [f"📖 Apertura: {name}" + (f" ({eco})" if eco else "")]
    if stats:
        top = sorted(stats.items(), key=lambda kv: -kv[1]["games"])[:4]
        lines.append("Las leyendas jugaron aquí:")
        for mv, s in top:
            lines.append(f"  • {mv}: {s['games']} partidas (1-0 {s['w']}, = {s['d']}, 0-1 {s['b']})")
    return "\n".join(lines)


@mcp.tool(
    name="search_classics",
    description="Busca partidas clásicas por jugador (fischer, tal...). Hasta 10 resultados.",
)
def search_classics(player: str) -> str:
    from history import get_history
    games = get_history().search_player(player, limit=10)
    if not games:
        return f"📜 Sin partidas de {player!r} (prueba fischer o tal)."
    lines = [f"📜 Clásicas de {player} ({len(games)}):"]
    for g in games:
        lines.append(f"  • {g.white} vs {g.black} ({g.event}, {g.date[:4]}) {g.result} — {len(g.moves_san)} jugadas")
    return "\n".join(lines)


if __name__ == "__main__":
    import atexit
    atexit.register(close_engine)
    mcp.run()
