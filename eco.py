"""
eco.py — Nombres de apertura por secuencia SAN (tabla manual curada).
Cubre los repertorios de personalities.py + líneas más comunes.
Cada entrada: prefijo SAN -> (nombre, eco_aprox).
"""

from __future__ import annotations

OPENINGS: list[tuple[tuple[str, ...], str, str]] = [
    # Abiertas 1.e4 e5
    (("e4", "e5"), "Apertura Abierta", "C20"),
    (("e4", "e5", "Nf3", "Nc6", "Bb5"), "Ruy López", "C60"),
    (("e4", "e5", "Nf3", "Nc6", "Bc4"), "Giuoco Piano", "C50"),
    (("e4", "e5", "Nf3", "Nc6", "d4"), "Escocesa", "C45"),
    (("e4", "e5", "Nf3", "Nf6"), "Petrov", "C42"),
    (("e4", "e5", "Nf3", "d6"), "Philidor", "C41"),
    (("e4", "e5", "Bc4",), "Alfil del Rey", "C23"),
    (("e4", "e5", "f4"), "Gambito de Rey", "C30"),
    # Siciliana 1.e4 c5
    (("e4", "c5"), "Defensa Siciliana", "B20"),
    (("e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3", "a6"),
     "Siciliana Najdorf", "B90"),
    (("e4", "c5", "Nf3", "Nc6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3", "e5"),
     "Siciliana Sveshnikov", "B33"),
    (("e4", "c5", "Nf3", "e6", "d4", "cxd4", "Nxd4", "a6"),
     "Siciliana Kan", "B41"),
    (("e4", "c5", "Nf3", "Nc6", "Bb5"), "Siciliana Rossolimo", "B31"),
    (("e4", "c5", "c3"), "Siciliana Alapin", "B22"),
    (("e4", "c5", "Nc3"), "Siciliana Cerrada", "B23"),
    # Francesa / Caro / Pirc / Moderna / Alekhine
    (("e4", "e6"), "Defensa Francesa", "C00"),
    (("e4", "e6", "d4", "d5", "Nc3"), "Francesa Paulsen/Winawer", "C10"),
    (("e4", "c6"), "Defensa Caro-Kann", "B10"),
    (("e4", "c6", "d4", "d5", "Nc3"), "Caro-Kann Principal", "B15"),
    (("e4", "d5"), "Defensa Escandinava", "B01"),
    (("e4", "d6"), "Defensa Pirc", "B07"),
    (("e4", "g6"), "Defensa Moderna", "B06"),
    (("e4", "Nf6"), "Defensa Alekhine", "B02"),
    # Cerradas 1.d4
    (("d4", "Nf6", "c4", "e6", "Nc3", "Bb4"), "Nimzoindia", "E20"),
    (("d4", "Nf6", "c4", "g6"), "India de Rey", "E60"),
    (("d4", "Nf6", "c4", "e6", "Nf3", "b6"), "India de Dama", "E12"),
    (("d4", "Nf6", "Nf3", "d5"), "Sistema Colle / QGD", "D00"),
    (("d4", "d5", "c4", "e6"), "Gambito de Dama Rehusado", "D30"),
    (("d4", "d5", "c4", "c6"), "Defensa Eslava", "D10"),
    (("d4", "d5", "Bf4"), "Sistema Londres", "D02"),
    (("d4", "f5"), "Defensa Holandesa", "A80"),
    (("d4", "g6", "e4", "Bg7"), "Moderna / Pirc", "B06"),
    # Flanco
    (("c4",), "Apertura Inglesa", "A10"),
    (("Nf3",), "Apertura Reti / Zukertort", "A04"),
    (("g3",), "Apertura Benko / Rey fianchetto", "A00"),
    (("f4",), "Apertura Bird", "A02"),
]


def opening_name(history_san: list[str]) -> tuple[str, str]:
    """Devuelve (nombre, eco) del prefijo más largo que encaje. ("Desconocida", "") si nada."""
    best: tuple[str, str] = ("Posición inicial" if not history_san else "Apertura desconocida", "")
    best_len = -1
    for seq, name, eco in OPENINGS:
        if len(seq) <= len(history_san) and list(seq) == history_san[:len(seq)]:
            if len(seq) > best_len:
                best, best_len = (name, eco), len(seq)
    return best
