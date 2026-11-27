# Estado actual

**Turno:** libre
**Última actualización:** 2026-11-27

## En qué estamos

- **Juegos NAOMI:** los dos Capcom Vs. SNK ya funcionan en RetroBat (`roms\naomi`). Bloody Roar 3 (System 246) y Dragon Ball Zenkai Battle Royale (System 357) quedan para TeknoParrot, sin probar. Detalle en `docs/investigacion/2026-11-27-capcom-vs-snk-naomi.md`.

- **Gestor, permisos en discos de otro PC:** se recuperó el acceso a la configuración de RetroBat y a TeknoParrot en el disco revisado. El Gestor ahora distingue un emulador inaccesible de uno ausente al preparar un sistema. Pasaron 66 pruebas y se omitieron 4. Corrección en el commit 96358fb.

- **Gestor 41:** publicado con la pestaña Migrar RetroBat. Compara dos instalaciones, permite copiar sistemas o juegos elegidos con BIOS, fichas y medios, y guarda un respaldo si se elige reemplazar una ROM del destino. Se verificaron siete pruebas de migración y el arranque del portable. [Portable 41](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-41-77af9d7)

- **Gestor Arcade Tecnoticis:** el portable 40 está publicado y su arranque se verificó en GitHub Actions. Se retiró el scraper integrado. Las descargas de fichas y medios se hacen en RetroBat. En **Configurar RetroBat → Temas** se pueden listar temas, exportar e importar ZIP y retirar temas con respaldo. Se protege el activo y la importación con otro nombre conserva el original. [PR #4](https://github.com/mardiles2k18-png/tecnotic_arcade/pull/4) · [Portable 40](https://github.com/mardiles2k18-png/tecnotic_arcade/releases/tag/retrobat-manager-preview-40-a1318d5)
- **Tema AluBrush:** disponible en `main`, con los recursos y el XML verificados. Sigue pendiente la prueba visual en RetroBat.

- **Temas adaptados:** Hypertocera AI, Batocer Club Reloaded, DarkGames y Reload tienen copias ZIP con la marca Tecnotics en la carpeta de temas del Escritorio. Los cuatro pasaron por el importador del Gestor en una instalación temporal.

El [estado general del ecosistema](https://github.com/mardiles2k18-png/tecnotic_arcade/blob/main/docs/estado-proyecto.md) conserva el inventario histórico.

## Próximos pasos

1. Verificar con el portable actualizado la carga de uno o varios juegos de TeknoParrot y el aviso de acceso denegado. Probar también el Gestor en el arcade, incluida una migración entre instalaciones y la importación y retiro de un tema de prueba.
2. Probar las cuatro adaptaciones en RetroBat y revisar visualmente los logos, las pantallas de carga y cualquier marca que aparezca en pantalla.
3. Validar el arranque, el PIN y la restauración de Modo arcade en el equipo dedicado. Confirmar la edición de Windows y si TeknoParrot admite palanca y cruceta simultáneas.
4. Revisar el PR #4 y verificar el paso de una versión anterior a la 41 desde el actualizador.

## Bloqueos o dudas abiertas

Falta completar las pruebas en el arcade y revisar cómo se ven las cuatro adaptaciones en RetroBat.
