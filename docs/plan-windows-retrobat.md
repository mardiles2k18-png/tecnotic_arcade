# Plan: Tecnotics Arcade con Windows 10 LTSC + RetroBat

Objetivo: al encender, el arcade entra directamente en RetroBat, sin logos, escritorio ni rastros de Windows, y se maneja solo con las palancas y los botones.

Placa de referencia: HP ProOne 400 G2 (i5 6.ª gen, Intel HD 530, 16 GB RAM).

## Fase 1: Windows mínimo (con internet, por última vez)

- [ ] Instalar Windows 10 Enterprise LTSC.
- [ ] **Activar Windows antes de desconectar internet.**
- [ ] Drivers de HP para la ProOne 400 G2: chipset, gráfica Intel HD 530, audio y red. Descargarlos del soporte de HP.
- [ ] Runtimes que piden los juegos (instaladores offline, guardarlos en un USB para otras máquinas):
  - Visual C++ Redistributable 2005–2022 (x86 y x64).
  - DirectX End-User Runtime (junio 2010).
  - .NET Framework 3.5 y 4.8.
- [ ] Si se usan juegos de la tienda de Microsoft (por ejemplo DBFZ): comprobar **sin internet** que siguen arrancando. Estos juegos validan la licencia en línea y pueden dejar de funcionar sin conexión.
- [ ] Desactivar Windows Defender (directivas de grupo), Windows Update, notificaciones, Xbox Game Bar e informes de errores.
- [ ] Energía: rendimiento alto, nunca suspender, nunca apagar la pantalla, sin protector de pantalla.
- [ ] Desactivar los atajos de accesibilidad (teclas especiales con Shift ×5, teclas filtro), porque los botones del arcade pueden activarlos.
- [ ] BIOS (F10): After Power Loss → Power On.

## Fase 2: probar los juegos de Windows

- [ ] Copiar y probar cada juego en Windows tal cual.
- [ ] Anotar en `README.md` el ejecutable de cada juego y si necesita algo especial.

## Fase 3: RetroBat

- [ ] Instalar RetroBat.
- [ ] Añadir los juegos de Windows a RetroBat (sistema "windows": accesos directos o `.lnk`/`.bat` en `roms\windows`).
- [ ] Vídeo de intro Tecnotics: `arranque/splash/tecnotics-arcade.mp4`, configurado en `retrobat.ini`.
- [ ] Tema Tecnotics: copiar `themes/es-theme-tecnotics` a la carpeta de temas de RetroBat y comprobar que se ve bien.
- [ ] Con el espacio que quede: emuladores (MAME, SNES, etc.).

## Fase 4: controles

- [ ] Placa de botones en modo XInput (se reconoce como mando de Xbox).
- [ ] Configurar los controles en RetroBat.
- [ ] Juegos que solo aceptan teclado: usar el mapeo de mando a teclado de RetroBat.
- [ ] Combinación para salir de cualquier juego (Hotkey + Start).

## Fase 5: modo quiosco (eliminar rastros de Windows)

- [ ] Usuario "arcade" con inicio de sesión automático.
- [ ] Usuario administrador aparte, con escritorio normal, para mantenimiento.
- [ ] Unbranded Boot: sin logo ni animación de Windows.
- [ ] Custom Logon: sin pantalla de bienvenida ni de apagado.
- [ ] Shell Launcher: el usuario "arcade" arranca RetroBat en lugar del escritorio, y se reinicia si se cierra.
- [ ] Ocultar el cursor del ratón.

## Fase 6: copia maestra

- [ ] Hacer una imagen completa del disco (Clonezilla o Macrium Reflect).
- [ ] Usarla para preparar las demás máquinas con la misma placa.
