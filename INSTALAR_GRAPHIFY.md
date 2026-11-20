# INSTALAR GRAPHIFY EN UN NUEVO COMPUTADOR

**Tecnotics Arcade — configuración de Claude Code + Codex y reducción de lecturas de código.**

## Respuesta corta

**Sí:** Graphify es una herramienta que se ejecuta en cada computador o entorno que analiza el repositorio. **No hay que repetir manualmente todos los pasos**: este repositorio contiene los scripts de instalación y las instrucciones que sirven en cualquier equipo compatible.

GitHub sincroniza **el código, estas instrucciones y `graphify-out/graph.json`**. Instala la CLI y las skills en cada PC. El grafo versionado llega con `git clone` o `git pull` en la rama de trabajo. Si se utiliza Codex en la nube, la instalación debe ejecutarse también dentro de ese entorno (no hereda la del PC).

## Mensaje para copiar y pegar a Claude Code o Codex

> Estoy trabajando en `mardiles2k18-png/tecnotic_arcade`. Prepara Graphify en **este equipo o entorno** usando los scripts del propio repositorio. Primero lee `INSTALAR_GRAPHIFY.md` y `AGENTS.md` (y `CLAUDE.md` si eres Claude). Si el repositorio no está clonado, solicita la ubicación donde clonarlo y usa Git con la rama de trabajo correcta; **no sobreescribas cambios locales**. En Windows ejecuta `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-graphify.ps1`; en Linux/Codex Cloud ejecuta `bash scripts/setup-graphify.sh`. Comprueba que existe `graphify-out/graph.json` y ejecuta una consulta con `--budget 1000 --depth 2`. No solicites ni uses claves API: analiza código solamente con `--code-only`. Si faltan permisos, dependencias, red o un paso necesita autorización, explícame cuál. No toques archivos de juegos ni el sistema arcade. Al terminar, informa qué se instaló, dónde quedó el grafo y qué falta.

## En Windows — un solo comando (desde la raíz del proyecto)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-graphify.ps1
```

El script:
1. Detecta `uv`; si no lo encuentra, intenta instalarlo con `winget` para el usuario (evita PowerShell como administrador).
2. Instala `graphifyy` solo si falta y corrige `PATH` para esa sesión.
3. Registra la skill de Graphify en Codex y Claude.
4. Construye `graphify-out/graph.json` con `--code-only`, **sin consumir API de IA**.

Si pide reiniciar PowerShell para completar la instalación de `uv`, ciérralo, abre otra consola y repite el mismo comando. Para reinstalar skills sin regenerar el grafo, usa `-SkipExtract`.

## En Linux / Codex Cloud

```bash
bash scripts/setup-graphify.sh
```

Requiere Python 3.11+ con soporte de entornos virtuales y pip, además de acceso para instalar dependencias. Instala Graphify dentro de `.graphify-venv/` y genera el grafo local. Las instrucciones del repositorio se comparten con Codex y Claude, pero las skills globales no se copian automáticamente entre máquinas.

Para Codex Cloud, configurar la preparación del entorno (setup) para ejecutar el script **una vez clonado el repositorio**. Si no se puede establecer un setup, pedir a Codex que lo ejecute al inicio de la tarea. El entorno necesita acceso para descargar paquetes.

## Si el repositorio aún no existe en la PC

```powershell
git clone https://github.com/mardiles2k18-png/tecnotic_arcade.git
cd tecnotic_arcade
```

**Atención:** mientras la configuración esté en la PR #2 y no fusionada, clona la rama `chore/graphify-multidevice` con `git clone -b chore/graphify-multidevice ...`, o cambia a ella explícitamente. Cuando se fusione, bastará la rama predeterminada. No ejecutar `git clone` sobre una carpeta de trabajo existente.

## Comprobación en Windows

```powershell
graphify --help
Test-Path .\graphify-out\graph.json
graphify query "scripts RetroBat" --budget 1000 --depth 2
```

En Linux/Codex Cloud usa `.graphify-venv/bin/graphify` en lugar de `graphify`.

## Uso diario

- Trabajar en una rama distinta por agente/tarea y usar Pull Requests para integrar cambios.
- Después de `git pull`, consulta el grafo versionado. Si cambias el código, regenera con `graphify extract . --code-only` (en Linux: `.graphify-venv/bin/graphify extract . --code-only`) e incluye `graphify-out/graph.json` en el commit.
- Consultar el grafo antes de abrir docenas de archivos, pero verificar cambios en los archivos reales.
- `--budget 1000` limita la salida de **una consulta**, no la factura total del asistente.
- Para compartir el **estado de las tareas**, actualizar GitHub con commits, PRs y documentación. Graphify no reemplaza esa coordinación.

Guía ampliada: `docs/graphify-colaboracion.md`.
