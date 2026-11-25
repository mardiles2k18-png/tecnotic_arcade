# Estado del ecosistema Tecnotics Arcade

Documento actualizado el **25 de noviembre de 2026**.

## Objetivo confirmado por Mauricio

Construir un **ecosistema de herramientas que permita crear un sistema arcade bajo Windows**. Cada herramienta debe aportar a preparar, configurar, personalizar, operar, mantener, recuperar o reproducir ese sistema.

La experiencia final buscada es encender el arcade, ver Tecnotics, elegir juegos con palancas y botones y disponer de acceso a Windows para mantenimiento. El tema, el gestor y el configurador se complementan; ninguno equivale por sí solo al sistema completo.

## Versiones y estado de validación

- **Gestor de RetroBat**. La última publicación es la Vista previa 32 para Windows x64. GitHub Actions verificó las pruebas, la compilación y el arranque del ejecutable. Mauricio confirmó el 24 de noviembre la Vista previa 28: detecta el firmware en el RPCS3 de TeknoParrot y **Dragon Ball Zenkai Battle Royale abre** con «Probar desde RetroBat». La V32 añade el selector de movimiento en TeknoParrot a partir de la prueba de Mauricio con Street Fighter. Falta probar la selección de personaje y el combate en su PC. [Vista previa 32](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-32-9f46c57) · [Documento de continuidad del gestor](https://github.com/mardiles2k18-png/tecnotic_arcade/blob/codex/retrobat-manager/docs/gestor-retrobat-reorganizacion.md)
- **Lanzador Tecnotics 1.2.0**. Incluye el configurador de arranque y la bienvenida con modo arcade. Mauricio confirmó esta versión el 21 de noviembre.

Cada herramienta mantiene su propia numeración. Queda pendiente la prueba de arranque, mantenimiento y reversión del lanzador en la edición de Windows instalada en el arcade.

## Decisiones vigentes y límites de lo confirmado

- Plataforma objetivo: Windows.
- Componente de menú que se personaliza actualmente: RetroBat/EmulationStation.
- Identidad común: Tecnotics, con logos, intro, bienvenida y tema.
- El configurador actual documenta una sola cuenta de Windows con inicio automático, bienvenida como shell del usuario y PIN para abrir el escritorio. Los planes antiguos de dos cuentas o Shell Launcher no describen esa implementación.
- La edición final de Windows no está cerrada: hay un plan de Windows 10 LTSC para la placa HP y antecedentes de alternativas Windows 10/11 IoT LTSC. Confirmar hardware, edición y licencia antes de instalar.
- El prototipo portátil de Pegasus y el trabajo previo con Batocera son antecedentes separados. No aplicarlos como arquitectura principal sin una nueva instrucción de Mauricio.
- El desarrollo portátil en otros PCs no autoriza modificar su registro, shell o arranque. Las funciones de instalación del modo arcade son para un equipo dedicado y requieren respaldo/reversión.
- La integración total y las pruebas entre herramientas siguen pendientes.

## Inventario y finalidad de las herramientas

| Herramienta | Función en el ecosistema | Ubicación | Estado y evidencia |
|---|---|---|---|
| Gestor de RetroBat · Vista previa 32 | Pestañas Inicio, Biblioteca, Cargar sistemas, BIOS, Emuladores, Firmware, Mandos y Configurar RetroBat. Importa juegos de Windows, ROMs y TeknoParrot eligiendo cuáles traspasar, bloquea la carga si faltan el emulador o el firmware, muestra el estado de cada juego, gestiona duplicados y respaldos y configura emuladores, BIOS, firmware, mandos con adaptación automática por juego de TeknoParrot, temas, intro, música y `retrobat.ini` | `codex/retrobat-manager`, en `retrobat/gestor-retrobat.pyw` y módulos `gestor_*.py`. Continuidad: `docs/gestor-retrobat-reorganizacion.md` en esa rama | Publicado con pruebas unitarias y prueba automática de apertura en Windows. Interfaz probada con instalaciones simuladas. Vista previa 28 validada por Mauricio con Dragon Ball. [Publicación y SHA-256](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-32-9f46c57) |
| Lanzador Tecnotics 1.2.0 — configurador | Revisar el equipo, instalar/desactivar modo arcade, configurar PIN y arranque y aplicar/restaurar ajustes de Windows | claude/sweet-noether-plai9b: configurador/ y dist/TecnoticsArcadeConfigurador.exe | Versión 1.2.0 confirmada por Mauricio, documentada y con ejecutable disponible. No ejecutado durante la revisión del repositorio |
| Lanzador Tecnotics 1.2.0 — bienvenida / modo arcade | Cuenta atrás, apertura de RetroBat, menú al salir y entrada protegida al escritorio | Misma rama: modo-arcade/ | Implementación y documentación disponibles. Validación completa en el equipo destino pendiente de registrar |
| Tema completo AluBrush | Interfaz de RetroBat con la identidad Tecnotics y los fondos/logos entregados de windows, mame y fbneo | main: themes/es-theme-tecnotics-alubrush/ | Conserva 2.438 archivos originales; 2.498 archivos en la adaptación. XML, rutas y conservación comprobados; prueba visual y de mando pendiente |
| Constructor, normalizador y validador del tema | Reconstrucción repetible y comprobación antes de distribuir | main: scripts/Construir-Tema-RetroBat.ps1, Normalizar-Rutas-Tema.ps1 y Validar-Tema-RetroBat.ps1 | Constructor probado desde cero y validación aprobada. No prueban el renderizado del motor |
| Logos, intro y generadores | Identidad visual común y recursos regenerables | main: logo/, arranque/splash/tecnotics-arcade.mp4, herramientas/ | Recursos generados presentes; los generadores usan Python/Pillow y, para vídeo, ffmpeg |
| Accesos de juegos Windows | Crear accesos directos en roms/windows | main: retrobat/crear-accesos-carpeta.ps1 y crear-accesos-lucha.ps1 | Código disponible con rutas específicas de una máquina. Revisar antes de ejecutar; el selector automático de ejecutables no sustituye probar cada juego |
| Temas básico y oficina | Presentaciones alternativas de EmulationStation | main: themes/es-theme-tecnotics/ y es-theme-oficina/ | Recursos y XML presentes. No confundir con el tema completo AluBrush |
| Graphify | Ayudar a los asistentes a consultar relaciones del código y continuar entre equipos | chore/graphify-multidevice y codex/retrobat-manager | Código/configuración y guía presentes en esas ramas. No se requiere para ejecutar juegos ni se instala automáticamente por leer GitHub |
| Configuración HP y Wine/Proton | Antecedentes de adaptación de la placa y ejecución de juegos en Batocera | main: sistema/ y arranque/instalar-logo-arranque.sh | Son scripts de Linux/Batocera, no instaladores Windows |

## Dónde está cada avance

- **main**: tema AluBrush completo, recursos de marca, herramientas del tema, accesos antiguos, temas anteriores y contexto central del proyecto.
- **codex/retrobat-manager**: gestor de biblioteca y compilación portable.
- **claude/sweet-noether-plai9b**: configurador, bienvenida, ejecutable y prototipo Pegasus. En la última revisión seguía siendo la rama predeterminada de GitHub.
- **chore/graphify-multidevice**: instalación/documentación de Graphify para varios entornos.

Esta actualización solo reúne **el contexto documental** en main. No integra el código de las otras ramas ni cambia la rama predeterminada. Al retomar, consultar sus cabezas y versiones: pueden avanzar después de esta revisión.

## Registro del 25 de noviembre de 2026

- **Vista previa 32.** En la V31 Mauricio pudo combatir con la cruceta y reportó problemas al elegir personaje en Ultra Street Fighter IV con su mando. Ahora **Mandos → TeknoParrot → Movimiento al adaptar** permite elegir la palanca izquierda, la cruceta o el mapa del juego. El cambio de movimiento conserva las asignaciones de ataque del jugador y permite comprobar las entradas en vivo. Se verificó el guardado de las cuatro direcciones e Inicio con el perfil de Ultra Street Fighter IV. Queda pendiente la prueba en el juego con el mando físico. [Portable](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-32-9f46c57) · [Pruebas en Windows](https://github.com/mardiles2k18-png/tecnotic_arcade/actions/runs/45540466454)

## Registro del 24 de noviembre de 2026

### Reorganización del Gestor de RetroBat (Vistas previas 28 a 31)

El trabajo lo comenzó Codex y lo continuó Claude. Todo el detalle está en el [documento de continuidad](https://github.com/mardiles2k18-png/tecnotic_arcade/blob/codex/retrobat-manager/docs/gestor-retrobat-reorganizacion.md): decisiones, inventario de cada función con su nuevo lugar, diseño, estado de avance y cómo retomar.

- **Vista previa 28.** Asistente «Preparar juego» en cuatro pasos (juego, emulador exacto, BIOS y firmware, probar). Para TeknoParrot lee el `EmulatorType` del perfil: Dragon Ball Zenkai usa el **RPCS3 de TeknoParrot** (`emulators/teknoparrot/RPCS3`), no el de RetroBat. Por eso el firmware instalado en el otro RPCS3 no le servía. La comprobación de `dev_flash` respeta `vfs.yml`. **Mauricio la validó:** firmware detectado y Dragon Ball abre con «Probar desde RetroBat». [Portable](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-28-e493918) · [Pruebas](https://github.com/mardiles2k18-png/tecnotic_arcade/actions/runs/45419353208)
- **Decisiones de Mauricio para la reorganización:**
  - Orden de pestañas: **Inicio · Biblioteca · Cargar sistemas · BIOS · Emuladores · Firmware · Mandos · Configurar RetroBat**.
  - Filtro por sistema en la biblioteca (tenía 1730 juegos en una sola lista).
  - «Cargar juegos» pasa a «Cargar sistemas» y bloquea la carga si faltan el emulador o el firmware.
  - TeknoParrot se reparte por función: instalación y pantalla de carga en Emuladores, importación en Cargar sistemas y mandos en Mandos.
  - Nueva pestaña Mandos.
  - Todo en una sola versión, sin perder lo validado.
- **Vista previa 29.** Implementa esa reorganización:
  - Biblioteca con lista desplegable por sistema y cantidad de juegos, buscador, nombre real de los juegos de TeknoParrot y panel con los pasos del juego o del sistema.
  - Cargar sistemas con «Preparación del sistema»: emulador, firmware (bloquea) y BIOS (solo avisa), con «Siguiente paso» para instalar en orden.
  - Sección TeknoParrot en Emuladores.
  - Pestaña Mandos:
    - Mandos detectados y prueba en vivo.
    - Orden de Jugador 1 y 2 con `INPUT P{n}NAME/GUID/PATH`.
    - Mapeo manual por sistema con `<sistema>.disableautocontrollers`.
    - Editor por juego de TeknoParrot.

    Estas claves se comprobaron en el código de RetroBat (`emulatorLauncher/Program.cs` y `InputManager.cpp` de EmulationStation).

  La prueba de un juego desde el editor de TeknoParrot usa ahora el lanzamiento con DLL aisladas de la V27. [Portable](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-29-259f70e) · [Pruebas](https://github.com/mardiles2k18-png/tecnotic_arcade/actions/runs/45435510220)
- **Vista previa 30.** Mauricio probó Cargar sistemas con `D:/Pc Games/REMAKE GAMES` y pidió dos cambios:
  1. **Ver todo lo que hay en la carpeta.** Las carpetas sin `.exe` aparecen ahora como «Sin ejecutable» con su motivo: imagen `.iso`, comprimido `.rar` o `.zip`, carpeta vacía o sin `.exe`.
  2. **Decidir qué juegos listos se traspasan.** Hay una columna «Traspasar» con casillas y los botones «Marcar listos», «Desmarcar» e «Importar marcados (N)», en todos los sistemas.

  [Portable](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-30-2f0e0d4) · [Pruebas](https://github.com/mardiles2k18-png/tecnotic_arcade/actions/runs/45449889298)
- **Vista previa 31.** Las dos vistas de mandos usan Controller Studio 0.1.1 y muestran el esquema Xbox completo para gamepads XInput con capacidades parciales. En el editor de TeknoParrot, «Adaptar juego a nuestro mando» propone los botones del juego y jugador elegidos y guarda el perfil con respaldo al confirmar. Se verificaron con mandos simulados las seis acciones principales de Street Fighter V 3.53, sus botones EX1 y EX2 y el crédito de Contra y Raiden III. [Portable](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-31-87e5651) · [Pruebas y arranque en Windows](https://github.com/mardiles2k18-png/tecnotic_arcade/actions/runs/45535669818)
- **Pendiente en el PC de Mauricio:**
  1. Comprobar que aparezcan las seis carpetas en Cargar sistemas con Windows.
  2. Recorrer Biblioteca, Cargar sistemas (PS3 y TeknoParrot), Emuladores y Mandos con los mandos reales del arcade. La detección y la prueba en vivo solo se pueden comprobar en Windows.
  3. Probar el mapeo de Street Fighter V 3.53 con el mando real desde RetroBat.
  4. Confirmar el orden de jugadores con las placas reales. Con dos placas idénticas se usa CONTROLLERS PRIORITY de RetroBat.

- **Vista previa 27.** La pestaña Firmware inicia los emuladores con la búsqueda de bibliotecas de Windows y restaura las rutas del portable después de iniciarlos. Se corrigió el error de `vcruntime140.dll` al iniciar RPCS3 desde la carpeta temporal del portable. GitHub Actions verificó la instalación real de PS3UPDAT.PUP con el RPCS3 distribuido por RetroBat desde el ejecutable empaquetado. [Portable y SHA-256](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-27-befa24b) · [Pruebas](https://github.com/mardiles2k18-png/tecnotic_arcade/actions/runs/45412479576)
- **Vista previa 26.** Firmware permite elegir un archivo individual y guardar un PUP verificado aunque falte el emulador. El estado «Paquete guardado» indica que la instalación aún está pendiente. Windows verificó la importación de un PUP oficial y su instalación posterior con el RPCS3 de TeknoParrot. [Portable y SHA-256](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-26-27b0abc) · [Pruebas](https://github.com/mardiles2k18-png/tecnotic_arcade/actions/runs/45410750613)
- **Vista previa 25.** La pestaña Emuladores lee la compatibilidad de la instalación local, descarga los paquetes de RetroBat, Libretro y los proyectos compatibles, y permite elegir el emulador que usará cada sistema. Admite copias locales de los programas que requieren licencia o una descarga manual. [Portable y SHA-256](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-25-ad701e1)
- En Windows se comprobaron la instalación real de Snes9x y RetroArch, el núcleo **fceumm**, la selección por sistema y el arranque del portable. [Pruebas](https://github.com/mardiles2k18-png/tecnotic_arcade/actions/runs/45408759492)
- **Vista previa 24.** La pestaña Firmware consulta el catálogo de RetroBat, verifica las descargas publicadas e importa copias locales. Instala el software de Sony en RPCS3 y Vita3K y reconoce por separado la copia de RPCS3 que abre Dragon Ball Zenkai Battle Royale desde TeknoParrot. Ryujinx utiliza su instalador interno para los archivos extraídos de Switch. [Portable y SHA-256](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-24-be10485)
- En Windows se probaron la instalación real del firmware de PS3 con el RPCS3 oficial de TeknoParrot, la instalación del software y fuentes en Vita3K y el arranque del portable. [Pruebas de GitHub Actions](https://github.com/mardiles2k18-png/tecnotic_arcade/actions/runs/45405351203)
- **Vista previa 23.** El editor de TeknoParrot incorpora la vista reutilizable de TECNOTICS Controller Studio 0.1.0. El dibujo cambia de tamaño con la ventana. Verde indica una entrada activa y cian la selección. El editor conserva la asignación por juego y jugador, los perfiles XML y los respaldos de mandos. [Publicación](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-23-1fc39ee)
- Se verificó la demo independiente, el escalado a 875×570 y 1060×660, y la integración con la lectura simulada de XInput y DirectInput. Las pruebas también comprobaron la captura por jugador, la recuperación visual después de una desconexión y la copia íntegra de los XML de respaldo. GitHub Actions verificó la compilación y la respuesta de la vista en el portable Windows x64. Queda pendiente la prueba con el mando físico del arcade. [Pruebas en Windows y compilación](https://github.com/mardiles2k18-png/tecnotic_arcade/actions/runs/45393737329)

## Registro del 23 de noviembre de 2026

| Vista previa | Cambios del gestor | Publicación |
|---|---|---|
| 12 | Reorganización en cinco pestañas. Inicio pasó a mostrar la instalación, ruta y versión de RetroBat. Se añadieron el retiro de un sistema con respaldo, el retiro de temas y la importación de música. | [230a6f6](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-12-230a6f6) |
| 13 | Pestaña TeknoParrot con catálogo de perfiles, detección de duplicados e importación de carpetas con sus archivos de arranque. | [70e885d](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-13-70e885d) |
| 14 | **Instalar y configurar TeknoParrot** descarga y verifica los componentes oficiales, prepara el sistema y respalda la instalación previa. | [5ca0b83](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-14-5ca0b83) |
| 15 | Las descargas usan el almacén de certificados de Windows para corregir el error HTTPS `CERTIFICATE_VERIFY_FAILED`. | [7c928e5](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-15-7c928e5) |
| 16 | Lectura e importación de ZIP, 7z y RAR con 7-Zip incluido en el portable. La extracción conserva los archivos de origen. | [2781706](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-16-2781706) |
| 17 | **TeknoParrot → Pantalla de carga…** permite ocultar EmulationStation al lanzar un juego, con respaldo y reversión. El ajuste `HideWindow` se aplica a todos los sistemas. | [389a627](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-17-389a627) |
| 18 | **Biblioteca → Respaldos…** muestra contenido, fecha y tamaño. Permite eliminar copias seleccionadas o vaciar la lista con confirmación. | [6619b0b](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-18-6619b0b) |
| 19 | TeknoParrot consulta el catálogo de RetroBat para detectar ejecutables como `game.exe` de Battle Fantasia. Conserva la selección manual, permite seleccionar archivos sin extensión e indica cuál falta cuando un perfil pide dos. | [f1210a9](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-19-f1210a9) |
| 20 | Consulta la guía oficial por perfil y el lanzador de RetroBat cuando falta un archivo de arranque. Reconoce `game.exe` de BlazBlue Central Fiction (`BBCF`) y comprueba la cabecera del archivo `game` sin extensión. El diagnóstico muestra candidatos, archivos ausentes y fuentes. | [5582b1c](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-20-5582b1c) |
| 21 | **TeknoParrot → Configurar mandos…** detecta dispositivos XInput y DirectInput. Aplica el mapa a los juegos instalados, permite elegir el mando del jugador 1 y respalda los ajustes que cambian. | [1deaea5](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-21-1deaea5) |
| 22 | Editor de mandos por juego con lectura en vivo, reasignación por pulsación, guardado individual y prueba desde el lanzador. Raiden III deja Test y Servicio libres en la plantilla. Contra conserva Service / Coin para la ficha. | [87d4469](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-22-87d4469) |

### Pruebas y hallazgos de la jornada

- GitHub Actions compiló y verificó el arranque en Windows x64 de las once vistas previas. Se probó el borrado selectivo y el vaciado con una biblioteca de prueba, comprobando que el juego activo seguía intacto. También se probó la importación con el perfil oficial de Battle Fantasia y archivos de prueba, incluyendo un caso con dos archivos de arranque y un ZIP con un ejecutable sin extensión. [Compilación de la Vista previa 18](https://github.com/mardiles2k18-png/tecnotic_arcade/actions/runs/45239019560) · [Compilación de la Vista previa 19](https://github.com/mardiles2k18-png/tecnotic_arcade/actions/runs/45240353230)
- Se verificaron la consulta oficial y el diagnóstico del perfil `BBCF` con archivos de prueba en carpeta, ZIP y 7z. Queda pendiente comprobar el arranque del juego real desde RetroBat en el arcade. [Ficha oficial de BlazBlue Central Fiction](https://teknoparrot.com/en/Compatibility/GameDetail/BBCF) · [Compilación de la Vista previa 20](https://github.com/mardiles2k18-png/tecnotic_arcade/actions/runs/45248706427)
- Se probó el mapeo para uno y dos jugadores, la conservación de ajustes de juego y la reversión ante un cambio de archivo durante el guardado. Queda pendiente probar mandos físicos y el arranque de los juegos con los controles configurados en el arcade. [Compilación de la Vista previa 21](https://github.com/mardiles2k18-png/tecnotic_arcade/actions/runs/45310171191)
- Mauricio reportó que **Raiden III** entraba a un menú en japonés al mover la nave y que **Contra: Evolution** no respondía. Se verificaron los perfiles oficiales, la asignación de ficha, la captura simulada y el guardado de un solo juego. Queda pendiente confirmar la respuesta de ambos títulos con el mando físico. [Compilación de la Vista previa 22](https://github.com/mardiles2k18-png/tecnotic_arcade/actions/runs/45315010475)
- Se registró en el README del gestor la colección comunitaria de TeknoParrot. Se localizó **Dragon Ball Zenkai Battle Royale 3.26.01** y se identificó el flujo de RetroBat para Namco 357/369 en `roms/namco3xx` con carpeta `.game`. Su importación y arranque en el arcade siguen pendientes. [Registro de la colección](https://github.com/mardiles2k18-png/tecnotic_arcade/commit/ad1dbc8) · [Namco 357/369 en RetroBat](https://wiki.retrobat.org/systems-and-emulators/supported-game-systems/arcade/namco3xx)
- El aviso de **TeknoCPS** reportó una licencia de tester ausente y señaló **ElfLoader** para activarla. Quedó pendiente confirmar el título y el perfil afectados, y verificar el arranque con su licencia y los archivos requeridos.
- Mauricio confirmó una importación de TeknoParrot y reportó que **Raiden III** arrancaba detrás de EmulationStation. Falta comprobar si con el nuevo ajuste el juego toma el foco sin teclado ni ratón. También queda pendiente probar la importación y el arranque de **Battle Fantasia** en el arcade.

## Evidencias de la revisión inicial

- [Gestor Preview 11 publicado](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-11-bb7d550), correspondiente al commit bb7d550b873ce359c6f7fd091ad79b6fa0508e09.
- [Compilación y prueba automática de apertura del gestor](https://github.com/mardiles2k18-png/tecnotic_arcade/actions/runs/44862826798): resultado success. La prueba crea la ventana, la actualiza y la cierra; no recorre todas las funciones.
- [Registro de cambios del configurador](https://github.com/mardiles2k18-png/tecnotic_arcade/blob/claude/sweet-noether-plai9b/CHANGELOG.md): versión 1.2.0.
- Tema completo publicado inicialmente en main mediante el commit 056e0506e2cd25533f13c3f23d91a76120e91795. Informe: themes/es-theme-tecnotics-alubrush/VALIDACION.json.
- El README anterior registra juegos probados en Batocera: Creed Champions, Hunter x Hunter, Blade Strangers y KOF XIII. Son antecedentes de esa plataforma, no pruebas de esos juegos en Windows. KOF XIII conserva un problema documentado con los vídeos en Batocera.

## Equipos y emuladores: contexto conocido

- PC principal indicado por Mauricio: Ryzen 7 3700X, 16 GB RAM, RTX 5060 Ti y Windows 11 Pro. Es contexto aportado previamente, no una nueva inspección del hardware.
- Placa de referencia del plan y las pruebas antiguas de Batocera: HP ProOne 400 G2, i5 de sexta generación, Intel HD 530 y 16 GB RAM. Confirmar la máquina real antes de aplicar ajustes específicos.
- El prototipo anterior contemplaba PCSX2, RPCS3, Xenia, Citron/Yuzu y ShadPS4. La presencia de recursos en el tema no prueba instalación, configuración ni rendimiento de esos emuladores.
- Los otros equipos, el disco externo y las rutas/versiones actualmente instaladas deben confirmarse. No tratar la mención histórica de RetroBat 7.5.3 como detección de la versión instalada.

## Próximos resultados necesarios

1. Reunir las herramientas vigentes en una entrega o integración revisada, preservando las funciones y los cambios de cada rama. Documentar versiones y procedencia.
2. Confirmar el equipo Windows de pruebas, la edición instalada, RetroBat, los emuladores y las rutas reales.
3. Validar el flujo completo: preparar equipo -> importar biblioteca -> aplicar tema e intro -> configurar controles -> abrir/cerrar juegos -> volver al menú -> mantenimiento con PIN -> desactivar/restaurar.
4. Comprobar visualmente el tema completo y todas sus variantes relevantes en RetroBat.
5. Probar cada juego/emulador por separado y registrar equipo, versión, controles, salida y resultado.
6. Revisar portabilidad y rutas para que las herramientas se puedan utilizar en otros PCs sin aplicarles cambios de instalación no solicitados.
7. Preparar respaldo y recuperación de una instalación funcional y, después de probarla, una copia maestra para repetir el sistema en equipos compatibles.

Este listado expresa pendientes, no autorizaciones automáticas para cambiar Windows, fusionar ramas o instalar herramientas.

## Cómo continuar sin perder el contexto

La IA debe empezar leyendo AGENTS.md, README.md y este archivo en main; comprobar después las ramas y los archivos pertinentes. Para el Gestor de RetroBat, leer además `docs/gestor-retrobat-reorganizacion.md` en la rama `codex/retrobat-manager` ([enlace](https://github.com/mardiles2k18-png/tecnotic_arcade/blob/codex/retrobat-manager/docs/gestor-retrobat-reorganizacion.md)) y actualizar su sección «Estado de avance». Al terminar una tarea autorizada, actualizar decisiones, estado, evidencia y próximos pasos cuando hayan cambiado. No presentar como probado lo que solo está implementado o compilado.

## Antecedentes

docs/plan-windows-retrobat.md conserva el plan inicial. Sus casillas no representan automáticamente el estado actual y algunas decisiones de arranque difieren del configurador posterior. Las secciones de Batocera del README son históricas. El AGENTS.md anterior del checkout local describía Pegasus como arquitectura principal; esa indicación queda sustituida por el objetivo Windows confirmado por Mauricio y por este estado documentado.

Prototipo personal/familiar; no se incluyen juegos ni BIOS en el repositorio.
