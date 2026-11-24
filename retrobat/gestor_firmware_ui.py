"""Pestaña de firmware del gestor de RetroBat."""

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser

from gestor_firmware import (FALTA, GUIA_BIOS, abrir_ryujinx, aplicar_firmware, revisar_firmware)

TODOS = "Todos los sistemas"
AUTOMATICAS = {"Descarga oficial", "Instalar"}


def nombre_archivo(requisito):
    return "Firmware (.nca)" if requisito.tipo in {"nca", "ryujinx"} else requisito.destino.name


class PanelFirmware(ttk.Frame):
    def __init__(self, padre, app):
        super().__init__(padre, padding=16)
        self.app = app
        self.raiz = None
        self.filas = []
        self.visibles = {}
        self.filtro = tk.StringVar(value=TODOS)
        self.detalle = tk.StringVar(value="Selecciona una instalación de RetroBat en Inicio.")
        self.aviso = tk.StringVar()

        opciones = ttk.Frame(self)
        opciones.pack(fill="x", pady=(0, 8))
        ttk.Label(opciones, text="Sistema").pack(side="left")
        self.selector = ttk.Combobox(opciones, textvariable=self.filtro, state="readonly", width=33,
                                     values=(TODOS,))
        self.selector.pack(side="left", padx=8)
        self.selector.bind("<<ComboboxSelected>>", lambda _: self.mostrar_filas())
        ttk.Button(opciones, text="Comprobar firmware", command=self.actualizar).pack(side="left")
        ttk.Label(self, textvariable=self.aviso, wraplength=720).pack(anchor="w")

        tabla = ttk.Frame(self)
        tabla.pack(fill="both", expand=True, pady=6)
        self.tabla = ttk.Treeview(tabla, columns=("sistema", "archivo", "estado", "accion"), show="headings")
        for columna, etiqueta, ancho in (
            ("sistema", "Sistema", 210), ("archivo", "Archivo", 235),
            ("estado", "Estado", 182), ("accion", "Acción disponible", 155),
        ):
            self.tabla.heading(columna, text=etiqueta)
            self.tabla.column(columna, width=ancho, minwidth=95)
        barra = ttk.Scrollbar(tabla, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.tabla.pack(fill="both", expand=True)
        self.tabla.bind("<<TreeviewSelect>>", self.seleccionar)

        ttk.Label(self, textvariable=self.detalle, wraplength=720).pack(fill="x", pady=(0, 6))
        acciones = ttk.Frame(self)
        acciones.pack(fill="x")
        self.boton_instalar = ttk.Button(acciones, text="Instalar seleccionados…", command=self.instalar)
        self.boton_instalar.pack(side="left", padx=(0, 6))
        self.boton_disponibles = ttk.Button(acciones, text="Instalar disponibles…",
                                             command=lambda: self.instalar(todos=True))
        self.boton_disponibles.pack(side="left", padx=(0, 6))
        self.boton_importar = ttk.Button(acciones, text="Importar copias locales…", command=self.importar)
        self.boton_importar.pack(side="left", padx=(0, 6))
        self.boton_ryujinx = ttk.Button(acciones, text="Abrir Ryujinx", command=self.ryujinx)
        self.boton_ryujinx.pack(side="left", padx=(0, 6))
        ttk.Button(acciones, text="Ver guía", command=self.guia).pack(side="right")
        self.seleccionar()

    def limpiar(self):
        self.raiz = None
        self.filas = []
        self.aviso.set("")
        self.mostrar_filas()

    def actualizar(self, sistema=None):
        if not self.app.raiz.get():
            return

        def revisar(raiz):
            raiz = raiz.resolve()
            sistemas = self.app.sistemas.copy()

            def mostrar(resultado):
                if Path(self.app.raiz.get()).resolve() != raiz:
                    return
                self.raiz = raiz
                self.filas, aviso = resultado
                self.aviso.set(aviso)
                nombres = sorted({fila.requisito.sistema for fila in self.filas}, key=str.casefold)
                self.selector.configure(values=(TODOS, *nombres))
                if sistema in nombres:
                    self.filtro.set(sistema)
                if self.filtro.get() not in nombres:
                    self.filtro.set(TODOS)
                self.mostrar_filas()

            self.app.ejecutar(lambda informar: revisar_firmware(raiz, sistemas, informar), mostrar,
                              "Comprobando el firmware…", con_progreso=True)

        self.app.operar(revisar)

    def mostrar_filas(self):
        filtro = self.filtro.get()
        self.tabla.delete(*self.tabla.get_children())
        self.visibles.clear()
        for fila in self.filas:
            requisito = fila.requisito
            if filtro != TODOS and requisito.sistema != filtro:
                continue
            item = self.tabla.insert("", "end", values=(
                requisito.sistema, nombre_archivo(requisito), fila.estado, fila.accion or "—",
            ))
            self.visibles[item] = fila
        self.seleccionar()

    def seleccion(self):
        return [self.visibles[item] for item in self.tabla.selection() if item in self.visibles]

    def seleccionar(self, _=None):
        seleccionadas = self.seleccion()
        self.boton_instalar.configure(state="normal" if any(fila.accion in AUTOMATICAS
                                                           for fila in seleccionadas) else "disabled")
        self.boton_disponibles.configure(state="normal" if any(
            fila.accion in AUTOMATICAS and not fila.requisito.opcional for fila in self.visibles.values())
            else "disabled")
        self.boton_importar.configure(state="normal" if any(self.admite_importacion(fila)
                                                           for fila in seleccionadas) else "disabled")
        puede_ryujinx = (len(seleccionadas) == 1 and seleccionadas[0].requisito.tipo == "ryujinx"
                         and seleccionadas[0].requisito.emulador.is_file())
        self.boton_ryujinx.configure(state="normal" if puede_ryujinx else "disabled")
        if not self.raiz:
            self.detalle.set("Selecciona una instalación de RetroBat en Inicio." if not self.app.raiz.get()
                             else "Pulsa Comprobar firmware para revisar esta instalación.")
        elif not seleccionadas:
            self.detalle.set("Selecciona archivos para instalar o importar. Usa Ctrl o Mayús para elegir varios.")
        elif len(seleccionadas) > 1:
            self.detalle.set(f"{len(seleccionadas)} archivos seleccionados.")
        else:
            fila = seleccionadas[0]
            requisito = fila.requisito
            destino = requisito.destino.relative_to(self.raiz)
            notas = []
            if requisito.emulador and requisito.paquete:
                notas.append(str(requisito.emulador.relative_to(self.raiz)))
            if requisito.grupo:
                notas.append("Una variante compatible de este grupo es suficiente.")
            elif requisito.opcional:
                notas.append("Depende del emulador o del juego.")
            if requisito.tipo == "ryujinx":
                notas.append("Abre Ryujinx y usa Tools → Install Firmware con tu copia local.")
            self.detalle.set(" · ".join([str(destino), *notas]))

    @staticmethod
    def admite_importacion(fila):
        return (fila.estado == FALTA and fila.requisito.tipo != "ryujinx"
                and (not fila.requisito.emulador or fila.requisito.emulador.is_file()))

    def instalar(self, *, todos=False):
        origen = self.visibles.values() if todos else self.seleccion()
        filas = [fila for fila in origen if fila.accion in AUTOMATICAS
                 and (not todos or not fila.requisito.opcional)]
        if not filas or self.app.ocupado:
            return
        if messagebox.askyesno("Firmware", f"¿Preparar {len(filas)} archivos de firmware? "
                               "Cierra los emuladores antes de continuar.", parent=self):
            self.aplicar(filas)

    def importar(self):
        filas = [fila for fila in self.seleccion() if self.admite_importacion(fila)]
        if not filas or self.app.ocupado:
            return
        origen = filedialog.askdirectory(title="Carpeta con tus copias de firmware", parent=self)
        if origen:
            self.aplicar(filas, Path(origen))

    def aplicar(self, filas, origen=None):
        def iniciar(raiz):
            if self.raiz != raiz.resolve():
                self.actualizar()
                return

            def terminar(resultados):
                self.app.informe("Resultado del firmware", resultados)
                if Path(self.app.raiz.get()).resolve() == raiz.resolve():
                    self.actualizar()

            self.app.ejecutar(lambda informar: aplicar_firmware(raiz, filas, origen, informar),
                              terminar, "Preparando el firmware…", con_progreso=True)

        self.app.operar(iniciar)

    def ryujinx(self):
        seleccionadas = self.seleccion()
        if len(seleccionadas) == 1 and seleccionadas[0].requisito.tipo == "ryujinx":
            self.app.operar(lambda raiz: abrir_ryujinx(raiz, seleccionadas[0].requisito)
                            if raiz.resolve() == self.raiz else self.actualizar())

    def guia(self):
        seleccionadas = self.seleccion()
        webbrowser.open(seleccionadas[0].requisito.guia if seleccionadas else GUIA_BIOS)
