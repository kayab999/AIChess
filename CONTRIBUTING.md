# Contribuir a AIChess

> ❄️ **Congelación temporal de features**: hasta recoger 2 semanas de
> señal real de usuarios (ver `docs/ROADMAP.md`), solo se aceptan fixes,
> tests y docs. Las ideas nuevas van como issues para discutir.

## Regla de oro

## Regla de oro

**Toda feature entra con tests o no entra.** La suite (`tests/`) es el
contrato del proyecto: cubre ciclo de vida, PGN, rutas, reglas, coach,
ELO, MCP y torneo. Un PR sin tests para comportamiento nuevo se rechaza.

## Cómo trabajar

1. Rama por cambio, PR contra `main` (la CI debe estar verde).
2. Tests deterministas: usa `seed` fijo en el motor; evita depender de
   tiempos de Stockfish (aserciones sobre estructura, no sobre jugadas
   concretas salvo libro de aperturas).
3. Sin red en tests (los datos CC0 van commiteados en `data/`).
4. Limpieza: los artefactos de test usan prefijo `test-` (los borra
   `conftest.py` automáticamente).

## Convenciones

- Español en mensajes de usuario y docs; código en inglés.
- Estado de partida: `result` solo vive en estado terminal
  (`in_progress`/`check` ⇒ `result is None`). Testéalo si tocas
  `player_move`, `undo`, `load_game` o `claim_draw`.
- Rutas de ficheros: siempre vía `sandboxed()` (nunca `open()` directo
  con input de usuario/MCP).
- Tools MCP: sin tracebacks al cliente (usar `_io_guard`), mutaciones
  bajo `_locked`, errores como `{"error": ...}` / `❌ ...`.
- Nombres honestos: la tool debe describir lo que devuelve, no para
  qué se usará después (ver `build_coach_context`).
