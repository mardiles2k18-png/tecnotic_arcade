# Graphify: Codex, Claude Code y varios computadores

## Qué sincroniza cada herramienta
- **GitHub** sincroniza el código, los documentos de trabajo y estas instrucciones (`AGENTS.md` / `CLAUDE.md`).
- **Graphify OSS** genera **un grafo por checkout** en `graphify-out/`. Está ignorado por Git para evitar conflictos y archivos regenerados constantemente.
- **Codex Cloud** no accede a la instalación de Graphify de un PC personal. Debe instalarse en el propio entorno de ejecución.
- Graphify no optimiza automáticamente el chat de ChatGPT; ayuda a los agentes capaces de ejecutar la CLI dentro del repositorio.
- El código se analiza localmente con `--code-only`. No autorizar extracción semántica/documentos/imágenes ni conectar APIs sin revisión.

## Primer uso — Windows (PC casa o segundo PC)
Desde PowerShell (no desde `C:\Windows\system32`):

```powershell
git clone https://github.com/mardiles2k18-png/tecnotic_arcade.git
cd tecnotic_arcade
powershell -ExecutionPolicy Bypass -File .\scripts\setup-graphify.ps1
graphify query "scripts RetroBat y accesos directos" --budget 1000 --depth 2
```

Si el repo ya existe, usar `git pull` desde su rama de trabajo, sin volver a clonar. Para actualizar el grafo tras cambios: `graphify update .` (si la CLI está disponible).

## Primer uso — Linux / Codex Cloud / terminal de Claude
En la raíz del checkout:

```bash
bash scripts/setup-graphify.sh
.graphify-venv/bin/graphify query "configuración HP y scripts Wine" --budget 1000 --depth 2
```

En **Codex Cloud**, configurar el *setup script* del entorno para que ejecute `bash scripts/setup-graphify.sh` **desde la raíz del repositorio**. Si los comandos de configuración se ejecutan antes de disponer del checkout, ejecutarlo en la primera tarea tras el checkout. La disponibilidad y persistencia del entorno de Codex Cloud dependen de sus opciones de ejecución; esta configuración no se activa automáticamente por el mero hecho de existir el archivo.

En Codex, solicitar explícitamente que consulte `AGENTS.md` y `graphify-out/graph.json`. En Claude Code, consultar `CLAUDE.md` y la skill de Graphify. Si no se dispone de graphify, continuar usando los archivos directamente.

## Trabajo diario entre dos PCs y agentes
1. `git fetch`, revisar ramas, y actualizar la rama de trabajo con seguridad (`git pull --ff-only` cuando corresponda).
2. Crear ramas separadas para trabajos de Claude y Codex; preparar PRs para revisión antes de mezclar cambios.
3. Si el grafo falta: ejecutar el script de setup. Si hay cambios en archivos: `graphify update .`.
4. Primero consultar `graphify query "... " --budget 1000 --depth 2` y después leer el código relevante.
5. Ejecutar las pruebas apropiadas al sistema destino. Evitar asumir que scripts .ps1 o .sh ya se probaron.
6. Subir solo código, documentación e instrucciones; el grafo permanece local. Una rama remota no guarda automáticamente el estado de una sesión del asistente.

## Diagnóstico rápido
```powershell
graphify --help
graphify god-nodes --top 10
graphify benchmark
```

En Linux reemplazar `graphify` por `.graphify-venv/bin/graphify` cuando el ejecutable no esté en PATH.

## Consideraciones específicas del proyecto
El README actual describe Batocera, mientras que `docs/plan-windows-retrobat.md` documenta una transición planificada a Windows LTSC + RetroBat. Los agentes deben distinguir esas plataformas y evitar cambios contradictorios. Los scripts tienen rutas absolutas de Windows: no deben ejecutarse en el equipo arcade sin verificar rutas y efectos. No incluir juegos, ROMs ni secretos en Git.
