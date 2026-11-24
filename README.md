# Tecnotics Arcade

## Objetivo principal del proyecto

**Construir un ecosistema de herramientas que permita crear, configurar, personalizar y mantener un sistema arcade Tecnotics sobre Windows.**

Objetivo confirmado por Mauricio el **21 de noviembre de 2026**.

El Gestor de RetroBat tiene publicada la **Vista previa 22** para Windows x64. El **Lanzador Tecnotics 1.2.0** está diseñado para ocultar Windows durante el uso del arcade y dar acceso al mantenimiento mediante PIN. [Descargar el gestor](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/download/retrobat-manager-preview-22-87d4469/Tecnotics-Arcade-Portable-Preview-22.exe) · [Registro del 23 de noviembre](docs/estado-proyecto.md#registro-del-23-de-noviembre-de-2026)

El resultado buscado es encender el arcade, entrar a la experiencia Tecnotics y manejar los juegos con palancas y botones, manteniendo una forma controlada de volver a Windows para mantenimiento.

## Antes de continuar con una IA

Lee **[AGENTS.md](AGENTS.md)** y **[docs/estado-proyecto.md](docs/estado-proyecto.md)**. Este último registra las decisiones vigentes, las herramientas, sus ramas, la evidencia de pruebas y los pendientes.

La rama de referencia para este contexto es **main**. La rama que GitHub abre por defecto puede ser otra: confirma la rama antes de trabajar. La IA debe consultar estos archivos al retomar; el historial de un chat no sustituye el estado guardado en el repositorio.

## Para qué sirve cada parte del ecosistema

| Parte | Aporte al arcade Windows | Ubicación y estado |
|---|---|---|
| Gestor de RetroBat · Vista previa 22 | Administrar biblioteca, duplicados, respaldos y BIOS, importar juegos y configurar RetroBat, TeknoParrot y sus mandos | Compilación y apertura verificadas en Windows. [Rama del gestor](https://github.com/mardiles2k18-png/tecnotic_arcade/tree/codex/retrobat-manager) · [Publicación y SHA-256](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-22-87d4469) |
| Lanzador Tecnotics 1.2.0 (configurador y bienvenida) | Preparar el inicio de Windows, entrada a RetroBat, PIN de mantenimiento y ajustes del equipo | Rama [claude/sweet-noether-plai9b](https://github.com/mardiles2k18-png/tecnotic_arcade/tree/claude/sweet-noether-plai9b). Versión 1.2.0 confirmada por Mauricio; código y ejecutable disponibles |
| Tema Tecnotics AluBrush | Presentación visual de RetroBat con marca Tecnotics y recursos de los sistemas | En main. Validación estática aprobada; prueba visual pendiente |
| Logos, intro y generadores | Crear y mantener una identidad visual común | En main: logo/, arranque/ y herramientas/ |
| Constructor y validador del tema | Repetir la construcción y detectar errores antes de distribuir | En main: scripts/; ejecutados correctamente |
| Accesos de juegos Windows | Integrar ejecutables de PC en el menú | En main: retrobat/crear-accesos-*.ps1; requieren revisar sus rutas |
| Documentación y Graphify | Ayudar a continuar el desarrollo entre PCs y asistentes | Contexto en main; Graphify está en otras ramas y no es necesario para jugar |
| Respaldo y despliegue | Poder recuperar y repetir una instalación en otra máquina | Objetivo de integración; copia maestra pendiente |

**Documentar una herramienta en main no significa que su código ya esté integrado allí.** El gestor y el configurador siguen en sus ramas. Descargar solamente main todavía no entrega todo el ecosistema reunido.

Windows es la plataforma objetivo. Los scripts de Batocera y el prototipo Pegasus se conservan como antecedentes; no deben confundirse con instrucciones del flujo Windows vigente. La edición final de Windows y la validación conjunta de las herramientas siguen pendientes.

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


