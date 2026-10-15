"""
cli_test.py — Juega al ajedrez desde la terminal (sin MCP).
Útil para verificar que Stockfish y python-chess funcionan.

Icono: aichess.png | Splash: aichesssplashscreen.png
"""

from pathlib import Path
import sys

from chess_engine import ChessEngine

SPLASH = Path(__file__).parent / "aichesssplashscreen.png"
ICON = Path(__file__).parent / "aichess.png"

BANNER = r"""
   ___    ____   ______ __  ________________
  / _ |  /  _/  / ____// / / / __/ ___/ __/
 / __ |_/ /   / /___ / /_/ / _/ / /__ \ \
/_/ |_/___/  /____/ \____/ /___/ \___/___/
           ♟️  AI CHESS — MVP
"""


def main():
    print(BANNER)
    if SPLASH.exists():
        print(f"[splash: {SPLASH.name} — {SPLASH.stat().st_size // 1024} KB]")
    if ICON.exists():
        print(f"[icono: {ICON.name} — {ICON.stat().st_size // 1024} KB]")
    print("Comandos: [movimiento e4/Nf3/e2e4] | hint [1|2|3] | explain | coach on/off | color on/off | pgn | save [ruta] | load <ruta> | games | svg [blancas|negras] | png [blancas|negras] [tamaño] | viewer [refresh] | 3d [estilo] | personalities | personality <key> | history | opening | status | moves | analyze | undo | resign | quit\n")

    engine = ChessEngine(elo=1600)
    use_color = sys.stdout.isatty()

    def show_board(state: dict) -> None:
        print(engine.render_ascii(color=use_color))

    try:
        while True:
            state = engine.get_state()
            show_board(state)
            print(f"Turno: {state['turn']} | Estado: {state['status']}")

            if state["status"] in ("checkmate", "stalemate", "draw", "resigned"):
                print(f"Partida terminada: {state['result']}")
                break

            try:
                cmd = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            low = cmd.lower()
            if low in ("quit", "exit", "q"):
                break
            if low == "undo":
                engine.undo()
                continue
            if low.startswith("hint"):
                parts = cmd.split()
                level = 1
                if len(parts) > 1:
                    try:
                        level = max(1, min(3, int(parts[1])))
                    except ValueError:
                        print("Uso: hint [1|2|3]")
                        continue
                res = engine.hint_with_level(level=level)
                if "error" in res:
                    print(f"❌ {res['error']}")
                else:
                    print(f"💡 Nivel {res['level']}: {res['hint']}")
                continue
            if low == "explain":
                res = engine.explain_last()
                if "error" in res:
                    print(f"❌ {res['error']}")
                else:
                    print(f"🎓 {res['emoji']} {res['veredicto']} ({res['cp_loss']:.0f}cp): {res['consejo']}")
                continue
            if low == "coach on":
                engine.toggle_coach(True)
                print("🎓 Modo entrenador ACTIVADO")
                continue
            if low == "coach off":
                engine.toggle_coach(False)
                print("🎓 Modo entrenador DESACTIVADO")
                continue
            if low == "color on":
                use_color = True
                print("🎨 Color ACTIVADO")
                continue
            if low == "color off":
                use_color = False
                print("🎨 Color DESACTIVADO (plano, apto MCP)")
                continue
            if low == "pgn":
                print(engine.to_pgn())
                continue
            if low.startswith("save"):
                parts = cmd.split(maxsplit=1)
                dest = parts[1].strip() if len(parts) > 1 else None
                res = engine.save_game(dest)
                print(f"💾 Guardada ({res['moves']} jugadas): {res['path']}")
                continue
            if low.startswith("load"):
                parts = cmd.split(maxsplit=1)
                if len(parts) < 2:
                    print("Uso: load <ruta o nombre en games/>")
                    continue
                res = engine.load_game(parts[1].strip())
                if "error" in res:
                    print(f"❌ {res['error']}")
                else:
                    print(f"📂 Cargada desde {res.get('loaded_from')}")
                continue
            if low == "games":
                res = engine.list_games()
                if not res["games"]:
                    print("Sin partidas en games/.")
                else:
                    print(f"📚 {res['count']} partidas:")
                    for g in res["games"]:
                        print(f"  • {g}")
                continue
            if low.startswith("svg"):
                parts = cmd.split()
                ori = parts[1] if len(parts) > 1 else "blancas"
                res = engine.save_board_image(orientation=ori)
                print(f"🖼️ Tablero SVG: {res['path']}")
                continue
            if low.startswith("png"):
                parts = cmd.split()
                ori = parts[1] if len(parts) > 1 else "blancas"
                size = 960
                if len(parts) > 2:
                    try:
                        size = int(parts[2])
                    except ValueError:
                        print("Uso: png [blancas|negras] [tamaño 256-2048]")
                        continue
                try:
                    res = engine.save_board_png(orientation=ori, size=size)
                except RuntimeError as exc:
                    print(f"❌ {exc}")
                    continue
                print(f"🖼️ Tablero PNG ({res['size']}px): {res['path']}")
                continue
            if low.startswith("viewer"):
                parts = cmd.split()
                refresh = 5
                if len(parts) > 1:
                    try:
                        refresh = max(0, min(60, int(parts[1])))
                    except ValueError:
                        print("Uso: viewer [segundos refresh 0-60]")
                        continue
                res = engine.save_viewer(refresh=refresh)
                print(f"🌐 Visor: {res['path']} (ábrelo en el navegador)")
                continue
            if low.startswith("3d"):
                parts = cmd.split()
                style = parts[1] if len(parts) > 1 else "clasico"
                try:
                    res = engine.save_viewer3d(style=style)
                except KeyError as exc:
                    print(f"❌ {exc}")
                    continue
                print(f"🧊 Visor 3D ({res['style']}): {res['path']}")
                continue
            if low == "personalities":
                from personalities import list_personalities as _list
                for p in _list():
                    mark = "→" if p["key"] == engine.personality_key else " "
                    print(f"{mark} {p['key']:12} {p['name']} (ELO {p['elo']}): {p['desc']}")
                continue
            if low.startswith("personality"):
                parts = cmd.split(maxsplit=1)
                if len(parts) < 2:
                    print("Uso: personality <key>  (ver 'personalities')")
                    continue
                try:
                    info = engine.set_personality(parts[1].strip())
                    engine.reset()
                    print(f"🎭 Rival: {info['name']} (ELO {info['elo']})")
                except KeyError as exc:
                    print(f"❌ {exc}")
                continue
            if low == "history":
                from history import get_history
                refs = get_history().lookup_board(engine.board)[:5]
                if not refs:
                    print("📜 Sin referencias clásicas aquí.")
                else:
                    for r in refs:
                        print(f"📜 {r.white} vs {r.black}: {r.move_san} ({r.event}, {r.date[:4]}, {r.result})")
                continue
            if low == "opening":
                from eco import opening_name
                from history import get_history
                name, eco = opening_name(engine.state.moves_history)
                print(f"📖 {name}" + (f" ({eco})" if eco else ""))
                for mv, s in sorted(get_history().stats(engine.board).items(),
                                    key=lambda kv: -kv[1]["games"])[:4]:
                    print(f"   {mv}: {s['games']} ({s['w']}-{s['d']}-{s['b']})")
                continue
            if low == "status":
                st = engine.coach_status()
                on = "activo" if st.get("coach_enabled") else "inactivo"
                iss = st.get("current_issues", {})
                print(f"🎓 Coach {on} | jugada {st.get('move_number')}")
                print(f"   Colgadas: {iss.get('piezas_colgadas',0)} | Desarrollo: {iss.get('problemas_desarrollo',0)} | Rey: {iss.get('seguridad_rey',0)}")
                if st.get("detalle_colgadas"):
                    print("   " + "; ".join(st["detalle_colgadas"]))
                continue
            if low == "analyze":
                print(engine.analyze(depth=15))
                continue
            if low == "moves":
                print(", ".join(engine.get_legal_moves_san()))
                continue
            if low == "resign":
                print(engine.resign())
                break
            if not cmd:
                continue

            result = engine.player_move(cmd)
            if "error" in result:
                print(f"❌ {result['error']}")
            elif "coach" in result:
                coach = result["coach"]
                print(f"🎓 {coach['emoji']} {coach['veredicto']} ({coach['cp_loss']:.0f}cp): {coach['consejo']}")
    finally:
        engine.close()
    print("¡Hasta la próxima! ♟️")


if __name__ == "__main__":
    main()
