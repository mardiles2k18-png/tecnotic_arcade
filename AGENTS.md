# tecnotic_arcade — instrucciones para los agentes

Este proyecto lo trabajan **Claude** y **Codex** por turnos, con el mismo
repositorio y la misma memoria. Este archivo es la fuente de verdad para los dos
(Claude lo lee a través de `CLAUDE.md`).

- Repositorio: https://github.com/mardiles2k18-png/tecnotic_arcade
- Descripción: Proyecto para crear arcades con lanzadores de código abierto

## Memoria del proyecto

| Archivo | Para qué sirve |
|---|---|
| `docs/PROYECTO.md` | De qué se trata, objetivos, alcance. Cambia poco. |
| `docs/ESTADO.md` | **Dónde quedamos**: en qué se está trabajando, próximos pasos, bloqueos y quién tiene el turno. |
| `docs/BITACORA.md` | Una entrada por sesión: quién, qué se hizo, qué quedó pendiente. Lo nuevo va arriba. |
| `docs/DECISIONES.md` | Decisiones importantes y su porqué, para no volver a discutirlas. |
| `docs/ideas/` | Ideas sueltas y borradores. Un archivo por idea. |
| `docs/planes/`, `docs/investigacion/`, `docs/diseno/` | Trabajo de cada rol (ver "Equipo" al final). |
| `graphify-out/GRAPH_REPORT.md` | Mapa del proyecto generado por Graphify (código, documentos e ideas conectados). |

## Al empezar una sesión ("vamos a tecnotic_arcade")

1. `git pull` para traer lo último que hizo el otro agente.
2. Lee, en este orden: `docs/ESTADO.md`, las 3 últimas entradas de
   `docs/BITACORA.md`, `docs/PROYECTO.md` y, si existe,
   `graphify-out/GRAPH_REPORT.md`.
3. Si en `docs/ESTADO.md` el turno lo tiene **el otro agente**, avisa al usuario
   antes de tocar nada (puede haber trabajo sin subir).
4. Pon tu nombre en "Turno" de `docs/ESTADO.md`, haz commit y push.
5. Responde al usuario con un resumen corto: de qué va el proyecto, dónde
   quedamos, qué propones hacer ahora. Espera su confirmación.

## Mientras trabajas

- Commits pequeños y frecuentes. Empieza el mensaje con `[claude]` o `[codex]`.
- `git push` después de cada avance que funcione: GitHub es el respaldo.
- Una idea nueva → archivo en `docs/ideas/`. Una decisión → `docs/DECISIONES.md`.
- Antes de buscar en el código o responder preguntas de arquitectura, consulta
  `graphify-out/GRAPH_REPORT.md`.
- No reescribas el historial (`push --force`, `rebase` de lo ya subido).

## Al cerrar la sesión ("cerramos sesión")

1. Actualiza `docs/ESTADO.md`: qué está hecho, qué sigue, bloqueos. Deja el
   turno en **libre**.
2. Añade una entrada arriba en `docs/BITACORA.md` (usa el formato que hay ahí).
3. El código se re-indexa solo en cada commit (hook de git de Graphify). Si
   cambiaron documentos o ideas, actualiza también la parte semántica:
   Claude `/graphify . --update`, Codex `$graphify . --update`.
4. Commit y push. Confirma al usuario que quedó subido a GitHub.

## Datos técnicos

- Tecnologías: Por definir
- Cómo ejecutar / probar: (completar cuando exista)

<!-- equipo:inicio -->
## Cómo hablar con el usuario

El usuario puede no saber nada de programación, de IA ni de la terminal.

- Habla en palabras simples y frases cortas. Si usas un término técnico,
  explícalo en una línea o, mejor, evítalo.
- Las decisiones técnicas son tuyas: elige la opción razonable, hazla y
  cuéntala en una frase. Pregunta solo lo que el usuario sabe (qué quiere,
  cómo debe verse, qué es más importante), nunca confirmaciones técnicas
  ("¿confirmas la ruta…?", "¿hago commit?").
- No le pidas que ejecute comandos, edite archivos ni cambie configuraciones:
  hazlo tú. Si de verdad necesitas algo de él (iniciar sesión, aprobar un
  permiso), dile exactamente qué botón pulsar.
- Al empezar, responde con: de qué trata el proyecto, dónde quedamos y qué
  propones hacer ahora, en 3 a 5 líneas.

## Equipo (roles)

El proyecto parte con cuatro roles y la skill `marca-tecnotics`, instalados como skills en `.agents/skills/`
(Codex y Gemini) y `.claude/skills/` (Claude). Usa el rol que corresponda a la tarea o
el que pida el usuario ("como diseñador...").

| Rol | Skill | Se apoya en | Deja su trabajo en |
|---|---|---|---|
| Jefe de proyecto | `jefe-de-proyecto` | brainstorming, writing-plans, executing-plans, github-release | `docs/planes/`, `docs/ESTADO.md` |
| Programador y analista | `programador-analista` | test-driven-development, systematic-debugging, verification-before-completion, requesting/receiving-code-review, security-review | código, pruebas, `docs/DECISIONES.md` |
| Diseñador gráfico | `disenador-grafico` | marca-tecnotics, frontend-design, theme-factory | `docs/diseno/` |
| Investigador | `investigador` | deep-research | `docs/investigacion/` |

Además de esta base, el proyecto puede tener **paquetes** según su tecnología
(Escritorio .NET, Web, Datos, GitHub Actions, Documentación, Arte, Crear
skills, Trabajo en paralelo) y skills agregadas a mano. Lo elegido está en
`.agents/equipo.json` y el detalle en `.agents/skills/FUENTES.md`. Usa esas
skills cuando la tarea lo pida.

Si el chat se alarga o vas a dejar el trabajo a mitad de sesión, usa
`memoria-de-chat`: deja una nota en `docs/memoria/` para que el siguiente chat
(de cualquier IA) siga sin perder el hilo. Al ponerte al día, lee la última nota.

Si una skill externa propone guardar archivos en otra ruta (por ejemplo
`docs/superpowers/`), usa las rutas de esta tabla. El origen y la licencia de
cada skill están en `.agents/skills/FUENTES.md`.
<!-- equipo:fin -->

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- When graphify-out/graph.json exists, run `graphify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. When the answer is under a Markdown heading, `graphify section "<heading>"` prints that section's text, so the .md need not be opened. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- A committed graphify-out/graph.json is rewritten whole on every build, so a large diff to it in a pull request is expected. Do not flag it as churn or suggest skipping the graph rebuild or its hooks.
