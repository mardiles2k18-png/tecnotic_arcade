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

from PIL import Image, ImageOps, ImageTk

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from gestor_teknoparrot_archivos import ejecutar_7zip
from gestor_teknoparrot_instalacion import contexto_tls
from gestor_teknoparrot_ui import PanelTeknoParrot
from gestor_biblioteca import editar_nombre, eliminar_juego, plan_eliminar
from gestor_bios import (NO_REQUIERE_BIOS, RELEASES_RETROBAT, biblioteca_instalada, buscar_bios_publicas,
                         comprobar_actualizacion, enlace_busqueda, importar_bios_locales, revisar_bios_mame)
from gestor_duplicados import (Entrada, Grupo, buscar_duplicados, candidato_windows, carpeta_respaldos, clave_titulo,
                               comparar_juego, eliminar_respaldos, guardar_respaldo, leer_entradas, listar_respaldos,
                               marca_archivo, mismo_archivo, plan_duplicados, reemplazar_entrada, restaurar_respaldo,
                               retirar_entradas, se_puede_reemplazar)
from gestor_core import (CARPETAS_MULTIMEDIA, IMPORTACION_MANUAL, NUEVO_LISTO, NUEVO_PENDIENTE,
                         REPETIDO_ORIGEN, YA_INSTALADO,
                         accesos_windows, buscar_juegos, clave_juego, copiar, copiar_juego_windows, copiar_rom,
                         descargar_firmware_ps3, destinos_accesos_windows, detectar_sistema_externo, discos_mame,
                         editar_ini, indexar_accesos, inspeccionar_tema,
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


def tamano_visible(tamano):
    if tamano is None:
        return "—"
    if tamano < 1024**2:
        return f"{tamano:,} bytes"
    return f"{tamano / 1024**3:.2f} GiB" if tamano >= 1024**3 else f"{tamano / 1024**2:.2f} MiB"


class Gestor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tecnotics Arcade · Gestor de RetroBat · Vista previa 20")
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
        self.coincidencias = {}
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
        self.pestañas = pestañas = ttk.Notebook(self)
        pestañas.pack(fill="both", expand=True, padx=16, pady=(8, 0))
        inicio, panel, bios, biblioteca, ajustes = (ttk.Frame(pestañas, padding=16) for _ in range(5))
        self.panel_teknoparrot = PanelTeknoParrot(pestañas, self)
        for pagina, titulo in ((inicio, "Inicio"), (panel, "Cargar juegos"), (bios, "BIOS"),
                               (biblioteca, "Biblioteca"), (ajustes, "Configurar RetroBat"),
                               (self.panel_teknoparrot, "TeknoParrot")):
            pestañas.add(pagina, text=titulo)

        inicio.columnconfigure(1, weight=1)
        self.carpeta(inicio, 0, "Instalación", self.raiz, lambda: self.cargar_sistemas(guardar=True))
        self.estado_instalacion = tk.StringVar()
        self.estado_ruta = tk.StringVar()
        for fila, titulo, valor in ((1, "Estado de RetroBat", self.estado_instalacion),
                                    (2, "Ruta predeterminada", self.estado_ruta),
                                    (3, "Versión", self.version_disponible)):
            ttk.Label(inicio, text=titulo).grid(row=fila, column=0, sticky="nw", pady=8)
            ttk.Label(inicio, textvariable=valor, wraplength=600).grid(
                row=fila, column=1, columnspan=2, sticky="w", padx=8, pady=8)
        ttk.Button(inicio, text="Volver a comprobar", command=self.comprobar_sistema).grid(
            row=4, column=0, sticky="w", pady=8)
        ttk.Button(inicio, text="Versiones de RetroBat", command=lambda: webbrowser.open(RELEASES_RETROBAT)).grid(
            row=4, column=1, sticky="w", padx=8)

        self.panel_bios, self.panel_biblioteca = bios, biblioteca
        self.iniciar_panel_biblioteca(bios, solo_bios=True)
        self.iniciar_panel_biblioteca(biblioteca)
        pestañas.bind("<<NotebookTabChanged>>", self.cambio_pestana)

        for titulo, acciones in (
                ("Temas", (("Importar tema…", self.importar_tema), ("Crear tema…", self.tema),
                           ("Editar tema…", self.editar_tema), ("Eliminar tema…", self.eliminar_tema))),
                ("Sonido y arranque", (("Instalar intro…", self.intro), ("Importar música…", self.importar_musica))),
                ("Ajustes", (("Editar retrobat.ini…", self.configurar),))):
            grupo = ttk.LabelFrame(ajustes, text=titulo, padding=10)
            grupo.pack(fill="x", pady=(0, 12))
            for etiqueta, accion in acciones:
                ttk.Button(grupo, text=etiqueta, command=accion).pack(side="left", padx=(0, 8))

        panel.columnconfigure(1, weight=1)
        panel.rowconfigure(4, weight=1)
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
        acciones_juegos = ttk.Frame(panel)
        acciones_juegos.grid(row=5, column=2, sticky="e")
        self.boton_comparar = ttk.Button(acciones_juegos, text="Comparar copias…", state="disabled",
                                        command=self.comparar_seleccion)
        self.boton_comparar.pack(side="left", padx=(0, 5))
        self.boton_importar = ttk.Button(acciones_juegos, text="Importar nuevos", state="disabled", command=self.importar)
        self.boton_importar.pack(side="left")

        pie = ttk.Frame(self, padding=(16, 8, 16, 10))
        pie.pack(fill="x")
        ttk.Label(pie, textvariable=self.estado).pack(anchor="w")
        self.barra = ttk.Progressbar(pie, maximum=100)
        self.barra.pack(fill="x", pady=(6, 2))
        ttk.Label(pie, textvariable=self.detalle_progreso).pack(anchor="w")
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
            if (raiz / "retrobat.exe").is_file():
                self.raiz.set(raiz.as_posix())
        except (OSError, ValueError, KeyError, TypeError):
            pass
        self.comprobar_sistema()

    def comprobar_sistema(self):
        if self.ocupado:
            return
        predeterminada = Path("C:/RetroBat")
        en_c = (predeterminada / "retrobat.exe").is_file()
        if en_c and not (self.raiz.get() and (Path(self.raiz.get()) / "retrobat.exe").is_file()):
            self.raiz.set(predeterminada.as_posix())
        self.estado_ruta.set(rf"C:\RetroBat · {'Instalación detectada' if en_c else 'Sin instalación detectada'}")
        if self.raiz.get() and (Path(self.raiz.get()) / "retrobat.exe").is_file():
            self.cargar_sistemas()
        else:
            self.estado_instalacion.set("RetroBat no se detectó. Si está en otra unidad, elige su carpeta.")
            self.version_disponible.set("Pendiente de detectar la instalación.")
            self.sistemas = {}
            self.selector["values"] = ()
            self.sistema.set("")
            self.limpiar_paneles_biblioteca()

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
        self.coincidencias.clear()
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
        self.limpiar_paneles_biblioteca()
        try:
            raiz = self.raiz_retrobat()
            self.estado_instalacion.set(f"Instalado · {raiz}")
            en_c = (Path("C:/RetroBat") / "retrobat.exe").is_file()
            self.estado_ruta.set(rf"C:\RetroBat · {'Instalación detectada' if en_c else 'Sin instalación detectada'}")
            self.verificar_version(raiz)
            self.sistemas = sistemas_instalados(raiz)
        except (OSError, ValueError, ParseError) as error:
            instalado = self.raiz.get() and (Path(self.raiz.get()) / "retrobat.exe").is_file()
            self.estado_instalacion.set(f"Instalado · {self.raiz.get()}\n{error}" if instalado else str(error))
            if not instalado:
                self.version_disponible.set("Pendiente de detectar la instalación.")
            return
        self.selector["values"] = sorted(self.sistemas)
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
                accesos = destinos_accesos_windows(carpeta_sistema)
                objetivos, nombres = indexar_accesos(accesos)
            else:
                accesos = None
            por_titulo, por_archivo, por_ejecutable = {}, {}, {}
            for entrada in leer_entradas(sistema, accesos):
                por_titulo.setdefault(clave_titulo(entrada.ruta.stem), []).append(entrada)
                if entrada.archivo:
                    por_archivo.setdefault(entrada.archivo, []).append(entrada)
                    if es_windows:
                        por_ejecutable.setdefault(entrada.archivo.name.casefold(), []).append(entrada)
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
                coincidencias = []
                try:
                    nombre_seguro(nombre + sufijo)
                except ValueError:
                    estado = "Nombre inválido"
                else:
                    if es_windows:
                        elegido, estado = estado_windows(
                            candidatos, salida, objetivos, nombres, origen, biblioteca_windows
                        )
                    coincidencias = list(por_titulo.get(clave_titulo(nombre), ()))
                    if elegido in por_archivo:
                        coincidencias.extend(entrada for entrada in por_archivo[elegido] if entrada not in coincidencias)
                    if es_windows and not any(entrada.archivo for entrada in coincidencias):
                        for candidato in candidatos:
                            for entrada in por_ejecutable.get(candidato.name.casefold(), ()):
                                titulo = clave_titulo(nombre)
                                nombre_acceso = clave_titulo(entrada.ruta.stem)
                                if len(titulo) < 6 or not (titulo.startswith(nombre_acceso) or nombre_acceso.startswith(titulo)):
                                    continue
                                try:
                                    if mismo_archivo(candidato, entrada.archivo) and entrada not in coincidencias:
                                        coincidencias.append(entrada)
                                except OSError:
                                    continue
                    if coincidencias:
                        coincidencias.sort(key=lambda entrada: (entrada.archivo is None, entrada.ruta != salida))
                        instalada = coincidencias[0]
                        sugerido = candidato_windows(candidatos, instalada) if es_windows else candidatos[0]
                        if sugerido:
                            elegido = sugerido
                            try:
                                resultado = comparar_juego(sugerido, instalada, origen)
                                estado = YA_INSTALADO if resultado.estado == "Misma ruta" else resultado.estado
                            except OSError:
                                estado = "Nombre en uso · revisar"
                        else:
                            estado = "Nombre en uso · elegir archivo"
                    elif not es_windows:
                        if salida.exists():
                            estado = "Destino en uso"
                        elif requiere_importacion_manual(elegido):
                            estado = IMPORTACION_MANUAL
                filas.append((nombre, candidatos, elegido, salida, estado, coincidencias))
            if not es_windows:
                copias = Counter(clave_juego(sistema, salida) for _, _, _, salida, estado, _ in filas
                                 if estado == NUEVO_LISTO)
                filas = [(nombre, candidatos, elegido, salida,
                          REPETIDO_ORIGEN if estado == NUEVO_LISTO and copias[clave_juego(sistema, salida)] > 1 else estado,
                          coincidencias)
                         for nombre, candidatos, elegido, salida, estado, coincidencias in filas]
            return filas

        def mostrar(filas):
            if self.parametros_revision() != parametros:
                return
            self.limpiar()
            for nombre, candidatos, elegido, salida, estado, coincidencias in filas:
                item = self.lista.insert("", "end", values=(nombre, elegido or "", estado), tags=(estado,))
                self.filas[item] = (candidatos, elegido, salida, estado)
                if coincidencias:
                    self.coincidencias[item] = coincidencias
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
        puede_comparar = len(seleccion) == 1 and seleccion[0] in self.coincidencias
        self.boton_comparar.configure(state="normal" if puede_comparar else "disabled")
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

    def comparar_seleccion(self):
        seleccion = self.lista.selection()
        if self.ocupado or len(seleccion) != 1 or seleccion[0] not in self.coincidencias:
            return
        item = seleccion[0]
        candidatos, elegido, _, _ = self.filas[item]
        coincidencias = self.coincidencias[item]
        raiz = self.raiz_retrobat()
        origen = Path(self.origen.get())
        ventana = tk.Toplevel(self)
        ventana.title(f"Comparar copias · {self.lista.set(item, 'juego')}")
        ventana.geometry("1020x325")
        contenido = ttk.Frame(ventana, padding=12)
        contenido.pack(fill="both", expand=True)
        contenido.columnconfigure(1, weight=1)
        archivo_instalado = tk.StringVar(ventana, value=str(coincidencias[0].ruta))
        archivo_origen = tk.StringVar(ventana, value=str(elegido) if elegido in candidatos else "")
        detalle = tk.StringVar(ventana, value="Selecciona los archivos que deseas comparar.")
        por_ruta = {str(entrada.ruta): entrada for entrada in coincidencias}
        for fila, (titulo, variable, valores) in enumerate((
            ("En RetroBat", archivo_instalado, tuple(por_ruta)),
            ("Archivo de origen", archivo_origen, tuple(map(str, candidatos))),
        )):
            ttk.Label(contenido, text=titulo).grid(row=fila, column=0, sticky="w")
            selector = ttk.Combobox(contenido, textvariable=variable, values=valores, state="readonly")
            selector.grid(row=fila, column=1, sticky="ew", padx=(8, 0), pady=5)
        ttk.Label(contenido, textvariable=detalle, wraplength=960, justify="left").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=12
        )
        botones = ttk.Frame(contenido)
        botones.grid(row=3, column=0, columnspan=2, sticky="w")
        resultado = None

        def invalidar(*_):
            nonlocal resultado
            resultado = None
            reemplazar.configure(state="disabled")
            detalle.set("Vuelve a verificar el contenido de la selección.")

        def verificar():
            if self.ocupado or not archivo_origen.get():
                return
            actual = por_ruta[archivo_instalado.get()]
            candidato = Path(archivo_origen.get())
            invalidar()
            detalle.set("Verificando archivos y midiendo sus tamaños…")

            def mostrar(comparacion):
                nonlocal resultado
                if not ventana.winfo_exists() or (str(actual.ruta), str(candidato)) != (
                        archivo_instalado.get(), archivo_origen.get()):
                    return
                resultado = comparacion
                nuevo, instalado = comparacion.bytes_origen, comparacion.bytes_instalados
                cambio = ""
                if nuevo is not None and instalado is not None:
                    if nuevo != instalado:
                        signo = "+" if nuevo > instalado else "−"
                        cambio = f" · diferencia: {signo}{tamano_visible(abs(nuevo - instalado))}"
                    else:
                        cambio = " · mismo tamaño"
                puede = se_puede_reemplazar(comparacion)
                nota = "" if puede or comparacion.estado == "Misma ruta" else "\nEste formato requiere reemplazo manual."
                detalle.set(
                    f"{comparacion.estado}\n{comparacion.evidencia}\n"
                    f"Destino actual: {actual.archivo or 'No disponible'}\n"
                    f"{comparacion.unidades}: en RetroBat {tamano_visible(instalado)} · "
                    f"origen {tamano_visible(nuevo)}{cambio}{nota}"
                )
                reemplazar.configure(state="normal" if puede else "disabled")

            self.ejecutar(lambda: comparar_juego(candidato, actual, origen, medir_paquetes=True),
                          mostrar, "Verificando las dos copias…")

        def aplicar():
            comparacion = resultado
            if comparacion is None or self.ocupado:
                return
            destino = comparacion.instalada.ruta
            if comparacion.instalada.sistema.identificador == "windows":
                accion = "Se copiará el juego nuevo y se cambiará el acceso. Los archivos anteriores del juego se conservan."
            else:
                accion = "La ROM anterior quedará en un respaldo."
            if not messagebox.askyesno("Reemplazar copia", f"¿Reemplazar {destino}?\n\n{accion}", parent=ventana):
                return

            def terminar(respaldo):
                if ventana.winfo_exists():
                    ventana.destroy()
                messagebox.showinfo("Reemplazo terminado", f"Respaldo de la entrada anterior:\n{respaldo}", parent=self)
                if Path(self.raiz.get()) == raiz:
                    self.previsualizar()

            self.ejecutar(lambda informar: reemplazar_entrada(raiz, origen, comparacion, informar), terminar,
                          "Preparando el respaldo y la copia nueva…", con_progreso=True)

        ttk.Button(botones, text="Verificar contenido", command=verificar).pack(side="left", padx=(0, 6))
        ttk.Button(botones, text="Conservar la instalada", command=ventana.destroy).pack(side="left", padx=(0, 6))
        reemplazar = ttk.Button(botones, text="Reemplazar con esta copia…", state="disabled", command=aplicar)
        reemplazar.pack(side="left")
        archivo_instalado.trace_add("write", invalidar)
        archivo_origen.trace_add("write", invalidar)
        if elegido in candidatos:
            verificar()

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
            self.ejecutar(lambda informar: buscar_duplicados(sistemas, informar),
                          lambda grupos: self.gestionar_duplicados(raiz, grupos),
                          "Buscando copias en la biblioteca…", con_progreso=True)
        self.operar(revisar)

    def gestionar_duplicados(self, raiz, grupos):
        ventana = tk.Toplevel(self)
        ventana.title("Gestionar duplicados de RetroBat")
        ventana.geometry("1220x660")
        ventana.minsize(780, 420)
        ttk.Label(
            ventana, padding=8, wraplength=1050,
            text="Marca las copias que quieres conservar. En los grupos revisados, las copias sin marcar "
                 "se retirarán al aplicar. Los grupos sin ninguna marca quedan intactos.",
        ).pack(fill="x")
        filtros = ttk.Frame(ventana, padding=(8, 0, 8, 6))
        filtros.pack(fill="x")
        filtro = tk.StringVar(ventana)
        ttk.Label(filtros, text="Buscar título o sistema").pack(side="left", padx=(0, 8))
        ttk.Entry(filtros, textvariable=filtro, width=45).pack(side="left")
        resumen = tk.StringVar(ventana)
        ttk.Label(filtros, textvariable=resumen).pack(side="right")
        marcadas = set()
        acciones = ttk.Frame(ventana, padding=8)
        acciones.pack(side="bottom", fill="x")
        cuerpo = ttk.Frame(ventana, padding=(8, 0, 8, 0))
        cuerpo.pack(fill="both", expand=True)
        cuerpo.rowconfigure(0, weight=1)
        cuerpo.columnconfigure(0, weight=1)
        tabla = ttk.Treeview(cuerpo, show="tree headings", selectmode="browse",
                             columns=("conservar", "sistema", "tamano", "decision", "ruta", "destino"))
        for campo, titulo, ancho in (("#0", "Juego / versión", 295), ("conservar", "Conservar", 86),
                                     ("sistema", "Sistema", 115), ("tamano", "Tamaño", 94),
                                     ("decision", "Decisión", 105), ("ruta", "Entrada de RetroBat", 430),
                                     ("destino", "Archivo o destino", 430)):
            tabla.heading(campo, text=titulo)
            tabla.column(campo, width=ancho, minwidth=70, stretch=False,
                         anchor="center" if campo == "conservar" else "w")
        vertical = ttk.Scrollbar(cuerpo, command=tabla.yview)
        horizontal = ttk.Scrollbar(cuerpo, orient="horizontal", command=tabla.xview)
        tabla.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        tabla.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        tabla.tag_configure("grupo", background="#EDF2F8")
        tabla.tag_configure("conservar", foreground="#17643D")
        tabla.tag_configure("retirar", foreground="#854021")
        por_fila, por_grupo = {}, {}

        def actualizar_decisiones():
            conservar, retirar = plan_duplicados(grupos, marcadas)
            pendientes = {entrada.ruta for entrada in retirar}
            for item, entrada in por_fila.items():
                marcada = entrada.ruta in marcadas
                decision = "Conservar" if marcada else "Retirar" if entrada.ruta in pendientes else "Por decidir"
                tabla.set(item, "conservar", "☑" if marcada else "☐")
                tabla.set(item, "decision", decision)
                tabla.item(item, tags=(decision.casefold(),))
            detalle = f"{len(grupos)} grupos · {len(marcadas)} marcadas · {len(retirar)} por retirar"
            if len(por_grupo) != len(grupos):
                detalle += f" · {len(por_grupo)} visibles"
            resumen.set(detalle)
            aplicar.configure(state="normal" if retirar else "disabled")

        def cargar_lista(*_):
            consulta = clave_titulo(filtro.get())
            tabla.delete(*tabla.get_children())
            por_fila.clear()
            por_grupo.clear()
            for grupo in grupos:
                coincidencias = (grupo.nombre, *(entrada.ruta.stem for entrada in grupo.entradas),
                                 *(entrada.sistema.nombre for entrada in grupo.entradas))
                if consulta and not any(consulta in clave_titulo(nombre) for nombre in coincidencias):
                    continue
                padre = tabla.insert("", "end", text=grupo.nombre, open=True, tags=("grupo",),
                                     values=("", "", "", "", grupo.evidencia, f"{len(grupo.entradas)} copias"))
                por_grupo[padre] = grupo
                for entrada in grupo.entradas:
                    item = tabla.insert(padre, "end", text=entrada.ruta.name, values=(
                        "", entrada.sistema.nombre, tamano_visible(entrada.bytes), "", str(entrada.ruta),
                        str(entrada.archivo) if entrada.archivo else "Destino no encontrado",
                    ))
                    por_fila[item] = entrada
            actualizar_decisiones()

        def alternar(item):
            if self.ocupado or item not in por_fila:
                return
            ruta = por_fila[item].ruta
            if ruta in marcadas:
                marcadas.remove(ruta)
            else:
                marcadas.add(ruta)
            actualizar_decisiones()

        def marcar_casilla(evento):
            item = tabla.identify_row(evento.y)
            if tabla.identify_column(evento.x) == "#1" and item in por_fila:
                tabla.focus(item)
                tabla.selection_set(item)
                tabla.focus_set()
                alternar(item)
                return "break"

        def marcar_con_teclado(_):
            alternar(tabla.focus())
            return "break"

        def marcar_sistema():
            item = tabla.focus()
            if not self.ocupado and item in por_fila:
                sistema = por_fila[item].sistema
                grupo = por_grupo[tabla.parent(item)]
                marcadas.update(entrada.ruta for entrada in grupo.entradas if entrada.sistema == sistema)
                actualizar_decisiones()

        def aplicar_lote():
            if self.ocupado:
                return
            conservar, retirar = plan_duplicados(grupos, marcadas)
            if not retirar:
                return
            rutas = {entrada.ruta for entrada in retirar}
            afectados = sum(any(entrada.ruta in rutas for entrada in grupo.entradas) for grupo in grupos)
            retirar_texto = "\n".join(f"• {x.sistema.nombre}: {x.ruta}" for x in retirar[:8])
            if len(retirar) > 8:
                retirar_texto += f"\n… y {len(retirar) - 8} más."
            if not messagebox.askyesno(
                "Retirar copias con respaldo",
                f"Se aplicarán las decisiones de {afectados} grupos y se conservarán {len(conservar)} copias.\n\n"
                f"Se retirarán {len(retirar)} entradas:\n{retirar_texto}\n\n"
                "Las entradas se guardarán en un respaldo. En Windows solo se retira el acceso directo.",
                parent=ventana,
            ):
                return

            def terminar(respaldo):
                nonlocal grupos
                if ventana.winfo_exists():
                    grupos = [
                        Grupo(grupo.nombre, grupo.evidencia, restantes)
                        for grupo in grupos
                        if len(restantes := tuple(entrada for entrada in grupo.entradas if entrada.ruta not in rutas)) > 1
                    ]
                    marcadas.intersection_update(entrada.ruta for grupo in grupos for entrada in grupo.entradas)
                    cargar_lista()
                messagebox.showinfo("Respaldo creado",
                                    f"{len(retirar)} copias retiradas de RetroBat.\n\nRespaldo: {respaldo}",
                                    parent=self)

            self.ejecutar(lambda: retirar_entradas(raiz, conservar, retirar), terminar, "Retirando copias con respaldo…")

        def restaurar():
            if self.ocupado:
                return
            base = carpeta_respaldos(raiz)
            if not base.is_dir():
                messagebox.showinfo("Respaldos", "Todavía no hay respaldos del gestor.", parent=ventana)
                return
            carpeta = filedialog.askdirectory(title="Selecciona el respaldo a restaurar", initialdir=base, parent=ventana)
            if not carpeta or not messagebox.askyesno("Restaurar", "¿Volver a colocar los archivos en RetroBat?",
                                                     parent=ventana):
                return

            def terminar(cantidad):
                if ventana.winfo_exists():
                    ventana.destroy()
                messagebox.showinfo("Restaurar", f"{cantidad} archivos restaurados. Actualiza la lista de juegos.",
                                    parent=self)

            self.ejecutar(lambda: restaurar_respaldo(raiz, Path(carpeta)), terminar, "Restaurando archivos…")

        aplicar = ttk.Button(acciones, text="Aplicar selección…", command=aplicar_lote)
        aplicar.pack(side="left", padx=(0, 6))
        ttk.Button(acciones, text="Marcar este sistema en el grupo", command=marcar_sistema).pack(side="left")
        ttk.Button(acciones, text="Restaurar respaldo…", command=restaurar).pack(side="right")
        tabla.bind("<Button-1>", marcar_casilla)
        tabla.bind("<space>", marcar_con_teclado)
        filtro.trace_add("write", cargar_lista)
        cargar_lista()

    def iniciar_panel_biblioteca(self, panel, *, solo_bios=False):
        barra = ttk.Frame(panel)
        barra.pack(fill="x", pady=(0, 10))
        ttk.Button(barra, text="Actualizar sistemas",
                   command=lambda: self.ver_biblioteca(panel, solo_bios=solo_bios)).pack(side="left")
        if solo_bios:
            ttk.Button(barra, text="Verificar manifiesto MD5…", command=self.verificar_manifiesto).pack(
                side="left", padx=8)
        else:
            ttk.Button(barra, text="Verificar y gestionar duplicados…", command=self.ver_duplicados).pack(
                side="left", padx=8)
            ttk.Button(barra, text="Respaldos…", command=self.ver_respaldos).pack(side="left")
        panel.contenido = ttk.Frame(panel)
        panel.contenido.pack(fill="both", expand=True)

    def ver_respaldos(self):
        self.operar(self.mostrar_respaldos)

    def mostrar_respaldos(self, raiz):
        ventana = tk.Toplevel(self)
        ventana.title("Respaldos de la biblioteca")
        ventana.transient(self)
        ventana.geometry("860x490")
        ventana.minsize(660, 360)
        ventana.grab_set()
        panel = ttk.Frame(ventana, padding=12)
        panel.pack(fill="both", expand=True)
        resumen = tk.StringVar(ventana)
        mensaje = tk.StringVar(ventana)
        ttk.Label(panel, textvariable=resumen).pack(anchor="w", pady=(0, 8))

        listado = ttk.Frame(panel)
        listado.pack(fill="both", expand=True)
        tabla = ttk.Treeview(listado, columns=("contenido", "fecha", "tamano"), show="headings",
                             selectmode="extended")
        for campo, titulo, ancho in (("contenido", "Contenido del respaldo", 525), ("fecha", "Fecha", 145),
                                    ("tamano", "Tamaño", 110)):
            tabla.heading(campo, text=titulo)
            tabla.column(campo, width=ancho, stretch=campo == "contenido",
                         anchor="e" if campo == "tamano" else "w")
        scroll = ttk.Scrollbar(listado, command=tabla.yview)
        tabla.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        tabla.pack(fill="both", expand=True)

        detalle_panel = ttk.Frame(panel)
        detalle_panel.pack(fill="x", pady=8)
        detalle = tk.Text(detalle_panel, height=4, wrap="word", state="disabled", font="TkDefaultFont")
        scroll_detalle = ttk.Scrollbar(detalle_panel, command=detalle.yview)
        detalle.configure(yscrollcommand=scroll_detalle.set)
        scroll_detalle.pack(side="right", fill="y")
        detalle.pack(fill="x", expand=True)
        ttk.Label(panel, textvariable=mensaje).pack(anchor="w", pady=(0, 8))
        acciones = ttk.Frame(panel)
        acciones.pack(fill="x")
        por_fila = {}

        def tamano(respaldos):
            total = tamano_visible(sum(respaldo.bytes or 0 for respaldo in respaldos))
            if any(respaldo.bytes is None for respaldo in respaldos):
                return f"{total} medidos · hay tamaños desconocidos"
            return total

        def seleccionar(_=None):
            elegidos = [por_fila[item] for item in tabla.selection() if item in por_fila]
            boton_borrar.state(["!disabled" if elegidos and not self.ocupado else "disabled"])
            boton_vaciar.state(["!disabled" if por_fila and not self.ocupado else "disabled"])
            boton_actualizar.state(["disabled" if self.ocupado else "!disabled"])
            if len(elegidos) == 1:
                respaldo = elegidos[0]
                texto = "\n".join(respaldo.rutas) if respaldo.rutas else "Sin lista de rutas originales."
            elif elegidos:
                texto = f"{len(elegidos)} respaldos seleccionados · {tamano(elegidos)}"
            else:
                texto = "Usa Ctrl o Mayús para seleccionar varios respaldos." if por_fila else ""
            detalle.configure(state="normal")
            detalle.delete("1.0", "end")
            detalle.insert("1.0", texto)
            detalle.configure(state="disabled")

        def cargar(resultado=""):
            def revisar():
                try:
                    return listar_respaldos(raiz), None
                except (OSError, ValueError) as error:
                    return [], str(error)

            def mostrar(datos):
                if not ventana.winfo_exists():
                    return
                respaldos, error = datos
                tabla.delete(*tabla.get_children())
                por_fila.clear()
                for respaldo in respaldos:
                    contenido = respaldo.rutas[0] if respaldo.rutas else respaldo.carpeta.name
                    if len(respaldo.rutas) > 1:
                        contenido += f" (+{len(respaldo.rutas) - 1})"
                    fila = tabla.insert("", "end", values=(contenido, respaldo.fecha.strftime("%d-%m-%Y %H:%M:%S"),
                                                             tamano_visible(respaldo.bytes)))
                    por_fila[fila] = respaldo
                resumen.set(f"{len(respaldos)} respaldos · {tamano(respaldos)}" if respaldos else "No hay respaldos.")
                mensaje.set(resultado)
                seleccionar()
                if error:
                    resumen.set("No se pudo leer la carpeta de respaldos.")
                    messagebox.showerror("Respaldos", error, parent=ventana)

            if not self.ocupado:
                mensaje.set("Calculando el tamaño de los respaldos…")
                self.ejecutar(revisar, mostrar, mensaje.get())
                seleccionar()

        def borrar(*, todos=False):
            if self.ocupado:
                return
            elegidos = list(por_fila.values()) if todos else [por_fila[fila] for fila in tabla.selection()]
            if not elegidos:
                return
            titulo = "Vaciar respaldos" if todos else "Eliminar respaldos seleccionados"
            if not messagebox.askyesno(
                titulo, f"¿Eliminar definitivamente {len(elegidos)} respaldos?\n\n"
                f"Tamaño de los respaldos seleccionados: {tamano(elegidos)}.\n"
                "Los respaldos eliminados no se podrán restaurar.", parent=ventana, default=messagebox.NO,
            ) or self.ocupado:
                return

            def terminado(resultado):
                eliminados, errores = resultado
                informe = f"{eliminados} de {len(elegidos)} respaldos eliminados."
                self.estado.set(informe)
                if ventana.winfo_exists():
                    if errores:
                        detalles = "\n".join(errores[:4])
                        if len(errores) > 4:
                            detalles += f"\nY {len(errores) - 4} errores más."
                        messagebox.showwarning(titulo, f"{informe}\n\n{detalles}", parent=ventana)
                    cargar(informe)

            mensaje.set("Eliminando respaldos…")
            self.ejecutar(lambda: eliminar_respaldos(raiz, elegidos), terminado, mensaje.get())
            seleccionar()

        boton_actualizar = ttk.Button(acciones, text="Actualizar", command=cargar)
        boton_actualizar.pack(side="left")
        boton_borrar = ttk.Button(acciones, text="Eliminar seleccionados…", command=borrar)
        boton_borrar.pack(side="left", padx=8)
        boton_vaciar = ttk.Button(acciones, text="Vaciar respaldos…", command=lambda: borrar(todos=True))
        boton_vaciar.pack(side="left")
        ttk.Button(acciones, text="Cerrar", command=ventana.destroy).pack(side="right")
        tabla.bind("<<TreeviewSelect>>", seleccionar)
        cargar()

    def limpiar_paneles_biblioteca(self):
        for panel in (self.panel_bios, self.panel_biblioteca):
            for widget in panel.contenido.winfo_children():
                widget.destroy()

    def cambio_pestana(self, evento):
        pestañas = evento.widget
        seleccion = pestañas.select()
        if seleccion == str(self.panel_teknoparrot):
            self.panel_teknoparrot.actualizar()
        elif self.sistemas and seleccion in (str(self.panel_bios), str(self.panel_biblioteca)):
            panel = pestañas.nametowidget(seleccion)
            self.ver_biblioteca(panel, solo_bios=panel is self.panel_bios)

    def ver_biblioteca(self, panel, *, solo_bios=False):
        def revisar(raiz):
            sistemas = self.sistemas.copy()

            def mostrar(filas):
                if Path(self.raiz.get()) != raiz or self.sistemas != sistemas:
                    return
                for widget in panel.contenido.winfo_children():
                    widget.destroy()
                self.mostrar_biblioteca(raiz, sistemas, filas, panel.contenido, solo_bios=solo_bios)

            self.ejecutar(
                lambda informar: biblioteca_instalada(raiz, sistemas, informar),
                mostrar, "Revisando la biblioteca de este PC…", con_progreso=True,
            )
        self.operar(revisar)

    def mostrar_biblioteca(self, raiz, sistemas, filas, ventana, *, solo_bios=False):
        resumen = ttk.Label(ventana, text=f"{raiz} · {len(filas)} sistemas con juegos")
        resumen.pack(anchor="w", pady=(0, 8))
        botones = ttk.Frame(ventana, padding=8)
        botones.pack(side="bottom", fill="x")
        tabla = ttk.Treeview(ventana, columns=("juegos", "bios"), show="tree headings", selectmode="browse")
        tabla.heading("#0", text="Sistema" if solo_bios else "Sistema / categoría / juego")
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
        rutas = {}
        sistemas_fila = set()
        for clave, nombre, bios, categorias in filas:
            estado = self.estados_bios.get((raiz.resolve(), clave), bios)
            item = tabla.insert("", "end", text=nombre, values=(sum(map(len, categorias.values())), estado))
            claves[item] = clave
            sistemas_fila.add(item)
            if solo_bios:
                continue
            for categoria, juegos in sorted(categorias.items(), key=lambda par: par[0].casefold()):
                hijo = tabla.insert(item, "end", text=categoria, values=(len(juegos), ""))
                claves[hijo] = clave
                for ruta, titulo in juegos:
                    fila = tabla.insert(hijo, "end", text=titulo)
                    claves[fila] = clave
                    rutas[fila] = ruta

        def seleccion_valida():
            seleccion = tabla.selection()
            if not seleccion or self.ocupado:
                return None
            item = seleccion[0]
            clave = claves[item]
            if Path(self.raiz.get()) != raiz or self.sistemas.get(clave) != sistemas[clave]:
                messagebox.showinfo("Biblioteca", "La instalación cambió. Abre nuevamente su biblioteca.", parent=ventana)
                return None
            return item

        def accion(agregar=False):
            item = seleccion_valida()
            if item:
                self.preparar_bios(raiz, claves[item], agregar=agregar)

        def editar():
            item = seleccion_valida()
            if item not in rutas:
                return
            ruta = rutas[item]
            nombre = simpledialog.askstring("Editar nombre", "Nombre que se mostrará en RetroBat",
                                           initialvalue=tabla.item(item, "text"), parent=ventana)
            if nombre is None:
                return
            try:
                entrada = Entrada(sistemas[claves[item]], ruta, None, marca_archivo(ruta))
                titulo = editar_nombre(raiz, entrada, nombre)
            except (OSError, ValueError, ParseError) as error:
                messagebox.showerror("Editar nombre", str(error), parent=ventana)
                return
            tabla.item(item, text=titulo)
            self.estado.set(f"Nombre guardado: {titulo}. Recarga la lista de juegos en RetroBat.")

        def quitar():
            item = seleccion_valida()
            if item not in rutas:
                return
            ruta = rutas[item]
            try:
                entrada = Entrada(sistemas[claves[item]], ruta, None, marca_archivo(ruta))
            except OSError as error:
                messagebox.showerror("Eliminar juego", str(error), parent=ventana)
                return

            def confirmar(plan):
                if not ventana.winfo_exists():
                    return
                if Path(self.raiz.get()) != raiz:
                    messagebox.showinfo("Biblioteca", "La instalación cambió.", parent=ventana)
                    return
                archivos = "\n".join(str(archivo) for archivo, _ in plan)
                aviso = ("\nSolo se retirará el acceso directo."
                         if ruta.suffix.lower() == ".lnk" and len(plan) == 1 and plan[0][0] == ruta else "")
                if not messagebox.askyesno(
                    "Eliminar juego", f"¿Eliminar {tabla.item(item, 'text')} de RetroBat?\n\n"
                    f"{archivos}{aviso}\n\nLos archivos se moverán a un respaldo recuperable.",
                    parent=ventana,
                ):
                    return

                def terminar(respaldo):
                    self.estado.set(f"Juego eliminado de la biblioteca. Respaldo: {respaldo}")
                    if ventana.winfo_exists():
                        retirados = [fila for fila, archivo in rutas.items()
                                     if any(archivo.is_relative_to(destino) for destino, _ in plan)]
                        for fila in retirados:
                            categoria = tabla.parent(fila)
                            sistema = tabla.parent(categoria)
                            tabla.delete(fila)
                            for padre in (categoria, sistema):
                                cantidad = int(tabla.set(padre, "juegos")) - 1
                                tabla.set(padre, "juegos", cantidad)
                            rutas.pop(fila)
                            claves.pop(fila)
                        seleccionar(None)

                self.ejecutar(lambda: eliminar_juego(raiz, entrada, plan), terminar, "Retirando el juego…")

            self.ejecutar(lambda: plan_eliminar(raiz, entrada), confirmar, "Revisando los archivos del juego…")

        def quitar_sistema():
            item = seleccion_valida()
            if item not in sistemas_fila:
                return
            sistema = sistemas[claves[item]]
            carpeta = sistema.carpeta
            if not messagebox.askyesno(
                "Eliminar sistema", f"¿Retirar todos los juegos de {sistema.nombre}?\n\n{carpeta}"
                "\n\nLa carpeta se moverá a un respaldo. Se conservarán los emuladores, "
                "las partidas guardadas y las instalaciones de Windows fuera de esta carpeta.", parent=ventana,
            ):
                return

            def retirar():
                base = (raiz / "roms").resolve()
                if carpeta.resolve() != carpeta or carpeta == base or not carpeta.is_relative_to(base):
                    raise ValueError("La carpeta ya no está dentro de la biblioteca de RetroBat.")
                return guardar_respaldo(raiz, [carpeta], mover=True)

            def terminado(respaldo):
                self.cargar_categorias()
                self.estado.set(f"Sistema retirado. Respaldo: {respaldo}")
                if ventana.winfo_exists():
                    for fila in tabla.get_children():
                        if sistemas[claves[fila]].carpeta.is_relative_to(carpeta):
                            tabla.delete(fila)
                    resumen.configure(text=f"{raiz} · {len(tabla.get_children())} sistemas con juegos")
                    seleccionar(None)

            self.ejecutar(retirar, terminado, "Retirando el sistema…")

        if solo_bios:
            buscar = ttk.Button(botones, text="Verificar / buscar BIOS…", command=accion, state="disabled")
            buscar.pack(side="left", padx=(0, 6))
            agregar = ttk.Button(botones, text="Agregar BIOS desde carpeta…", command=lambda: accion(True),
                                 state="disabled")
            agregar.pack(side="left")
        else:
            borrar = ttk.Button(botones, text="Eliminar juego…", command=quitar, state="disabled")
            borrar.pack(side="right")
            renombrar = ttk.Button(botones, text="Editar nombre…", command=editar, state="disabled")
            renombrar.pack(side="right", padx=6)
            retirar = ttk.Button(botones, text="Eliminar sistema…", command=quitar_sistema, state="disabled")
            retirar.pack(side="left")

        def seleccionar(_):
            seleccion = tabla.selection()
            item = seleccion[0] if seleccion else None
            if solo_bios:
                disponible = item in sistemas_fila and sistemas[claves[item]].identificador not in NO_REQUIERE_BIOS
                buscar.configure(state="normal" if disponible else "disabled")
                agregar.configure(state="normal" if disponible else "disabled")
            else:
                estado = "normal" if item in rutas else "disabled"
                renombrar.configure(state=estado)
                borrar.configure(state=estado)
                retirar.configure(state="normal" if item in sistemas_fila else "disabled")

        tabla.bind("<<TreeviewSelect>>", seleccionar)
        def refrescar_bios(_):
            for item in tabla.get_children():
                estado = self.estados_bios.get((raiz.resolve(), claves[item]))
                if estado:
                    tabla.set(item, "bios", estado)

        tabla.bind("<FocusIn>", refrescar_bios)

    def verificar_manifiesto(self):
        def revisar(raiz):
            archivo = filedialog.askopenfilename(title="Manifiesto de BIOS (MD5 y ruta relativa)", parent=self)
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

    def importar_musica(self):
        def elegir(raiz):
            elegidas = filedialog.askopenfilenames(
                title="Elige la música para el menú de RetroBat",
                filetypes=[("Música", "*.mp3 *.ogg *.wav *.flac")], parent=self)
            if not elegidas:
                return
            destino = raiz / "emulationstation" / ".emulationstation" / "music"

            def instalar(informar):
                copiadas, existentes, errores = 0, 0, []
                for ruta in map(Path, elegidas):
                    salida = destino / ruta.name
                    if ruta.suffix.lower() not in {".mp3", ".ogg", ".wav", ".flac"}:
                        errores.append(f"{ruta.name}: formato no admitido.")
                        continue
                    try:
                        copiar_con_progreso(ruta, salida, informar, f"Copiando {ruta.name}…")
                    except FileExistsError:
                        if salida.is_file():
                            existentes += 1
                        else:
                            errores.append(f"{ruta.name}: el destino ya está ocupado.")
                    except (OSError, ValueError) as error:
                        errores.append(f"{ruta.name}: {error}")
                    else:
                        copiadas += 1
                return copiadas, existentes, errores

            def terminar(resultado):
                copiadas, existentes, errores = resultado
                self.estado.set(f"Música: {copiadas} copiadas · {existentes} nombres existentes · {len(errores)} errores.")
                if errores:
                    self.informe("Archivos de música pendientes", errores)

            self.ejecutar(instalar, terminar, "Importando música…", con_progreso=True)
        self.operar(elegir)

    def eliminar_tema(self):
        def elegir(raiz):
            temas = raiz.resolve() / "emulationstation" / ".emulationstation" / "themes"
            if not temas.is_dir():
                raise ValueError("No hay una carpeta de temas en esta instalación.")
            elegida = filedialog.askdirectory(title="Selecciona el tema instalado que quieres eliminar",
                                              initialdir=temas, parent=self)
            if not elegida:
                return
            tema = Path(elegida)
            if tema.parent != temas or tema.resolve() != tema:
                raise ValueError("Selecciona una carpeta de tema instalada directamente dentro de themes.")
            marca = marca_archivo(tema)
            if not messagebox.askyesno(
                "Eliminar tema", f"¿Retirar {tema.name} de RetroBat?\n\n{tema}\n\n"
                "Se moverá a un respaldo. Si está activo, elige otro tema en RetroBat.", parent=self,
            ):
                return

            def retirar():
                if tema.resolve() != tema or marca_archivo(tema) != marca:
                    raise ValueError("La carpeta del tema cambió. Selecciónala de nuevo.")
                respaldos = raiz / "user" / "tecnotics-gestor" / "temas-retirados"
                respaldos.mkdir(parents=True, exist_ok=True)
                carpeta = Path(tempfile.mkdtemp(dir=respaldos))
                destino = carpeta / tema.name
                try:
                    tema.rename(destino)
                except OSError:
                    carpeta.rmdir()
                    raise
                return destino

            self.ejecutar(retirar, lambda destino: self.estado.set(f"Tema retirado. Respaldo: {destino}"),
                          "Retirando el tema…")
        self.operar(elegir)

    def importar_tema(self):
        def elegir(raiz):
            carpeta = filedialog.askdirectory(
                title="Selecciona la carpeta que contiene theme.xml", parent=self)
            if not carpeta:
                return
            origen = Path(carpeta).resolve()
            destino, imagenes = inspeccionar_tema(raiz, origen)
            ventana = tk.Toplevel(self)
            ventana.title("Vista previa del tema")
            ventana.transient(self)
            panel = ttk.Frame(ventana, padding=16)
            panel.pack(fill="both", expand=True)
            ttk.Label(panel, text=origen.name, font=("Segoe UI", 14, "bold")).pack(anchor="w")

            vista = ttk.Label(panel, text="El tema no incluye una imagen de vista previa.",
                             anchor="center")
            vista.pack(fill="both", expand=True, pady=8)
            for imagen in imagenes:
                try:
                    with Image.open(imagen) as original:
                        miniatura = ImageOps.contain(original.convert("RGBA"), (640, 360))
                    vista.foto = ImageTk.PhotoImage(miniatura, master=ventana)
                except (OSError, ValueError, Image.DecompressionBombError):
                    continue
                vista.configure(image=vista.foto)
                ttk.Label(panel, text=f"Imagen del tema · {imagen.name}").pack(anchor="w")
                break

            ttk.Label(panel, text=f"Destino: {destino}", wraplength=640).pack(anchor="w")
            progreso = ttk.Label(panel, wraplength=640)
            progreso.pack(anchor="w", pady=(8, 0))
            acciones = ttk.Frame(panel)
            acciones.pack(fill="x", pady=(12, 0))
            ttk.Button(acciones, text="Cerrar", command=ventana.destroy).pack(side="right")

            def instalar():
                if self.ocupado:
                    return
                if raiz != Path(self.raiz.get()) or not (raiz / "retrobat.exe").is_file():
                    messagebox.showerror("Importar tema", "La instalación seleccionada cambió. "
                                         "Vuelve a abrir la vista previa.", parent=ventana)
                    return
                progreso.configure(textvariable=self.detalle_progreso)

                def terminar(_):
                    mensaje = f"Tema instalado: {origen.name}. Selecciónalo en RetroBat."
                    self.estado.set(mensaje)
                    if ventana.winfo_exists():
                        progreso.configure(textvariable="", text=mensaje)
                        boton.configure(state="disabled")

                self.ejecutar(
                    lambda informar: copiar_con_progreso(origen, destino, informar, "Copiando el tema…"),
                    terminar, "Preparando la copia del tema…", con_progreso=True,
                )

            boton = ttk.Button(acciones, text="Instalar en RetroBat", command=instalar)
            boton.pack(side="right", padx=8)
        self.operar(elegir)

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
            formatos_compresion = ejecutar_7zip("i", "-sccUTF-8")
            if not all(formato in formatos_compresion for formato in ("7z", "Rar", "zip")):
                raise RuntimeError("El portable no incluye los formatos de 7-Zip esperados.")
            contexto = contexto_tls()
            if not contexto.check_hostname:
                raise RuntimeError("La validación TLS debe comprobar el nombre del servidor.")
            app = Gestor()
            app.update()
            titulos = tuple(app.pestañas.tab(pagina, "text") for pagina in app.pestañas.tabs())
            if titulos != ("Inicio", "Cargar juegos", "BIOS", "Biblioteca", "Configurar RetroBat", "TeknoParrot"):
                raise RuntimeError(f"Pestañas inesperadas: {titulos}")
            app.destroy()
            informe.write_text("OK\n", encoding="utf-8")
        except Exception:
            import traceback
            informe.write_text(traceback.format_exc(), encoding="utf-8")
            raise SystemExit(1) from None
    else:
        Gestor().mainloop()
