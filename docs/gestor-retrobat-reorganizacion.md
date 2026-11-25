# Gestor de RetroBat · Reorganización de la Vista previa 29

Documento de continuidad del Gestor de RetroBat. Sirve para que Claude o Codex puedan retomar el trabajo sin perder contexto.
Creado el **24 de noviembre de 2026**. Rama de trabajo: `codex/retrobat-manager`.

> **Cómo usar este documento:** leerlo completo antes de tocar el gestor. Al terminar una parte, actualizar
> la sección [Estado de avance](#estado-de-avance), con fecha y evidencia (commit, ejecución de GitHub Actions o prueba
> de Mauricio). No marcar nada como probado si solo está implementado o compilado.

## 1. Punto de partida

- **Vista previa 28** (commit `e493918`, publicación
  [retrobat-manager-preview-28-e493918](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-28-e493918)).
  Añadió la pestaña «Preparar juego», que guía en cuatro pasos (juego, emulador, BIOS y firmware, probar).
- **Validado por Mauricio el 24-11-2026:**
  - La Vista previa 28 detecta el firmware de PS3 en el RPCS3 de TeknoParrot (`emulators/teknoparrot/RPCS3/dev_flash`).
  - **Dragon Ball Zenkai Battle Royale abre** con «Probar desde RetroBat».
  - La biblioteca leyó 1730 juegos.
- Problema detectado: con 1730 juegos, una sola lista es inmanejable. Hace falta filtrar por sistema.

## 2. Decisiones de Mauricio (24-11-2026)

1. **Filtro por sistema** (lista desplegable) para revisar los juegos de un sistema a la vez.
2. **Nuevo orden de pestañas:**
   **Inicio · Biblioteca · Cargar sistemas · BIOS · Emuladores · Firmware · Mandos · Configurar RetroBat**.
3. «Cargar juegos» pasa a llamarse **«Cargar sistemas»**. Primero se elige un sistema de la lista de RetroBat y
   después el origen: una carpeta con varios juegos o un juego en particular.
4. **Verificación previa a la carga.** Si el sistema necesita un emulador o firmware que falta, el gestor
   **no deja cargar juegos** y lo explica. Primero se instala el emulador y después el firmware. Si el sistema
   ya está instalado y configurado, deja cargar.
5. **TeknoParrot se reparte por función** (propuesta aceptada):

   | Función actual de la pestaña TeknoParrot | Nuevo lugar |
   |---|---|
   | Instalar y configurar TeknoParrot (componentes y RPCS3) | **Emuladores** |
   | Pantalla de carga… | **Emuladores** (sección TeknoParrot) |
   | Importar juegos (varias carpetas, una carpeta o un archivo comprimido; perfil, ejecutable principal, segundo archivo, quitar del lote, diagnóstico) | **Cargar sistemas**, cuando el sistema elegido es TeknoParrot |
   | Configurar mandos… (editor por juego) | **Mandos** |

6. **Pestaña nueva «Mandos»:**
   - Configuración global de RetroBat.
   - Excepciones de los emuladores que no son compatibles con ella: TeknoParrot y quizá PS2 o PS3.
   - Mandos conectados con prueba en vivo.
   - Jugador 1 y Jugador 2 fijos.
7. **«Preparar juego»** se integra en **Biblioteca** como panel de detalle: eliges un juego y ves sus cuatro pasos.
   Desaparece como pestaña propia. El botón de Inicio lleva a Biblioteca.
8. **Todo se entrega junto en la Vista previa 29**, sin etapas intermedias.
9. **No perder nada de lo validado.** Cada botón actual tiene un destino en el inventario de la sección 3.

### Decisiones posteriores (24-11-2026, prueba de la Vista previa 29)

Mauricio probó Cargar sistemas con Windows (`D:/Pc Games/REMAKE GAMES`) y pidió:

1. **Ver todo lo que hay en la carpeta de origen.** Las carpetas sin `.exe` (imágenes `.iso`, comprimidos `.rar` o
   `.zip`, carpetas vacías o sin ejecutable) no aparecían. Desde la **Vista previa 30** se muestran como
   «Sin ejecutable · motivo» (`gestor_core.sin_ejecutable_windows`). Al seleccionarlas, la barra de estado explica
   qué hacer.
