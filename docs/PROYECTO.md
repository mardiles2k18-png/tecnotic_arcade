# Tecnotics Arcade

**Repositorio:** [Tecnotics Arcade en GitHub](https://github.com/mardiles2k18-png/tecnotic_arcade)

## De qué se trata

Tecnotics Arcade reúne herramientas para crear máquinas arcade personalizadas con Windows y RetroBat. La experiencia buscada es encender el equipo, ver la bienvenida de Tecnotics, elegir un juego con palancas y botones, y poder volver al escritorio de Windows para mantenimiento.

## Componentes

| Componente | Para qué sirve | Rama |
|---|---|---|
| Gestor de RetroBat | Organiza la biblioteca, importa juegos y ayuda a preparar emuladores, firmware, mandos y opciones de RetroBat. | `codex/retrobat-manager` |
| Configurador y bienvenida | Prepara el arranque en modo arcade, abre RetroBat y protege con PIN el acceso al escritorio de Windows. | `claude/sweet-noether-plai9b` |
| Tema AluBrush de Tecnotics | Da al menú de RetroBat la identidad visual de Tecnotics. | `main` |

El Gestor y el Configurador tienen numeraciones independientes. Las versiones y las pruebas pendientes se registran en [ESTADO.md](ESTADO.md).

## Plataforma

Windows es la plataforma objetivo y RetroBat/EmulationStation es el menú que se personaliza. Pegasus y Batocera quedan registrados como prototipos y antecedentes. La edición de Windows del equipo dedicado sigue pendiente de confirmar.

Claude y Codex se turnan y registran los avances en [BITACORA.md](BITACORA.md). El [inventario general](https://github.com/mardiles2k18-png/tecnotic_arcade/blob/main/docs/estado-proyecto.md) reúne el contexto de las distintas ramas.
