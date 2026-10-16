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
    Piezas propias (sin peones ni rey) con más atacantes rivales que defensores.
    Heurística: no ve clavadas ni táctica profunda.
    """
    hanging: list[str] = []
    opponent = not color
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if not piece or piece.color != color:
            continue
        if piece.piece_type in (chess.PAWN, chess.KING):
            continue
        attackers = len(board.attackers(opponent, square))
        if attackers == 0:
            continue
        defenders = len(board.attackers(color, square))
        if attackers > defenders:
            name = _PIECE_NAMES.get(piece.piece_type, "pieza")
            hanging.append(f"{name} en {chess.square_name(square)} colgada/o")
    return hanging


def detect_lesser_attack(board: chess.Board, color: chess.Color) -> list[str]:
    """Pieza atacada por alguna rival de menor valor (aviso, aunque esté defendida)."""
    values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
              chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 100}
    warnings: list[str] = []
    opponent = not color
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if not piece or piece.color != color:
            continue
        if piece.piece_type in (chess.PAWN, chess.KING):
            continue
        for atk in board.attackers(opponent, square):
            ap = board.piece_at(atk)
            if ap and values[ap.piece_type] < values[piece.piece_type]:
                name = _PIECE_NAMES.get(piece.piece_type, "pieza")
                warnings.append(
                    f"{name} en {chess.square_name(square)} bajo ataque de pieza menor")
                break
    return warnings


def detect_development(board: chess.Board, move_number: int, color: chess.Color) -> list[str]:
    """Problemas de desarrollo en apertura (jugadas 4-9; antes es ruido)."""
    motifs: list[str] = []
    if move_number < 4 or move_number >= 10:
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
    motifs.extend(detect_lesser_attack(board, color))
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


def hint_level(motifs: list[str], level: int, best_move: Optional[str],
               evaluation: str, dest_square: Optional[str] = None) -> str:
    """
    Nivel 1: idea general. Nivel 2: zona (casilla destino real). Nivel 3: jugada exacta.
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
        target = dest_square
        if not target and best_move and len(best_move) >= 2:
            # Fallback SAN: últimas 2 letras solo si parecen casilla
            tail = best_move[-2:]
            if len(tail) == 2 and tail[0] in "abcdefgh" and tail[1] in "12345678":
                target = tail
        if target:
            return f"Mira la zona de {target} como candidata."
        return "Busca jugadas que mejoren tu control central."
    if best_move:
        return f"Juega {best_move} (eval: {evaluation})."
    return "No hay jugada clara, revisa tu posición."


# ---------------------------------------------------------------------------
# Contexto para LLM cliente (coach híbrido: la tool NO llama a ningún LLM,
# solo empaqueta datos + plantilla; el cliente redacta el consejo final)
# ---------------------------------------------------------------------------

COACH_PROMPT_TEMPLATE = """Eres un entrenador de ajedrez. Explica la última jugada en español,
claro y breve (2-4 frases), para un jugador intermedio.

REGLA DE ANCLA (obligatoria): la evaluación de Stockfish manda.
Si dice {eval_note}, no afirmes lo contrario. Tu trabajo es explicar
el porqué humano (táctica, planes, casillas), no reevaluar la posición.

Datos:
- Posición (FEN): {fen}
- Turno ahora: {turn} | Última jugada: {last_move}
- Veredicto del motor: {veredicto} ({cp_loss:.0f}cp) | Mejor era: {best_move}
- Motivos detectados: {motivos}

Redacta el consejo final."""


def build_coach_prompt(feedback: dict, fen: str, turn: str, last_move: str) -> str:
    """Rellena la plantilla con el feedback del motor. Puro y testeable."""
    cp = feedback.get("cp_loss", 0.0)
    if feedback.get("veredicto") == "mate":
        eval_note = "jaque mate: la partida terminó"
    elif cp >= 180:
        eval_note = f"gran error (pierde ~{cp / 100:.1f} peones)"
    elif cp >= 30:
        eval_note = f"imprecisión leve (~{cp / 100:.1f} peones)"
    else:
        eval_note = "jugada correcta, ventaja mantenida"
    motifs = feedback.get("motivos") or ["ninguno"]
    return COACH_PROMPT_TEMPLATE.format(
        eval_note=eval_note,
        fen=fen,
        turn=turn,
        last_move=last_move or "—",
        veredicto=feedback.get("veredicto", "?"),
        cp_loss=cp,
        best_move=feedback.get("best_move") or "—",
        motivos="; ".join(motifs),
    )


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
    # Mate dado: veredicto especial, sin pérdidas absurdas en peones.
    if board_after.is_checkmate():
        return {
            "veredicto": "mate",
            "emoji": "🏁",
            "cp_loss": 0.0,
            "motivos": [],
            "consejo": f"¡Jaque mate con {move_san}! Partida redonda.",
            "best_move": best_move,
        }

    if mover == chess.WHITE:
        cp_loss = (eval_before - eval_after) * 100.0
    else:
        cp_loss = (eval_after - eval_before) * 100.0

    # Solo es "grave" si quien movía tenía el mate a favor y lo dejó escapar.
    had_mate = abs(eval_before) >= 9000
    still_mate = abs(eval_after) >= 9000
    mate_lost = had_mate and not still_mate and (
        eval_before * (1 if mover == chess.WHITE else -1) > 0
    )

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
