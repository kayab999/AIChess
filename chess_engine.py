"""
chess_engine.py — Núcleo del juego de ajedrez AI Chess.
Encapsula python-chess + Stockfish con una API limpia.
Sin dependencias MCP: reutilizable desde CLI, tests y servidor.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import chess
import chess.engine
import chess.pgn

from personalities import (
    Personality,
    book_move,
    choose_move,
    get_personality,
)

GAMES_DIR = Path(__file__).parent / "games"
BOARDS_DIR = Path(__file__).parent / "boards"

from coach import (
    current_motifs,
    detect_hanging,
    detect_development,
    detect_king_safety,
    evaluate_move,
    hint_level,
)


# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

DEFAULT_ENGINE_PATHS = [
    shutil.which("stockfish") or "",
    "/usr/games/stockfish",   # Debian/Ubuntu apt
    "/usr/bin/stockfish",
    "/usr/local/bin/stockfish",
]

DEFAULT_ELO = 1600
DEFAULT_TIME_LIMIT = 0.5  # segundos por jugada del bot
MIN_ELO = 1320
MAX_ELO = 3190


def find_engine() -> str:
    """Busca Stockfish: STOCKFISH_PATH, PATH y rutas comunes."""
    import os
    env = os.environ.get("STOCKFISH_PATH", "")
    if env and Path(env).exists():
        return env
    for path in DEFAULT_ENGINE_PATHS:
        if path and Path(path).exists():
            return path
    raise FileNotFoundError(
        "Stockfish no encontrado (se necesita 12+ para UCI_Elo). "
        "Instálalo con: sudo apt install stockfish "
        "o define STOCKFISH_PATH=/ruta/a/stockfish"
    )


def _elo_strength_factor(elo: int) -> float:
    """1320 -> ~2.1 (errático), 1600 -> ~1.7, 2200 -> 0.67, 2600+ -> 0.4.

    Escala temperature/blunder del muestreo para que el ELO sea real
    (Stockfish ignora UCI_Elo en analyse/MultiPV).
    """
    return max(0.4, min(2.5, (2600 - elo) / 600.0))


def _elo_blunder_bonus(elo: int) -> float:
    return max(0.0, (1700 - elo)) / 5000.0


def pov_cp(score, turn: chess.Color) -> float:
    """Score UCI -> centipeones relativos al bando que mueve (mate=±100000)."""
    if score is None:
        return 0.0
    try:
        pov = score.pov(turn)
    except AttributeError:
        pov = score
    if pov.is_mate():
        m = pov.mate() or 0
        return 100000.0 if m > 0 else -100000.0
    return float(pov.score() or 0)


def _is_empty_game(game: "chess.pgn.Game") -> bool:
    """El parser fabrica headers por defecto ante basura: sin datos reales ni
    jugadas, no hay partida."""
    try:
        has_moves = any(True for _ in game.mainline_moves())
    except (ValueError, IndexError):
        return True
    if has_moves:
        return False
    return all(v in ("?", "*", "????.??.??", "") for v in game.headers.values())


def sandboxed(base: Path, name: Optional[str], suffix: str, auto_prefix: str) -> Path:
    """Resuelve un nombre de fichero estrictamente dentro de base.

    Rechaza rutas absolutas, subdirectorios y `..` (incluye enlaces
    simbólicos vía resolve()). Solo para escritura/lectura del proyecto.
    """
    import datetime
    base.mkdir(parents=True, exist_ok=True)
    based = base.resolve()
    if name:
        p = Path(name)
        if p.is_absolute() or p.parent != Path(".") or ".." in p.parts:
            raise ValueError(f"Ruta no permitida (solo ficheros en {base.name}/): {name!r}")
        dest = (based / p.name).resolve()
    else:
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        dest = (based / f"{auto_prefix}-{stamp}{suffix}").resolve()
    if dest.parent != based or dest.suffix != suffix:
        if dest.suffix != suffix:
            dest = dest.with_suffix(suffix)
        if dest.parent != based:
            raise ValueError(f"Ruta no permitida (solo ficheros en {base.name}/): {name!r}")
    return dest


# ---------------------------------------------------------------------------
# Estado de la partida
# ---------------------------------------------------------------------------

@dataclass
class GameState:
    """Estado serializable de una partida."""
    board_fen: str = chess.STARTING_FEN
    root_fen: str = chess.STARTING_FEN  # posición inicial (estándar o FEN importado)
    moves_history: list[str] = field(default_factory=list)  # SAN
    elo: int = DEFAULT_ELO
    # in_progress | check | checkmate | stalemate | draw | resigned | finished
    # finished = terminada importada sin causa de tablero (abandono/tablas acuerdo)
    status: str = "in_progress"
    result: Optional[str] = None  # "1-0", "0-1", "1/2-1/2"; None = partida activa

    def to_dict(self) -> dict:
        return {
            "fen": self.board_fen,
            "moves": self.moves_history,
            "elo": self.elo,
            "status": self.status,
            "result": self.result,
        }


# ---------------------------------------------------------------------------
# Motor principal
# ---------------------------------------------------------------------------

class ChessEngine:
    """Gestor del juego con Stockfish como oponente (el bot juega negras)."""

    def __init__(self, elo: int = DEFAULT_ELO, time_limit: float = DEFAULT_TIME_LIMIT,
                 personality: str = "club", seed: Optional[int] = None):
        import random
        self.engine_path = find_engine()
        self.engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
        self._rng = random.Random(seed)
        self.personality_key = "club"
        self.personality: Personality = get_personality("club")
        self.elo = elo
        self.time_limit = time_limit
        if personality and personality != "club":
            # La personalidad fija ELO/tiempo salvo elo explícito no-default
            self.set_personality(personality)
            if elo != DEFAULT_ELO:
                self._set_elo(elo)
        else:
            self._set_elo(elo)
        self.board: chess.Board = chess.Board()
        self.state = GameState(elo=self.elo)
        self._resigned = False  # abandono propio: sticky hasta undo/reset/load
        # Modo entrenador
        self.coach_enabled = True
        self.last_coach_feedback: Optional[dict] = None
        self.hint_counter: dict[str, int] = {}  # FEN -> último nivel dado

    def _set_elo(self, elo: int) -> None:
        """Configura el nivel de fuerza del bot."""
        elo = max(MIN_ELO, min(MAX_ELO, elo))
        self.elo = elo
        try:
            self.engine.configure({
                "UCI_LimitStrength": True,
                "UCI_Elo": elo,
            })
        except chess.engine.EngineError:
            # Algunos builds no soportan estas opciones; se juega a full.
            pass

    def set_personality(self, key: str) -> dict:
        """Aplica una personalidad: fija su ELO y tiempo de reflexión."""
        p = get_personality(key)
        self.personality_key = p.key
        self.personality = p
        self.time_limit = p.time_limit
        self._set_elo(p.elo)
        return {"key": p.key, "name": p.name, "elo": self.elo}

    # -----------------------------------------------------------------------
    # Control de partida
    # -----------------------------------------------------------------------

    def reset(self, elo: Optional[int] = None, personality: Optional[str] = None) -> dict:
        """Reinicia la partida. La personalidad fija su ELO; un elo explícito lo sobrescribe."""
        if personality:
            self.set_personality(personality)
        if elo is not None:
            self._set_elo(elo)
        self.board = chess.Board()
        self.state = GameState(elo=self.elo)
        self._resigned = False
        self.last_coach_feedback = None
        self.hint_counter = {}
        return self.get_state()

    def resign(self) -> dict:
        """El jugador abandona la partida."""
        if self._is_game_over():
            return {"error": "La partida ya terminó", **self.get_state()}
        self._resigned = True
        self.state.status = "resigned"
        self.state.result = "0-1"
        self.state.board_fen = self.board.fen()
        return self.get_state()

    def undo(self) -> dict:
        """Deshace la última ronda (jugador+bot; 1 ply si el jugador dio mate).
        Tras un abandono, reabre la posición tal cual sin retirar jugadas."""
        if self._resigned:
            self._resigned = False
            self._rebuild_history()
            self.last_coach_feedback = None
            return self.get_state()
        if not self.board.move_stack:
            return {"error": "Nada que deshacer", **self.get_state()}
        popped = 0
        while self.board.move_stack and (popped == 0 or self.board.turn != chess.WHITE):
            self.board.pop()
            popped += 1
        self._rebuild_history()
        self.last_coach_feedback = None
        return self.get_state()

    def claim_draw(self) -> dict:
        """Reclama tablas (triple repetición o 50 movimientos)."""
        reasons = []
        if self.board.can_claim_threefold_repetition():
            reasons.append("triple repetición")
        if self.board.can_claim_fifty_moves():
            reasons.append("regla de los 50 movimientos")
        if not reasons:
            return {"error": "No hay reclamación disponible", **self.get_state()}
        self.state.status = "draw"
        self.state.result = "1/2-1/2"
        self.state.board_fen = self.board.fen()
        result = self.get_state()
        result["claim"] = " y ".join(reasons)
        return result

    def _rebuild_history(self) -> None:
        """Reconstruye el historial SAN desde la posición raíz."""
        temp_board = chess.Board(self.state.root_fen)
        history = []
        for move in self.board.move_stack:
            history.append(temp_board.san(move))
            temp_board.push(move)
        self.state.moves_history = history
        self.state.board_fen = self.board.fen()
        self._update_status()

    # -----------------------------------------------------------------------
    # Jugar
    # -----------------------------------------------------------------------

    def _quick_eval(self) -> tuple[Optional[float], Optional[str]]:
        """Evaluación rápida acotada (coach). Returns (eval_pawns_white, best_san)."""
        if self.board.is_checkmate():
            winner_white = self.board.turn == chess.BLACK
            return (10000.0 if winner_white else -10000.0), None
        if self.board.is_game_over():
            return 0.0, None
        try:
            info = self.engine.analyse(
                self.board, chess.engine.Limit(time=0.3, depth=10)
            )
            score = info["score"].white()
            if score.is_mate():
                m = score.mate() or 0
                evaluation = 10000.0 if m > 0 else -10000.0
            else:
                evaluation = (score.score() or 0) / 100.0
            pv = info.get("pv", [])
            best_san = None
            if pv:
                try:
                    best_san = self.board.san(pv[0])
                except (ValueError, chess.IllegalMoveError):
                    best_san = None
            return evaluation, best_san
        except chess.engine.EngineError:
            return None, None

    def player_move(self, move_str: str) -> dict:
        """
        Aplica la jugada del jugador (blancas) y responde con la del bot.
        Acepta SAN (e4, Nf3, O-O) o UCI (e2e4).
        Con coach activo: evalúa antes/después y adjunta feedback en "coach".
        """
        if self._is_game_over():
            return {"error": "La partida ya terminó", **self.get_state()}
        if self.board.turn != chess.WHITE:
            return {"error": "No es tu turno (juegas blancas)", **self.get_state()}

        move_str = move_str.strip()
        move = self._parse_move(move_str)

        if move is None:
            return {
                "error": f"Movimiento inválido: {move_str}",
                "legal_moves": self.get_legal_moves_san(),
            }

        # Análisis ANTES (coach)
        eval_before: Optional[float] = None
        best_before: Optional[str] = None
        board_before: Optional[chess.Board] = None
        if self.coach_enabled:
            board_before = self.board.copy()
            eval_before, best_before = self._quick_eval()

        # Aplicar jugada del jugador
        san = self.board.san(move)
        move_number = len(self.state.moves_history) // 2 + 1
        self.board.push(move)
        self.state.moves_history.append(san)

        # Análisis DESPUÉS (coach) — solo la jugada del jugador, antes del bot
        coach_feedback: Optional[dict] = None
        if self.coach_enabled and eval_before is not None and board_before is not None:
            eval_after, _ = self._quick_eval()
            if eval_after is not None:
                coach_feedback = evaluate_move(
                    board_before, self.board,
                    eval_before, eval_after,
                    san, move_number, best_before,
                )
                # Cita histórica: ¿qué jugó un maestro en la posición que viste?
                try:
                    from history import cite_position
                    classic = cite_position(board_before)
                    if classic:
                        coach_feedback["classic"] = classic
                except Exception:
                    pass
                self.last_coach_feedback = coach_feedback

        if self._is_game_over():
            self._update_status()
            result = self.get_state()
            if coach_feedback:
                result["coach"] = coach_feedback
            return result

        # Respuesta del bot (transaccional: si falla, se revierte tu jugada)
        bot_move = self._get_bot_move()
        if bot_move is None:
            self.board.pop()
            self.state.moves_history.pop()
            self._update_status()
            return {"error": "El motor no respondió; tu jugada se ha revertido",
                    **self.get_state()}
        bot_san = self.board.san(bot_move)
        self.board.push(bot_move)
        self.state.moves_history.append(bot_san)

        self._update_status()
        result = self.get_state()
        if coach_feedback:
            result["coach"] = coach_feedback
        return result

    def _parse_move(self, move_str: str) -> Optional[chess.Move]:
        # 1. Intentar SAN (tolera +/# y O-O)
        try:
            candidate = self.board.parse_san(move_str)
            if candidate in self.board.legal_moves:
                return candidate
        except (ValueError, chess.InvalidMoveError, chess.IllegalMoveError):
            pass
        # 2. Intentar UCI
        try:
            candidate = self.board.parse_uci(move_str)
            if candidate in self.board.legal_moves:
                return candidate
        except (ValueError, chess.InvalidMoveError, chess.IllegalMoveError):
            pass
        return None

    @staticmethod
    def _pov_cp(score, turn: chess.Color) -> float:
        """Compat: ver pov_cp() a nivel de módulo."""
        return pov_cp(score, turn)

    def _get_bot_move(self) -> Optional[chess.Move]:
        """Jugada del bot según su personalidad (repertorio + muestreo con estilo)."""
        import dataclasses
        p = self.personality
        # El ELO escala el muestreo (analyse ignora UCI_Elo): a menor ELO,
        # más temperatura y más blunders. Medible en tests.
        factor = _elo_strength_factor(self.elo)
        eff = dataclasses.replace(
            p,
            temperature=p.temperature * factor,
            blunder_rate=min(0.6, p.blunder_rate + _elo_blunder_bonus(self.elo)),
        )
        # 1. Repertorio de aperturas
        san = book_move(self.state.moves_history, p.openings, self._rng)
        if san:
            try:
                candidate = self.board.parse_san(san)
                if candidate in self.board.legal_moves:
                    return candidate
            except (ValueError, chess.InvalidMoveError, chess.IllegalMoveError):
                pass
        # 2. Muestreo MultiPV con estilo (parámetros efectivos por ELO)
        try:
            infos = self.engine.analyse(
                self.board,
                chess.engine.Limit(time=eff.time_limit),
                multipv=max(1, eff.top_k),
            )
            if isinstance(infos, dict):
                infos = [infos]
            candidates: list[tuple[chess.Move, float]] = []
            for info in infos:
                pv = info.get("pv", [])
                if not pv:
                    continue
                candidates.append((pv[0], self._pov_cp(info.get("score"), self.board.turn)))
            if candidates:
                pick = choose_move(self.board, candidates, eff, self._rng)
                if pick in self.board.legal_moves:
                    return pick
        except chess.engine.EngineError:
            pass
        # 3. Fallback: mejor jugada directa
        try:
            result = self.engine.play(
                self.board,
                chess.engine.Limit(time=self.time_limit),
            )
            return result.move
        except chess.engine.EngineError:
            return None

    # -----------------------------------------------------------------------
    # Análisis
    # -----------------------------------------------------------------------

    def analyze(self, depth: int = 15) -> dict:
        """Analiza la posición actual y devuelve evaluación + mejor jugada."""
        if self._is_game_over():
            return {"error": "La partida terminó, no hay nada que analizar"}

        depth = max(5, min(30, depth))
        try:
            info = self.engine.analyse(
                self.board,
                chess.engine.Limit(depth=depth),
            )
        except chess.engine.EngineError as exc:
            return {"error": f"El motor no respondió: {exc}"}
        score = info["score"].white()

        if score.is_mate():
            evaluation = f"mate en {score.mate()}"
            numeric = 10000.0 if (score.mate() or 0) > 0 else -10000.0
        else:
            cp = score.score() or 0
            numeric = cp / 100.0
            evaluation = f"{numeric:+.2f}"

        pv = info.get("pv", [])
        best_move = pv[0] if pv else None
        try:
            best_san = self.board.san(best_move) if best_move else None
        except (ValueError, chess.IllegalMoveError):
            best_san = None

        return {
            "evaluation": evaluation,
            "numeric": numeric,
            "best_move": best_san,
            "depth": info.get("depth", depth),
            "turn": "blancas" if self.board.turn else "negras",
        }

    def hint(self) -> dict:
        """Sugiere una jugada sin jugarla (análisis rápido)."""
        return self.analyze(depth=12)

    # -----------------------------------------------------------------------
    # Modo entrenador
    # -----------------------------------------------------------------------

    def explain_last(self) -> dict:
        """Explica la última jugada del jugador."""
        if not self.last_coach_feedback:
            return {"error": "No hay jugada previa para explicar (juega primero o el coach está desactivado)"}
        return self.last_coach_feedback

    def toggle_coach(self, enabled: bool) -> dict:
        """Activa/desactiva el modo entrenador."""
        self.coach_enabled = enabled
        if not enabled:
            self.last_coach_feedback = None
        return {"coach_enabled": enabled}

    def hint_with_level(self, level: int = 1) -> dict:
        """
        Pista progresiva. Nivel 1: idea, 2: zona, 3: jugada exacta.
        Si se repite hint en la misma posición, auto-escala al siguiente nivel.
        """
        try:
            level = int(level)
        except (TypeError, ValueError):
            level = 1
        level = max(1, min(3, level))

        fen = self.board.fen()
        last_level = self.hint_counter.get(fen, 0)
        if last_level and level <= last_level:
            level = min(last_level + 1, 3)
        self.hint_counter[fen] = level

        info = self.analyze(depth=12)
        if "error" in info:
            return info

        move_number = len(self.state.moves_history) // 2 + 1
        motifs = current_motifs(self.board, move_number, self.board.turn)
        best_san = info.get("best_move")
        dest = None
        if best_san:
            try:
                dest = chess.square_name(self.board.parse_san(best_san).to_square)
            except (ValueError, chess.InvalidMoveError, chess.IllegalMoveError):
                dest = None
        text = hint_level(motifs, level, best_san, info.get("evaluation", ""), dest)

        return {
            "level": level,
            "hint": text,
            "best_move": info.get("best_move"),
            "evaluation": info.get("evaluation"),
        }

    def coach_status(self) -> dict:
        """Snapshot actual: piezas colgadas, desarrollo, seguridad del rey."""
        move_number = len(self.state.moves_history) // 2 + 1
        color = self.board.turn
        return {
            "coach_enabled": self.coach_enabled,
            "move_number": move_number,
            "turn": "blancas" if color else "negras",
            "current_issues": {
                "piezas_colgadas": len(detect_hanging(self.board, color)),
                "problemas_desarrollo": len(detect_development(self.board, move_number, color)),
                "seguridad_rey": len(detect_king_safety(self.board, color)),
            },
            "total_moves": len(self.state.moves_history),
            "detalle_colgadas": detect_hanging(self.board, color),
        }

    # -----------------------------------------------------------------------
    # PGN: exportar / guardar / cargar / listar
    # -----------------------------------------------------------------------

    def to_pgn(self) -> str:
        """Partida actual en formato PGN estándar (headers + movimientos)."""
        from datetime import date
        game = chess.pgn.Game()
        game.headers["Event"] = "AI Chess Casual Game"
        game.headers["Site"] = "Local"
        game.headers["Date"] = date.today().strftime("%Y.%m.%d")
        game.headers["White"] = "Jugador"
        game.headers["Black"] = f"Stockfish {self.personality.name} ELO {self.elo}"
        game.headers["BlackPersonality"] = self.personality_key
        if self.state.root_fen != chess.STARTING_FEN:
            game.headers["SetUp"] = "1"
            game.headers["FEN"] = self.state.root_fen
        game.headers["Result"] = self.state.result or "*"
        node = game
        board = chess.Board(self.state.root_fen)
        for san in self.state.moves_history:
            try:
                move = board.parse_san(san)
            except (ValueError, chess.InvalidMoveError, chess.IllegalMoveError):
                break
            node = node.add_variation(move)
            board.push(move)
        exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=False)
        return game.accept(exporter)

    def save_game(self, path: Optional[str] = None) -> dict:
        """Guarda la partida en games/ (solo ese directorio). Devuelve path."""
        dest = sandboxed(GAMES_DIR, path, ".pgn", "ai-chess")
        dest.write_text(self.to_pgn(), encoding="utf-8")
        return {"path": str(dest), "moves": len(self.state.moves_history)}

    def load_game(self, path: str) -> dict:
        """Carga la primera partida de un PGN de games/ y restaura el estado."""
        try:
            src = sandboxed(GAMES_DIR, path, ".pgn", "ai-chess")
        except ValueError as exc:
            return {"error": str(exc), **self.get_state()}
        if not src.exists():
            return {"error": f"Archivo no encontrado en games/: {path}", **self.get_state()}
        try:
            with open(src, encoding="utf-8") as f:
                game = chess.pgn.read_game(f)
            if game is None or _is_empty_game(game):
                return {"error": f"Sin partidas en: {src}", **self.get_state()}
            board = game.board()
            history: list[str] = []
            for move in game.mainline_moves():
                try:
                    history.append(board.san(move))
                except (ValueError, chess.IllegalMoveError):
                    break
                board.push(move)
        except (OSError, ValueError) as exc:
            return {"error": f"PGN ilegible: {exc}", **self.get_state()}

        self.board = board
        self.state = GameState(elo=self.elo)
        self.state.root_fen = game.headers.get("FEN", chess.STARTING_FEN)
        self.state.moves_history = history
        self._resigned = False
        self.last_coach_feedback = None
        self.hint_counter = {}
        # Personalidad rival si el PGN la trae (nuestros exports)
        bkey = game.headers.get("BlackPersonality", "")
        if bkey:
            try:
                self.set_personality(bkey)
                self.state.elo = self.elo
            except KeyError:
                pass
        # ELO rival si viene en el header Black "Stockfish ELO 1700"
        black = game.headers.get("Black", "")
        if "ELO" in black:
            try:
                self._set_elo(int(black.rsplit(None, 1)[-1]))
                self.state.elo = self.elo
            except (ValueError, IndexError):
                pass
        self._update_status()
        # Resultado importado sin causa de tablero (abandono, acuerdo): estado finished
        res = game.headers.get("Result", "*")
        if res in ("1-0", "0-1", "1/2-1/2") and self.state.result is None:
            self.state.status = "finished"
            self.state.result = res
            self.state.board_fen = self.board.fen()
        result = self.get_state()
        result["loaded_from"] = str(src)
        return result

    def list_games(self) -> dict:
        """Lista PGNs guardados en games/."""
        if not GAMES_DIR.exists():
            return {"games": []}
        games = sorted(p.name for p in GAMES_DIR.glob("*.pgn"))
        return {"games": games, "count": len(games)}

    # -----------------------------------------------------------------------
    # Estado
    # -----------------------------------------------------------------------

    def get_state(self) -> dict:
        return {
            **self.state.to_dict(),
            "board_ascii": self.render_ascii(),
            "board_ansi": self.render_ascii(color=True),
            "turn": "blancas" if self.board.turn else "negras",
            "in_check": self.board.is_check(),
            "legal_moves_count": self.board.legal_moves.count(),
            "personality": self.personality_key,
            "personality_name": self.personality.name,
        }

    def get_legal_moves_san(self) -> list[str]:
        return sorted(self.board.san(m) for m in self.board.legal_moves)

    # Paleta ANSI (fondo gris claro/oscuro, piezas por forma+brillo).
    _ANSI_RESET = "\x1b[0m"
    _ANSI_LIGHT_BG = "\x1b[48;5;250m"
    _ANSI_DARK_BG = "\x1b[48;5;238m"
    _ANSI_LAST_LIGHT_BG = "\x1b[48;5;222m"
    _ANSI_LAST_DARK_BG = "\x1b[48;5;178m"
    _ANSI_CHECK_BG = "\x1b[48;5;196m"
    _ANSI_WHITE_FG = "\x1b[38;5;15;1m"
    _ANSI_BLACK_FG = "\x1b[38;5;16;1m"
    _ANSI_CHECK_FG = "\x1b[38;5;15;1m"
    _ANSI_COORD = "\x1b[36m"

    def render_ascii(self, color: bool = False) -> str:
        """Tablero con coordenadas y símbolos Unicode. color=True añade ANSI (CLI)."""
        import os
        if color and os.environ.get("NO_COLOR"):
            color = False
        if color:
            return self._render_ansi()
        symbols = {
            "P": "♙", "N": "♘", "B": "♗", "R": "♖", "Q": "♕", "K": "♔",
            "p": "♟", "n": "♞", "b": "♝", "r": "♜", "q": "♛", "k": "♚",
        }
        lines = ["  a b c d e f g h"]
        for rank in range(7, -1, -1):
            row = [f"{rank + 1} "]
            for file in range(8):
                piece = self.board.piece_at(chess.square(file, rank))
                row.append(symbols.get(piece.symbol(), ".") if piece else "·")
                row.append(" ")
            lines.append("".join(row).rstrip())
        lines.append("  a b c d e f g h")
        return "\n".join(lines)

    def _render_ansi(self) -> str:
        """Tablero a color: casillas alternas, última jugada en amarillo, rey en jaque en rojo."""
        R = self._ANSI_RESET
        symbols = {
            "P": "♙", "N": "♘", "B": "♗", "R": "♖", "Q": "♕", "K": "♔",
            "p": "♟", "n": "♞", "b": "♝", "r": "♜", "q": "♛", "k": "♚",
        }
        last_from = last_to = None
        if self.board.move_stack:
            last = self.board.move_stack[-1]
            last_from, last_to = last.from_square, last.to_square
        check_king = self.board.king(self.board.turn) if self.board.is_check() else None

        C = self._ANSI_COORD
        lines = [f"{C}    a  b  c  d  e  f  g  h{R}"]
        for rank in range(7, -1, -1):
            row = [f"{C} {rank + 1} {R}"]
            for file in range(8):
                sq = chess.square(file, rank)
                piece = self.board.piece_at(sq)
                is_light = (file + rank) % 2 == 1
                if sq == check_king:
                    bg = self._ANSI_CHECK_BG
                    fg = self._ANSI_CHECK_FG
                elif sq == last_from or sq == last_to:
                    bg = self._ANSI_LAST_LIGHT_BG if is_light else self._ANSI_LAST_DARK_BG
                    fg = self._ANSI_WHITE_FG if not piece or piece.color == chess.WHITE else self._ANSI_BLACK_FG
                else:
                    bg = self._ANSI_LIGHT_BG if is_light else self._ANSI_DARK_BG
                    fg = self._ANSI_WHITE_FG if not piece or piece.color == chess.WHITE else self._ANSI_BLACK_FG
                glyph = symbols.get(piece.symbol(), "·") if piece else "·"
                row.append(f"{bg}{fg} {glyph} {R}")
            row.append(f"{C} {rank + 1}{R}")
            lines.append("".join(row))
        lines.append(f"{C}    a  b  c  d  e  f  g  h{R}")
        return "\n".join(lines)

    def get_board_ascii(self, color: bool = False) -> str:
        return self.render_ascii(color=color)

    def get_board_ansi(self) -> str:
        return self.render_ascii(color=True)

    # -----------------------------------------------------------------------
    # Tablero 2D (SVG)
    # -----------------------------------------------------------------------

    def get_board_svg(self, orientation: str = "blancas") -> str:
        """Tablero actual como string SVG."""
        from board_svg import to_svg
        return to_svg(self.board, orientation=orientation)

    def save_board_image(self, path: Optional[str] = None, orientation: str = "blancas") -> dict:
        """Guarda el tablero SVG en boards/. Devuelve path."""
        from board_svg import save_board_svg
        return save_board_svg(self.board, path=path, orientation=orientation)

    def get_board_png(self, orientation: str = "blancas", size: int = 960) -> bytes:
        """Tablero actual como bytes PNG (960px por defecto)."""
        from board_svg import to_png
        return to_png(self.board, orientation=orientation, size=size)

    def save_board_png(
        self, path: Optional[str] = None, orientation: str = "blancas", size: int = 960
    ) -> dict:
        """Guarda el tablero PNG en boards/. Devuelve {path, size}."""
        from board_svg import save_board_png
        return save_board_png(self.board, path=path, orientation=orientation, size=size)

    def save_viewer(self, path: Optional[str] = None, refresh: int = 5) -> dict:
        """Genera el visor HTML (splash + tablero + jugadas + coach). Devuelve {path}."""
        from board_viewer import save_viewer
        from board_svg import to_svg
        state = self.get_state()
        return save_viewer(
            self.board,
            svg=to_svg(self.board),
            moves=state["moves"],
            status=state["status"],
            turn=state["turn"],
            elo=self.elo,
            coach=self.last_coach_feedback,
            path=path,
            refresh=refresh,
        )

    def save_viewer3d(self, style: str = "clasico", path: Optional[str] = None,
                      refresh: int = 5) -> dict:
        """Genera el visor 3D (Three.js) con la partida embebida. Devuelve {path, style}."""
        from viewer3d import save_viewer3d
        state = self.get_state()
        return save_viewer3d(
            self.board,
            moves_uci=[m.uci() for m in self.board.move_stack],
            moves_san=state["moves"],
            status=state["status"],
            turn=state["turn"],
            elo=self.elo,
            style=style,
            path=path,
            refresh=refresh,
        )

    # -----------------------------------------------------------------------
    # Internos
    # -----------------------------------------------------------------------

    def _is_game_over(self) -> bool:
        # Invariante: solo in_progress/check están activos; todo lo demás es terminal.
        if self.state.status not in ("in_progress", "check"):
            return True
        b = self.board
        return (
            b.is_checkmate()
            or b.is_stalemate()
            or b.is_insufficient_material()
            or b.is_seventyfive_moves()
            or b.is_fivefold_repetition()
        )

    def _update_status(self) -> None:
        # Invariante: result solo vive en estado terminal.
        if self._resigned:
            self.state.status = "resigned"
            self.state.result = "0-1"
            self.state.board_fen = self.board.fen()
            return
        if self.state.status == "finished":
            self.state.board_fen = self.board.fen()
            return
        b = self.board
        if b.is_checkmate():
            self.state.status = "checkmate"
            # Si es turno de blancas y hay mate, ganan negras (0-1)
            self.state.result = "0-1" if b.turn else "1-0"
        elif b.is_stalemate():
            self.state.status = "stalemate"
            self.state.result = "1/2-1/2"
        elif b.is_insufficient_material() or b.is_seventyfive_moves() or b.is_fivefold_repetition():
            self.state.status = "draw"
            self.state.result = "1/2-1/2"
        elif b.is_check():
            self.state.status = "check"
            self.state.result = None
        else:
            self.state.status = "in_progress"
            self.state.result = None
        self.state.board_fen = b.fen()

    def close(self) -> None:
        try:
            self.engine.quit()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Singleton para uso desde el servidor MCP
# ---------------------------------------------------------------------------

_engine: Optional[ChessEngine] = None


def get_engine() -> ChessEngine:
    """Devuelve la instancia global del motor (singleton)."""
    global _engine
    if _engine is None:
        _engine = ChessEngine()
    return _engine


def close_engine() -> None:
    global _engine
    if _engine is not None:
        _engine.close()
        _engine = None
