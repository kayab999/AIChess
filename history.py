"""
history.py — Base histórica de partidas clásicas (Fischer + Tal, CC0).
Índice en memoria por transposition_key: posición -> jugadas que
los maestros hicieron allí, con metadatos para citar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import chess
import chess.pgn

DATA_DIR = Path(__file__).parent / "data" / "classics"


def position_key(board: chess.Board) -> str:
    """Identidad de posición (piezas + turno + enroques + peón al paso)."""
    ep = chess.square_name(board.ep_square) if board.ep_square else "-"
    turn = "w" if board.turn == chess.WHITE else "b"
    return f"{board.board_fen()} {turn} {board.castling_xfen()} {ep}"


@dataclass
class ClassicRef:
    white: str
    black: str
    event: str
    date: str
    result: str
    move_san: str   # jugada que se hizo EN esta posición
    ply: int        # medio-movimientos hasta aquí


@dataclass
class ClassicGame:
    white: str
    black: str
    event: str
    date: str
    result: str
    moves_san: list[str] = field(default_factory=list)


class HistoryDB:
    def __init__(self) -> None:
        self.games: list[ClassicGame] = []
        self.by_position: dict[str, list[ClassicRef]] = {}

    def load(self, paths: Optional[list[Path]] = None) -> dict:
        """Indexa todos los PGNs (todas las posiciones de cada partida)."""
        if paths is None:
            paths = sorted(DATA_DIR.glob("*.pgn"))
        games = positions = errors = 0
        for path in paths:
            try:
                with open(path, encoding="utf-8", errors="replace") as f:
                    while True:
                        try:
                            game = chess.pgn.read_game(f)
                        except (ValueError, IndexError):
                            errors += 1
                            continue
                        if game is None:
                            break
                        self._index_game(game)
                        games += 1
            except OSError:
                errors += 1
        positions = len(self.by_position)
        return {"games": games, "positions": positions, "errors": errors}

    def _index_game(self, game: chess.pgn.Game) -> None:
        h = game.headers
        meta = ClassicGame(
            white=h.get("White", "?"), black=h.get("Black", "?"),
            event=h.get("Event", "?"), date=h.get("Date", "????.??.??"),
            result=h.get("Result", "*"),
        )
        board = game.board()
        ply = 0
        for move in game.mainline_moves():
            try:
                san = board.san(move)
            except (ValueError, chess.IllegalMoveError):
                break
            key = position_key(board)
            self.by_position.setdefault(key, []).append(ClassicRef(
                white=meta.white, black=meta.black, event=meta.event,
                date=meta.date, result=meta.result, move_san=san, ply=ply,
            ))
            board.push(move)
            meta.moves_san.append(san)
            ply += 1
        self.games.append(meta)

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def lookup_board(self, board: chess.Board) -> list[ClassicRef]:
        return list(self.by_position.get(position_key(board), []))

    def lookup_fen(self, fen: str) -> list[ClassicRef]:
        try:
            return self.lookup_board(chess.Board(fen))
        except ValueError:
            return []

    def stats(self, board: chess.Board) -> dict[str, dict]:
        """Por jugada hecha aquí: partidas y resultados (desde Blancas)."""
        out: dict[str, dict] = {}
        for ref in self.lookup_board(board):
            s = out.setdefault(ref.move_san, {"games": 0, "w": 0, "d": 0, "b": 0})
            s["games"] += 1
            s["w" if ref.result == "1-0" else "b" if ref.result == "0-1" else "d"] += 1
        return out

    def search_player(self, name: str, limit: int = 20) -> list[ClassicGame]:
        q = name.strip().lower()
        return [g for g in self.games
                if q in g.white.lower() or q in g.black.lower()][:limit]


# ---------------------------------------------------------------------------
# Singleton perezoso (carga ~162 partidas en <1s)
# ---------------------------------------------------------------------------

_db: Optional[HistoryDB] = None


def get_history() -> HistoryDB:
    global _db
    if _db is None:
        _db = HistoryDB()
        _db.load()
    return _db


def cite_position(board: chess.Board, max_refs: int = 2) -> str:
    """Cita corta para el coach: 'Tal jugó X aquí (evento, año, resultado)'."""
    refs = get_history().lookup_board(board)[:max_refs]
    parts = []
    for r in refs:
        year = r.date.split(".")[0] if r.date else "¿?"
        mover = r.white.split(",")[0] if board.turn == chess.WHITE else r.black.split(",")[0]
        parts.append(f"{mover} jugó {r.move_san} aquí ({r.event}, {year}, {r.result})")
    return " · ".join(parts)