2. **Decidir qué juegos listos se traspasan.** Antes, Windows importaba todos los listos. Desde la V30 la tabla tiene
   la columna **«Traspasar»** con casillas (clic o barra espaciadora) y los botones «Marcar listos», «Desmarcar» e
   «Importar marcados (N)». Vale para todos los sistemas. Al elegir el ejecutable de una fila, esa fila queda
   marcada. La confirmación lista los juegos marcados.

## 3. Inventario: cada función actual y su destino en la Vista previa 29

Regla: **mover sin reescribir**. Las clases y funciones validadas se reutilizan tal cual. Solo cambia dónde aparecen.

| Pestaña actual (V28) | Función o botón | Código | Destino (V29) |
|---|---|---|---|
| Inicio | Instalación (Elegir carpeta), estado, ruta predeterminada y versión | `Gestor.__init__`, `comprobar_sistema`, `verificar_version` | Inicio (sin cambios) |
| Inicio | Volver a comprobar · Versiones de RetroBat | ídem | Inicio (sin cambios) |
| Inicio | Preparar un juego… | `Gestor.preparar_juego` | Inicio: ahora abre **Biblioteca** |
| Preparar juego | Lista de juegos, buscador, 4 pasos, requisitos, Siguiente paso, Instalar requisitos, Importar archivo…, Probar desde RetroBat | `gestor_preparar.py`, `gestor_preparar_ui.py` | **Biblioteca**, panel «Estado del juego» |
| Preparar juego | Importar un juego nuevo… | `PanelPreparar.importar_nuevo` | Lleva a **Cargar sistemas** con el sistema del juego ya elegido |
| Cargar juegos | Origen (Elegir carpeta) con detección de carpeta externa y oferta de importar | `detectar_origen`, `revision_automatica` | **Cargar sistemas** (se conserva) |
| Cargar juegos | Sistema, Categoría, Nueva categoría…, Verificar juegos | `cargar_categorias`, `crear_categoria`, `previsualizar` | Cargar sistemas. El sistema pasa a la primera fila |
| Cargar juegos | Tabla, Ejecutable de la fila, Comparar copias… (Verificar contenido, Conservar, Reemplazar…) | `mostrar_candidatos`, `elegir_ejecutable`, `comparar_seleccion` | Cargar sistemas (sin cambios) |
| Cargar juegos | Importar nuevos o seleccionados y, al terminar, ofrecer revisar BIOS | `importar`, `ofrecer_bios` | Cargar sistemas, con la verificación previa |
| BIOS | Actualizar sistemas, Verificar manifiesto MD5…, tabla de estado | `iniciar_panel_biblioteca(solo_bios=True)`, `verificar_manifiesto` | **BIOS** (sin cambios) |
| BIOS | Verificar / buscar BIOS…, ventana con Buscar en Internet, Abrir fuente, Agregar BIOS desde carpeta… e Instalar firmware… (PS3) | `preparar_bios`, `mostrar_bios` | BIOS (sin cambios) |
| Firmware | Sistema, Comprobar firmware, Instalar seleccionados o disponibles…, Importar archivo o carpeta…, Abrir Ryujinx, Ver guía | `gestor_firmware_ui.PanelFirmware` | **Firmware** (sin cambios) |
| Emuladores | Sistema, Buscar, Actualizar lista, Instalar seleccionados…, Importar copia… (archivo o carpeta), Usar para un sistema…, Ver fuente | `gestor_emuladores_ui.PanelEmuladores` | **Emuladores** (sin cambios) |
| Emuladores | — | — | **Nuevo:** sección TeknoParrot con estado, Instalar y configurar TeknoParrot y Pantalla de carga… |
| Biblioteca | Árbol sistema, categoría y juego | `ver_biblioteca`, `mostrar_biblioteca` | **Biblioteca** con filtro por sistema y buscador |
| Biblioteca | Eliminar sistema…, Editar nombre…, Eliminar juego… | closures de `mostrar_biblioteca` | Biblioteca (misma lógica, en funciones con nombre) |
| Biblioteca | Verificar y gestionar duplicados… · Respaldos… | `ver_duplicados`, `gestionar_duplicados`, `ver_respaldos` | Biblioteca (sin cambios) |
| Configurar RetroBat | Temas (Importar, Crear, Editar, Eliminar), Instalar intro…, Importar música…, Editar retrobat.ini… | `importar_tema`, `tema`, `editar_tema`, `eliminar_tema`, `intro`, `importar_musica`, `configurar` | **Configurar RetroBat** (sin cambios) |
| TeknoParrot | Estado (perfiles, juegos registrados, mapa de controles) | `PanelTeknoParrot.actualizar` | Cargar sistemas (lote) y Emuladores (instalación) |
| TeknoParrot | Instalar y configurar TeknoParrot | `PanelTeknoParrot.instalar` → `preparar_instalacion` | **Emuladores** |
| TeknoParrot | Pantalla de carga… | `configurar_pantalla` (`gestor_teknoparrot_pantalla`) | **Emuladores** |
| TeknoParrot | Configurar mandos… | `EditorMandos` (`gestor_teknoparrot_editor_ui.py`) | **Mandos**: «Editor de mandos por juego de TeknoParrot…» |
| TeknoParrot | Elegir carpeta con varios juegos…, Carpeta de un juego…, Elegir archivo comprimido…, Importar seleccionados, tabla, Perfil de la fila, Ejecutable principal…, Segundo archivo…, Quitar del lote, Diagnóstico… (y doble clic) | `PanelTeknoParrot` | **Cargar sistemas**, cuando el sistema es TeknoParrot |

