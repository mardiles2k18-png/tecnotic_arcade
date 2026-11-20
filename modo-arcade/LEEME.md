# Modo Arcade de Tecnotics: pantalla de bienvenida

`TecnoticsArcade.cs` es la pantalla de bienvenida del arcade. **Se instala y se configura con el Configurador** (`configurador/`, que genera `dist/TecnoticsArcadeConfigurador.exe`). Los instaladores antiguos de esta carpeta, que usaban un segundo usuario "Arcade", se retiraron porque dejaban la pantalla en negro.

## Cómo funciona (una sola cuenta)

- Al encender, Windows entra solo con la cuenta del arcade.
- El escritorio de esa cuenta (valor `Shell` del usuario) es `C:\TecnoticsArcade\TecnoticsArcade.exe`.
- La bienvenida muestra **"Hola, Tecnotics te da la bienvenida a TECNOTICS ARCADE"**, hace una cuenta atrás y abre RetroBat. Si RetroBat se cierra, vuelve a empezar.
- **Modo Windows:** combinación secreta del mando (por defecto 7 + 8 durante 3 s), F12 durante la cuenta atrás, o **Ctrl + Alt + F12** en cualquier momento, y después el **PIN**. Se abre el escritorio normal de Windows en la misma cuenta. Al reiniciar vuelve el modo arcade.

## Parámetros

- `/prueba`: prueba sin cambiar nada. Franja naranja arriba; Esc o Ctrl + Alt + F12 la cierran, y termina al cerrar RetroBat.
- `/botones`: muestra el número de cada botón del mando.

Registro de lo que hace: `%TEMP%\TecnoticsArcade-registro.txt`.

## Si algo falla al arrancar

- **Ctrl + Alt + Supr → Administrador de tareas → Archivo → Ejecutar nueva tarea → `explorer.exe`** abre el escritorio.
- En el Configurador, **Desactivar Modo Arcade** lo deja todo como antes.
