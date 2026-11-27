# Scraping de juegos para Gestor Arcade Tecnoticis

Evaluación técnica · 25 de noviembre de 2026

## Recomendación

El Gestor puede buscar fichas, logos, imágenes y vídeos y guardarlos en el catálogo que usa RetroBat. Conviene empezar con una acción **Buscar ficha y medios…** en Biblioteca, por juego, con vista previa y elección de qué guardar. La opción preferida es integrar ScreenScraper mediante su API. Skyscraper es el primer candidato para una prueba comparativa en Windows y screenscraper-cli ofrece un cliente pequeño y permisivo como referencia. La cobertura de TeknoParrot y juegos de Windows debe medirse con entradas reales antes de activar el trabajo por lotes.

## Qué permite RetroBat y qué reutilizar

RetroBat documenta scraping individual y por sistema, descarga de textos, carátulas, logos, imágenes, vídeos y otros recursos. Guarda los medios dentro de la carpeta de ROM del sistema y admite nombres convencionales para archivos locales. La salida del Gestor debe comprobarse con la versión instalada de RetroBat y con AluBrush, ya que el tema decide qué recursos aparecen. [Documentación de RetroBat](https://wiki.retrobat.org/navigation/scraping-and-metadata)

El Gestor ya ofrece la selección por sistema y por juego en retrobat/gestor_biblioteca_ui.py. Las funciones catalogo_juegos y guardar_catalogo, en retrobat/gestor_biblioteca.py, indexan las entradas por ruta, detectan modificaciones concurrentes al catálogo y sustituyen el XML preparado. gestor_duplicados.py contiene el sistema existente de respaldos. El diseño debe reutilizar estos puntos y comprobar la integración de archivos de medios y XML para que una interrupción no deje referencias rotas. La edición del catálogo debe preservar rutas, favoritos, contadores, nombres personalizados y campos que RetroBat gestione por su cuenta.

## Alternativas

| Opción | Evidencia | Encaje |
|---|---|---|
| ScreenScraper API | La API documenta identificación por sistema, nombre o huella, metadatos, imágenes y vídeo. Hay credenciales de desarrollador y límites de concurrencia y cuota. [API oficial](https://www.screenscraper.fr/webapi2.php) | Primera opción para un flujo nativo. Permite controlar la selección, la descarga y la escritura en la biblioteca existente. |
| Gemba/Skyscraper | CLI de C++/Qt con licencia GPL-3.0. Documenta Windows y un perfil de salida para RetroBat. Tiene caché y varios proveedores. [Repositorio](https://github.com/Gemba/skyscraper) · [Salida para RetroBat](https://gemba.github.io/skyscraper/FRONTENDS/#retrobat) | Mejor candidato para comparar cobertura y formato con un catálogo temporal. Si se distribuye con el Gestor, revisar licencia, dependencias de Qt, tamaño y actualización del auxiliar. |
| Dakaric/screenscraper-cli | Cliente Go con licencia MIT. Documenta Windows, salida JSON y descarga de imágenes, logos y vídeo. Usa credenciales propias de ScreenScraper. [Repositorio](https://github.com/Dakaric/screenscraper-cli) | Referencia para la API y candidato a una prueba como proceso auxiliar. Su madurez y manejo de credenciales y fallos se deben validar antes de empaquetarlo. |
| Gnzlt/pySkraper | Herramienta Python GPL-3.0 o posterior. Escribe medios y catálogo de EmulationStation. Su README indica que Windows está sin probar. [Repositorio](https://github.com/Gnzlt/pySkraper) | Referencia cercana al lenguaje del Gestor. La compatibilidad en Windows y la licencia pesan en una incorporación directa. |
| SteamGridDB | Catálogo de portadas, fondos, logos e iconos. [API oficial](https://www.steamgriddb.com/api/v2) | Complemento para juegos de PC y arte alternativo. La propuesta mantiene ScreenScraper para el vídeo y las fichas. |

La licencia del programa y los permisos del proveedor sobre los medios se deben verificar por separado si Tecnotics distribuye equipos o paquetes con arte preinstalado. El flujo de prueba descarga los recursos a la instalación local y mantiene las credenciales fuera del repositorio y los registros.

## Flujo propuesto

1. En **Biblioteca**, elegir un juego y pulsar **Buscar ficha y medios…**. Mostrar las coincidencias con título, plataforma y región.
2. Dar preferencia a una coincidencia por huella cuando sea aplicable. Para accesos directos de Windows y perfiles de TeknoParrot, buscar por título y plataforma, mostrar candidatos y pedir confirmación cuando haya duda.
3. Mostrar una vista previa de logo, carátula, captura y disponibilidad del vídeo. Guardar únicamente los elementos elegidos. Por defecto, completar campos faltantes y conservar arte y textos personalizados.
4. Guardar en carpetas compatibles con RetroBat, actualizar la entrada del juego con rutas relativas y respaldar los cambios. Si RetroBat tiene abierto el mismo catálogo, comprobar cómo evitar que sobrescriba la actualización.
5. Cuando el flujo por juego quede validado, ofrecer **Buscar medios faltantes** por sistema, con progreso, cancelación, pausa por cuota y reanudación.

## Prueba que decide la implementación

Usar una copia de una biblioteca con ejemplos de MAME o FBNeo, una consola, TeknoParrot y Windows. Incluir títulos repetidos, regiones, juegos con arte personalizado y entradas sin coincidencia. Comparar ScreenScraper y Skyscraper en identificación correcta, disponibilidad de logos y vídeos, rutas generadas y visualización en AluBrush. Probar también cancelación, cuota, descarga dañada, falta de espacio y edición concurrente de gamelist.xml. Usar fixtures del proveedor para pruebas repetibles y limitar las consultas reales a una muestra.

La evaluación se hizo con documentación oficial y revisión del repositorio local. Quedan por verificar las credenciales de desarrollo, la cobertura efectiva de los juegos del arcade y la compatibilidad de los vídeos con el equipo y tema de destino.