Comprobaciones automáticas que deben seguir funcionando (`--verificar` en GitHub Actions):

- 7-Zip con zip, 7z y rar.
- TLS con comprobación del nombre del servidor.
- XInput y DirectInput.
- Apertura de la ventana con las pestañas esperadas.
- Catálogos de firmware y de emuladores.
- Controller Studio: resalta el botón y registra el clic.
- Instalación real de PS3UPDAT.PUP cuando se pide.

## 4. Diseño de la Vista previa 29

### 4.1 Biblioteca (reemplaza «Biblioteca» y «Preparar juego»)

- Barra superior:
  - **Sistema**: lista desplegable con «Todos los sistemas» y cada sistema con juegos, con la cantidad («TeknoParrot (13)»).
  - **Buscar**: filtra dentro del sistema elegido.
  - Botones Actualizar, Verificar y gestionar duplicados… y Respaldos….
- Izquierda: árbol **categoría / juego** del sistema elegido. Con «Todos los sistemas» muestra sistema / categoría / juego,
  como la V28. La columna «Juegos» se conserva.
- Derecha, panel **«Estado del juego»**:
  - Los cuatro pasos de `gestor_preparar.preparar_plan`.
  - Tabla de requisitos.
  - Botones Siguiente paso, Probar desde RetroBat, Instalar requisitos e Importar archivo….
  - Al elegir un sistema (no un juego), muestra el resumen del sistema con `revisar_sistema` (sección 4.2).
- Debajo del árbol: Editar nombre…, Eliminar juego… y Eliminar sistema…, con la misma lógica de la V28.
- **TeknoParrot:** se muestra el nombre del perfil (`GameName` del XML de usuario o de GameProfiles) en vez del
  nombre de carpeta («Dragon Ball Zenkai Battle Royale» en lugar de «dbzenkai»).
- La lectura de la biblioteca usa `gestor_preparar.juegos_instalados`, que lee los nombres de `gamelist.xml`.

### 4.2 Cargar sistemas

1. **Sistema**: todos los sistemas declarados en `es_systems.cfg` (`self.sistemas`), en la primera fila.
2. **Caja «Preparación del sistema»**, calculada con `gestor_preparar.revisar_sistema(raiz, sistemas, clave)`:
   - **Emulador**: el elegido para el sistema (ajuste del sistema o predeterminado de RetroBat), y si está instalado.
     Botón **Instalar emulador** (`instalar_emulador`); en TeknoParrot, `preparar_instalacion`.
   - **Firmware**: requisitos obligatorios de `requisitos_firmware` para ese sistema y ese emulador.
     Botón **Instalar firmware** (`aplicar_firmware` con las filas automáticas) e **Importar archivo…**.
   - **BIOS**: conteo local de `rutas_bios_sistema`, igual que la tabla de la pestaña BIOS. Botón **Revisar BIOS…**
     (`preparar_bios`). **Avisa, no bloquea**, porque varios núcleos funcionan sin BIOS.
   - Resultado:
     - ✔ **Listo para cargar juegos**.
     - ⛔ **Falta el emulador o el firmware**. El mensaje pide instalar primero el emulador y después el firmware.
     - ⚠ **Emulador desconocido para el gestor**. Avisa y no bloquea; por ejemplo, el sistema `windows`
       no necesita emulador.
