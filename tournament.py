"""
tournament.py — Round-robin entre personalidades AI Chess.

Cada emparejamiento juega N partidas alternando color. Adjudica por
evaluación si se supera max_ply. Guarda PGNs e imprime tabla + métrica
de estilo (% jugadas tácticas: jaques + capturas).

Uso:
  .venv/bin/python tournament.py --players vikingo,muro,profesor
  .venv/bin/python tournament.py --players fischer,kasparov --games 2 --time 0.3
"""

from __future__ import annotations

import argparse
import datetime
import random
import sys
from pathlib import Path

import chess
import chess.engine
import chess.pgn

sys.path.insert(0, str(Path(__file__).parent))
from chess_engine import find_engine
from personalities import book_move, choose_move, get_personality


def _pov_cp(score, turn: chess.Color) -> float:
    if score is None:
        return 0.0
    pov = score.pov(turn) if hasattr(score, "pov") else score
    if pov.is_mate():
        m = pov.mate() or 0
        return 100000.0 if m > 0 else -100000.0
    return float(pov.score() or 0)


class Rival:
    """Una personalidad con su propio proceso Stockfish."""

    def __init__(self, key: str, time_limit: float, seed: int):
        self.p = get_personality(key)
        self.time_limit = time_limit
        self.rng = random.Random(seed)
        self.engine = chess.engine.SimpleEngine.popen_uci(find_engine())
        try:
            self.engine.configure({"UCI_LimitStrength": True, "UCI_Elo": self.p.elo})
        except chess.engine.EngineError:
            pass

    def select(self, board: chess.Board, history_san: list[str]) -> chess.Move:
        san = book_move(history_san, self.p.openings, self.rng)
        if san:
            try:
                m = board.parse_san(san)
                if m in board.legal_moves:
                    return m
            except (ValueError, chess.InvalidMoveError, chess.IllegalMoveError):
                pass
        try:
            infos = self.engine.analyse(
                board, chess.engine.Limit(time=self.time_limit),
                multipv=max(1, self.p.top_k),
            )
            if isinstance(infos, dict):
                infos = [infos]
            cands = []
            for info in infos:
                pv = info.get("pv", [])
                if pv:
                    cands.append((pv[0], _pov_cp(info.get("score"), board.turn)))
            if cands:
                pick = choose_move(board, cands, self.p, self.rng)
                if pick in board.legal_moves:
                    return pick
        except chess.engine.EngineError:
            pass
        return self.engine.play(board, chess.engine.Limit(time=self.time_limit)).move

    def quick_eval_white(self, board: chess.Board) -> float:
        try:
            info = self.engine.analyse(board, chess.engine.Limit(depth=8))
            s = info["score"].white()
            if s.is_mate():
                return 10000.0 if (s.mate() or 0) > 0 else -10000.0
            return (s.score() or 0) / 100.0
        except chess.engine.EngineError:
            return 0.0

    def close(self) -> None:
        try:
            self.engine.quit()
        except Exception:
            pass


def play_game(white: Rival, black: Rival, max_ply: int = 120) -> dict:
    board = chess.Board()
    history: list[str] = []
    tactics = {True: 0, False: 0}  # blancas/negras
    moves = 0
    while not board.is_game_over() and moves < max_ply:
        side = white if board.turn == chess.WHITE else black
        move = side.select(board, history)
        if board.gives_check(move) or board.is_capture(move):
            tactics[board.turn] += 1
        history.append(board.san(move))
        board.push(move)
        moves += 1

    if board.is_checkmate():
        result = "1-0" if board.turn == chess.BLACK else "0-1"
    elif (board.is_stalemate() or board.is_insufficient_material()
          or board.is_seventyfive_moves() or board.is_fivefold_repetition()):
        result = "1/2-1/2"
    else:  # adjudicación por evaluación
        ev = white.quick_eval_white(board)
        result = "1-0" if ev > 1.5 else ("0-1" if ev < -1.5 else "1/2-1/2")

    game = chess.pgn.Game()
    game.headers["Event"] = "AI Chess Tournament"
    game.headers["Site"] = "Local"
    game.headers["Date"] = datetime.date.today().strftime("%Y.%m.%d")
    game.headers["White"] = f"{white.p.name} ELO {white.p.elo}"
    game.headers["Black"] = f"{black.p.name} ELO {black.p.elo}"
    game.headers["Result"] = result
    node = game
    b = chess.Board()
    for san in history:
        mv = b.parse_san(san)
        node = node.add_variation(mv)
        b.push(mv)
    return {"result": result, "moves": history, "pgn": game, "tactics": tactics,
            "plies": moves}


def main() -> None:
    ap = argparse.ArgumentParser(description="Round-robin entre personalidades")
    ap.add_argument("--players", default="novato,vikingo,muro,profesor,maestro,stanley",
                    help="keys separadas por coma")
    ap.add_argument("--games", type=int, default=2, help="partidas por emparejamiento (alterna color)")
    ap.add_argument("--time", type=float, default=0.2, help="segundos por jugada")
    ap.add_argument("--max-ply", type=int, default=100)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    keys = [k.strip() for k in args.players.split(",") if k.strip()]
    for k in keys:
        get_personality(k)  # valida

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    outdir = Path(__file__).parent / "games"
    outdir.mkdir(parents=True, exist_ok=True)

    scores = {k: 0.0 for k in keys}
    tact_n = {k: 0 for k in keys}
    tact_d = {k: 0 for k in keys}

    rivals = {k: Rival(k, args.time, args.seed + i) for i, k in enumerate(keys)}
    try:
        n = 0
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                for g in range(args.games):
                    w, b = (keys[i], keys[j]) if g % 2 == 0 else (keys[j], keys[i])
                    r = play_game(rivals[w], rivals[b], args.max_ply)
                    n += 1
                    if r["result"] == "1-0":
                        scores[w] += 1.0
                    elif r["result"] == "0-1":
                        scores[b] += 1.0
                    else:
                        scores[w] += 0.5
                        scores[b] += 0.5
                    tact_n[w] += r["tactics"][True]
                    tact_d[w] += len(r["moves"][::2])
                    tact_n[b] += r["tactics"][False]
                    tact_d[b] += len(r["moves"][1::2])
                    fn = outdir / f"tour-{stamp}-{w}-vs-{b}-g{g + 1}.pgn"
                    fn.write_text(r["pgn"].accept(chess.pgn.StringExporter()),
                                  encoding="utf-8")
                    print(f"[{n}] {w} vs {b}: {r['result']} ({r['plies']} plies) → {fn.name}",
                          flush=True)
    finally:
        for r in rivals.values():
            r.close()

    print("\n🏆 Tabla:")
    for k in sorted(scores, key=lambda k: -scores[k]):
        t = f"{100.0 * tact_n[k] / max(1, tact_d[k]):.0f}%"
        print(f"  {k:12} {scores[k]:.1f} pts   tácticas {t}")


if __name__ == "__main__":
    main()
