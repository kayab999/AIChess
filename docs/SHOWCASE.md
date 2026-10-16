# Publicar AIChess (runbook del owner)

Ángulo: "Chess Toolkit para Agentes" — entrenador local de ajedrez vía
MCP. Stockfish + tu LLM. Sin APIs de pago.

## Ficha común (copiar/pegar)

- **Nombre**: AI Chess — entrenador de ajedrez local vía MCP
- **Descripción**: Juega contra 15 personalidades (Stockfish 16),
  recibe feedback educativo, citas de Fischer/Tal y tableros
  SVG/PNG/3D. 100% local, open source (Apache-2.0).
- **URL**: https://github.com/kayab999/AIChess
- **Instalación** (pegar en el formulario que lo pida):
```json
{
  "mcpServers": {
    "ai-chess": {
      "command": "/ruta/a/AIChess/.venv/bin/python",
      "args": ["/ruta/a/AIChess/chess_mcp_server.py"],
      "env": { "STOCKFISH_PATH": "/usr/games/stockfish" }
    }
  }
}
```
- **Tags**: chess, coach, education, stockfish, local, spanish

## 1. MCP Registry oficial (canónico)

Estado: `server.json` listo en el repo. Falta el paquete público.

1. Publicar `aichess-mcp` 1.0.0 en PyPI (requiere cuenta + release;
   el nombre en server.json debe coincidir).
2. `mcp-publisher login github && mcp-publisher validate && mcp-publisher publish`
3. Verificar la ficha en el Registry.

## 2. mcp.so

Formulario en mcp.so/submit (gratis con revisión; $39 fast-track
opcional). Usar la ficha común + repo URL.

## 3. Glama

Revisar flujo vigente de alta y enviar con la ficha común.

## 4. Reddit (respetando reglas)

- **r/LocalLLaMA**: SOLO megathread quincenal de showcase. Reglas:
  1/10 autopromoción, afiliación declarada ("soy el autor"),
  texto 100% propio (prohibido copy generado por LLM), sin hype.
  Ángulo: "entrenador de ajedrez 100% local que combina Stockfish
  con tu LLM local vía MCP".
- **r/chess**: leer reglas vigentes antes de postear; formato
  show-and-tell, sin hype. Si solo admiten hilo semanal, ir ahí.

Títulos propuestos (sin sensacionalismo):
- LocalLLaMA (megathread): "AIChess: entrenador de ajedrez local (Stockfish + MCP + tu LLM), open source"
- r/chess: solo si las reglas lo permiten; si no, no postear.

## 5. Checklist pre-publicación

- [ ] LICENSE Apache-2.0 en el repo (existe: `LICENSE`)
- [ ] CI verde + tag vigente
- [ ] `docs/DEMO.md` reproducible por un tercero
- [ ] server.json validado contra el schema ($schema incluido)