3. **Origen de los juegos:**
   - Sistemas normales: los controles actuales de Cargar juegos (origen, categoría, Verificar juegos, tabla,
     ejecutable, comparar e importar).
   - **TeknoParrot**: en ese espacio aparece el lote de importación de `PanelTeknoParrot` (sin la fila de instalación).
4. **Bloqueo:** cuando el resultado es ⛔:
   - Se desactivan Verificar juegos, Importar y los botones de lote de TeknoParrot.
   - `importar()` y `previsualizar()` vuelven a comprobar el estado y muestran el mensaje.
   - La detección automática de una carpeta externa también respeta el bloqueo.

### 4.3 Emuladores

Sección nueva **«TeknoParrot»**, encima de la tabla:

- Estado: componentes instalados y RPCS3 de TeknoParrot.
- Botón **Instalar y configurar TeknoParrot** (`PanelTeknoParrot.instalar`).
- Botón **Pantalla de carga…** (`PanelTeknoParrot.configurar_pantalla`).

El resto de la pestaña no cambia.

### 4.4 Mandos (nueva)

Hechos comprobados en el código fuente de RetroBat (24-11-2026):

- `emulatorLauncher` (RetroBat-Official/emulatorlauncher, `emulatorLauncher/Program.cs`, líneas 568–572) carga
  `es_settings.cfg` y aplica en orden:
  1. `global.<opción>`
  2. `<sistema>.<opción>`
  3. `<sistema>["<archivo del juego>"].<opción>`
- La opción **`disableautocontrollers` = `1`** hace que cada generador omita la configuración automática de mandos.
  Lo verifican, entre otros, `Rpcs3.Controllers.cs`, `Pcsx2.Controllers.cs`, `TeknoParrot.Controllers.cs`,
  `Fbneo.Controllers.cs` y `Mupen64.Controllers.cs`.
- **TeknoParrot también se autoconfigura** desde RetroBat (`TeknoParrot.Controllers.cs`). Por eso el editor por juego
  del gestor guarda `teknoparrot["<juego>"].disableautocontrollers = 1` («Conservar este mapeo al iniciar desde
  RetroBat»).
- **Orden de jugadores.** EmulationStation (batocera-emulationstation, `es-core/src/InputManager.cpp`) asigna los
  jugadores con estos ajustes de `es_settings.cfg`:
  1. `INPUT P{n}PATH`, máxima prioridad.
  2. `INPUT P{n}NAME` + `INPUT P{n}GUID`.
  3. Solo `INPUT P{n}NAME`.
  4. Los mandos libres restantes.

  El menú de RetroBat **CONTROLLER SETTINGS → CONTROLLERS PRIORITY** escribe esos valores. Dos placas idénticas,
  con el mismo nombre y GUID, solo se distinguen por `PATH`. En ese caso hay que usar el menú de RetroBat.
- La asignación de botones de cada mando la guarda RetroBat en
  `emulationstation/.emulationstation/es_input.cfg` (`inputConfig type="joystick"` con `deviceName` y
  `deviceGUID`). El gestor **no modifica** ese archivo; solo lo lee.

Diseño de la pestaña:

1. **Mandos conectados**
   - Lista detectada con `gestor_mandos_windows.detectar_mandos` (XInput y DirectInput). Por cada mando indica si
     RetroBat ya lo tiene configurado en `es_input.cfg`.
   - **Prueba en vivo:** al elegir un mando se dibuja con `controller_studio.VistaMando` y los botones pulsados se
     iluminan, usando `gestor_mandos_lectura.abrir_lector`.
