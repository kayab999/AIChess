"""MCP: arranque real por stdio, nº de tools y errores sin traceback (auditoría C1)."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SERVER = str(ROOT / "chess_mcp_server.py")
PY = sys.executable  # mismo intérprete que ejecuta pytest (venv local o CI)

EXPECTED_TOOLS = {
    "new_game", "make_move", "get_board", "get_status", "get_legal_moves",
    "undo", "resign", "claim_draw", "analyze", "hint", "explain_move",
    "build_coach_context",
    "coach_status", "toggle_coach", "export_pgn", "save_game", "load_game",
    "list_games", "get_board_svg", "save_board_image", "get_board_png",
    "save_board_png", "get_board_viewer", "list_personalities",
    "set_personality", "lookup_history", "opening_info", "search_classics",
    "get_board_3d", "list_3d_styles",
}


def _session(requests, timeout=60):
    """Ejecuta el servidor, envía requests JSON-RPC y devuelve las líneas.

    El servidor stdio no siempre sale ante EOF: tras capturar las
    respuestas se le envía terminate() (el handshake + tools ya probaron
    el arranque).
    """
    proc = subprocess.Popen(
        [PY, SERVER], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, bufsize=1, cwd=str(ROOT),
    )
    try:
        out = []
        for req in requests:
            proc.stdin.write(json.dumps(req) + "\n")
            proc.stdin.flush()
            if "id" in req:  # las notificaciones no responden
                line = proc.stdout.readline()
                assert line, "el servidor no respondió (¿arranque roto?)"
                out.append(line)
        return [json.loads(line) for line in out if line.strip()]
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=15)


def _init_seq(extra=None):
    seq = [
        {"jsonrpc": "2.0", "id": 0, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                    "clientInfo": {"name": "t", "version": "0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
    ]
    if extra:
        seq.extend(extra)
    return seq


def test_handshake_and_tool_count():
    resps = _session(_init_seq())
    assert resps[0]["result"]["serverInfo"]["name"] == "ai-chess"
    names = {t["name"] for t in resps[1]["result"]["tools"]}
    assert names == EXPECTED_TOOLS, names ^ EXPECTED_TOOLS


def test_error_paths_have_no_traceback():
    resps = _session(_init_seq([
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "new_game", "arguments": {"personality": "inexistente"}}},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "save_game", "arguments": {"path": "/tmp/x"}}},
    ]))
    for r in resps[2:]:
        text = r["result"]["content"][0]["text"]
        assert text.startswith("❌") and "Traceback" not in text, text[:200]


def test_new_game_defaults_to_club():
    resps = _session(_init_seq([
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "new_game", "arguments": {}}},
    ]))
    assert "El Socio del Club" in resps[2]["result"]["content"][0]["text"]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-x", "-q"]))
