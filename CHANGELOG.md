# Registro de cambios · Tecnotics Arcade

Versiones del Configurador (`dist/TecnoticsArcadeConfigurador.exe`) y de la pantalla de bienvenida (`modo-arcade/TecnoticsArcade.cs`).

## 1.2.0 — 2026-11-20
- Si el equipo ya tiene PIN, el Configurador muestra "PIN configurado" y el botón **Cambiar PIN**, que pide el PIN actual y el nuevo dos veces. Los dos campos solo aparecen en la primera instalación.
- **Desactivar Modo Arcade pide el PIN.**
- "Instalar / actualizar" mantiene el PIN existente. Se quita el botón "Guardar solo el PIN".

## 1.1.1 — 2026-11-20
- Corrige el error "el archivo está siendo utilizado por otro proceso" al actualizar: el instalador cierra antes la bienvenida que quedó abierta.

## 1.1.0 — 2026-11-20
- **Menú de Tecnotics al salir de RetroBat:** Volver a RetroBat, Reiniciar el sistema y Apagar. Se maneja con la palanca y los botones, con el teclado o con el ratón. Desde el menú también se puede entrar al modo Windows (combinación secreta, F12 o Ctrl+Alt+F12, y PIN).
- **PIN obligatorio** al instalar o actualizar el Modo Arcade.
- Número de versión visible en el Configurador (título, cabecera y Estado) y en la bienvenida (esquina inferior derecha).
- El PIN cancelado vuelve a la pantalla de origen (cuenta atrás o menú).

## 1.0.0 — 2026-11-20
- **Una sola cuenta:** el escritorio de la cuenta del arcade es la bienvenida de Tecnotics, que abre RetroBat. Con el PIN se abre el escritorio normal de Windows; al reiniciar vuelve el modo arcade.
- Inicio de sesión automático con la contraseña comprobada y guardada cifrada (secreto LSA). Admite cuentas sin contraseña.
- Modo seguro: la pantalla "Bienvenido" de Windows solo se oculta si se marca la casilla.
- Tecla de emergencia Ctrl+Alt+F12, botón "Detener prueba", una sola copia de la bienvenida y registro en `%TEMP%\TecnoticsArcade-registro.txt`.
- Limpieza automática de la versión anterior (usuario "Arcade" y Shell Launcher), que dejaba la pantalla en negro.
- Optimización de Windows: antivirus, actualizaciones, búsqueda, telemetría, informes de errores, notificaciones, Game Bar, energía, impresión y servicios sin uso.
- Compilado contra .NET Framework 4.8 (incluido en Windows 10/11).
