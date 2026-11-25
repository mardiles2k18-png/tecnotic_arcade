# Gestor Arcade Tecnoticis 33 Implementation Plan

> Ejecutar con la skill executing-plans y verificar cada tarea antes de publicar.

**Objetivo** — Entregar una aplicación portable para Windows con las funciones del Gestor y el Configurador.

**Arquitectura** — Usar el Gestor como aplicación principal. Incorporar los componentes del modo arcade a su compilación y compartir el dibujo vectorial del mando mediante Controller Studio.

**Tecnologías** — Python, Tkinter, PowerShell 5.1, C# y GitHub Actions.

**Diseño** — [Diseño aprobado](2026-11-25-gestor-arcade-33-diseno.md).

## 1. Nombre y versión

- [ ] Centralizar Gestor Arcade Tecnoticis y la versión 33 en código consumido por la aplicación y el compilador del portable.
- [ ] Actualizar el título, el ejecutable y la configuración de publicación en `.github/workflows/gestor-retrobat-portable.yml`.
- [ ] Verificar que el nombre y el número coincidan en la ventana, el ejecutable y el artefacto del flujo de compilación.

## 2. Modo arcade

- [ ] Revisar las operaciones de `configurador/scripts/` y el contrato con `modo-arcade/TecnoticsArcade.cs`. Conservar la detección de una instalación 1.2.0 existente.
- [ ] Añadir la pestaña **Modo arcade** en `retrobat/gestor-retrobat.pyw`, con lectura de estado, prueba de bienvenida, configuración, activación y restauración. Empaquetar los recursos y comprobar que la bienvenida instalada persiste al cerrar el portable.
- [ ] Verificar la apertura sin elevación, la cancelación de UAC, la selección de RetroBat y los errores de los scripts. Validar activación, acceso a Windows y reversión en un entorno Windows dedicado.

## 3. Vista de mandos

- [ ] Redibujar la vista frontal en `retrobat/controller_studio/__init__.py`, con estados de entrada y asignación visibles. Mantener la geometría interactiva alineada con el dibujo al redimensionar.
- [ ] Comprobar las dos vistas y la demo con `retrobat/test_controller_studio.py` y una revisión visual. Probar botones, gatillos, palancas, cruceta y cambio de tamaño con perfiles XInput y DirectInput.
- [ ] Probar la vista con el mando real en Ultra Street Fighter IV y comprobar que los perfiles guardados siguen cargando.

## 4. Actualización desde la aplicación

- [ ] Publicar el número de versión, la plataforma, el portable y su SHA-256 desde el flujo oficial. Usar una fuente accesible desde el equipo arcade y validar que el paquete corresponde al Gestor y a Windows x64.
- [ ] Al iniciar, comparar los números de versión en segundo plano y ofrecer la actualización solo cuando exista una versión superior compatible. Permitir posponerla y seguir usando el Gestor sin conexión.
- [ ] Descargar a un temporal, verificar la integridad y usar un proceso auxiliar para sustituir el ejecutable cerrado. Conservar los perfiles y ajustes, mantener una copia recuperable, y reabrir la aplicación al terminar.
- [ ] Probar aviso y aceptación con dos compilaciones numeradas. Cubrir versión igual o anterior, falta de conexión, descarga incompleta, integridad inválida, archivo bloqueado y recuperación del ejecutable anterior. Comprobar que el Gestor actualizado abre con la configuración previa.

## 5. Entrega

- [ ] Ejecutar la suite, construir y abrir el portable en Windows x64.
- [ ] Registrar resultados, actualizar la bitácora de esta sesión y publicar la versión 33 después de comprobar el flujo integrado.
