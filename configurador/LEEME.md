# Tecnotics Arcade · Configurador

Aplicación portable (un solo `.exe`) que configura el **arranque** de un PC con Windows 10/11 como lanzador arcade basado en RetroBat: al encender se ve solo la bienvenida de Tecnotics y RetroBat, y el modo Windows queda oculto tras un PIN.

La gestión de juegos no forma parte de esta herramienta; es un complemento de las demás herramientas del repositorio.

- **No se instala ni descarga nada.** Solo usa componentes que ya trae Windows: .NET Framework 4.x y PowerShell 5.1.
- **Se ejecuta desde cualquier sitio** (escritorio, pendrive…). Pide permisos de administrador al abrirse.
- **Requiere RetroBat instalado y configurado.** Si no lo encuentra, lo avisa y bloquea las opciones que dependen de él.

## Pestañas

| Pestaña | Qué hace |
|---|---|
| Estado del equipo | Windows, RAM, disco, RetroBat, usuario Arcade, inicio automático, PIN y antivirus. |
| Modo Arcade | Cuenta atrás, combinación y tecla secretas, PIN y contraseña de la cuenta (para entrar sola al encender); instala o desactiva el modo arcade; prueba la bienvenida y los botones del mando; detiene la prueba. |
| Optimizar Windows | Desactiva o restaura antivirus, actualizaciones, búsqueda, telemetría, informes de errores, notificaciones, Game Bar, energía, impresión y otros servicios. |

## Una sola cuenta

El arcade usa **la cuenta de Windows con la que se ejecuta el Configurador**. Su escritorio pasa a ser la bienvenida de Tecnotics. La contraseña de la cuenta se comprueba antes de guardarla y se guarda cifrada por Windows (secreto LSA `DefaultPassword`), igual que hace el inicio automático de Windows.

## Ediciones de Windows

- **Enterprise / LTSC / Education:** además se ocultan las animaciones y los botones de las pantallas de inicio (Custom Logon). La pantalla "Bienvenido" solo se oculta si se marca la casilla, cuando ya se ha comprobado que el arranque funciona.
- **Home / Pro:** funciona igual, pero puede verse un instante la pantalla de inicio de Windows.

## Compilar

- Desde Linux: `configurador/compilar.sh` (necesita `mono-mcs` y Python con Pillow). Genera `dist/TecnoticsArcadeConfigurador.exe`.
- El código es C# 5 (`Configurador.cs` y `../modo-arcade/TecnoticsArcade.cs`). Los scripts de `scripts/` van incrustados en el `.exe`.
