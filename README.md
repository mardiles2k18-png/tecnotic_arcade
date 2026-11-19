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
