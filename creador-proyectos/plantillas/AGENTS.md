# {{NOMBRE}} — instrucciones para los agentes

Este proyecto lo trabajan **Claude** y **Codex** por turnos, con el mismo
repositorio y la misma memoria. Este archivo es la fuente de verdad para los dos
(Claude lo lee a través de `CLAUDE.md`).

- Repositorio: {{URL}}
- Descripción: {{DESCRIPCION}}

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

## Al empezar una sesión ("vamos a {{NOMBRE}}")

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

- Tecnologías: {{TECNOLOGIAS}}
- Cómo ejecutar / probar: (completar cuando exista)
