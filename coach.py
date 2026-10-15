"""
coach.py — Módulo de análisis educativo para AI Chess.
Detecta errores comunes, clasifica pérdidas y genera explicaciones en español.
Sin dependencias de motor: recibe boards + evaluaciones ya calculadas.
"""

from __future__ import annotations

from typing import Optional

import chess


# ---------------------------------------------------------------------------
# Clasificación de pérdida (umbrales estándar estilo chess.com, en centipeones)
# ---------------------------------------------------------------------------

def classify_loss(cp_loss: float, mate_lost: bool = False) -> tuple[str, str]:
    """
    Clasifica la pérdida en centipeones (positiva = empeora).
    Returns: (veredicto, emoji)
    """
    if mate_lost:
        return ("grave", "💀")
    if cp_loss < 30:
        return ("bien", "✅")
    if cp_loss < 70:
        return ("imprecisión", "⚠️")
    if cp_loss < 180:
        return ("error", "❌")
    return ("blunder", "💥")


# ---------------------------------------------------------------------------
# Detección de motivos
# ---------------------------------------------------------------------------

_PIECE_NAMES = {
    chess.KNIGHT: "caballo",
    chess.BISHOP: "alfil",
    chess.ROOK: "torre",
    chess.QUEEN: "dama",
    chess.KING: "rey",
    chess.PAWN: "peón",
}


def detect_hanging(board: chess.Board, color: chess.Color) -> list[str]:
    """
    Piezas propias (no peones) atacadas con más atacantes rivales que defensores.
    """
    hanging: list[str] = []
    opponent = not color
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if not piece or piece.color != color or piece.piece_type == chess.PAWN:
            continue
        attackers = len(board.attackers(opponent, square))
        if attackers == 0:
            continue
        defenders = len(board.attackers(color, square))
        if attackers > defenders:
            name = _PIECE_NAMES.get(piece.piece_type, "pieza")
            hanging.append(f"{name} en {chess.square_name(square)} colgada/o")
    return hanging


def detect_development(board: chess.Board, move_number: int, color: chess.Color) -> list[str]:
    """Problemas de desarrollo en apertura (jugadas < 10)."""
    motifs: list[str] = []
    if move_number >= 10:
        return motifs

    knight_starts = [chess.B1, chess.G1] if color == chess.WHITE else [chess.B8, chess.G8]
    for sq in knight_starts:
        piece = board.piece_at(sq)
        if piece and piece.piece_type == chess.KNIGHT and piece.color == color:
            motifs.append("caballo sin desarrollar")
            break

    bishop_starts = [chess.C1, chess.F1] if color == chess.WHITE else [chess.C8, chess.F8]
    for sq in bishop_starts:
        piece = board.piece_at(sq)
        if piece and piece.piece_type == chess.BISHOP and piece.color == color:
            motifs.append("alfil sin desarrollar")
            break

    if move_number >= 8:
        king_sq = board.king(color)
        home = chess.E1 if color == chess.WHITE else chess.E8
        if king_sq == home:
            motifs.append("rey sin enrocar")
    return motifs


def detect_king_safety(board: chess.Board, color: chess.Color) -> list[str]:
    """Escudo de peones del rey debilitado (2+ peones movidos)."""
    shield = [chess.F2, chess.G2, chess.H2] if color == chess.WHITE else [chess.F7, chess.G7, chess.H7]
    moved = 0
    for sq in shield:
        piece = board.piece_at(sq)
        if not piece or piece.piece_type != chess.PAWN or piece.color != color:
            moved += 1
    if moved >= 2:
        return ["estructura de peones del rey debilitada"]
    return []


def current_motifs(board: chess.Board, move_number: int, color: chess.Color) -> list[str]:
    """Todos los motivos actuales para una posición (usado por hints)."""
    motifs: list[str] = []
    motifs.extend(detect_hanging(board, color))
    motifs.extend(detect_development(board, move_number, color))
    motifs.extend(detect_king_safety(board, color))
    return motifs


# ---------------------------------------------------------------------------
# Explicación y pistas
# ---------------------------------------------------------------------------

def explain(move_san: str, cp_loss: float, motifs: list[str], veredicto: str) -> str:
    """Genera consejo educativo en español."""
    detail = f" Pierdes {cp_loss / 100:.1f} peones." if cp_loss >= 30 else ""
    motive = f" {motifs[0].capitalize()}." if motifs else ""
    if veredicto == "bien":
        if motifs:
            return f"Bien jugado {move_san}. Consejo:{motive}"
        return f"Buena jugada {move_san}."
    if veredicto == "imprecisión":
        return f"Imprecisión en {move_san}.{motive}{detail}"
    if veredicto == "error":
        return f"Error en {move_san}.{motive}{detail}"
    if veredicto == "grave":
        return f"Jugada grave en {move_san}: pierdes el mate forzado.{motive}"
    return f"Blunder en {move_san}.{motive}{detail}"


def hint_level(motifs: list[str], level: int, best_move: Optional[str], evaluation: str) -> str:
    """
    Nivel 1: idea general. Nivel 2: zona. Nivel 3: jugada exacta.
    """
    level = max(1, min(3, level))
    text = " ".join(motifs)
    if level == 1:
        if "sin desarrollar" in text:
            return "Desarrolla tus piezas menores (caballos/alfiles) hacia el centro."
        if "colgada" in text:
            return "Protege tus piezas atacadas o retíralas a casilla segura."
        if "rey" in text or "enrocar" in text:
            return "Mejora la seguridad de tu rey (enroca pronto)."
        return "Controla el centro y coordina tus piezas antes de atacar."
    if level == 2:
        if best_move and len(best_move) >= 2:
            return f"Mira la zona de {best_move[-2:]} como candidata."
        return "Busca jugadas que mejoren tu control central."
    if best_move:
        return f"Juega {best_move} (eval: {evaluation})."
    return "No hay jugada clara, revisa tu posición."


# ---------------------------------------------------------------------------
# Evaluación completa (llamada por el engine)
# ---------------------------------------------------------------------------

def evaluate_move(
    board_before: chess.Board,
    board_after: chess.Board,
    eval_before: float,
    eval_after: float,
    move_san: str,
    move_number: int,
    best_move: Optional[str] = None,
) -> dict:
    """
    eval_before/after en perspectiva BLANCAS (pawns, mate = ±10000).
    cp_loss positiva = el que movió empeoró.
    """
    mover = board_before.turn
    if mover == chess.WHITE:
        cp_loss = (eval_before - eval_after) * 100.0
    else:
        cp_loss = (eval_after - eval_before) * 100.0

    mate_lost = (abs(eval_before) >= 9000) and (abs(eval_after) < 9000)
    # Si quien movía tenía mate a favor y lo pierde, es grave aunque cp parezca raro
    if mate_lost and eval_before * (1 if mover == chess.WHITE else -1) > 0:
        pass  # tenía mate y lo perdió -> grave
    elif mate_lost:
        mate_lost = False  # el rival tenía mate, no aplica

    veredicto, emoji = classify_loss(cp_loss, mate_lost)
    motifs = current_motifs(board_after, move_number, mover)
    consejo = explain(move_san, cp_loss, motifs, veredicto)

    return {
        "veredicto": veredicto,
        "emoji": emoji,
        "cp_loss": round(cp_loss, 1),
        "motivos": motifs,
        "consejo": consejo,
        "best_move": best_move,
    }
