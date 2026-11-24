# Tecnotics Arcade

Personalización de Batocera para las máquinas arcade de Tecnotics.

En los ejemplos, `IP` es la dirección de la máquina (por ejemplo `192.168.4.9`).

## Contenido

| Carpeta | Qué hay |
|---|---|
| `logo/` | Logos originales de Tecnotics |
| `arranque/` | Logo y vídeo que se ven al encender la máquina |
| `themes/es-theme-tecnotics/` | Tema de la interfaz (versión básica) |
| `herramientas/` | Script que genera las imágenes y el vídeo a partir del logo |

## Al encender la máquina, Batocera enseña tres pantallas

1. **Logo fijo (un instante):** se cambia con `arranque/instalar-logo-arranque.sh`.
2. **Vídeo de inicio:** se cambia con `arranque/splash/tecnotics-arcade.mp4`.
3. **Pantalla de carga de la interfaz:** se cambia al elegir el tema `es-theme-tecnotics`.

## Instalación

### 1. Vídeo de inicio
Copia `arranque/splash/tecnotics-arcade.mp4` en:
```
\\IP\share\splash\
```
Si la carpeta `splash` no existe, créala. Batocera usará ese vídeo en lugar del suyo.

### 2. Tema
Copia la carpeta completa `themes/es-theme-tecnotics` en:
```
\\IP\share\themes\
```
Debe quedar así: `\\IP\share\themes\es-theme-tecnotics\theme.xml`.

En la máquina: **Menú → Ajustes de interfaz → Tema** y elige *tecnotics* (puede aparecer como *es-theme-tecnotics*).

