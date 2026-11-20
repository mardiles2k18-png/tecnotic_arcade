# Claude Code — Tecnotics Arcade

Leer `AGENTS.md` como instrucciones compartidas de Claude y Codex.

## Graphify
- En Claude Code, invocar `/graphify .` desde la raíz cuando corresponda; la alternativa CLI local sin LLM es `graphify extract . --code-only`.
- Si el entorno es nuevo o temporal, ejecutar `bash scripts/setup-graphify.sh` (Linux) o `powershell -ExecutionPolicy Bypass -File scripts/setup-graphify.ps1` (Windows).
- Consultar primero `graphify query "pregunta" --budget 1000 --depth 2`; abrir después solo los archivos relevantes.
- Si el grafo falta, está obsoleto o la herramienta falla, consultar los archivos directamente.
- No activar extracción semántica con servicios externos sin consentimiento.
