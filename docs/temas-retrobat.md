# Construir y modificar un tema correcto para RetroBat

## Qué versión usar

`themes/es-theme-tecnotics-alubrush/` es la adaptación XML completa para RetroBat/EmulationStation. Conserva todos los archivos del ZIP AluBrush original, con sus vistas, variantes, idiomas, sonidos, tipografías, shaders, imágenes y personalización por juego. Windows, MAME y FinalBurn Neo ya existían como identificadores en el original: ahora se incorporan además los fondos y logos entregados por Mauricio. No se limita a ocho sistemas.

La versión `pegasus/themes/tecnotics/` es otra interfaz, escrita en QML para Pegasus. No se instala en RetroBat. El ZIP cuyo nombre termina en Pegasus tampoco sirve para RetroBat.

## Instalar en RetroBat

1. Cierra RetroBat y guarda una copia de tu tema anterior si lo vas a modificar.
2. Copia **la carpeta completa** `themes/es-theme-tecnotics-alubrush`, no solo `theme.xml`, dentro de `RetroBat/emulationstation/.emulationstation/themes/`.
3. Comprueba que la ruta final sea `RetroBat/emulationstation/.emulationstation/themes/es-theme-tecnotics-alubrush/theme.xml`. Evita duplicar la carpeta al descomprimir.
4. Abre RetroBat. En el menú de ajustes de interfaz, elige el conjunto de temas `es-theme-tecnotics-alubrush`.
5. Para ver los nuevos fondos en la pantalla de sistemas, utiliza la variante de fondo de consolas del tema (la opción original que carga `subsets/systembackground/batomachines.xml`). Las demás variantes originales siguen disponibles: algunas muestran vídeos, carátulas o fanart en lugar del fondo fijo.
6. Revisa Windows, MAME y FinalBurn Neo con juegos válidos. El tema solo define su aspecto: no instala emuladores, juegos ni BIOS. Usa las carpetas y extensiones reconocidas por tu versión de RetroBat.

Para revertir, selecciona el tema anterior. Esta instalación no modifica el registro, el shell de Windows ni los emuladores.

## Estructura

```text
es-theme-tecnotics-alubrush/
├── theme.xml                 # Punto de entrada XML, formato 7
├── tecnotics.xml              # Capa final de marca y logos nuevos
├── _splash.xml                # Carga de la interfaz con Tecnotics
├── gamesplash.xml             # Pantalla al cargar juegos
├── art/                      # Todos los recursos de AluBrush
│   └── tecnotics/
│       ├── logo.png          # Logo horizontal del proyecto
│       └── systems/          # Los seis archivos nuevos
├── views/                    # Menú, sistemas y vistas de juegos
├── subsets/                  # Colores, fondos, animaciones y opciones
├── layouts/                  # Ajustes por sistema y pantalla
├── lang/                     # Idiomas originales
├── resources/                # Recursos auxiliares originales
├── games/                    # Personalizaciones por juego originales
├── originales/               # Copias de todo archivo sustituido y manifiesto
├── readme.txt                # Créditos/licencia originales, íntegros
├── CREDITOS.md               # Procedencia y cambios Tecnotics
└── VALIDACION.json           # Resultado de la comprobación estática
```

Los nombres de las carpetas no son una obligación del motor. Lo obligatorio es un punto de entrada que EmulationStation pueda encontrar y rutas correctas a todos los archivos utilizados. Un conjunto puede tener un XML general y/o `theme.xml` por sistema. En este tema se conserva la organización general original.

## Reglas para modificarlo

- Usa XML de EmulationStation, nunca QML de Pegasus. Declara `<theme>` y `<formatVersion>7</formatVersion>` en los nuevos archivos incluidos.
- Conserva los `include`, `subset`, `view`, `customView`, las herencias y las condiciones originales. No reemplaces todo el tema por una pantalla mínima.
- Las rutas que empiezan por `./` se resuelven respecto del XML donde aparecen. Para recursos compartidos utiliza `${themePath}/art/...`, con `/` y sin letras de disco fijas.
- Los recursos por sistema deben coincidir con `<theme>` en `es_systems.cfg`. Windows usa `windows`, MAME `mame` y FinalBurn Neo `fbneo`; no confundas esa clave con el nombre visible o el nombre de un emulador. Comprueba los valores de la versión instalada antes de agregar otros dispositivos.
- Un logo PNG con transparencia y un fondo JPG son suficientes como recursos nuevos para un sistema que ya exista, pero hay que conectarlos al XML. Conserva además las imágenes opcionales de mandos, consolas, regiones y colecciones que ya traía AluBrush.
- En esta adaptación los fondos nuevos están tanto en `art/tecnotics/systems/<clave>.jpg` como en el destino utilizado por AluBrush `art/background/<clave>.jpg`. Las imágenes representativas también se copian a `art/consoles/<clave>.png`. La capa `tecnotics.xml`, incluida al final, fuerza los logos PNG nuevos para que no gane un SVG anterior.
- No borres recursos originales para quitar una marca visible. Conserva una copia histórica y cambia las referencias activas. No renombres claves técnicas como `retrobat`, porque participan en la selección de sistemas y vistas.
- El logo general se cambia en `art/tecnotics/logo.png`. Para cambiar un recurso nuevo, actualiza su copia en systems y el destino activo correspondiente. Para que una reconstrucción conserve cambios XML, actualiza también `scripts/tema-retrobat/tecnotics.xml`.
- Mantén créditos y licencia. No incluyas juegos ni BIOS. El README original declara condiciones no comerciales y compartir igual; se conserva tal como venía, incluida su discrepancia entre las menciones de versiones de licencia.

