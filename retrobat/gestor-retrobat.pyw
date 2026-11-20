"""Gestor de escritorio Tecnotics para RetroBat."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import filecmp
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from time import monotonic
import webbrowser
from xml.etree.ElementTree import ParseError

PORTABLE = getattr(sys, "frozen", False)
RECURSOS = Path(sys._MEIPASS) if PORTABLE else Path(__file__).resolve().parents[1]
if PORTABLE:
    # Resolve Tcl/Tk from the extracted bundle before loading the Tcl library.
    os.chdir(RECURSOS)
    os.environ["TCL_LIBRARY"] = "_tcl_data"
    os.environ["TK_LIBRARY"] = "_tk_data"

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from gestor_bios import (NO_REQUIERE_BIOS, RELEASES_RETROBAT, biblioteca_instalada, buscar_bios_publicas,
                         comprobar_actualizacion, enlace_busqueda, importar_bios_locales, revisar_bios_mame)
from gestor_core import (CARPETAS_MULTIMEDIA, IMPORTACION_MANUAL, NUEVO_LISTO, NUEVO_PENDIENTE,
                         REPETIDO_ORIGEN, YA_INSTALADO,
                         accesos_windows, buscar_juegos, clave_juego, copiar, copiar_juego_windows, copiar_rom,
                         descargar_firmware_ps3, detectar_sistema_externo, discos_mame, duplicados, editar_ini,
                         estado_windows, nombre_seguro, nombres_instalados, revisar_bios,
                         requiere_importacion_manual, shortcut, sistemas_instalados, tamanio_copia,
                         ubicacion_juego_windows)

def duracion(segundos):
    segundos = max(0, round(segundos))
    horas, resto = divmod(segundos, 3600)
    minutos, segundos = divmod(resto, 60)
    return f"{horas} h {minutos:02d} min" if horas else f"{minutos:02d}:{segundos:02d}"


def copiar_con_progreso(origen, destino, informar, fase):
    total = tamanio_copia(origen) + 1
    hecho = 0

    def avanzar(cantidad):
        nonlocal hecho
        hecho += cantidad
        informar(min(hecho, total - 1), total, fase)

    informar(0, total, fase)
    copiar(origen, destino, avanzar)


class Gestor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tecnotics Arcade · Gestor de RetroBat · Vista previa 6")
        self.geometry("1100x720")
        self.minsize(850, 580)
        self.raiz = tk.StringVar()
        self.origen = tk.StringVar()
        self.categoria = tk.StringVar()
        self.sistema = tk.StringVar()
        self.estado = tk.StringVar(value="Selecciona tu instalación de RetroBat.")
        self.detalle_progreso = tk.StringVar()
        self.version_disponible = tk.StringVar(value="Elige la instalación para comprobar su versión.")
        self.candidato = tk.StringVar()
        self.sistemas = {}
        self.filas = {}
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.executor_version = ThreadPoolExecutor(max_workers=1)
        self.consulta_version = None
        self.revision_version = None
        self.estados_bios = {}
        self.ocupado = False
        self.revision_pendiente = None
        self.consulta_pendiente = None
        self.origen_detectado = None
        self.oferta_importar = False
        self.preferencias = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / (
            "TecnoticsArcade"
        ) / "gestor-retrobat.json"

        logos = RECURSOS / "logo"
        logo_horizontal = tk.PhotoImage(file=logos / "tecnotics-horizontal.png")
        self.logo = logo_horizontal.subsample(7)
        logo_vertical = tk.PhotoImage(file=logos / "tecnotics-vertical.png")
        self.icono = logo_vertical.subsample(5)
        self.iconphoto(True, self.icono)

        cabecera = ttk.Frame(self, padding=(16, 8, 16, 0))
        cabecera.pack(fill="x")
        ttk.Label(cabecera, image=self.logo).pack(side="left")
        ttk.Label(cabecera, text="Gestor de RetroBat", font=("Segoe UI", 18, "bold")).pack(
            side="left", padx=(16, 0)
        )
        version = ttk.Frame(cabecera)
        version.pack(side="right", padx=(8, 0))
        ttk.Label(version, textvariable=self.version_disponible, wraplength=440).pack(anchor="e")
        ttk.Button(version, text="Versiones de RetroBat", command=lambda: webbrowser.open(RELEASES_RETROBAT)).pack(
            anchor="e"
        )

        panel = ttk.Frame(self, padding=16)
        panel.pack(fill="both", expand=True)
        panel.columnconfigure(1, weight=1)
        panel.rowconfigure(4, weight=1)
        self.carpeta(panel, 0, "Carpeta de RetroBat de este PC", self.raiz,
                     lambda: self.cargar_sistemas(guardar=True))
        self.carpeta(panel, 1, "Origen de los juegos a importar", self.origen, self.detectar_origen)
        ttk.Label(panel, text="Sistema").grid(row=2, column=0, sticky="w")
        self.selector = ttk.Combobox(panel, textvariable=self.sistema, state="readonly")
        self.selector.grid(row=2, column=1, sticky="ew", padx=8, pady=4)
        ttk.Label(panel, text="Categoría en RetroBat (opcional)").grid(row=3, column=0, sticky="w")
        categorias = ttk.Frame(panel)
        categorias.grid(row=3, column=1, sticky="ew", padx=8, pady=4)
        self.selector_categoria = ttk.Combobox(categorias, textvariable=self.categoria)
        self.selector_categoria.pack(side="left", fill="x", expand=True)
        ttk.Button(categorias, text="Nueva categoría…", command=self.crear_categoria).pack(side="right", padx=(6, 0))
        ttk.Button(panel, text="Verificar juegos", command=self.previsualizar).grid(row=3, column=2)

        tabla = ttk.Frame(panel)
        tabla.grid(row=4, column=0, columnspan=3, sticky="nsew", pady=8)
        self.lista = ttk.Treeview(tabla, columns=("juego", "archivo", "estado"), show="headings")
        for columna, titulo, ancho in (("juego", "Juego", 250), ("archivo", "Archivo de origen", 460),
                                       ("estado", "Estado", 190)):
            self.lista.heading(columna, text=titulo)
            self.lista.column(columna, width=ancho)
        scroll = ttk.Scrollbar(tabla, command=self.lista.yview)
        self.lista.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.lista.pack(fill="both", expand=True)
        self.lista.bind("<<TreeviewSelect>>", self.mostrar_candidatos)
        self.lista.tag_configure(YA_INSTALADO, foreground="#14704b")
        self.lista.tag_configure(NUEVO_LISTO, foreground="#0d5795")
        self.lista.tag_configure(NUEVO_PENDIENTE, foreground="#805400")
        self.lista.tag_configure(REPETIDO_ORIGEN, foreground="#805400")

        ttk.Label(panel, text="Ejecutable de la fila").grid(row=5, column=0, sticky="w")
        self.ejecutables = ttk.Combobox(panel, textvariable=self.candidato, state="readonly")
        self.ejecutables.grid(row=5, column=1, sticky="ew", padx=8)
        self.ejecutables.bind("<<ComboboxSelected>>", self.elegir_ejecutable)
        self.boton_importar = ttk.Button(panel, text="Importar nuevos", state="disabled", command=self.importar)
        self.boton_importar.grid(row=5, column=2, sticky="ew")

        herramientas = ttk.Frame(panel)
        herramientas.grid(row=6, column=0, columnspan=3, sticky="w", pady=12)
        for titulo, accion in (("Biblioteca de este PC", self.ver_biblioteca), ("Duplicados", self.ver_duplicados),
                               ("Verificar BIOS", self.bios),
                               ("Instalar intro", self.intro), ("Crear tema", self.tema),
                               ("Editar tema", self.editar_tema), ("Configurar RetroBat", self.configurar)):
            ttk.Button(herramientas, text=titulo, command=accion).pack(side="left", padx=(0, 6))
        ttk.Label(panel, textvariable=self.estado).grid(row=7, column=0, columnspan=3, sticky="w")
        self.barra = ttk.Progressbar(panel, maximum=100)
        self.barra.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(6, 2))
        ttk.Label(panel, textvariable=self.detalle_progreso).grid(row=9, column=0, columnspan=3, sticky="w")
        for variable in (self.raiz, self.origen, self.sistema, self.categoria):
            variable.trace_add("write", self.cambio_revision)
        self.sistema.trace_add("write", self.cambio_sistema)
        self.restaurar_instalacion()

    def destroy(self):
        for pendiente in (self.revision_pendiente, self.consulta_pendiente, self.consulta_version):
            if pendiente is not None:
                self.after_cancel(pendiente)
        self.executor.shutdown(wait=False, cancel_futures=True)
        self.executor_version.shutdown(wait=False, cancel_futures=True)
        super().destroy()

    def restaurar_instalacion(self):
        try:
            datos = json.loads(self.preferencias.read_text(encoding="utf-8"))
            raiz = Path(datos["retrobat"])
            if not (raiz / "retrobat.exe").is_file():
                return
        except (OSError, ValueError, KeyError, TypeError):
            return
        self.raiz.set(raiz.as_posix())
        self.cargar_sistemas()

    def guardar_instalacion(self, raiz):
        self.preferencias.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=self.preferencias.parent) as temporal:
            archivo = Path(temporal) / self.preferencias.name
            archivo.write_text(json.dumps({"retrobat": raiz.resolve().as_posix()}, ensure_ascii=False), encoding="utf-8")
            archivo.replace(self.preferencias)

    def verificar_version(self, raiz):
        if self.consulta_version is not None:
            self.after_cancel(self.consulta_version)
        if self.revision_version is not None:
            self.revision_version.cancel()
        self.version_disponible.set("Comprobando actualizaciones estables de RetroBat…")
        consulta = self.executor_version.submit(comprobar_actualizacion, raiz)
        self.revision_version = consulta

        def mostrar():
            self.consulta_version = None
            if not consulta.done():
                self.consulta_version = self.after(180, mostrar)
            elif Path(self.raiz.get()) == raiz:
                try:
                    texto, _ = consulta.result()
                except Exception:
                    texto = "No se pudo comprobar la actualización de RetroBat."
                self.version_disponible.set(texto)

        self.consulta_version = self.after(180, mostrar)

    def cambio_sistema(self, *_):
        self.categoria.set("")
        self.cargar_categorias()

    def cargar_categorias(self):
        sistema = self.sistemas.get(self.sistema.get())
        nombres = []
        if sistema and sistema.carpeta.is_dir():
            nombres = sorted(
                (carpeta.name for carpeta in sistema.carpeta.iterdir()
                 if carpeta.is_dir() and not carpeta.name.startswith(".")
                 and carpeta.name.casefold() not in CARPETAS_MULTIMEDIA
                 and carpeta.suffix.lower() not in sistema.extensiones
                 and not (sistema.es_mame and any(
                     carpeta.with_name(carpeta.name + ext).is_file() for ext in (".zip", ".7z")))),
                key=str.casefold,
            )
        self.selector_categoria.configure(values=nombres)

    def crear_categoria(self):
        sistema = self.sistemas.get(self.sistema.get())
        if self.ocupado:
            return
        if not sistema:
            messagebox.showinfo("Nueva categoría", "Selecciona primero el sistema de RetroBat.", parent=self)
            return
        nombre = simpledialog.askstring("Nueva categoría", f"Nombre de la categoría de {sistema.nombre}",
                                        initialvalue=self.categoria.get(), parent=self)
        if not nombre:
            return
        try:
            nombre = nombre_seguro(nombre.strip())
            if (nombre.startswith(".") or nombre.casefold() in CARPETAS_MULTIMEDIA
                    or Path(nombre).suffix.lower() in sistema.extensiones):
                raise ValueError("Elige un nombre que RetroBat pueda mostrar como carpeta de juegos.")
        except ValueError as error:
            messagebox.showerror("Nueva categoría", str(error), parent=self)
            return

        def terminar(_):
            if self.sistemas.get(self.sistema.get()) == sistema:
                self.cargar_categorias()
                self.categoria.set(nombre)
            messagebox.showinfo("Categoría lista",
                                "Importa juegos a esta categoría y actualiza la lista de juegos en RetroBat.",
                                parent=self)

        destino = sistema.carpeta / nombre
        self.ejecutar(lambda: destino.mkdir(parents=True, exist_ok=True), terminar, "Creando categoría…")

    def carpeta(self, panel, fila, titulo, variable, despues=None):
        def elegir():
            carpeta = filedialog.askdirectory(initialdir=variable.get() or None)
            if carpeta:
                variable.set(carpeta)
                if despues:
                    despues()
        ttk.Label(panel, text=titulo).grid(row=fila, column=0, sticky="w")
        ttk.Entry(panel, textvariable=variable, state="readonly").grid(
            row=fila, column=1, sticky="ew", padx=8, pady=4)
        ttk.Button(panel, text="Elegir carpeta", command=elegir).grid(row=fila, column=2, sticky="ew")

    def limpiar(self):
        self.lista.delete(*self.lista.get_children())
        self.filas.clear()
        self.mostrar_candidatos()
        self.boton_importar.state(["disabled"])

    def parametros_revision(self):
        return self.raiz.get(), self.origen.get(), self.sistema.get(), self.categoria.get().strip()

    def detectar_origen(self):
        self.origen_detectado = None
        self.oferta_importar = False
        if not self.sistemas or not self.origen.get():
            return
        try:
            sistema = detectar_sistema_externo(Path(self.origen.get()), self.raiz_retrobat(), self.sistemas)
        except (OSError, ValueError) as error:
            self.estado.set(str(error))
            return
        if sistema:
            if self.sistema.get() != sistema:
                self.sistema.set(sistema)
            self.origen_detectado = self.parametros_revision()[:3]
            self.oferta_importar = True

    def cambio_revision(self, *_):
        self.limpiar()
        sistema = self.sistemas.get(self.sistema.get())
        texto = "Importar nuevos" if sistema and sistema.identificador == "windows" else "Importar seleccionados"
        self.boton_importar.configure(text=texto)
        if self.revision_pendiente is not None:
            self.after_cancel(self.revision_pendiente)
        self.revision_pendiente = self.after(350, self.revision_automatica)

    def revision_automatica(self):
        self.revision_pendiente = None
        raiz, origen, sistema, _ = self.parametros_revision()
        if raiz and origen and sistema in self.sistemas:
            if self.ocupado:
                self.revision_pendiente = self.after(350, self.revision_automatica)
            else:
                self.previsualizar(automatica=True)
        elif not self.ocupado and raiz:
            self.estado.set("Elige la carpeta donde guardas los juegos que quieres cargar a este RetroBat.")

    def actualizar_resumen(self):
        estados = [fila[3] for fila in self.filas.values()]
        listos = estados.count(NUEVO_LISTO)
        instalados = estados.count(YA_INSTALADO)
        pendientes = len(estados) - listos - instalados
        repetido_seleccionado = any(self.filas[item][3] == REPETIDO_ORIGEN
                                     for item in self.lista.selection() if item in self.filas)
        self.boton_importar.state(["!disabled" if listos or repetido_seleccionado else "disabled"])
        resumen = f"{instalados} ya en RetroBat · {listos} nuevos listos · {pendientes} por revisar"
        if REPETIDO_ORIGEN in estados:
            resumen += " · Para repetidos, selecciona una copia por juego."
        return resumen

    def raiz_retrobat(self):
        raiz = Path(self.raiz.get())
        if not self.raiz.get() or not (raiz / "retrobat.exe").is_file():
            raise ValueError("Selecciona la carpeta que contiene retrobat.exe.")
        return raiz

    def ejecutar(self, tarea, al_terminar, mensaje="Procesando…", *, con_progreso=False):
        if self.ocupado:
            return
        self.ocupado = True
        self.estado.set("")
        avance = (0, None, mensaje)
        fase_actual = None
        inicio = inicio_fase = monotonic()

        def informar(hecho, total, fase=mensaje):
            nonlocal avance
            avance = (hecho, total, fase)

        def mostrar_avance():
            nonlocal fase_actual, inicio_fase
            hecho, total, fase = avance
            ahora = monotonic()
            if (fase, total) != fase_actual:
                fase_actual = (fase, total)
                inicio_fase = ahora
                self.barra.stop()
                self.barra.configure(mode="determinate" if total else "indeterminate", value=0)
                if not total:
                    self.barra.start(60)
            if total:
                porcentaje = min(100, 100 * hecho // total)
                self.barra.configure(value=porcentaje)
                transcurrido = ahora - inicio_fase
                restante = (total - hecho) * transcurrido / hecho if hecho and transcurrido >= 0.5 else None
                if porcentaje == 100:
                    tiempo = ""
                else:
                    tiempo = (f" · restan aprox. {duracion(max(1, restante))}" if restante is not None
                              else " · calculando tiempo…")
                self.detalle_progreso.set(f"{fase} {porcentaje}%{tiempo}")
            else:
                self.detalle_progreso.set(f"{fase} · {duracion(ahora - inicio_fase)} transcurridos")

        mostrar_avance()
        futuro = self.executor.submit(tarea, informar) if con_progreso else self.executor.submit(tarea)

        def consultar():
            self.consulta_pendiente = None
            if not futuro.done():
                mostrar_avance()
                self.consulta_pendiente = self.after(75, consultar)
                return
            self.ocupado = False
            self.barra.stop()
            try:
                resultado = futuro.result()
                self.barra.configure(mode="determinate", value=100)
                self.detalle_progreso.set(f"100% · terminado en {duracion(monotonic() - inicio)}")
                self.estado.set("Listo")
                al_terminar(resultado)
            except Exception as error:
                self.barra.configure(mode="determinate", value=0)
                self.detalle_progreso.set("")
                self.estado.set("La operación falló. Revisa el mensaje e inténtalo de nuevo.")
                messagebox.showerror("RetroBat", str(error), parent=self)
        self.consulta_pendiente = self.after(75, consultar)

    def cargar_sistemas(self, *, guardar=False):
        self.sistema.set("")
        self.selector["values"] = ()
        self.sistemas = {}
        try:
            raiz = self.raiz_retrobat()
            self.sistemas = sistemas_instalados(raiz)
        except (OSError, ValueError, ParseError) as error:
            self.version_disponible.set("Elige una instalación válida de RetroBat.")
            messagebox.showerror("Sistemas", str(error), parent=self)
            return
        self.selector["values"] = sorted(self.sistemas)
        self.verificar_version(raiz)
        self.estado.set(f"{len(self.sistemas)} sistemas de RetroBat. Elige la carpeta de juegos para verificar.")
        if guardar:
            try:
                self.guardar_instalacion(raiz)
            except OSError as error:
                messagebox.showwarning("Preferencias", f"No se pudo guardar la carpeta para la próxima sesión: {error}",
                                       parent=self)
        self.detectar_origen()

    def previsualizar(self, *, automatica=False):
        if self.ocupado:
            return
        if self.revision_pendiente is not None:
            self.after_cancel(self.revision_pendiente)
            self.revision_pendiente = None
        parametros = self.parametros_revision()
        _, carpeta_origen, clave_sistema, categoria = parametros
        try:
            raiz = self.raiz_retrobat()
            if not carpeta_origen or clave_sistema not in self.sistemas:
                raise ValueError("Elige la carpeta de juegos y el sistema.")
            origen = Path(carpeta_origen)
            sistema = self.sistemas[clave_sistema]
            es_windows = sistema.identificador == "windows"
            carpeta_sistema = sistema.carpeta
            biblioteca_windows = raiz / "library" / "windows"
            destino = carpeta_sistema / nombre_seguro(categoria) if categoria else carpeta_sistema
        except ValueError as error:
            self.estado.set(str(error))
            if not automatica:
                messagebox.showerror("Verificar juegos", str(error), parent=self)
            return

        def buscar(informar):
            juegos = buscar_juegos(origen, sistema)
            if es_windows:
                objetivos, nombres = accesos_windows(carpeta_sistema)
            else:
                existentes = nombres_instalados(sistema)
            filas = []
            for indice, (nombre, candidatos) in enumerate(juegos):
                informar(indice, len(juegos), "Comparando juegos con RetroBat…")
                elegido = candidatos[0] if len(candidatos) == 1 else None
                if es_windows:
                    sufijo = ".lnk"
                    subcarpeta = Path()
                else:
                    archivo = candidatos[0]
                    sufijo = ".ps3" if archivo.is_dir() and sistema.identificador == "ps3" else archivo.suffix
                    subcarpeta = archivo.relative_to(origen).parent
                salida = destino / subcarpeta / (nombre + sufijo)
                estado = NUEVO_LISTO if elegido else NUEVO_PENDIENTE
                try:
                    nombre_seguro(nombre + sufijo)
                except ValueError:
                    estado = "Nombre inválido"
                else:
                    if es_windows:
                        elegido, estado = estado_windows(
                            candidatos, salida, objetivos, nombres, origen, biblioteca_windows
                        )
                    elif clave_juego(sistema, salida) in existentes or salida.exists():
                        estado = YA_INSTALADO
                    elif requiere_importacion_manual(elegido):
                        estado = IMPORTACION_MANUAL
                filas.append((nombre, candidatos, elegido, salida, estado))
            if not es_windows:
                copias = Counter(clave_juego(sistema, salida) for _, _, _, salida, estado in filas
                                 if estado == NUEVO_LISTO)
                filas = [(nombre, candidatos, elegido, salida,
                          REPETIDO_ORIGEN if estado == NUEVO_LISTO and copias[clave_juego(sistema, salida)] > 1 else estado)
                         for nombre, candidatos, elegido, salida, estado in filas]
            return filas

        def mostrar(filas):
            if self.parametros_revision() != parametros:
                return
            self.limpiar()
            for nombre, candidatos, elegido, salida, estado in filas:
                item = self.lista.insert("", "end", values=(nombre, elegido or "", estado), tags=(estado,))
                self.filas[item] = (candidatos, elegido, salida, estado)
            resumen = self.actualizar_resumen()
            self.estado.set(resumen if filas else "No se encontraron juegos compatibles en la carpeta elegida.")
            if self.oferta_importar and self.origen_detectado == parametros[:3]:
                self.oferta_importar = False
                listos = [item for item, fila in self.filas.items() if fila[3] == NUEVO_LISTO]
                if listos:
                    self.lista.selection_set(listos)
                    self.importar()
                elif filas:
                    self.ofrecer_bios(raiz, clave_sistema)

        self.limpiar()
        self.ejecutar(buscar, mostrar, "Verificando la carpeta y los juegos de RetroBat…", con_progreso=True)

    def mostrar_candidatos(self, _=None):
        seleccion = self.lista.selection()
        fila = self.filas.get(seleccion[0]) if len(seleccion) == 1 else None
        puede_elegir = fila is not None and fila[3] in (NUEVO_LISTO, NUEVO_PENDIENTE) and len(fila[0]) > 1
        self.ejecutables.configure(values=tuple(map(str, fila[0])) if puede_elegir else (),
                                  state="readonly" if puede_elegir else "disabled")
        self.candidato.set(str(fila[1]) if fila and fila[1] else "")
        self.actualizar_resumen()

    def elegir_ejecutable(self, _):
        seleccion = self.lista.selection()
        if len(seleccion) != 1:
            return
        item = seleccion[0]
        candidatos, _, salida, estado = self.filas[item]
        elegido = Path(self.candidato.get())
        if elegido not in candidatos or estado not in (NUEVO_LISTO, NUEVO_PENDIENTE):
            return
        self.filas[item] = (candidatos, elegido, salida, NUEVO_LISTO)
        self.lista.set(item, "archivo", str(elegido))
        self.lista.set(item, "estado", NUEVO_LISTO)
        self.lista.item(item, tags=(NUEVO_LISTO,))
        self.estado.set(self.actualizar_resumen())

    def importar(self):
        if self.ocupado:
            return
        parametros = self.parametros_revision()
        carpeta_externa = self.origen_detectado == parametros[:3]
        clave_sistema = parametros[2]
        sistema = self.sistemas.get(clave_sistema)
        if sistema is None:
            return
        es_windows = sistema.identificador == "windows"
        seleccion = self.filas if es_windows else self.lista.selection()
        filas = [(item, self.filas[item]) for item in seleccion
                 if self.filas[item][3] in (NUEVO_LISTO, REPETIDO_ORIGEN)]
        if not filas:
            mensaje = "No hay juegos nuevos listos para importar." if es_windows else (
                "Selecciona un juego nuevo o una sola copia de un juego repetido."
            )
            messagebox.showinfo("Importar", mensaje, parent=self)
            return
        try:
            raiz = self.raiz_retrobat()
        except ValueError as error:
            messagebox.showerror("Importar", str(error), parent=self)
            return
        biblioteca_windows = raiz / "library" / "windows"
        origen = Path(parametros[1])
        carpeta_sistema = sistema.carpeta
        titulo_sistema = sistema.nombre
        copiar_windows = es_windows and carpeta_externa
        destino = carpeta_sistema / parametros[3] if parametros[3] else carpeta_sistema
        if not es_windows and len({clave_juego(sistema, fila[2]) for _, fila in filas}) != len(filas):
            messagebox.showinfo("Juegos repetidos", "Selecciona una sola copia de cada juego repetido.", parent=self)
            return
        titulo = f"Carpeta externa de {titulo_sistema}" if carpeta_externa else f"Importar a {titulo_sistema}"
        if copiar_windows:
            pregunta = (
                f"¿Copiar {len(filas)} juegos nuevos a {biblioteca_windows} "
                f"y crear sus accesos directos en {destino}?"
            )
        elif es_windows:
            pregunta = f"¿Crear accesos directos para {len(filas)} juegos nuevos en {destino}?"
        else:
            pregunta = f"¿Copiar {len(filas)} juegos nuevos a {destino}?"
        if not messagebox.askyesno(titulo, pregunta, parent=self):
            if carpeta_externa:
                self.ofrecer_bios(raiz, clave_sistema)
            return

        def importar_filas(informar):
            resultados = []
            if es_windows:
                objetivos, nombres = accesos_windows(carpeta_sistema)
            else:
                existentes = nombres_instalados(sistema)
            fase = "Creando accesos directos…" if es_windows and not copiar_windows else "Copiando juegos…"
            tamanos = []
            for _, (_, elegido, destino, _) in filas:
                tamano = 0
                try:
                    if copiar_windows:
                        paquete, _, _ = ubicacion_juego_windows(origen, elegido, biblioteca_windows, destino.stem)
                        tamano = tamanio_copia(paquete)
                    elif not es_windows:
                        tamano = tamanio_copia(elegido)
                        if sistema.es_mame:
                            tamano += sum(disco.stat().st_size for disco in discos_mame(elegido))
                except OSError:
                    # La importación de esta fila comunicará el error específico.
                    pass
                tamanos.append(tamano + 1)
            total = sum(tamanos)
            procesado = 0
            informar(0, total, fase)
            for (item, (candidatos, elegido, destino, _)), tamano in zip(filas, tamanos):
                copiado = 0

                def avanzar(bytes_copiados):
                    nonlocal copiado
                    copiado += bytes_copiados
                    informar(procesado + min(copiado, tamano - 1), total, fase)

                try:
                    if es_windows:
                        registrado, estado = estado_windows(
                            candidatos, destino, objetivos, nombres, origen, biblioteca_windows
                        )
                        if estado not in (NUEVO_LISTO, NUEVO_PENDIENTE):
                            resultados.append((item, registrado, estado, None))
                            continue
                        if not elegido.is_file():
                            raise FileNotFoundError(f"El ejecutable ya no existe: {elegido}")
                        if copiar_windows:
                            elegido = copiar_juego_windows(origen, elegido, biblioteca_windows, destino, avanzar)
                        else:
                            shortcut(elegido, destino)
                        objetivos.add(elegido.resolve())
                        nombres[destino.name.casefold()] = True
                    else:
                        nombre = clave_juego(sistema, destino)
                        if nombre in existentes:
                            resultados.append((item, elegido, YA_INSTALADO, None))
                            continue
                        copiar_rom(sistema, elegido, destino, avanzar)
                        existentes.add(nombre)
                    resultados.append((item, elegido, "Importado", None))
                except (OSError, ValueError, subprocess.SubprocessError) as error:
                    resultados.append((item, elegido, "Error", f"{destino.name}: {error}"))
                finally:
                    procesado += tamano
                    informar(procesado, total, fase)
            return resultados

        def terminar(resultados):
            errores = []
            for item, archivo, estado, detalle in resultados:
                if item in self.filas:
                    candidatos, _, destino, _ = self.filas[item]
                    estado_visible = YA_INSTALADO if estado == "Importado" else estado
                    self.filas[item] = candidatos, archivo, destino, estado_visible
                    self.lista.item(item, tags=(estado_visible,))
                    self.lista.set(item, "archivo", str(archivo) if archivo else "")
                    self.lista.set(item, "estado", estado_visible)
                if detalle:
                    errores.append(detalle)
            importados = sum(estado == "Importado" for _, _, estado, _ in resultados)
            if self.filas:
                self.estado.set(f"{importados} importados · {self.actualizar_resumen()}")
                self.mostrar_candidatos()
            else:
                self.estado.set(f"{importados} importados · {len(errores)} errores")
            if errores:
                self.informe("Errores de importación", errores)
            if self.sistemas.get(self.sistema.get()) == sistema:
                self.cargar_categorias()
            if carpeta_externa and self.parametros_revision() == parametros:
                self.ofrecer_bios(raiz, clave_sistema)

        self.ejecutar(importar_filas, terminar, "Preparando la importación…", con_progreso=True)

    def informe(self, titulo, lineas, enlaces=()):
        ventana = tk.Toplevel(self)
        ventana.title(titulo)
        ventana.geometry("780x380")
        if enlaces:
            botones = ttk.Frame(ventana, padding=8)
            botones.pack(side="bottom", fill="x")
            for nombre, url in enlaces:
                ttk.Button(botones, text=nombre, command=lambda destino=url: webbrowser.open(destino)).pack(
                    side="left", padx=(0, 6)
                )
        texto = tk.Text(ventana, wrap="word", padx=12, pady=12)
        scroll = ttk.Scrollbar(ventana, command=texto.yview)
        texto.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        texto.pack(fill="both", expand=True)
        texto.insert("1.0", "\n".join(lineas) or "Sin resultados.")
        texto.configure(state="disabled")

    def operar(self, accion):
        if self.ocupado:
            return
        try:
            accion(self.raiz_retrobat())
        except (OSError, ValueError, ParseError) as error:
            messagebox.showerror("RetroBat", str(error), parent=self)

    def ver_duplicados(self):
        def revisar(raiz):
            sistemas = sistemas_instalados(raiz)
            self.ejecutar(lambda: list(duplicados(sistemas)),
                         lambda lineas: self.informe("Juegos repetidos", lineas))
        self.operar(revisar)

    def ver_biblioteca(self):
        def revisar(raiz):
            sistemas = self.sistemas.copy()
            self.ejecutar(
                lambda informar: biblioteca_instalada(raiz, sistemas, informar),
                lambda filas: self.mostrar_biblioteca(raiz, sistemas, filas),
                "Revisando la biblioteca de este PC…",
                con_progreso=True,
            )
        self.operar(revisar)

    def mostrar_biblioteca(self, raiz, sistemas, filas):
        ventana = tk.Toplevel(self)
        ventana.title("Biblioteca de RetroBat de este PC")
        ventana.geometry("840x490")
        ttk.Label(ventana, text=f"{raiz} · {len(filas)} sistemas con juegos", padding=10).pack(fill="x")
        botones = ttk.Frame(ventana, padding=8)
        botones.pack(side="bottom", fill="x")
        tabla = ttk.Treeview(ventana, columns=("juegos", "bios"), show="tree headings", selectmode="browse")
        tabla.heading("#0", text="Sistema / categoría")
        tabla.heading("juegos", text="Juegos")
        tabla.heading("bios", text="Estado de BIOS")
        tabla.column("#0", width=330)
        tabla.column("juegos", width=75, anchor="center")
        tabla.column("bios", width=350)
        scroll = ttk.Scrollbar(ventana, command=tabla.yview)
        tabla.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        tabla.pack(fill="both", expand=True)
        claves = {}
        for clave, nombre, bios, categorias in filas:
            estado = self.estados_bios.get((raiz.resolve(), clave), bios)
            item = tabla.insert("", "end", text=nombre, values=(sum(categorias.values()), estado))
            claves[item] = clave
            for categoria, cantidad in sorted(categorias.items(), key=lambda par: par[0].casefold()):
                hijo = tabla.insert(item, "end", text=categoria, values=(cantidad, ""))
                claves[hijo] = clave

        def accion(agregar=False):
            seleccion = tabla.selection()
            if not seleccion or self.ocupado:
                return
            clave = claves[seleccion[0]]
            if Path(self.raiz.get()) != raiz or self.sistemas.get(clave) != sistemas[clave]:
                messagebox.showinfo("Biblioteca", "La instalación cambió. Abre nuevamente su biblioteca.", parent=ventana)
                return
            self.preparar_bios(raiz, clave, agregar=agregar)

        buscar = ttk.Button(botones, text="Buscar BIOS…", command=accion, state="disabled")
        buscar.pack(side="left", padx=(0, 6))
        agregar = ttk.Button(botones, text="Agregar BIOS desde carpeta…", command=lambda: accion(True), state="disabled")
        agregar.pack(side="left")

        def seleccionar(_):
            seleccion = tabla.selection()
            habilitado = seleccion and sistemas[claves[seleccion[0]]].identificador not in NO_REQUIERE_BIOS
            estado = "normal" if habilitado else "disabled"
            buscar.configure(state=estado)
            agregar.configure(state=estado)

        tabla.bind("<<TreeviewSelect>>", seleccionar)
        def refrescar_bios(_):
            for item in tabla.get_children():
                estado = self.estados_bios.get((raiz.resolve(), claves[item]))
                if estado:
                    tabla.set(item, "bios", estado)

        ventana.bind("<FocusIn>", refrescar_bios)

    def bios(self):
        def revisar(raiz):
            sistema = self.sistema.get()
            configuracion = self.sistemas.get(sistema)
            if configuracion:
                self.preparar_bios(raiz, sistema)
                return
            archivo = filedialog.askopenfilename(title="Manifiesto de BIOS (MD5 y ruta relativa)")
            if archivo:
                self.ejecutar(lambda: revisar_bios(raiz, Path(archivo)),
                             lambda lineas: self.informe("Verificación de BIOS", lineas))
        self.operar(revisar)

    def ofrecer_bios(self, raiz, sistema):
        configuracion = self.sistemas[sistema]
        if configuracion.identificador in ("windows", "psp"):
            return
        if configuracion.identificador == "ps3" or messagebox.askyesno(
            "BIOS", f"¿Revisar las BIOS de {configuracion.nombre} y consultar las fuentes oficiales?",
            parent=self
        ):
            self.preparar_bios(raiz, sistema)

    def preparar_bios(self, raiz, sistema, *, agregar=False):
        configuracion = self.sistemas[sistema]
        consultar = revisar_bios_mame if configuracion.identificador == "mame" else buscar_bios_publicas
        self.ejecutar(
            lambda informar: consultar(raiz, configuracion, informar),
            lambda resultado: self.mostrar_bios(raiz, sistema, configuracion, resultado, agregar),
            "Verificando las BIOS del sistema…",
            con_progreso=True,
        )

    def mostrar_bios(self, raiz, clave, sistema, informe, agregar=False):
        titulo = f"BIOS de {sistema.nombre}"
        if not informe.archivos:
            self.informe(titulo, informe.lineas, informe.enlaces)
            return
        ventana = tk.Toplevel(self)
        ventana.title(titulo)
        ventana.geometry("1050x530")
        ttk.Label(ventana, padding=10, text="\n".join(informe.lineas), wraplength=990).pack(fill="x")
        acciones = ttk.Frame(ventana, padding=8)
        acciones.pack(side="bottom", fill="x")
        fuentes = ttk.Frame(ventana, padding=(8, 4))
        fuentes.pack(side="bottom", fill="x")
        for nombre, url in informe.enlaces:
            ttk.Button(fuentes, text=nombre, command=lambda enlace=url: webbrowser.open(enlace)).pack(side="left", padx=3)
        tabla = ttk.Treeview(ventana, columns=("archivo", "estado", "juegos", "destino", "fuente"),
                             show="headings", selectmode="browse")
        for columna, encabezado, ancho in (("archivo", "Archivo para buscar", 180), ("estado", "Estado", 235),
                                           ("juegos", "Juegos", 65), ("destino", "Destino en RetroBat", 275),
                                           ("fuente", "Fuente", 235)):
            tabla.heading(columna, text=encabezado)
            tabla.column(columna, width=ancho)
        scroll = ttk.Scrollbar(ventana, command=tabla.yview)
        tabla.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        tabla.pack(fill="both", expand=True)
        por_item = {}
        for archivo in sorted(informe.archivos, key=lambda bios: (
                bios.estado == "Verificada", -bios.juegos, bios.destino.name.casefold())):
            ubicacion = raiz.resolve()
            destino = (archivo.destino.relative_to(ubicacion)
                       if archivo.destino.is_relative_to(ubicacion) else archivo.destino)
            item = tabla.insert("", "end", values=(
                archivo.destino.name, archivo.estado, archivo.juegos or "—", str(destino),
                "Enlace de la fuente" if archivo.url else "Buscar por nombre y versión",
            ))
            por_item[item] = archivo

        def guardar_estado():
            estados = [tabla.set(item, "estado") for item in por_item]
            verificadas = estados.count("Verificada")
            pendientes = estados.count("Por buscar")
            self.estados_bios[(raiz.resolve(), clave)] = (
                f"{verificadas}/{len(estados)} verificadas · {pendientes} por buscar"
            )

        def seleccionado():
            items = tabla.selection()
            return por_item[items[0]] if items else None

        def buscar():
            archivo = seleccionado()
            if archivo:
                webbrowser.open(enlace_busqueda(archivo, informe.contexto))

        def fuente():
            archivo = seleccionado()
            if archivo and archivo.url:
                webbrowser.open(archivo.url)

        def importar_local():
            if self.ocupado:
                return
            requisitos = [archivo for item, archivo in por_item.items()
                          if archivo.verificable and tabla.set(item, "estado") != "Verificada"
                          and not archivo.destino.exists()]
            if not requisitos:
                messagebox.showinfo(titulo, "No quedan archivos pendientes que se puedan verificar y agregar.",
                                    parent=ventana)
                return
            origen = filedialog.askdirectory(title="Carpeta donde tienes guardadas las BIOS", parent=ventana)
            if not origen or not messagebox.askyesno(
                titulo, f"¿Copiar los archivos compatibles de esta carpeta a {raiz / 'bios'}?",
                parent=ventana,
            ):
                return

            def terminar(resultados):
                if ventana.winfo_exists():
                    copiadas = {bios.destino for bios, resultado in resultados if resultado == "Copiada y verificada"}
                    for item, archivo in por_item.items():
                        if archivo.destino in copiadas:
                            tabla.set(item, "estado", "Verificada")
                    guardar_estado()
                self.informe("Resultado al agregar BIOS",
                             [f"{bios.destino.name}: {resultado}" for bios, resultado in resultados])

            self.ejecutar(
                lambda informar: importar_bios_locales(raiz, Path(origen), requisitos, informar),
                terminar, "Buscando y verificando BIOS locales…", con_progreso=True,
            )

        def firmware_ps3():
            if self.ocupado:
                return
            destino = raiz / "bios" / "PS3UPDAT.PUP"
            if destino.exists():
                messagebox.showinfo(titulo, f"Ya existe {destino}.", parent=ventana)
                return
            if not messagebox.askyesno(titulo, f"¿Descargar el firmware oficial 4.93 (206 MB) a {destino}?",
                                       parent=ventana):
                return

            def terminar(_):
                if ventana.winfo_exists():
                    for item in por_item:
                        tabla.set(item, "estado", "Verificada")
                    guardar_estado()
                messagebox.showinfo(titulo, "Firmware descargado. RPCS3 ofrecerá instalarlo al iniciar un juego.",
                                    parent=self)

            self.ejecutar(lambda informar: descargar_firmware_ps3(destino, informar),
                          terminar, "Descargando el firmware de Sony…", con_progreso=True)

        ttk.Button(acciones, text="Buscar en Internet", command=buscar).pack(side="left", padx=3)
        boton_fuente = ttk.Button(acciones, text="Abrir fuente", command=fuente, state="disabled")
        boton_fuente.pack(side="left", padx=3)
        ttk.Button(acciones, text="Agregar BIOS desde carpeta…", command=importar_local).pack(side="left", padx=3)
        if sistema.identificador == "ps3":
            ttk.Button(acciones, text="Descargar firmware de Sony", command=firmware_ps3).pack(side="left", padx=3)

        def seleccionar(_):
            archivo = seleccionado()
            boton_fuente.configure(state="normal" if archivo and archivo.url else "disabled")

        tabla.bind("<<TreeviewSelect>>", seleccionar)
        tabla.selection_set(next(iter(por_item)))
        guardar_estado()
        if agregar:
            ventana.after_idle(importar_local)

    def intro(self):
        def instalar(raiz):
            archivo = filedialog.askopenfilename(title="Video de intro", filetypes=[("Video MP4", "*.mp4")],
                                                 initialdir=RECURSOS / "arranque" / "splash")
            if not archivo:
                return
            archivo = Path(archivo)
            if archivo.suffix.lower() != ".mp4":
                raise ValueError("Selecciona un video MP4.")
            destino = raiz / "emulationstation" / ".emulationstation" / "video" / archivo.name
            if not messagebox.askyesno("Intro", "¿Copiar el video y activarlo en retrobat.ini?", parent=self):
                return

            def aplicar(informar):
                if destino.exists():
                    if not filecmp.cmp(archivo, destino, shallow=False):
                        raise FileExistsError(f"Ya existe otro video con ese nombre: {destino}")
                else:
                    copiar_con_progreso(archivo, destino, informar, "Copiando el video de inicio…")
                informar(0, None, "Actualizando retrobat.ini…")
                editar_ini(raiz, "SplashScreen", {"EnableIntro": "1", "RandomVideo": "0",
                                                "FilePath": "default", "FileName": archivo.name})
            self.ejecutar(aplicar, lambda _: self.estado.set(f"Intro configurada: {archivo.name}"), con_progreso=True)
        self.operar(instalar)

    def tema(self):
        def crear(raiz):
            plantilla = filedialog.askdirectory(title="Tema base", initialdir=RECURSOS / "themes")
            if not plantilla:
                return
            plantilla = Path(plantilla)
            if not (plantilla / "theme.xml").is_file():
                raise ValueError("La carpeta del tema base debe contener theme.xml.")
            nombre = simpledialog.askstring("Crear tema", "Nombre de carpeta del nuevo tema", parent=self)
            if nombre:
                destino = raiz / "emulationstation" / ".emulationstation" / "themes" / nombre_seguro(nombre)
                self.ejecutar(
                    lambda informar: copiar_con_progreso(plantilla, destino, informar, "Copiando el tema…"),
                    lambda _: self.estado.set(f"Tema creado: {nombre}. Selecciónalo en RetroBat."),
                    con_progreso=True,
                )
        self.operar(crear)

    def editar_tema(self):
        def editar(raiz):
            archivo = filedialog.askopenfilename(
                title="Selecciona el XML del tema", filetypes=[("Tema XML", "*.xml")],
                initialdir=raiz / "emulationstation" / ".emulationstation" / "themes")
            if archivo:
                subprocess.Popen(["notepad.exe", archivo])
        self.operar(editar)

    def configurar(self):
        def abrir(raiz):
            archivo = raiz / "retrobat.ini"
            original = archivo.read_bytes()
            if original.startswith((b"\xff\xfe", b"\xfe\xff")):
                codificacion = "utf-16-le" if original.startswith(b"\xff\xfe") else "utf-16-be"
            else:
                try:
                    original.decode("utf-8")
                    codificacion = "utf-8"
                except UnicodeDecodeError:
                    codificacion = "cp1252"
            contenido = original.decode(codificacion)
            salto = "\r\n" if "\r\n" in contenido else "\n"
            bom = "\ufeff" if contenido.startswith("\ufeff") else ""
            contenido = contenido.removeprefix("\ufeff").replace("\r\n", "\n")

            ventana = tk.Toplevel(self)
            ventana.title("Configuración de RetroBat")
            ventana.geometry("800x550")
            ventana.transient(self)
            ventana.grab_set()
            ttk.Label(ventana, text=str(archivo), padding=10).pack(fill="x")
            cuerpo = ttk.Frame(ventana, padding=(10, 0, 10, 0))
            cuerpo.pack(fill="both", expand=True)
            texto = tk.Text(cuerpo, wrap="none", undo=True)
            scroll = ttk.Scrollbar(cuerpo, command=texto.yview)
            texto.configure(yscrollcommand=scroll.set)
            scroll.pack(side="right", fill="y")
            texto.pack(fill="both", expand=True)
            texto.insert("1.0", contenido)

            def guardar():
                actualizado = texto.get("1.0", "end-1c")
                if actualizado == contenido:
                    ventana.destroy()
                    return
                if not messagebox.askyesno(
                    "Guardar configuración", "¿Guardar los cambios y crear un respaldo?", parent=ventana
                ):
                    return
                try:
                    datos = (bom + actualizado.replace("\n", salto)).encode(codificacion)
                    if archivo.read_bytes() != original:
                        raise ValueError("Otro programa modificó retrobat.ini. Cierra el editor y vuelve a abrirlo.")
                    with tempfile.NamedTemporaryFile(
                        prefix="retrobat-", suffix=".ini.bak", dir=raiz, delete=False
                    ) as respaldo:
                        respaldo.write(original)
                    with tempfile.TemporaryDirectory(dir=raiz) as temporal:
                        preparado = Path(temporal) / archivo.name
                        preparado.write_bytes(datos)
                        preparado.replace(archivo)
                except (OSError, ValueError) as error:
                    messagebox.showerror("Configuración", str(error), parent=ventana)
                    return
                self.estado.set(f"Respaldo guardado: {Path(respaldo.name).name}")
                ventana.destroy()

            botones = ttk.Frame(ventana, padding=10)
            botones.pack(fill="x")
            ttk.Button(botones, text="Cerrar", command=ventana.destroy).pack(side="right")
            ttk.Button(botones, text="Guardar cambios", command=guardar).pack(side="right", padx=8)

        self.operar(abrir)


if __name__ == "__main__":
    if os.name != "nt":
        raise SystemExit("El gestor se ejecuta en Windows.")
    if len(sys.argv) == 3 and sys.argv[1] == "--verificar":
        informe = Path(sys.argv[2])
        try:
            app = Gestor()
            app.update()
            app.destroy()
            informe.write_text("OK\n", encoding="utf-8")
        except Exception:
            import traceback
            informe.write_text(traceback.format_exc(), encoding="utf-8")
            raise SystemExit(1) from None
    else:
        Gestor().mainloop()
