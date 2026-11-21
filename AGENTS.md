# Instrucciones para agentes — Tecnotics Arcade

## Alcance y fuente de verdad
Este repositorio contiene personalizaciones para Batocera y un plan de migración a Windows LTSC + RetroBat. **No** asumir que la migración está terminada: `README.md` documenta Batocera y `docs/plan-windows-retrobat.md` contiene tareas pendientes para Windows. Conservar ambas rutas, a menos que se solicite explícitamente un cambio de alcance.

- `retrobat/`: gestor portable de RetroBat, herramientas de BIOS y scripts de accesos directos de Windows.
- `sistema/`: configuración de placa HP ProOne 400 G2 y scripts de Wine/Batocera.
- `themes/`: temas EmulationStation (XML y recursos).
- `arranque/`: material y scripts de inicio.
- `herramientas/`: generación de recursos gráficos.
- Hardware de referencia documentado: HP ProOne 400 G2, Intel HD 530, 16 GB RAM.

## Política Graphify (ahorro de contexto)
1. Al iniciar tareas de código en un checkout, comprobar si existe `graphify-out/graph.json`. Si no existe y la CLI está disponible, ejecutar `graphify extract . --code-only`; en entornos efímeros utilizar `bash scripts/setup-graphify.sh`.
2. Para localizar relaciones o subsistemas, **preferir consultas acotadas**: `graphify query "pregunta" --budget 1000 --depth 2`, `graphify explain "nodo"`, `graphify path "A" "B"`. Restringir la respuesta antes de leer archivos completos.
3. Validar en los archivos originales toda decisión que cambie código o configuración. El grafo es índice, no sustituto del código ni de pruebas.
4. Tras cambios de código, ejecutar `graphify update .` cuando la CLI esté disponible. Incluye `graphify-out/graph.json` en el commit cuando cambie el índice. Genera la versión compartida con `graphify extract . --code-only`.
5. Si Graphify no está disponible, continuar trabajando con búsquedas selectivas; no bloquear el desarrollo ni inventar resultados del grafo.
6. No enviar documentación, imágenes, videos ni secretos a backends de IA sin autorización: la extracción predeterminada aquí es `--code-only`, local y sin API.
7. No imprimir archivos enteros ni listar todas las dependencias si basta un fragmento; utilizar el menor contexto relevante.

## Colaboración y validación
- No modificar hardware ni ejecutar scripts de sistema en la máquina arcade sin revisión humana.
- Evitar rutas absolutas nuevas: los scripts existentes contienen rutas específicas de Windows que requieren parametrización cuidadosa.
- No incorporar ROMs, ejecutables de juegos, claves, credenciales ni contenido comercial al repositorio.
- Para trabajo simultáneo entre Claude y Codex, trabajar sobre ramas distintas y proponer PRs; no sobrescribir cambios ajenos.
- Publicar en GitHub los cambios del proyecto una vez verificados. Para el Gestor de RetroBat, actualizar la rama de trabajo y su pull request, y regenerar el ejecutable portable cuando cambie la aplicación.
- Ejecutar comprobaciones apropiadas antes de afirmar que algo funciona. No afirmar haber probado scripts de Windows o Batocera sin sus entornos.