2. **Orden de jugadores (RetroBat)**
   - Muestra Jugador 1 a 4 según `INPUT P{n}NAME` / `GUID` / `PATH`.
   - Permite fijar Jugador 1 y Jugador 2 eligiendo entre los mandos configurados en `es_input.cfg`.
   - Al guardar escribe `INPUT P{n}NAME` y `INPUT P{n}GUID` y **vacía `INPUT P{n}PATH`** de ese jugador, porque PATH
     tiene más prioridad. Antes crea un respaldo.
   - Si el mando elegido tiene un gemelo (mismo nombre y GUID), lo avisa y recomienda el menú de RetroBat.
3. **Configuración automática por sistema**
   - Tabla con cada sistema que tiene juegos, el emulador que usa y el estado de `disableautocontrollers`
     (global, sistema o «automático»).
   - Botones **«RetroBat configura los mandos»** (borra el ajuste del sistema) y **«Mapeo manual en el emulador»**
     (`<sistema>.disableautocontrollers = 1`).
   - Ambos crean un respaldo y piden cerrar RetroBat.
4. **TeknoParrot por juego:** botón **«Editor de mandos por juego de TeknoParrot…»**, que abre el `EditorMandos`
   actual sin cambios.

Escritura de `es_settings.cfg`: con `gestor_teknoparrot_pantalla.leer_ajustes`,
`gestor_teknoparrot_controles.actualizar_opcion`, `Cambio` y `guardar_cambios`. Así cada escritura crea un respaldo en
`user/tecnotics-gestor/respaldos-mandos` y revierte si el archivo cambió mientras se editaba.

### 4.5 Código

- `retrobat/gestor_preparar.py`:
  - `revisar_sistema()` para la verificación previa por sistema.
  - `nombre_requisitos_sistema()`.
  - `titulo_teknoparrot()`.
- `retrobat/gestor_preparar_ui.py`: `PanelEstado`, el panel de pasos reutilizable. Muestra un `Plan` (juego, en
  Biblioteca) o un `EstadoSistema` (sistema; versión compacta en Cargar sistemas) y ejecuta la acción de cada paso.
- `retrobat/gestor_biblioteca_ui.py` (nuevo): `PanelBiblioteca`. Contiene el filtro por sistema, el árbol, las acciones
  Editar nombre, Eliminar juego y Eliminar sistema (misma lógica que la V28) y un `PanelEstado`.
- `retrobat/gestor_mandos.py` (nuevo, sin Tk): lectura y escritura de los ajustes de jugadores y de la
  configuración automática.
- `retrobat/gestor_mandos_ui.py` (nuevo): `PanelMandos`.
- `retrobat/gestor_teknoparrot_ui.py`: se separa la fila de instalación del lote de importación.
- `retrobat/gestor-retrobat.pyw`:
  - Nuevo orden de pestañas, panel Cargar sistemas y Vista previa 29.
  - `--verificar` con la nueva lista de pestañas.
- Pruebas: `test_gestor_preparar.py` (revisar_sistema) y `test_gestor_mandos.py` (nuevo). Se añaden al workflow.

### 4.6 Problemas conocidos que se corrigen en esta versión

- `gestor_teknoparrot_editor.probar_juego` usa `subprocess.Popen` y no `gestor_firmware.abrir_emulador`. En el
  portable puede repetirse el error de `vcruntime140.dll` que se corrigió en la V27. Pasará a usar `abrir_emulador`.

### 4.7 Límites conocidos (no se resuelven en la V29)

- «Probar desde RetroBat» llama a `emulatorLauncher` sin los parámetros `-p1index`, `-p1guid` y demás que envía
  EmulationStation. Abre el juego como en el arcade, pero la configuración automática de mandos puede no
  aplicarse igual que desde el menú. Dragon Ball abrió bien con la V28.
- El orden de jugadores con dos placas idénticas requiere el menú CONTROLLERS PRIORITY de RetroBat, porque depende
  de `PATH`.

## 5. Estado de avance

### Gestor Arcade Tecnoticis 36 · Scraping experimental