### 3. Logo fijo del primer instante
1. Crea la carpeta `\\IP\share\system\tecnotics\`.
2. Copia ahí `arranque/boot-logo.png` y `arranque/instalar-logo-arranque.sh`.
3. Entra por SSH (`ssh root@IP`) y ejecuta:
   ```bash
   bash /userdata/system/tecnotics/instalar-logo-arranque.sh
   ```
4. Reinicia con `reboot`.

Para volver al logo de Batocera:
```bash
bash /userdata/system/tecnotics/instalar-logo-arranque.sh restaurar
```
Al actualizar Batocera este paso se pierde y hay que repetirlo. Los pasos 1 y 2 se conservan.

## Regenerar las imágenes

Si cambia el logo, sustituye los archivos de `logo/` y ejecuta:
```bash
python3 herramientas/generar_recursos.py
```
Necesita Python con Pillow y ffmpeg.

## Licencias

Las tipografías Anton y Barlow (`themes/es-theme-tecnotics/art/fonts`) se usan bajo la SIL Open Font License; los textos de la licencia están en esa misma carpeta.

## Juegos de Windows: preparación automática

`sistema/scripts/tecnotics-wine.sh` prepara cada juego de Windows la primera vez que se abre: crea su prefijo de Wine e instala Media Foundation (los códecs que usan las cinemáticas) si la versión de Batocera lo incluye; la 44 no lo incluye. Opcionalmente también instala librerías con winetricks, que se configuran en la variable `LIBRERIAS_EXTRA` al principio del script.

Instalación:
1. Copia el archivo en `\\IP\share\system\scripts\`. Crea la carpeta `scripts` si no existe.
2. Por SSH, dale permiso de ejecución y prepara los juegos que ya tienes:
   ```bash
   chmod +x /userdata/system/scripts/tecnotics-wine.sh
   /userdata/system/scripts/tecnotics-wine.sh todos
   ```

El registro queda en `\\IP\share\system\logs\tecnotics-wine.log`. Para volver a preparar un juego, borra el archivo `.tecnotics-preparado` de su prefijo, en `/userdata/system/wine-bottles/windows/<runner>/<juego>.wine/`.

## Configuración de la placa HP ProOne 400 G2

Ajustes que necesita cada máquina con esta placa. Aplícalos con `sistema/configurar-placa-hp.sh`: cópialo a `\\IP\share\system\tecnotics\`, ejecuta `bash /userdata/system/tecnotics/configurar-placa-hp.sh` y reinicia.

| Ajuste | Motivo |
|---|---|
| `global.videooutput=HDMI-A-1` | Usar la salida trasera, que con adaptador va a HDMI. |
| `global.videooutput2=none` | La placa detecta la pantalla interna `eDP-1` aunque no esté conectada. Si no se desactiva, la imagen se desplaza y el teclado y el ratón dejan de responder en la interfaz. |
| `display.position=left-right` | Recoloca el monitor en la posición 0,0 al arrancar. Sin esto, los juegos de Windows salen descentrados. |
| `windows.wine-runner=wine-proton` | Proton reproduce las cinemáticas de los juegos de Windows; `wine-tkg` se cae en ellas. |

Otros ajustes:
- **Sonido por el monitor:** Ajustes de sonido → Perfil de audio → *Digital Stereo (HDMI) Output*.
- **Juegos que no ocupan toda la pantalla:** activa FSR para ese juego (`windows["Juego.pc"].fsr=1`) o pulsa Alt+Enter dentro del juego.
- **Secure Boot:** desactívalo en la BIOS (F10 → Advanced → Secure Boot Configuration) o registra `EFI/batocera/batocera-mok.cer` desde MokManager.

## Juegos de Windows probados

| Juego | Estado | Notas |
|---|---|---|
| Big Rumble Boxing: Creed Champions | ✅ | Proton |
| Hunter x Hunter: Nen x Impact | ✅ | Proton |
| Blade Strangers | ✅ | Proton + FSR + Alt+Enter |
| King of Fighters XIII | ✅ | Proton. Juego de 32 bits: los vídeos WMV dejan la pantalla en negro, así que se renombró la carpeta `video` a `video_respaldo`. Con wine-tkg no abre ventana. |

## Pendiente: vídeos de King of Fighters XIII

Los vídeos del juego no se ven (se queda en negro), así que de momento la carpeta `video` está renombrada a `video_respaldo` y el juego arranca sin ellos.

Lo que ya se probó (Batocera 44, placa HP con Intel HD 530):
- **Causa:** el error es `winegstreamer: failed to create glvideoflip, are 32-bit GStreamer "base" plugins installed?`. Afecta a la ruta de vídeo de 32 bits de Wine; el juego es de 32 bits.
- `/lib32/gstreamer-1.0/libgstopengl.so` existe y no le falta ninguna librería (`ldd` limpio).
- Convertir `opening.wmv` a H.264/MP4 con el nombre `.wmv` (truco de ProtonDB): el juego se cae (page fault).
- Convertir a WMV2/WMA2 en ASF: pantalla negra.
- Registro de GStreamer propio con `ENV=GST_REGISTRY_1_0=...` en `autorun.cmd`: pantalla negra.
- `wine-tkg` (también con `wayland_driver=native`): no abre ventana (`nodrv_CreateWindow`).

Ideas para retomar:
- Probar un runner GE-Proton en `/userdata/system/wine/custom/`.
- Revisar si el script `batocera-wine` define bien `GST_REGISTRY_1_0`: mezcla las rutas de 32 y 64 bits en una sola variable.
- Preguntar o informar en el foro o en el GitHub de Batocera con el error de `glvideoflip`.

## Tema discreto "oficina"

`themes/es-theme-oficina` hace que RetroBat o Batocera parezcan un gestor de documentos: fondo claro, barra de título "Gestor de Documentos", carpetas en vez de consolas, lista de archivos en vez de juegos, sin imágenes ni vídeos, sin contador de juegos, y pantalla de carga "Cargando espacio de trabajo...".

Instalación en RetroBat: descomprime la carpeta en `C:\RetroBat\emulationstation\.emulationstation\themes\` y elígela en Menú → Ajustes de interfaz → Tema. Las imágenes se regeneran con `python3 herramientas/generar_tema_oficina.py`.

## Gestor de RetroBat en Windows

La **Vista previa 28** se ejecuta sin instalación en Windows x64. Incluye
Python, Tcl/Tk, 7-Zip, los logos, los temas y el video de inicio. La descarga
de TeknoParrot y las consultas en línea requieren conexión. [Descargar la Vista previa 28](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/download/retrobat-manager-preview-28-e493918/Tecnotics-Arcade-Portable-Preview-28.exe) · [Publicación y SHA-256](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-28-e493918) · [Registro del 24 de noviembre](https://github.com/mardiles2k18-png/tecnotic_arcade/blob/main/docs/estado-proyecto.md#registro-del-24-de-noviembre-de-2026)

En **Configurar RetroBat** puedes editar `retrobat.ini`. Al guardar, el
editor crea un respaldo `retrobat-*.ini.bak` junto al archivo original.

Para compilar una copia desde el código fuente, usa Python 3.13 x64 con
Tcl/Tk y pip. Desde la raíz del repositorio ejecuta:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe retrobat\compilar_portable.py
```

