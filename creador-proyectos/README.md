# Generador de Proyectos IA Tecnotics

Herramienta para **crear proyectos nuevos o mejorar proyectos existentes** y
trabajarlos en conjunto con **Claude** y **Codex** (ChatGPT). Cada proyecto
queda con:

- **Memoria compartida**: los dos agentes saben de qué se trata y dónde
  quedaron (`AGENTS.md`, `docs/ESTADO.md`, `docs/BITACORA.md`...).
- **Un equipo de skills**: jefe de proyecto, programador y analista,
  diseñador gráfico e investigador, apoyados en skills open source.
- **Graphify** configurado para los dos, que integra código, ideas y
  decisiones en un grafo de conocimiento.
- **Respaldo constante en GitHub**.
- **"Vamos a <proyecto>"**: desde cualquier chat el agente encuentra el
  proyecto y retoma donde quedaron.

## Requisitos (una sola vez)

1. **Python 3.10+**: https://www.python.org (marca "Add python to PATH").
2. **Git**: https://git-scm.com
3. **GitHub CLI**: https://cli.github.com y luego, en una terminal:
   ```
   gh auth login
   ```
4. **Graphify**: si no lo tienes, el generador lo instala (`graphifyy` en PyPI).
   Para Codex añade en `~/.codex/config.toml`:
   ```
   [features]
   multi_agent = true
   ```

## Uso

| Quiero... | En Windows | En terminal |
|---|---|---|
| Elegir en un menú | doble clic en `generador.bat` | `python generador.py` |
| Crear un proyecto nuevo | doble clic en `nuevo-proyecto.bat` | `python generador.py --crear` |
| Mejorar un proyecto existente | arrastra su carpeta sobre `mejorar-proyecto.bat` | `python generador.py --mejorar RUTA` |

Al **crear** te pregunta: nombre, cuenta de GitHub (tu usuario o una de tus
organizaciones), nombre del repositorio, descripción, objetivo, tecnologías,
visibilidad (privado por defecto) y la carpeta donde guardas tus proyectos.

Al **mejorar** toma el nombre del `README.md` y la cuenta y el repo del
remoto de git, si existen. **Nunca sobrescribe tus archivos**: crea solo lo que
falta, añade bloques marcados a `AGENTS.md`, `CLAUDE.md` y `.gitignore`, y en
el commit incluye solo lo que añadió el generador. Si el proyecto aún no está en
GitHub, crea el repositorio.

Todo se puede dar por parámetros: `python generador.py --help`.

## Qué queda en cada proyecto

```
mi-proyecto/
├── AGENTS.md            reglas de trabajo (Codex; Claude las lee vía CLAUDE.md)
├── CLAUDE.md            importa AGENTS.md + notas solo para Claude
├── docs/
│   ├── PROYECTO.md      de qué se trata y objetivos
│   ├── ESTADO.md        dónde quedamos y de quién es el turno
│   ├── BITACORA.md      una entrada por sesión
│   ├── DECISIONES.md    decisiones y su porqué
│   ├── ideas/           ideas sueltas (entran al grafo)
│   ├── planes/          diseños y planes del jefe de proyecto
│   ├── investigacion/   informes con fuentes del investigador
│   └── diseno/          guía visual, maquetas y recursos del diseñador
├── .agents/skills/      equipo de skills para Codex (+ FUENTES.md con licencias)
├── .claude/skills/      la misma copia para Claude
├── .graphifyignore
├── guardar.bat / .sh    respaldo rápido a GitHub
└── configurar_graphify.bat
```

Y fuera del proyecto:

- `PROYECTOS.md` en tu carpeta de proyectos: índice de todos.
- Un bloque en `~/.claude/CLAUDE.md` y `~/.codex/AGENTS.md` (pregunta antes)
  para que los dos entiendan **"vamos a <proyecto>"**.

## El equipo

| Rol | Se apoya en (skills open source) |
|---|---|
| Jefe de proyecto | brainstorming, writing-plans, executing-plans ([obra/superpowers](https://github.com/obra/superpowers), MIT) |
| Programador y analista | test-driven-development, systematic-debugging, verification-before-completion, requesting/receiving-code-review (superpowers) y webapp-testing ([anthropics/skills](https://github.com/anthropics/skills), Apache 2.0) |
| Diseñador gráfico | frontend-design, theme-factory, algorithmic-art (anthropics/skills) |
| Investigador | deep-research ([staruhub/ClaudeSkills](https://github.com/staruhub/ClaudeSkills), MIT) |

Los roles son skills propias en español (`plantillas/_punto_agents/skills/`)
que conectan las externas con la memoria del proyecto. Las externas están
fijadas a un commit en `skills.json`: para añadir o actualizar una, revisa sus
cambios y edita ese archivo. Luego actualiza un proyecto con
`python generador.py --instalar-skills RUTA`.

## Cómo se trabaja

1. Abres Claude o Codex y dices **"vamos a <proyecto>"**. El agente hace
   `git pull`, lee `ESTADO.md` y la bitácora, y te dice dónde quedaron.
2. Pides el rol que necesitas: *"como investigador, compara..."*.
3. El agente hace commits pequeños con `[claude]` o `[codex]` y push.
4. Dices **"cerramos sesión"**: actualiza estado y bitácora, refresca el grafo
   y sube todo a GitHub.

Regla de oro: **un agente a la vez por proyecto**. El campo "Turno" de
`ESTADO.md` sirve para eso.

## Estructura de esta herramienta

| Archivo | Qué es |
|---|---|
| `generador.py` | el programa (solo biblioteca estándar de Python) |
| `plantillas/` | archivos que recibe cada proyecto (`_punto_x` se instala como `.x`) |
| `skills.json` | catálogo de skills open source, fijadas a un commit |
| `equipo.md` | sección "Equipo" que se añade al `AGENTS.md` de cada proyecto |
| `instruccion_global.md` | bloque "vamos a <proyecto>" para Claude y Codex |
