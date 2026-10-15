"""
personalities.py — Personalidades estilo Chessmaster para AI Chess.

Fiel al diseño de The King (Chessmaster): King Safety, Mobility, Randomness
y valores de piezas, más repertorios de apertura por personalidad.

Dos familias:
  - Arquetipos (ELO jugable 1320-2200): club, novato, stanley, vikingo,
    muro, profesor, maestro.
  - Leyendas (ELO exhibición 2700-2950): alekhine, fischer, botvinnik,
    karpov, kasparov, capablanca, tal, carlsen.
  Las tres canónicas del match Chessmaster 9000 vs Christiansen (2002):
  alekhine, fischer, botvinnik.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional

import chess


# ---------------------------------------------------------------------------
# Perfil
# ---------------------------------------------------------------------------

@dataclass
class Personality:
    key: str
    name: str
    elo: int
    desc: str
    # Pesos de estilo (bonus en centipeones, ver _style_bonus)
    aggression: float = 1.0   # jaques, capturas, avance
    solidity: float = 1.0     # enroque, no mover el rey pronto
    mobility: float = 1.0     # desarrollo, centralización
    # Muestreo
    temperature: float = 30.0  # softmax en cp; <=0 = siempre la mejor
    top_k: int = 4
    blunder_rate: float = 0.0  # prob. de jugada legal aleatoria
    time_limit: float = 0.5
    # Repertorio: líneas SAN desde la posición inicial
    openings: list[list[str]] = field(default_factory=list)


# Líneas de apertura compartidas (SAN desde la inicial)
RUY = ["e4", "e5", "Nf3", "Nc6", "Bb5"]
NAJDORF = ["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3", "a6"]
FRENCH = ["e4", "e6", "d4", "d5"]
CARO = ["e4", "c6", "d4", "d5"]
ALEKHINE_DEF = ["e4", "Nf6"]
KID = ["d4", "Nf6", "c4", "g6", "Nc3", "Bg7"]
QGD = ["d4", "d5", "c4", "e6"]
SLAV = ["d4", "d5", "c4", "c6"]
LONDON = ["d4", "d5", "Bf4"]
GIUOCO = ["e4", "e5", "Nf3", "Nc6", "Bc4"]
SCOTCH = ["e4", "e5", "Nf3", "Nc6", "d4"]


PERSONALITIES: dict[str, Personality] = {}


def _add(p: Personality) -> None:
    PERSONALITIES[p.key] = p


# ---------------------------------------------------------------------------
# Arquetipos
# ---------------------------------------------------------------------------

_add(Personality(
    key="club", name="El Socio del Club", elo=1600,
    desc="Jugador de club sólido y equilibrado. El rival por defecto.",
    aggression=1.0, solidity=1.0, mobility=1.0,
    temperature=30.0, top_k=4, blunder_rate=0.02, time_limit=0.5,
    openings=[RUY, QGD, CARO, GIUOCO],
))
_add(Personality(
    key="novato", name="Pepe el Novato", elo=1320,
    desc="Aprendiz entusiasta. Juega rápido y a veces regala piezas.",
    aggression=1.2, solidity=0.5, mobility=0.8,
    temperature=150.0, top_k=5, blunder_rate=0.12, time_limit=0.2,
    openings=[GIUOCO, LONDON, SCOTCH],
))
_add(Personality(
    key="stanley", name="Stanley", elo=1350,
    desc="Homenaje al chimpancé de CM9000. Casi siempre juega al azar.",
    aggression=1.0, solidity=0.0, mobility=0.0,
    temperature=500.0, top_k=8, blunder_rate=0.85, time_limit=0.1,
    openings=[],
))
_add(Personality(
    key="vikingo", name="El Vikingo", elo=1700,
    desc="Atacante temerario: jaques, capturas y peones al ataque.",
    aggression=2.5, solidity=0.4, mobility=1.2,
    temperature=80.0, top_k=4, blunder_rate=0.04, time_limit=0.4,
    openings=[SCOTCH, GIUOCO, NAJDORF],
))
_add(Personality(
    key="muro", name="El Muro", elo=1700,
    desc="Defensivo rocoso: enroca pronto y no regala nada.",
    aggression=0.4, solidity=2.5, mobility=0.8,
    temperature=20.0, top_k=3, blunder_rate=0.015, time_limit=0.5,
    openings=[CARO, SLAV, FRENCH],
))
_add(Personality(
    key="profesor", name="El Profesor", elo=1800,
    desc="Posicional didáctico: desarrollo, centro y buenas casillas.",
    aggression=0.8, solidity=1.2, mobility=2.2,
    temperature=20.0, top_k=3, blunder_rate=0.015, time_limit=0.5,
    openings=[RUY, QGD, SLAV],
))
_add(Personality(
    key="maestro", name="El Maestro", elo=2200,
    desc="Fuerte y equilibrado. El techo de los arquetipos.",
    aggression=1.2, solidity=1.2, mobility=1.2,
    temperature=25.0, top_k=3, blunder_rate=0.0, time_limit=0.6,
    openings=[RUY, NAJDORF, QGD, KID],
))

# ---------------------------------------------------------------------------
# Leyendas (estilos documentados de los campeones)
# ---------------------------------------------------------------------------

_add(Personality(
    key="alekhine", name="Alexander Alekhine", elo=2750,
    desc="Ataque dinámico con ambos colores. 1…Nf6 lleva su nombre.",
    aggression=2.0, solidity=0.8, mobility=1.4,
    temperature=30.0, top_k=3, blunder_rate=0.0, time_limit=0.7,
    openings=[ALEKHINE_DEF, FRENCH, QGD, NAJDORF],
))
_add(Personality(
    key="fischer", name="Bobby Fischer", elo=2800,
    desc="Precisión implacable, e4 siempre. Odia las tablas.",
    aggression=1.8, solidity=1.0, mobility=1.4,
    temperature=15.0, top_k=3, blunder_rate=0.0, time_limit=0.7,
    openings=[RUY, NAJDORF],
))
_add(Personality(
    key="botvinnik", name="Mijail Botvinnik", elo=2720,
    desc="Escuela científica: preparación profunda y juego sistemático.",
    aggression=0.9, solidity=1.5, mobility=1.8,
    temperature=15.0, top_k=3, blunder_rate=0.0, time_limit=0.7,
    openings=[CARO, SLAV, QGD],
))
_add(Personality(
    key="karpov", name="Anatoly Karpov", elo=2750,
    desc="La boa constrictor: profilaxis y estrangulamiento lento.",
    aggression=0.5, solidity=2.0, mobility=1.5,
    temperature=15.0, top_k=3, blunder_rate=0.0, time_limit=0.7,
    openings=[CARO, QGD, RUY],
))
_add(Personality(
    key="kasparov", name="Garry Kasparov", elo=2850,
    desc="Dinámica brutal e iniciativa a cualquier precio.",
    aggression=2.2, solidity=0.7, mobility=1.6,
    temperature=30.0, top_k=3, blunder_rate=0.0, time_limit=0.7,
    openings=[NAJDORF, KID, SCOTCH],
))
_add(Personality(
    key="capablanca", name="José R. Capablanca", elo=2700,
    desc="Claridad cristalina: simplifica y gana los finales.",
    aggression=0.7, solidity=1.6, mobility=1.4,
    temperature=15.0, top_k=3, blunder_rate=0.0, time_limit=0.7,
    openings=[RUY, QGD],
))
_add(Personality(
    key="tal", name="Mijail Tal", elo=2750,
    desc="El mago de Riga: sacrificios y caos calculado.",
    aggression=2.8, solidity=0.3, mobility=1.3,
    temperature=90.0, top_k=4, blunder_rate=0.02, time_limit=0.6,
    openings=[NAJDORF, KID, SCOTCH],
))
_add(Personality(
    key="carlsen", name="Magnus Carlsen", elo=2900,
    desc="Universal y tenaz: aprieta hasta en posiciones muertas.",
    aggression=1.1, solidity=1.3, mobility=1.5,
    temperature=25.0, top_k=3, blunder_rate=0.0, time_limit=0.8,
    openings=[RUY, QGD, LONDON, CARO, KID],
))


def get_personality(key: str) -> Personality:
    """Devuelve el perfil o lanza KeyError con mensaje útil."""
    k = (key or "").strip().lower()
    if k not in PERSONALITIES:
        valid = ", ".join(sorted(PERSONALITIES))
        raise KeyError(f"Personalidad desconocida: {key!r}. Válidas: {valid}")
    return PERSONALITIES[k]


def list_personalities() -> list[dict]:
    return [
        {"key": p.key, "name": p.name, "elo": p.elo, "desc": p.desc}
        for p in PERSONALITIES.values()
    ]


# ---------------------------------------------------------------------------
# Repertorio de aperturas
# ---------------------------------------------------------------------------

def book_move(history_san: list[str], openings: list[list[str]],
              rng: random.Random) -> Optional[str]:
    """Si el historial encaja como prefijo de alguna línea, devuelve la siguiente."""
    options: list[str] = []
    for line in openings:
        if len(history_san) < len(line) and history_san == line[:len(history_san)]:
            options.append(line[len(history_san)])
    if not options:
        return None
    return rng.choice(options)


# ---------------------------------------------------------------------------
# Selección de jugada con estilo
# ---------------------------------------------------------------------------

_PIECE_CP = {
    chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
    chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 0,
}

_CENTER = {chess.D4, chess.D5, chess.E4, chess.E5,
           chess.C4, chess.C5, chess.D3, chess.D6, chess.E3, chess.E6,
           chess.C3, chess.C6, chess.F3, chess.F6}


def style_bonus(board: chess.Board, move: chess.Move, p: Personality) -> float:
    """Bonus en cp según el estilo. board es ANTES de jugar move."""
    bonus = 0.0
    # Capturas ponderadas por valor de pieza (estilo The King: piece values)
    if board.is_capture(move):
        captured = board.piece_at(move.to_square)
        if board.is_en_passant(move):
            val = _PIECE_CP[chess.PAWN]
        else:
            val = _PIECE_CP.get(captured.piece_type, 0) if captured else 0
        bonus += 20.0 * p.aggression * (val / 300.0)
    # Jaques
    if board.gives_check(move):
        bonus += 50.0 * p.aggression
    # Enroque = seguridad del rey
    if board.is_castling(move):
        bonus += 70.0 * p.solidity
    # Mover el rey pronto (sin enrocar) = penalización sólida
    piece = board.piece_at(move.from_square)
    if piece and piece.piece_type == chess.KING and not board.is_castling(move):
        bonus -= 40.0 * p.solidity
    # Desarrollo: pieza menor/pesada sale de su fila inicial
    if piece and piece.piece_type in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
        home_rank = 0 if piece.color == chess.WHITE else 7
        if chess.square_rank(move.from_square) == home_rank:
            bonus += 15.0 * p.mobility
    # Centralización y avance de peones
    if move.to_square in _CENTER:
        bonus += 10.0 * (p.mobility + 0.5 * p.aggression)
    if piece and piece.piece_type == chess.PAWN:
        adv = chess.square_rank(move.to_square) - chess.square_rank(move.from_square)
        if piece.color == chess.BLACK:
            adv = -adv
        if adv > 0:
            bonus += 6.0 * adv * (p.aggression + p.mobility) / 2.0
    return bonus


def choose_move(board: chess.Board,
                candidates: list[tuple[chess.Move, float]],
                p: Personality,
                rng: random.Random) -> chess.Move:
    """
    candidates: [(move, cp_relativos_al_bando_que_mueve)].
    1) inyección de blunder  2) score+bonus  3) softmax(temperatura).
    """
    legal = list(board.legal_moves)
    if not candidates:
        return rng.choice(legal)
    # 1. Blunder humano: jugada legal aleatoria
    if p.blunder_rate > 0.0 and rng.random() < p.blunder_rate:
        return rng.choice(legal)
    # 2. Score + bonus de estilo
    scored = [(m, s + style_bonus(board, m, p)) for m, s in candidates[:max(1, p.top_k)]]
    if p.temperature <= 0:
        return max(scored, key=lambda t: t[1])[0]
    # 3. Softmax (estable numéricamente)
    best = max(s for _, s in scored)
    weights = [math.exp((s - best) / p.temperature) for _, s in scored]
    return rng.choices([m for m, _ in scored], weights=weights, k=1)[0]
