# TECNOTICS Controller Studio · 0.1.0

Biblioteca gráfica Python/Tkinter independiente de RetroBat. Sin dependencias externas ni acceso al hardware, archivos XML o red. Primera pieza de un futuro TECNOTICS UI Kit.

## Demo
Desde la carpeta retrobat:
```powershell
py -3.13 -m controller_studio.demo
```
Los eventos son simulados con el ratón. Verde = entrada activa; cian = selección.

## Integración
Copiar el paquete controller_studio junto al código de cualquier aplicación Python/Tkinter, o incluir su carpeta padre en la ruta de importación. Importar:
```python
from controller_studio import VistaMando
vista = VistaMando(panel, elegir=asignar_boton)
vista.pack(fill="both", expand=True)
vista.dibujar(mando, nombres)
vista.iluminar({"south"}, "south")
```
mando debe exponer api ("XInput" o DirectInput); para DirectInput, botones y crucetas. nombres es un mapping de IDs válidos a etiquetas. elegir recibe el ID sin modificarlo. dibujar reinicia la selección. iluminar recibe un iterable de IDs activos y un ID seleccionado opcional. Ejecutar todos los métodos en el hilo Tk.

## RetroBat / TeknoParrot
El contrato coincide con VistaMando de gestor_teknoparrot_editor_ui.py. Para integrar, sustituir la clase local por la importación anterior. Conservar EditorMandos, lectura física, captura, guardado y respaldos XML. Revisar el tamaño del panel: el canvas solicita 420x320 y escala al espacio disponible. Probar a 875x570 y 1060x660 y con DPI de Windows. El import estático permite a PyInstaller detectar el paquete; revisar el proceso de compilación portable antes de publicar.

## Alcance
Xbox con 24 entradas digitales/direccionales; DirectInput genérico con hasta 128 botones, 4 POV y 8 ejes en ambos sentidos según IDs disponibles. La vista compacta de dispositivos con muchas entradas puede requerir más espacio. No se infiere la posición real de botones DirectInput. No hay medición analógica continua, circularidad, soporte PlayStation dedicado ni paneles arcade específicos todavía.

Tema configurable mediante el argumento tema (dict con claves de TEMA). No modifica estilos ttk globales. No requiere imágenes externas.

## Validación pendiente
Ejecutar demo, comprobar clics y estados, probar desconexión/reconexión mediante el lector existente y validar que las asignaciones y respaldos XML sean idénticos a los de la versión anterior. Verificar compilación Python 3.13/PyInstaller en Windows x64. No publicar una release hasta completar esas pruebas.