El compilador descarga de PyPI las dependencias de compilación que falten y
deja el ejecutable en `dist/`. Los cambios verificados y el grafo del proyecto
se actualizan en GitHub en la rama de trabajo.

### Ejecutar desde el código fuente

Instala Python 3.11 o posterior para Windows con Tcl/Tk y ejecuta
`py -3 -m pip install Pillow truststore`. Con RetroBat cerrado,
abre `retrobat/gestor-retrobat.pyw` o ejecuta `py -3 retrobat/gestor-retrobat.pyw`
desde la raíz del repositorio.

1. Elige **Carpeta de RetroBat de este PC** (donde está `retrobat.exe`) y
   **Origen de los juegos a importar**. La app recuerda la instalación válida
   para tu cuenta de Windows. El selector carga todos los sistemas cuyo destino está en
   `roms/`, junto con sus carpetas y extensiones, desde el `es_systems.cfg`
   de la instalación. Las secciones del menú, capturas y biblioteca multimedia
   quedan fuera del selector de juegos.
2. Elige el sistema y, si quieres, una categoría como **Lucha**. Puedes usar una
   carpeta existente o crearla con **Nueva categoría**. Aparece dentro del
   sistema en RetroBat al contener juegos y actualizar la lista, si la vista
   de carpetas está habilitada. Para Windows, coloca un
   juego por subcarpeta o ejecutables individuales en la raíz.
3. La verificación comienza al elegir las carpetas y el sistema. Usa
   **Verificar juegos** para actualizar la lista manualmente. En Windows, el
   gestor busca accesos directos en todo `roms/windows` y comprueba sus
   destinos, incluso si el nombre del acceso es distinto al de la carpeta.
4. Si un juego nuevo tiene varios `.exe`, selecciona su fila y elige el
   archivo que debe arrancar. **Importar nuevos** crea accesos directos para
   los juegos nuevos listos después de confirmar. Para consolas, selecciona
   las filas con Ctrl o Mayús y usa **Importar seleccionados**. Los archivos
   originales se conservan en ambos casos.

La barra muestra avance y tiempo restante aproximado cuando se conocen
los bytes o el número de elementos. Durante búsquedas de duración desconocida,
muestra actividad y tiempo transcurrido.

Al elegir una carpeta externa con nombre de sistema, por ejemplo
`Juegos de PlayStation 2` o `ROMs - SNES`, el gestor selecciona el sistema
si aparece en el catálogo instalado. Verifica el contenido y pide confirmación
antes de copiar los juegos nuevos. Para una carpeta reconocida como Windows
copia los juegos a `library/windows` y apunta los accesos directos de
`roms/windows` a las copias. Puedes elegir el sistema manualmente si el nombre
de la carpeta es un género o no identifica una consola.

El gestor conserva las subcarpetas de origen al copiar ROMs. En MAME copia
los ZIP y 7z con su nombre original y lleva los CHD o IMG asociados en la
subcarpeta del mismo nombre. Si hay copias del mismo juego en el origen,
elige una fila por juego. También admite carpetas de disco PS3 con
`PS3_GAME/USRDIR/EBOOT.BIN`. Los descriptores de disco, listas multidisco
y accesos que dependen de otros archivos se marcan para revisión manual.

El gestor se organiza en seis pestañas:

- **Inicio** comprueba la instalación guardada, busca RetroBat en `C:\RetroBat`
  y compara la versión local con la última estable publicada.
- **Cargar juegos** conserva la verificación, comparación e importación.
- **BIOS** lista los sistemas con juegos y permite comprobar sus requisitos.
- **Biblioteca** reúne el inventario de juegos, los duplicados y los respaldos.
- **Configurar RetroBat** reúne temas, intro, música y el editor de ajustes.
- **TeknoParrot** prepara el emulador e importa juegos con sus perfiles.

Acciones disponibles:

