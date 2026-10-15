"""
fetch_classics.py — Descarga la base histórica CC0 a data/classics/.
Fuentes (licencia CC0-1.0, las jugadas además no son registrables):
  - Fischer, My 60 Memorable Games
  - Tal, The Life and Games of Mikhail Tal
Uso: .venv/bin/python fetch_classics.py [--force]
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data" / "classics"

SOURCES = {
    "fischer-memorable-60.pgn":
        "https://raw.githubusercontent.com/brianerdelyi/ChessPGN/main/My%20Memorable%2060.pgn",
    "tal-life-and-games.pgn":
        "https://raw.githubusercontent.com/brianerdelyi/ChessPGN/main/Life%20and%20Games%20of%20Mikhail%20Tal.pgn",
}


def fetch(force: bool = False) -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    result = {}
    for name, url in SOURCES.items():
        dest = DATA_DIR / name
        if dest.exists() and not force:
            result[name] = f"ya existe ({dest.stat().st_size // 1024} KB)"
            continue
        req = urllib.request.Request(url, headers={"User-Agent": "AI-Chess/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        dest.write_bytes(data)
        result[name] = f"descargado ({len(data) // 1024} KB)"
    return result


if __name__ == "__main__":
    for name, msg in fetch("--force" in sys.argv).items():
        print(f"{name}: {msg}")
