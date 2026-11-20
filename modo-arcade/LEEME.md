# Modo Arcade de Tecnotics

Herramienta para Windows 10 Enterprise LTSC que convierte el equipo en un arcade:

- Al pulsar el botón de encendido no se ve nada de Windows: ni logo, ni inicio de sesión, ni escritorio.
- Aparece la bienvenida **"Hola, Tecnotics te da la bienvenida a TECNOTICS ARCADE"** con una cuenta atrás de 5 segundos, y se abre RetroBat.
- Si RetroBat se cierra, vuelve la bienvenida y RetroBat se abre de nuevo.
- **Modo Windows (oculto):** durante la cuenta atrás, mantén pulsados los botones **7 + 8** del mando durante 3 segundos, o pulsa **F12** en el teclado. Se pide un **PIN**. Con el PIN correcto aparece la pantalla de inicio de sesión de Windows: entra con tu cuenta de administrador.
- Para volver al modo arcade, reinicia el equipo.

## Cómo funciona

| Pieza | Qué hace |
|---|---|
| Usuario `Arcade` | Sin contraseña ni permisos de administrador. Windows entra con él automáticamente. |
| `TecnoticsArcade.exe` | Pantalla de bienvenida. Sustituye al escritorio del usuario Arcade (Shell Launcher). Se maneja con mando, teclado o ratón. |
| Tu cuenta de administrador | Mantiene el escritorio normal, para mantenimiento. |
| Unbranded Boot y Custom Logon | Ocultan el logo de Windows y las pantallas de inicio de sesión. |

## Archivos

- `TecnoticsArcade.cs`: código de la pantalla de bienvenida. El instalador lo compila en el propio equipo.
- `logo.png`: logo que se muestra en la bienvenida.
- `instalar-modo-arcade.ps1`: lo configura todo. Se puede ejecutar varias veces.
- `desinstalar-modo-arcade.ps1`: lo deshace, sin borrar juegos ni RetroBat.

## Configuración (`C:\TecnoticsArcade\config.ini`)

| Clave | Por defecto | Para qué |
|---|---|---|
| `RetroBat` | `C:\RetroBat\retrobat.exe` | Programa que se abre en modo arcade. |
| `Segundos` | `5` | Duración de la cuenta atrás. |
| `ComboBotones` | `7,8` | Botones de la combinación secreta. |
| `ComboSegundos` | `3` | Cuánto tiempo hay que mantener la combinación. |
| `TeclaSecreta` | `F12` | Tecla para abrir el PIN. |

Para saber qué número tiene cada botón de tu mando: `C:\TecnoticsArcade\TecnoticsArcade.exe /botones` (Esc para salir).
Para probar la bienvenida sin activar nada: `C:\TecnoticsArcade\TecnoticsArcade.exe /prueba` (Esc para salir).

## Si algo sale mal

- **Por SSH**, con tu cuenta de administrador: ejecuta `desinstalar-modo-arcade.ps1`.
- **Sin SSH:** mantén pulsada la tecla **Shift** mientras arranca Windows para saltarte el inicio de sesión automático y entra con tu cuenta.

## Importante

Los juegos deben estar en una carpeta que el usuario Arcade pueda leer, por ejemplo `C:\Juegos`. No pueden estar en el escritorio de tu cuenta, porque esa carpeta es privada de tu usuario.
