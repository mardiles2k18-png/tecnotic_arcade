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
El editor de RetroBat importa `VistaMando` directamente. `EditorMandos` se
encarga de la lectura física, la captura, la asignación y el guardado. El
canvas se adapta al espacio disponible y mide sus etiquetas en píxeles
para mantener su proporción cuando cambia el DPI. La importación estática
permite que PyInstaller incluya el paquete en el portable.

## Alcance
Xbox con 24 entradas digitales/direccionales; DirectInput genérico con hasta 128 botones, 4 POV y 8 ejes en ambos sentidos según IDs disponibles. La vista compacta de dispositivos con muchas entradas puede requerir más espacio. No se infiere la posición real de botones DirectInput. No hay medición analógica continua, circularidad, soporte PlayStation dedicado ni paneles arcade específicos todavía.

Tema configurable mediante el argumento tema (dict con claves de TEMA). No modifica estilos ttk globales. No requiere imágenes externas.

## Validación

Desde la raíz del repositorio y con pantalla disponible:

```powershell
py -3.13 -m unittest discover -s retrobat -p test_controller_studio.py -v
```

La suite comprueba ambos modos a 875×570 y 1060×660, con escalados equivalentes
a 96 y 144 DPI. Usa mandos simulados para comprobar la desconexión, las
asignaciones por jugador y los respaldos. GitHub Actions ejecuta la suite en
Windows y comprueba ambos modos sobre el ejecutable empaquetado.
