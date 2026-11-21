# Tecnotics Arcade — instrucciones para agentes

## Objetivo y lectura inicial

Mauricio (Tecnotics, Vallenar, Chile) define el objetivo principal así: **construir un ecosistema de herramientas para crear, configurar, personalizar y mantener un sistema arcade bajo Windows**. Confirmado el 21 de noviembre de 2026.

Antes de trabajar, leer README.md y docs/estado-proyecto.md. Consultar la rama main y comprobar la rama real del checkout: la predeterminada de GitHub puede ser otra. Las instrucciones explícitas más recientes de Mauricio prevalecen sobre documentos antiguos.

Responder siempre en español, con pasos concretos y archivos listos para usar. Mauricio programó en Visual Basic y Delphi hace unos veinte años: explicar conceptos nuevos sin darlos por sabidos.

## Versiones vigentes confirmadas por Mauricio

- **Gestor RetroBat: versión 11.** La publicación de descarga usa el nombre Preview 11.
- **Lanzador Tecnotics para ocultar Windows: versión 1.2.0.** Incluye el configurador y la bienvenida/modo arcade.
- No confundir ambas herramientas ni sus números de versión. Antes de proponer actualizaciones, comprobar código y publicaciones; conservar estas referencias hasta una actualización confirmada.

## Dirección del producto

- Cada herramienta debe tener una función concreta dentro del ecosistema: preparación de Windows, administración de biblioteca y emuladores, identidad visual, arranque y controles, mantenimiento, recuperación o despliegue.
- Windows es la plataforma objetivo; RetroBat/EmulationStation es el componente de menú que se está personalizando actualmente.
- La experiencia buscada muestra Tecnotics al encender y permite operar con palancas/botones. Debe existir un acceso de mantenimiento a Windows, con PIN en el configurador actual.
- El tema es una parte del producto; el gestor de juegos y el configurador de arranque tienen funciones diferentes y complementarias.
- Batocera y Pegasus son antecedentes/prototipos separados. No recuperar automáticamente la antigua instrucción de utilizar Pegasus y nunca ejecutar RetroBat.
- La edición definitiva de Windows, los equipos de destino y la integración final deben comprobarse en el estado del proyecto; no inventar decisiones cerradas.
- Prototipo personal/familiar. No incluir juegos, ROMs ni BIOS en Git. Antes de cualquier distribución comercial, revisar las licencias de los componentes.

## Trabajo seguro y verificable

- Distinguir equipo dedicado y uso portátil: nunca aplicar cambios de shell, inicio automático o registro a los PCs anfitriones solo por ejecutar una herramienta portátil.
- Antes de cambios de registro, shell o arranque: respaldo y procedimiento/script de reversión. No ejecutar instaladores ni optimizadores solo para leer o revisar su código.
- Comprobar rutas reales y versión instalada de RetroBat antes de ejecutar scripts. Algunos scripts antiguos contienen rutas absolutas específicas de otro equipo.
- Probar cada juego y emulador por separado antes de integrarlo al menú.
- Registrar por separado: código implementado, binario compilado, prueba automática, prueba manual y pendiente. La existencia de un archivo o un check del README no prueba que funcione hoy en una máquina.
- Para temas RetroBat usar XML de EmulationStation y la guía docs/temas-retrobat.md. Conservar recursos originales, atribuciones y copias de lo modificado. QML de Pegasus es otro formato.
- Mantener las rutas de recursos del tema portátiles, con / y sin letras de disco fijas. En el prototipo Pegasus conservar rutas relativas o {env.TECNOTICS_ROOT}.
- No mezclar ramas, reemplazar aplicaciones ni cambiar la rama predeterminada por el solo hecho de documentar el estado.

## Continuidad

Al completar cambios autorizados, actualizar README.md y docs/estado-proyecto.md si cambian objetivos, arquitectura, versiones, ubicación de herramientas, pruebas o pendientes. Incluir evidencia verificable y fecha. No marcar pendientes como resueltos sin comprobarlos.
