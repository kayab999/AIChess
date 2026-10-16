# Roadmap público

Estado actual: **v1.0-remediated** — ciclo de vida sólido, 46+ tests en
CI verde, coach híbrido documentado. Congelamos features nuevas hasta
recoger señal real de usuarios (ver "Cómo decidir" abajo).

## Diferido (con motivo)

| Idea | Por qué espera |
|---|---|
| Jugar con negras | Toca turno, PGN, coach y visores a la vez; sin demanda real no compensa el riesgo |
| ECO por posición (transposiciones) | La tabla por secuencia cubre el 90%; el índice por EPD es un extra caro |
| `get_board_png` como imagen MCP | Cambia el contrato de la tool; esperar a que un agente lo pida |
| Consolidación de tools (v2) | Ver `docs/TOOLS.md`; romper compatibilidad exige aviso y versión mayor |
| Visor 3D como centro | Narrativa secundaria a propósito; el análisis es SVG/PGN |

## Cómo decidir qué entra

1. ¿Lo pide un usuario real (issue/discussion) o un modelo? Solo lo primero abre la puerta.
2. ¿Entra con tests (regla `CONTRIBUTING.md`)? Sin tests, no entra.
3. ¿Rompe compatibilidad MCP? Entonces va a v2 con aviso previo.

## Hecho (histórico)

MVP, coach, ANSI, PGN, SVG/PNG, visor HTML, personalidades + torneo,
base histórica, piezas 3D, remediación S0-S5, coach híbrido.
