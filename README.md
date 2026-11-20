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

La versión portable se ejecuta abriendo `Tecnotics-Arcade-Portable-Preview-7.exe`
en Windows x64. Incluye Python, Tcl/Tk, los logos, los temas y el video de
inicio. Funciona sin instalación y sin conexión. Abre **Configurar RetroBat**
para editar `retrobat.ini` dentro del gestor. Al guardar, el editor crea
un respaldo `retrobat-*.ini.bak` junto al archivo original.

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

Instala Python 3.11 o posterior para Windows con Tcl/Tk. Con RetroBat cerrado,
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

En la parte inferior de la app puedes:

- **Biblioteca de este PC** — muestra los sistemas con juegos, sus categorías
  y el estado conocido de sus BIOS. Windows figura como sistema sin BIOS.
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
- **Duplicados** — agrupa títulos iguales y archivos con SHA-256 idéntico,
  también entre sistemas. Puedes conservar una copia, conservar las de un
  sistema o retirar solo las seleccionadas. Las entradas retiradas van a
  `user/tecnotics-gestor/respaldos` y se pueden restaurar desde el gestor
  si la ruta está libre. En Windows se retiran accesos directos.
- **Verificar BIOS** — identifica la versión de RetroBat y consulta sus
  requisitos locales y las fuentes oficiales. Para MAME compara los nombres
  de las ROMs instaladas con el XML publicado para el núcleo estándar detectado
  y muestra sus BIOS asociadas y las coincidencias locales.
  Para PS3 ofrece descargar el firmware 4.93 de Sony a
  `bios/PS3UPDAT.PUP` y comprueba su SHA-256 antes de guardarlo. RPCS3
  pide instalarlo al abrir un juego. Para sistemas que requieren un archivo
  extraído de la consola, consulta **Missing BIOS Check** en RetroBat.
  Sin un sistema seleccionado, se puede verificar un manifiesto de texto de
  MD5 y rutas relativas a `bios`.
- **Instalar intro** — copia un MP4, activa la intro y respalda el `retrobat.ini`.
  Puedes elegir el video Tecnotics en `arranque/splash`.
- **Crear tema / Editar tema** — duplica un tema base y abre archivos XML en
  el Bloc de notas. Selecciona el nuevo tema en RetroBat.
- **Configurar RetroBat** — abre el editor integrado de `retrobat.ini`.

La app comprueba la última publicación estable de RetroBat al abrir una
instalación y deja que consultes las versiones oficiales desde la cabecera.

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
