# Creador de proyectos Claude + Codex

Crea un proyecto listo para trabajar por turnos con **Claude** y **Codex**:
carpeta con memoria compartida, Graphify configurado para los dos y un
repositorio en GitHub con el primer commit subido.

## Requisitos (una sola vez)

1. **Python 3.10+** — https://www.python.org (marca "Add python to PATH").
2. **Git** — https://git-scm.com
3. **GitHub CLI** — https://cli.github.com y luego, en una terminal:
   ```
   gh auth login
   ```
4. **Graphify** — si no lo tienes, el creador lo instala (`graphifyy` en PyPI).
   Para Codex añade en `~/.codex/config.toml`:
   ```
   [features]
   multi_agent = true
   ```

## Uso

Doble clic en `nuevo-proyecto.bat` (o `python nuevo_proyecto.py`). Te pregunta:

- nombre del proyecto
- cuenta de GitHub (tu usuario o una de tus organizaciones)
- nombre del repositorio, descripción, objetivo y tecnologías
- si el repositorio es privado o público
- carpeta donde guardas tus proyectos (por defecto `~/Proyectos`, se recuerda)

También acepta todo por parámetros (`python nuevo_proyecto.py --help`).

## Qué genera

```
mi-proyecto/
├── AGENTS.md            reglas de trabajo (las lee Codex; Claude vía CLAUDE.md)
├── CLAUDE.md            importa AGENTS.md + notas solo para Claude
├── docs/
│   ├── PROYECTO.md      de qué se trata y objetivos
│   ├── ESTADO.md        dónde quedamos y de quién es el turno
│   ├── BITACORA.md      una entrada por sesión
│   ├── DECISIONES.md    decisiones y su porqué
│   └── ideas/           ideas sueltas (entran al grafo)
├── .graphifyignore
├── guardar.bat / .sh    respaldo rápido a GitHub
└── configurar_graphify.bat
```

Además:

- `~/Proyectos/PROYECTOS.md`: índice de todos tus proyectos.
- Un bloque en `~/.claude/CLAUDE.md` y `~/.codex/AGENTS.md` (te pregunta antes)
  para que los dos entiendan **"vamos a <proyecto>"** desde cualquier carpeta.

## Cómo se trabaja

1. Abres Claude o Codex y dices **"vamos a <proyecto>"**. El agente hace
   `git pull`, lee `ESTADO.md` y la bitácora, y te dice dónde quedaron.
2. Trabajas. El agente hace commits pequeños con `[claude]` o `[codex]` y push.
3. Dices **"cerramos sesión"**: actualiza estado y bitácora, refresca el grafo
   y sube todo a GitHub. El otro agente lo encuentra todo al día siguiente.

Regla de oro: **un agente a la vez por proyecto**. El campo "Turno" de
`ESTADO.md` sirve para eso.
