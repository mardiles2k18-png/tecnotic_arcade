# Gestor Arcade Tecnoticis 33

Diseño aprobado el 25 de noviembre de 2026.

El Gestor será la aplicación única para preparar y operar el arcade. La versión 33 continúa la numeración de las vistas previas del Gestor. Una sola fuente de versión alimentará la interfaz, el nombre del ejecutable y la publicación.

La pestaña **Modo arcade** integrará las funciones del Configurador 1.2.0. Mostrará el estado del equipo y permitirá probar la bienvenida, configurar el arranque y el PIN, activar el modo arcade y restaurar el arranque anterior. Los ajustes de Windows se mantendrán en esa sección con sus acciones de restauración. Se solicitará elevación para las operaciones que la requieran. El gestor continuará ofreciendo la gestión de la biblioteca, los emuladores y los mandos.

La vista frontal renovada del mando se compartirá entre **Mandos** y el editor de **TeknoParrot**. La geometría dibujada se adaptará al tamaño del panel. Los controles mostrarán estados diferenciados al recibir una entrada y al seleccionarse para asignación. Se preservarán los identificadores de controles y las asignaciones guardadas.

## Actualización desde el Gestor

Al abrir, el Gestor consultará en segundo plano la última publicación compatible para Windows x64. Si la versión publicada es mayor, mostrará «Hay una versión nueva disponible. ¿Deseas actualizar?» con ambas versiones y las opciones **Actualizar** y **Ahora no**. La aplicación seguirá disponible si se pospone la actualización o si el equipo está sin conexión.

Al aceptar, descargará el portable oficial y verificará su integridad. Un proceso auxiliar reemplazará el ejecutable después de que el Gestor se cierre y abrirá la nueva versión. La ruta de lanzamiento se conservará para los accesos directos. Los datos de usuario permanecerán fuera del reemplazo y se guardará una copia recuperable del ejecutable anterior.

La versión 33 será el punto de partida de este mecanismo. Desde la Vista previa 32 se necesitará una descarga inicial desde la publicación oficial.
