# Estrategia del catálogo de tools (29 y creciendo)

## Problema

Los modelos pequeños degradan su tool-selection a partir de ~15-20
tools. AIChess expone 29. Crecer sin control contradice la apuesta por
modelos locales pequeños.

## Decisión: no romper, guiar, consolidar en v2

1. **Guiar (hecho)**: `docs/AGENTS.md` define un subconjunto esencial
   de 12 tools para clientes pequeños. El resto es opcional por flujo.
2. **No romper**: no se renombra ni elimina ninguna tool en v1.
   Los clientes existentes no se tocan.
3. **Consolidar en v2**: fusiones candidatas (requieren migración):
   - `get_board_svg` + `get_board_png` + `save_board_image` +
     `save_board_png` → `get_board_image(format=[svg|png], ...)`
   - `get_board(color)` ya admite ANSI: documentarlo como ejemplo de
     parámetro en vez de tool nueva.
   - `save_viewer` + `get_board_viewer` → una sola con flag.
   - Evaluar `toggle_coach` + `set_personality` como `configure(...)`.
   Regla v2: **una tool por verbo+objeto**, variantes vía parámetros.

## Regla para tools nuevas

Antes de añadir una tool: ¿puede ser parámetro de una existente?
¿La usa un flujo de agente real o solo depuración? Si es lo segundo,
CLI sí, MCP no.
