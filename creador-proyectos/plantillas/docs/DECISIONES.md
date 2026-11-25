# Decisiones

Una entrada por decisión importante. Formato:

```
## AAAA-MM-DD — Título corto
- Decisión: ...
- Por qué: ...
- Alternativas descartadas: ...
- Quién: usuario / Claude / Codex
```

## {{FECHA}} — Trabajo por turnos con memoria en el repositorio
- Decisión: Claude y Codex trabajan por turnos sobre la rama `main`; el estado
  vive en `docs/` y cada sesión termina con push a GitHub.
- Por qué: los dos agentes no comparten conversación; el repositorio es lo único común.
