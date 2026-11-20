# Tecnotics Arcade · Configurador

Aplicación portable (un solo `.exe`) para preparar cualquier PC con Windows 10/11 como lanzador arcade basado en RetroBat.

- **No se instala ni descarga nada.** Solo usa componentes que ya trae Windows: .NET Framework 4.x y PowerShell 5.1.
- **Se ejecuta desde cualquier sitio** (escritorio, pendrive…). Pide permisos de administrador al abrirse.
- **Requiere RetroBat instalado y configurado.** Si no lo encuentra, lo avisa y bloquea las opciones que dependen de él.

## Pestañas

| Pestaña | Qué hace |
|---|---|
| Estado del equipo | Windows, RAM, disco, RetroBat, usuario Arcade, inicio automático, PIN y antivirus. |
| Modo Arcade | Cuenta atrás, combinación secreta, tecla secreta y PIN; instala o desactiva el modo arcade; prueba la bienvenida y los botones del mando. |
| Optimizar Windows | Desactiva o restaura antivirus, actualizaciones, búsqueda, telemetría, informes de errores, notificaciones, Game Bar, energía, impresión y otros servicios. |
| Juegos de Windows | Crea en RetroBat los accesos directos de una carpeta de juegos y da permisos al usuario Arcade. |

## Ediciones de Windows

- **Enterprise / LTSC / Education:** Shell Launcher, Unbranded Boot y Custom Logon (funciones oficiales de quiosco).
- **Home / Pro:** escritorio alternativo por usuario. Funciona igual, pero el logo de Windows puede verse un instante al arrancar.

## Compilar

- Desde Linux: `configurador/compilar.sh` (necesita `mono-mcs` y Python con Pillow). Genera `dist/TecnoticsArcadeConfigurador.exe`.
- El código es C# 5 (`Configurador.cs` y `../modo-arcade/TecnoticsArcade.cs`). Los scripts de `scripts/` van incrustados en el `.exe`.