- **Biblioteca de este PC** — muestra los sistemas con juegos, sus categorías
  y el estado conocido de sus BIOS. Expande un sistema y una categoría para
  seleccionar un juego. Con RetroBat cerrado, **Editar nombre** guarda el
  título visible en `gamelist.xml` y **Eliminar juego** muestra los archivos
  que moverá a un respaldo. Para Windows se puede retirar por completo una
  copia administrada por el gestor o ubicada en `roms/windows`, junto con su
  acceso directo. Se retira la carpeta si se identifica como la del juego y
  no la usa otro acceso. Si el destino es externo, faltante o compartido,
  se puede retirar solo el acceso. Otros formatos con archivos asociados
  que el gestor no puede identificar se gestionan manualmente.
  **Eliminar sistema** mueve su carpeta de ROMs completa a un respaldo
  restaurable desde **Duplicados**. Los emuladores, las partidas guardadas
  y las instalaciones Windows que estén fuera de esa carpeta se conservan.
- **Biblioteca → Respaldos…** muestra el contenido, la fecha y el tamaño de
  cada respaldo de la biblioteca. Selecciona uno o varios con Ctrl o Mayús y
  pulsa **Eliminar seleccionados…**, o usa **Vaciar respaldos…** para borrar
  todos los respaldos de la lista. El borrado es definitivo y afecta solo a
  las copias ubicadas en `user/tecnotics-gestor/respaldos`.
- **Buscar BIOS** — en el informe, selecciona un archivo y abre la búsqueda
  por nombre y versión. **Abrir fuente** está disponible cuando se encuentra
  un archivo con el nombre esperado en la fuente oficial. **Agregar BIOS
  desde carpeta** busca copias locales y copia solo las que coincidan con
  las huellas del catálogo, sin reemplazar archivos. En MAME revisa los
  componentes de la BIOS predeterminada dentro del ZIP.
- **Comparar copias** — compara un juego de origen con el que ya está en
  RetroBat. Muestra los tamaños y distingue una huella SHA-256 igual de una
  coincidencia por nombre. En Windows, la huella corresponde al ejecutable
  y el tamaño de las carpetas se muestra cuando se pueden identificar.
  Puedes conservar la copia actual o reemplazarla con respaldo. Los
  reemplazos de Windows conservan los archivos anteriores del juego. Los
  formatos que requieren varios archivos deben reemplazarse manualmente.
- **Duplicados** — muestra en una lista todos los grupos por título o SHA-256,
  también entre sistemas. Marca una o más copias en **Conservar** y usa
  **Aplicar selección** para retirar las demás copias de esos grupos en un
  solo lote. Los grupos sin ninguna marca quedan intactos. Las entradas retiradas van a
  `user/tecnotics-gestor/respaldos` y se pueden restaurar desde el gestor
  si la ruta está libre. En Windows se retiran accesos directos.
- **Verificar BIOS** — identifica la versión de RetroBat y consulta sus
  requisitos locales y las fuentes oficiales. Para MAME compara los nombres
  de las ROMs instaladas con el XML publicado para el núcleo estándar detectado
  y muestra sus BIOS asociadas y las coincidencias locales.
  También permite verificar un manifiesto de texto con MD5 y rutas relativas a `bios`.
