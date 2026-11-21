# Tecnotics Arcade

## Tema completo Tecnotics AluBrush para RetroBat

La versión XML para RetroBat está en **[themes/es-theme-tecnotics-alubrush](themes/es-theme-tecnotics-alubrush)**. Conserva los **2.438 archivos originales de AluBrush**, incluidas todas sus vistas, opciones y recursos, y añade la marca Tecnotics y los fondos/logos entregados para **Windows, MAME y FinalBurn Neo**. Los originales sustituidos se conservan con un manifiesto de integridad.

**[Cómo instalar, construir, modificar y validar un tema de RetroBat](docs/temas-retrobat.md)** explica la estructura XML, rutas, identificadores por sistema, requisitos de imágenes, scripts de construcción y pruebas. Lee esa guía antes de modificar el tema.

Instalación: copia la carpeta completa en `RetroBat/emulationstation/.emulationstation/themes/` y selecciónala en los ajustes de interfaz. No confundas esta versión con `pegasus/themes/tecnotics/`: QML/Pegasus y XML/RetroBat son formatos distintos.

La validación estática pasa; queda pendiente probar la presentación real en RetroBat con sus variantes y mando. El tema no incluye juegos ni BIOS y no modifica el registro ni el shell de Windows.

### Reglas básicas para construir o modificar el tema

- El punto de entrada es `theme.xml`, con `<theme>` y `<formatVersion>7</formatVersion>`; RetroBat no carga temas QML de Pegasus.
- Conserva toda la carpeta original. Las vistas, variantes, fuentes, sonidos y archivos incluidos forman parte del tema.
- Haz las personalizaciones en `tecnotics.xml`, incluido al final. Usa rutas compartidas `${themePath}/art/...` y claves que coincidan con `<theme>` en `es_systems.cfg`.
- Para Windows, MAME y FinalBurn Neo utiliza las claves `windows`, `mame` y `fbneo`. Cada uno tiene el fondo JPG y el logo PNG nuevos, además de los recursos originales conservados.
- Comprueba los XML y las rutas con el validador; después prueba la pantalla real, las variantes y el mando en RetroBat.

```powershell
./scripts/Validar-Tema-RetroBat.ps1 -ThemeDirectory './themes/es-theme-tecnotics-alubrush'
```

La [guía completa](docs/temas-retrobat.md) incluye el comando para reconstruirlo desde el ZIP original, la estructura de carpetas y las pruebas antes de distribuirlo.

---

## Documentación previa: Batocera y tema básico

Las instrucciones siguientes corresponden a la implementación anterior para Batocera. Para el nuevo tema RetroBat utiliza la guía enlazada arriba.

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


