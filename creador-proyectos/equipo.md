## Equipo (roles)

El proyecto parte con cuatro roles, instalados como skills en `.agents/skills/`
(Codex) y `.claude/skills/` (Claude). Usa el rol que corresponda a la tarea o
el que pida el usuario ("como diseñador...").

| Rol | Skill | Se apoya en | Deja su trabajo en |
|---|---|---|---|
| Jefe de proyecto | `jefe-de-proyecto` | brainstorming, writing-plans, executing-plans | `docs/planes/`, `docs/ESTADO.md` |
| Programador y analista | `programador-analista` | test-driven-development, systematic-debugging, verification-before-completion, requesting/receiving-code-review, webapp-testing | código, pruebas, `docs/DECISIONES.md` |
| Diseñador gráfico | `disenador-grafico` | frontend-design, theme-factory, algorithmic-art | `docs/diseno/` |
| Investigador | `investigador` | deep-research | `docs/investigacion/` |

Si una skill externa propone guardar archivos en otra ruta (por ejemplo
`docs/superpowers/`), usa las rutas de esta tabla. El origen y la licencia de
cada skill están en `.agents/skills/FUENTES.md`.