- Biblioteca ofrece **Buscar medios faltantes** para el juego o sistema seleccionado. Usa Skyscraper compilado para Windows con ScreenScraper configurado en el propio auxiliar. [Compilar Skyscraper para Windows](https://github.com/Gemba/skyscraper#windows)
- El Gestor genera un catálogo temporal, agrega campos faltantes y respalda el catálogo anterior. Actualiza la lista de juegos dentro de RetroBat cuando termine.
- La publicación 3.21.1 de Skyscraper ofrece AppImages de Linux. Para Windows se requiere una compilación local compatible. Queda pendiente la descarga real en Windows con una cuenta ScreenScraper, la vista previa de coincidencias y la cobertura de TeknoParrot y juegos Windows.


### Gestor Arcade Tecnoticis 35

- El editor de TeknoParrot muestra los juegos con asignaciones XInput o DirectInput guardadas en **Configurados**. El selector **Sin configurar** solo ofrece los pendientes. El botón **Editar configuración guardada** carga el perfil seleccionado. Guardar actualiza los dos listados inmediatamente.


### Gestor Arcade Tecnoticis 34

- En Mandos → TeknoParrot, **Movimiento del jugador** aplica palanca izquierda (joycon) o cruceta a las cuatro direcciones del jugador seleccionado. **Guardar controles** confirma el cambio y crea un respaldo. La prueba gráfica verifica que las acciones ajenas al movimiento y el otro jugador se conservan. La asignación simultánea de ambas entradas queda pendiente de validar con TeknoParrot.


### Gestor Arcade Tecnoticis 33

- La versión 33 incorpora el mando renovado y una pestaña **Modo arcade**. El portable incluye los controles de arranque, PIN, bienvenida y restauración en una ventana auxiliar. El Gestor le pasa la instalación de RetroBat seleccionada.
- La comprobación de actualizaciones consulta las publicaciones públicas de GitHub, compara la numeración y verifica el SHA-256 del portable antes de reemplazarlo. Conserva el ejecutable anterior junto al actualizado con extensión `.anterior`.
- Quedan por validar el cambio efectivo del arranque de Windows, el PIN y la restauración en el equipo dedicado, así como una actualización real con la siguiente publicación numerada.


| Parte | Implementado | Pruebas automáticas | Probado por Mauricio |
|---|---|---|---|
| Documentación (este archivo) | 24-11-2026 | — | — |
| Biblioteca con filtro y detalle del juego | 24-11-2026 | Ventana simulada (Xvfb): filtro, nombre real de TeknoParrot, pasos de juego y sistema, editar nombre y eliminar juego con respaldo | pendiente |
| Cargar sistemas con verificación previa | 24-11-2026 | `SistemaTest` (5 pruebas) y ventana simulada: PS3 bloqueado sin emulador ni firmware; desbloqueado al instalarlos | pendiente |
| Importación de TeknoParrot dentro de Cargar sistemas | 24-11-2026 | Ventana simulada: el lote aparece al elegir TeknoParrot y «Siguiente paso: Juego» lleva allí | pendiente |
| Emuladores con sección TeknoParrot | 24-11-2026 | Ventana simulada: estado de componentes, RPCS3 y pantalla de carga | pendiente |
| Pestaña Mandos | 24-11-2026 | `test_gestor_mandos.py` (7 pruebas) y ventana simulada: orden de jugadores y mapeo manual por sistema guardados con respaldo. La detección y la prueba en vivo requieren Windows | pendiente |
| `probar_juego` de TeknoParrot con `abrir_emulador` | 24-11-2026 | Importación verificada | pendiente |
| V32 · Palanca izquierda para el movimiento en TeknoParrot | 25-11-2026 · [Portable publicado](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-32-9f46c57) | `test_controller_studio.py` verifica el guardado de los cuatro sentidos, la lectura en vivo, el cambio a cruceta y la conservación de los ataques y del otro jugador. [Pruebas y arranque en Windows](https://github.com/mardiles2k18-png/tecnotic_arcade/actions/runs/45540466454) | V31 solo respondía a la cruceta en combate. Falta probar la selección de personaje y el combate en la V32 |
| V31 · Controller Studio 0.1.1 y adaptación de mandos por juego | 24-11-2026 · [Portable publicado](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-31-87e5651) | `test_controller_studio.py` comprueba ambas vistas con capacidades XInput parciales, guardado de Street Fighter V, créditos de Contra y Raiden III, DirectInput, respaldos y escalado. [Pruebas y arranque en Windows](https://github.com/mardiles2k18-png/tecnotic_arcade/actions/runs/45535669818) | pendiente |
| V30: «Traspasar» y filas «Sin ejecutable» en Cargar sistemas | 24-11-2026 | `test_gestor_cargar.py`, ventana simulada con la carpeta de Mauricio y [GitHub Actions](https://github.com/mardiles2k18-png/tecnotic_arcade/actions/runs/45449889298) · publicada en [retrobat-manager-preview-30-2f0e0d4](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-30-2f0e0d4) | pendiente |
| Vista previa 29 publicada | 24-11-2026 · [retrobat-manager-preview-29-259f70e](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-29-259f70e) | [GitHub Actions](https://github.com/mardiles2k18-png/tecnotic_arcade/actions/runs/45435510220): pruebas, compilación y `--verificar` con las nuevas pestañas en Windows | pendiente |

En la V31 ambas vistas de Mandos usan el paquete independiente `retrobat/controller_studio`. La detección
mantiene el esquema Xbox completo para los gamepads XInput que reportan una máscara parcial. En el editor de
TeknoParrot, **Adaptar juego a nuestro mando** usa el mapa de RetroBat y las entradas disponibles del mando.
Para DirectInput se prioriza el mapa configurado por el usuario en RetroBat. La vista previa indica las acciones
pendientes y la confirmación guarda el perfil del juego con respaldo. Test y Service se asignan manualmente.
La entrada Service / Coin de Contra se trata como crédito. Las acciones EX1 y EX2 de Street Fighter V 3.53
se asignan al Jugador 1, tal como indica el perfil para el usuario.

En la V32 **Movimiento al adaptar** permite elegir **Palanca izquierda**, **Cruceta** o **Mapa del juego**.
Al elegir un control físico, el gestor asigna las cuatro direcciones del jugador y conserva sus botones de
ataque ya guardados para ese mando. El selector ofrece los controles que se pueden mapear en los cuatro sentidos.
El mapa de RetroBat para Ultra Street Fighter IV usa la cruceta de forma predeterminada. Si el juego arcade
pide la tarjeta NESiCA al seleccionar personaje, Taito indica que se puede omitir el aviso con Inicio.
[Mapa de RetroBat](https://github.com/RetroBat-Official/retrobat/blob/main/system/resources/inputmapping/teknoparrot.yml) · [Ayuda de Taito](https://support.taito.co.jp/faqarticle.php?id=8961&kid=69664&la=10)

## 6. Cómo retomar

1. Leer `AGENTS.md`, este documento y la sección «Gestor de RetroBat en Windows» del `README.md`.
2. Trabajar en la rama `codex/retrobat-manager`. Comprobar `git log` por si hubo cambios después de esta fecha.
3. Pruebas locales, desde `retrobat/`:

   ```bash
   python3 -m unittest test_gestor_preparar test_gestor_firmware test_gestor_emuladores test_gestor_mandos
   ```

   En Linux, `tkinter` puede no estar en el Python principal. La interfaz se prueba con
   `xvfb-run -a python3.12 <script>`, construyendo los paneles con una aplicación simulada.
4. Publicar: un push a `codex/retrobat-manager` que toque `retrobat/gestor*`, `retrobat/test_gestor_*.py`,
   `retrobat/compilar_portable.py` o el workflow dispara `.github/workflows/gestor-retrobat-portable.yml`. Ese
   workflow:
   - corre las pruebas, compila `Tecnotics-Arcade-Portable-Preview-N.exe` y ejecuta `--verificar`;
   - publica `retrobat-manager-preview-N-<sha7>`.
5. Después de publicar, hacer un commit que solo actualice el enlace del README, como en «Enlaza el portable
   publicado de la Vista previa N». Al tocar solo el README no se recompila.
6. Subir la versión en dos lugares: el título de `Gestor` en `gestor-retrobat.pyw` y `--name` en
   `compilar_portable.py`.
7. Mauricio prueba en el arcade, paso a paso. Registrar su resultado en la sección 5.
