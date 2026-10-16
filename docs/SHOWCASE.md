# Publicar AIChess en directorios MCP (checklist)

El valor diferencial es "Chess Toolkit para Agentes" (no "otro motor").
Ángulo de la ficha: coach local + personalidades + citas históricas.

## Directorios objetivo

1. **mcp.so** — ficha con: descripción (coach Stockfish local vía MCP),
   categoría Games/Education, link al repo, ejemplo `new_game`/`make_move`.
2. **GitHub topic `mcp-server`** — añadir el topic al repo + `mcp`
   en la descripción. Mejora descubrimiento en búsquedas.
3. **Smithery / PulseMCP** — revisar requisitos (algunos piden
   `package.json` o Dockerfile; si lo piden, empaquetar no cambia código).

## Material necesario (ya existe)

- GIF/sesión de ejemplo: ver `docs/AGENTS.md` (ejemplo de sesión).
- Badges: CI verde en README.
- Licencia: confirmar fichero LICENSE antes de publicar.

## No hacer todavía

- Cambiar nombres de tools por marketing (rompe clientes).
- Prometer fuerza ELO exacta (el ELO es aproximado: ver README).
