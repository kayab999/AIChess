# AIChess para agentes (Claude Desktop, GPT, modelos locales)

AIChess es un backend de ajedrez para agentes: el motor calcula
(posición, evaluación, motivos tácticos) y el LLM cliente explica,
entrena y planifica. Las heurísticas locales son la red de seguridad;
el LLM, el redactor.

## Conexión (Claude Desktop)

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

Sin `STOCKFISH_PATH`, Claude Desktop suele lanzar el servidor con un
`PATH` reducido y el binario no aparece aunque esté instalado.

## Receta: sesión de entrenamiento

1. `new_game` (o `set_personality` para elegir rival: `club` por defecto).
2. Bucle: `make_move` → lee `🎓 Entrenador` + `📜 Historia`.
3. Duda: `hint` (niveles 1→3 auto-escalan), `explain_move`, `opening_info`.
4. Para un plan semanal: `export_pgn` + `coach_status` y pide al LLM
   que detecte patrones (aperturas flojas, piezas colgadas, finales).

## Coach híbrido: cómo usar `build_coach_context`

La tool **no llama a ningún LLM**: devuelve un JSON con el contexto
(FEN, evaluación, pérdida en cp, mejor jugada, motivos) más una
plantilla de prompt con una regla de ancla:

> *Si la evaluación dice +2.0 a favor de blancas, no digas que la
> posición está perdida. La evaluación de Stockfish manda; tu trabajo
> es explicarla en lenguaje humano, no contradecirla.*

Flujo: el agente llama a `build_coach_context`, pega el contexto en su
propio razonamiento y redacta el consejo final.

### Calidad según tu modelo (decisión consciente)

La calidad del coach híbrido **depende del LLM cliente**, componente
que no controlamos:

- Modelos grandes con buen instruction-following (Claude Opus/Sonnet,
  GPT-4o): coach excelente.
- Modelos pequeños locales (Qwen3-1.7B, GLM-4-9B): el coach puede ser
  **peor que el modo heurístico puro**.
- Sin LLM potente: ignora `build_coach_context` y usa el bloque `🎓`
  de `make_move` (determinista, siempre disponible).

Recomendamos modelos de 7B+ con buen instruction-following para el
modo híbrido.

### Catálogo esencial (modelos pequeños)

Con ~15-20 tools el tool-selection de modelos pequeños decae. Si tu
cliente es pequeño, limita su configuración a este subconjunto
(documentado como estable):

`new_game, make_move, get_board, get_status, get_legal_moves, undo,
resign, claim_draw, analyze, hint, explain_move, build_coach_context`

El resto (visores, PGN, torneo, historial, 3D) es opcional por flujo.
Estrategia completa de consolidación: `docs/TOOLS.md`.

## Ejemplo de sesión

```
> new_game(personality="profesor")
♟️ Nueva partida vs El Profesor (ELO 1800) ...

> make_move e4
... e4 e6 ...
🎓 Entrenador: ✅ bien — Bien jugado e4. Consejo: Caballo sin desarrollar.
📜 Historia: Robert James Fischer jugó e4 aquí (Mar del Plata, 1959, 1-0)

> hint 2
💡 Nivel 2: Mira la zona de d4 como candidata.
```