## Reconstruir a partir del ZIP original

Abre PowerShell en la raíz del repositorio. Necesitas el ZIP original y una carpeta con los seis archivos entregados: `FB NEO wallpaper.jpg`, `fb neo.png`, `mame_wallpaper.jpg`, `mame.png`, `windows_wallpaper.jpg`, `windows.png`.

```powershell
./scripts/Construir-Tema-RetroBat.ps1 -SourceZip 'ruta/al/es-theme-AluBrush.zip' -MediaDirectory 'ruta/a/las/imagenes' -OutputDirectory './salida/es-theme-tecnotics-alubrush'
./scripts/Validar-Tema-RetroBat.ps1 -ThemeDirectory './salida/es-theme-tecnotics-alubrush'
```

El destino debe ser nuevo: el constructor no borra ni pisa una carpeta existente. Por defecto toma el logo de `logo/tecnotics-horizontal.png`; puedes especificar otro con `-Logo`. La construcción no necesita Python ni modifica Windows. `Normalizar-Rutas-Tema.ps1` es un auxiliar que ejecuta el constructor.

El constructor corrige `lang/gr.xml` a `lang/el.xml`, las seis rutas de colores del splash, dos etiquetas de color mal formadas y las rutas compartidas de arte y fuentes. Guarda copias exactas de cada archivo original cambiado. El manifiesto contiene SHA-256 de los 2.438 archivos del ZIP, y el validador comprueba que todos se conservan, ya sea activos o en originales.

## Validar antes de distribuir

1. Ejecuta el validador: XML bien formado, includes y fuentes estáticos existentes, recursos de marca y conservación de originales.
2. Confirma que cada clave nueva tiene fondo y logo; revisa también sus referencias dinámicas en las vistas. El validador no interpreta todas las expresiones del motor.
3. Prueba en RetroBat: pantalla de carga, carrusel de sistemas, listas, rejillas, vistas Content/Tiles/Icons/Boxes/Carousel, variantes de fondo y colores, vídeos, sonidos y entrada/salida de un juego.
4. Prueba el mando, teclado, 1920×1080 y una pantalla menor. Revisa que el logo no tape controles ni información. Las distribuciones verticales y las variantes requieren revisión visual propia.
5. Revisa `es_log.txt` en la carpeta de configuración de EmulationStation por errores de carga. No declares compatibilidad completa solo porque el XML se analiza sin errores.

Estado de esta entrega: validación estática ejecutada; prueba de renderizado en RetroBat pendiente. Las referencias dinámicas a juegos, carátulas y vídeos dependen de los datos de cada instalación. El tema cambia su propia presentación y el pie del menú; no puede garantizar eliminar textos generados por el ejecutable, ventanas de emuladores o vídeos de inicio externos.

El ZIP local completo se genera en `dist/Tecnotics-AluBrush-RetroBat-completo.zip`. Por su tamaño no se versiona como archivo binario en Git: GitHub permite descargar el repositorio con todos los recursos y copiar la carpeta del tema.

## Fuentes técnicas

- [Formato de temas del EmulationStation de RetroBat](https://raw.githubusercontent.com/RetroBat-Official/emulationstation/master/THEMES.md)
- [Estructura de carpetas de RetroBat](https://wiki.retrobat.org/get-started/retrobat-folder-structure)
- [Identificadores oficiales de sistemas](https://github.com/RetroBat-Official/retrobat/blob/main/system/templates/emulationstation/es_systems.cfg)

El .gitattributes de esta adaptación desactiva la conversión de saltos de línea dentro del tema para preservar los hashes originales. Su versión de origen también se conserva en originales/sustituidos/.gitattributes.original.