- **Firmware** — consulta los requisitos de la instalación y el catálogo de
  RetroBat incluido. Elige un sistema y usa **Instalar disponibles…** para
  preparar sus archivos publicados, o selecciona las variantes que necesitas.
  La pestaña comprueba las descargas, reutiliza `bios/PS3UPDAT.PUP` para PS3 y
  Namco 357/369 e instala el firmware en la copia correspondiente de RPCS3.
  También instala el software y las fuentes oficiales de PS Vita en Vita3K.
  Usa **Importar archivo…** para elegir una copia de firmware o
  **Importar carpeta…** para buscar varias copias. Puedes guardar un paquete
  de PS3 o PS Vita aunque el emulador falte y terminar la instalación cuando
  esté disponible. En Ryujinx, importa `prod.keys` desde tu copia y usa
  **Abrir Ryujinx** para instalar el firmware extraído desde su menú.
  [Guía de BIOS de RetroBat](https://wiki.retrobat.org/get-started/adding-bios-files)
- **Emuladores** — lee los emuladores y núcleos del `es_systems.cfg` de tu
  instalación. Filtra por sistema y usa **Instalar seleccionados…** para preparar
  los paquetes en las rutas de RetroBat. **Usar para un sistema…** guarda el
  emulador y núcleo preferidos, con respaldo de los ajustes. El lanzador de
  RetroBat aplica sus opciones al abrir cada juego. Para paquetes que requieren
  licencia o carecen de una descarga pública compatible, usa **Importar copia…**.
  Configura las BIOS y el firmware desde sus pestañas si el sistema los requiere.
  [Emuladores compatibles de RetroBat](https://wiki.retrobat.org/systems-and-emulators/supported-game-systems)
- **Instalar intro** — copia un MP4, activa la intro y respalda el `retrobat.ini`.
  Puedes elegir el video Tecnotics en `arranque/splash`.
- **Importar tema** — usa la instalación de RetroBat guardada. Selecciona la
  carpeta que contiene `theme.xml`, revisa el destino y pulsa **Instalar en
  RetroBat**. La ventana muestra una captura incluida o una imagen del tema y
  mantiene visible el progreso mientras copia la carpeta. Selecciona el tema
  instalado desde los ajustes de RetroBat.
- **Crear tema / Editar tema** — duplica un tema base y abre archivos XML en
  el Bloc de notas. Selecciona el nuevo tema en RetroBat.
- **Eliminar tema** — mueve una carpeta de tema instalada a
  `user/tecnotics-gestor/temas-retirados`. Para recuperarla, cópiala a la carpeta
  de temas de RetroBat.
- **Importar música** — copia archivos MP3, OGG, WAV o FLAC a
  `emulationstation/.emulationstation/music` sin sobrescribir archivos.
  La música se escucha cuando está habilitada en los ajustes de sonido de RetroBat.
- **Editar retrobat.ini** — abre el editor integrado.

La app comprueba la última publicación estable de RetroBat al abrir una
instalación. En **Inicio** puedes consultar las versiones oficiales.

### Aviso de Game Bar en Windows 10 LTSC

Si Windows pide una aplicación para abrir `ms-gamingoverlay` al iniciar
RetroBat, abre **Configuración → Juegos → Game Bar**. Desactiva **Permitir
que el mando abra Game Bar** y el interruptor de Game Bar. Esta configuración
se aplica a la cuenta de Windows. Se verificó el arranque de RetroBat después
de cambiar ambos ajustes.

## Graphify: instalación en cualquier PC y uso con IA

Para configurar Graphify en una nueva computadora (Windows), en Claude Code o Codex, **abre [INSTALAR_GRAPHIFY.md](INSTALAR_GRAPHIFY.md)**. Incluye un mensaje listo para copiar al asistente y scripts de instalación reproducibles para Windows y Linux/Codex Cloud.

- Windows: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-graphify.ps1`
- Linux / Codex Cloud: `bash scripts/setup-graphify.sh`
- Guía de colaboración: [docs/graphify-colaboracion.md](docs/graphify-colaboracion.md)

GitHub comparte el código y `graphify-out/graph.json`. Instala la CLI y las skills en cada equipo para consultar o regenerar el grafo.

### Configurar e importar TeknoParrot

1. Selecciona la instalación en **Inicio**. En **TeknoParrot**, pulsa
   **Instalar y configurar TeknoParrot**. El gestor descarga y verifica los
   componentes oficiales, instala el emulador en `emulators/teknoparrot`
   y prepara la carpeta de juegos del sistema. Cuando indique **Listo para
   cargar juegos**, el selector de carpetas quedará habilitado. Si existía
   una instalación, se guarda una copia bajo
   `user/tecnotics-gestor/teknoparrot-respaldos` y se conservan sus perfiles.
2. Elige una carpeta de juego o selecciona archivos ZIP, 7z o RAR. Para
   revisar un lote, elige la carpeta que contiene los archivos o subcarpetas. El
   gestor busca el identificador o título en los perfiles oficiales instalados
   y selecciona el ejecutable cuando hay una coincidencia única. Si el perfil
   no indica el nombre del ejecutable, revisa el catálogo local de RetroBat.
   Si todavía falta un archivo de arranque, consulta la ficha oficial del
   perfil en TeknoParrot y, cuando hace falta, la tabla del lanzador de RetroBat.
   Para BlazBlue Central Fiction (`BBCF`), acepta `game.exe` o un archivo
   `game` sin extensión con cabecera de ejecutable de Windows. Si hay varias
   coincidencias, puedes elegir el archivo de tu edición manualmente.
   En juegos comprimidos, usa **Mostrar todos los archivos** para ver también
   los nombres sin extensión.
3. Cierra RetroBat y TeknoParrot y pulsa **Importar seleccionados**. El gestor
   conserva las carpetas originales, crea una carpeta con el identificador
   del perfil y la extensión declarada por RetroBat, y guarda las rutas en
   `UserProfiles`. Los perfiles repetidos se marcan antes de copiar y se
   vuelven a comprobar al instalar. Actualiza la lista de juegos de RetroBat
   y abre el juego desde TeknoParrot.

Selecciona una fila y pulsa **Diagnóstico…** para volver a comprobar su
carpeta o comprimido. El informe muestra los nombres esperados, los candidatos
encontrados, los archivos mencionados por la guía que no aparecen en el origen
y enlaces a las fuentes. La consulta en línea usa el identificador del perfil
y solo descarga documentación. Si falta un componente, revisa en la ficha
oficial si corresponde a tu edición.

### Configurar los mandos de TeknoParrot

Con RetroBat y TeknoParrot cerrados, abre **TeknoParrot → Configurar mandos…**.
Elige el **Juego instalado**, el **Mando** y el jugador. Compara lo que hay
guardado con la nueva asignación. **Aplicar plantilla recomendada** usa el
mapa local de RetroBat o consulta su catálogo oficial si falta el mapa.
Selecciona una acción y elige su botón en la lista, en el dibujo o con
**Asignar al pulsar**. El dibujo y las filas se iluminan cuando el mando
registra una entrada.

La vista usa **TECNOTICS Controller Studio** y adapta el dibujo al tamaño
de la ventana. El verde marca la entrada activa y el cian la selección.
[Biblioteca y demo independiente](retrobat/controller_studio/README.md)

**Guardar este juego** guarda únicamente el perfil elegido y respalda los
ajustes que cambien. **Probar juego** abre el perfil guardado mediante el
lanzador de RetroBat cuando la entrada está en su biblioteca. Para un juego
registrado directamente en TeknoParrot, lo abre con ese emulador. La opción
**Conservar este mapeo al iniciar desde RetroBat** mantiene la asignación de
ese juego al volver a lanzarlo.

Las plantillas de **Raiden III** y **Raiden III NESiCAxLive** dejan Test y
Servicio sin asignar. En **Contra: Evolution**, **Service / Coin** se
conserva como acción de ficha. Para configurar a otro jugador,
elige su número y el mando correspondiente. La API de entrada se guarda
para el perfil completo del juego.

La detección usa **XInput** y **DirectInput** de Windows. Para DirectInput,
el gestor consulta la base de mandos y la configuración de EmulationStation
de tu instalación. Si un encoder USB queda sin distribución reconocida,
puedes asignar sus entradas pulsando los botones en el editor.

RetroBat 7 o posterior puede aplicar los controles de su catálogo
`teknoparrot.yml`. Los volantes, pistolas y juegos con requisitos especiales
pueden necesitar ajustes adicionales. Algunos perfiles requieren licencia,
un núcleo específico o dependencias de Windows, como DirectX de junio de 2010
y Visual C++. Sigue las indicaciones del emulador para esos requisitos. La
pestaña lee los ejecutables dentro de los ZIP, 7z y RAR y extrae el juego
al importarlo. Los archivos originales se conservan. El portable incluye
7-Zip y, al ejecutar el código fuente, se usa el 7-Zip instalado.
El portable incluye la licencia del descompresor. [Código fuente de 7-Zip 26.06](https://github.com/ip7z/7zip/releases/tag/26.06).

Si el juego arranca detrás de la pantalla de carga, cierra RetroBat y abre
**TeknoParrot → Pantalla de carga…**. Esta opción cambia el ajuste oficial
`HideWindow` de EmulationStation para todos los sistemas, guarda un respaldo
del archivo de ajustes y permite revertirlo desde el mismo botón.

- [Integración oficial en RetroBat](https://wiki.retrobat.org/systems-and-emulators/supported-game-systems/arcade/teknoparrot)
- [Mapeo de controles de RetroBat](https://wiki.retrobat.org/controllers/specific_mapping/teknoparrot-controller-mapping)
- [Descargas oficiales de TeknoParrot](https://teknoparrot.com/en/Home/Download)
- [Colección comunitaria de TeknoParrot en Internet Archive](https://archive.org/download/tp-roms_0/TeknoParrot%20Collection/)
