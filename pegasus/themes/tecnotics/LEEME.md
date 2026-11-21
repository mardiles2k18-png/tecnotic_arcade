# Tema Tecnotics basado en AluBrush

## Instalar
1. Cierra Pegasus.
2. Copia la carpeta completa `pegasus/themes/tecnotics` del proyecto a `Pegasus/config/themes/tecnotics` dentro de tu carpeta portátil Tecnotics.
3. Abre Pegasus y selecciona **Tecnotics AluBrush** en sus ajustes de tema. Si ya estaba seleccionado, F5 recarga los archivos.

El XML de AluBrush es de EmulationStation y no se puede usar directamente en Pegasus. Esta es una adaptación QML con fondos originales para PS2, PS3, PS4, Switch y Xbox 360. Se agregan FinalBurn Neo, MAME y Windows con las seis imágenes entregadas por Mauricio. Otros sistemas usan fondo neutro. No se ejecuta ni modifica RetroBat.

## Logo
Se incorpora el logo horizontal existente en `logo/tecnotics-horizontal.png` del repositorio del proyecto, copiado a `art/tecnotics-logo.png`. Para actualizarlo, reemplaza ese PNG manteniendo el nombre.

## Uso
- Izquierda/derecha: cambiar sistema. También funcionan los botones configurados en Pegasus como página anterior/siguiente.
- Arriba/abajo: elegir juego.
- Aceptar configurado en Pegasus: lanzar juego (normalmente A o Enter).
- Mouse: seleccionar, doble clic para jugar; botones inferiores para cambiar sistema o jugar.
- Atrás/Escape queda disponible para el menú de Pegasus.

Las carátulas se toman de `game.assets.boxFront`, con captura como alternativa. Si no hay imagen, se muestra la consola. Sin colecciones se muestra una bienvenida; no se intenta ejecutar ningún juego. Los lanzamientos dependen de los metadatos y de probar cada emulador por separado.

## Estado de validación
Recursos extraídos del ZIP y referencias de archivos verificadas. API consultada: https://pegasus-frontend.org/docs/themes/api/ . Instalación: https://pegasus-frontend.org/docs/user-guide/installing-themes/ . Todavía falta la prueba real en Pegasus con mando, carátulas y juegos: no se encontró un ejecutable de Pegasus ni herramientas QML en el entorno revisado. No se considera una versión final validada.

Los textos de la interfaz propia usan Tecnotics. Las atribuciones históricas se conservan en CREDITOS.md y credits/. Esto no cambia pantallas de los emuladores ni sus menús.


## Sistemas nuevos (versión 0.3)

| Colección | shortname en los metadatos | Fondo | Logo representativo |
|---|---|---|---|
| FinalBurn Neo | fbneo | art/background/fbneo.jpg | art/consoles/fbneo.png |
| MAME | mame | art/background/mame.jpg | art/consoles/mame.png |
| Windows | windows | art/background/windows.jpg | art/consoles/windows.png |

Las imágenes se copian sin modificar, conservando su transparencia original. El logo representativo aparece cuando el juego no tiene carátula o captura. Estos tres sistemas ya están reconocidos por el tema; para que aparezcan en Pegasus deben existir colecciones con juegos y el shortname indicado. No se crean juegos ficticios ni se añaden comandos de ejecución sin conocer los ejecutables instalados. Antes de integrar lanzamientos, probar MAME, FinalBurn Neo y cada juego de Windows por separado.
