# Estado del ecosistema Tecnotics Arcade

Última actualización documental: **21 de noviembre de 2026**.

## Objetivo confirmado por Mauricio

Construir un **ecosistema de herramientas que permita crear un sistema arcade bajo Windows**. Cada herramienta debe aportar a preparar, configurar, personalizar, operar, mantener, recuperar o reproducir ese sistema.

La experiencia final buscada es encender el arcade, ver Tecnotics, elegir juegos con palancas y botones y disponer de acceso a Windows para mantenimiento. El tema, el gestor y el configurador se complementan; ninguno equivale por sí solo al sistema completo.

## Versiones vigentes confirmadas por Mauricio

Confirmadas directamente por Mauricio el 21 de noviembre de 2026:

- **Gestor RetroBat: 11** (publicado como Preview 11).
- **Lanzador Tecnotics: 1.2.0**, destinado a ocultar Windows durante el uso del arcade; incluye el configurador de arranque y la bienvenida/modo arcade.

Son herramientas complementarias con versiones independientes. El objetivo de ocultar Windows no sustituye las pruebas de arranque, mantenimiento y reversión en la edición instalada de Windows.

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
| Gestor RetroBat 11 | Importar juegos Windows y ROMs; categorías, biblioteca, títulos, comparación, duplicados, BIOS, temas, intro y retrobat.ini | codex/retrobat-manager: retrobat/gestor-retrobat.pyw y módulos gestor_*.py | Versión 11 confirmada por Mauricio y publicada como Preview 11. GitHub Actions verificó compilación y apertura de la ventana; no equivale a probar todas las operaciones con juegos reales |
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

## Evidencias de la revisión

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

La IA debe empezar leyendo AGENTS.md, README.md y este archivo en main; comprobar después las ramas y los archivos pertinentes. Al terminar una tarea autorizada, actualizar decisiones, estado, evidencia y próximos pasos cuando hayan cambiado. No presentar como probado lo que solo está implementado o compilado.

## Antecedentes

docs/plan-windows-retrobat.md conserva el plan inicial. Sus casillas no representan automáticamente el estado actual y algunas decisiones de arranque difieren del configurador posterior. Las secciones de Batocera del README son históricas. El AGENTS.md anterior del checkout local describía Pegasus como arquitectura principal; esa indicación queda sustituida por el objetivo Windows confirmado por Mauricio y por este estado documentado.

Prototipo personal/familiar; no se incluyen juegos ni BIOS en el repositorio.
