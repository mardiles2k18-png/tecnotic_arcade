"""Pestaña de instalación y elección de emuladores."""

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser

from gestor_emuladores import EXTERNOS, GUIA, activar_emulador, instalar_emulador, revisar_emuladores

TODOS = "Todos los sistemas"


class PanelEmuladores(ttk.Frame):
    def __init__(self, padre, app):
        super().__init__(padre, padding=16)
        self.app = app
        self.raiz = None
        self.filas = []
        self.visibles = {}
        self.sistema = tk.StringVar(value=TODOS)
        self.busqueda = tk.StringVar()
        self.detalle = tk.StringVar()

        filtros = ttk.Frame(self)
        filtros.pack(fill="x", pady=(0, 8))
        ttk.Label(filtros, text="Sistema").pack(side="left")
        self.selector = ttk.Combobox(filtros, textvariable=self.sistema, width=28, state="readonly", values=(TODOS,))
        self.selector.pack(side="left", padx=8)
        self.selector.bind("<<ComboboxSelected>>", lambda _: self.mostrar())
        ttk.Button(filtros, text="Actualizar lista", command=self.actualizar).pack(side="right")
        ttk.Label(filtros, text="Buscar").pack(side="left", padx=(6, 5))
        ttk.Entry(filtros, textvariable=self.busqueda).pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.busqueda.trace_add("write", lambda *_: self.mostrar())

        contenedor = ttk.Frame(self)
        contenedor.pack(fill="both", expand=True)
        self.tabla = ttk.Treeview(contenedor, columns=("nombre", "estado", "fuente", "version"), show="headings")
        for columna, nombre, ancho in (("nombre", "Emulador o núcleo", 230), ("estado", "Estado", 190),
                                       ("fuente", "Fuente", 165), ("version", "Versión publicada", 130)):
            self.tabla.heading(columna, text=nombre)
            self.tabla.column(columna, width=ancho, minwidth=95)
        barra = ttk.Scrollbar(contenedor, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.tabla.pack(fill="both", expand=True)
        self.tabla.bind("<<TreeviewSelect>>", self.seleccionar)

        ttk.Label(self, textvariable=self.detalle, wraplength=740).pack(fill="x", pady=8)
        acciones = ttk.Frame(self)
        acciones.pack(fill="x")
        self.boton_instalar = ttk.Button(acciones, text="Instalar seleccionados…", command=self.instalar)
        self.boton_instalar.pack(side="left", padx=(0, 6))
        self.boton_importar = ttk.Menubutton(acciones, text="Importar copia…")
        menu = tk.Menu(self.boton_importar, tearoff=False)
        menu.add_command(label="Archivo comprimido…", command=lambda: self.importar(carpeta=False))
        menu.add_command(label="Carpeta del emulador…", command=lambda: self.importar(carpeta=True))
        self.boton_importar.configure(menu=menu)
        self.boton_importar.pack(side="left", padx=(0, 6))
        self.boton_configurar = ttk.Button(acciones, text="Usar para un sistema…", command=self.configurar)
        self.boton_configurar.pack(side="left", padx=(0, 6))
        ttk.Button(acciones, text="Ver fuente", command=self.fuente).pack(side="right")
        self.seleccionar()

    def limpiar(self):
        self.raiz = None
        self.filas = []
        self.selector.configure(values=(TODOS,))
        self.sistema.set(TODOS)
        self.mostrar()

    def actualizar(self):
        if not self.app.raiz.get():
            return

        def iniciar(raiz):
            raiz = raiz.resolve()

            def terminar(filas):
                if Path(self.app.raiz.get()).resolve() != raiz:
                    return
                self.raiz = raiz
                self.filas = filas
                sistemas = {v.nombre for fila in filas for v in fila.emulador.vinculos}
                self.selector.configure(values=(TODOS, *sorted(sistemas, key=str.casefold)))
                if self.sistema.get() not in sistemas:
                    self.sistema.set(TODOS)
                self.mostrar()

            self.app.ejecutar(lambda informar: revisar_emuladores(raiz, informar), terminar,
                              "Comprobando emuladores…", con_progreso=True)

        self.app.operar(iniciar)

    def mostrar(self):
        sistema = self.sistema.get()
        consulta = self.busqueda.get().strip().casefold()
        elegidos = {fila.emulador for fila in self.seleccion()}
        self.tabla.delete(*self.tabla.get_children())
        self.visibles.clear()
        for fila in self.filas:
            item = fila.emulador
            sistemas = {v.nombre for v in item.vinculos}
            if sistema != TODOS and sistema not in sistemas:
                continue
            if consulta and consulta not in f"{item.nombre} {' '.join(sistemas)}".casefold():
                continue
            if fila.instalado:
                estado = "Instalado · seleccionado" if fila.configurado else "Instalado"
            elif item.via_automatica:
                estado = "Disponible" if fila.version else "Consultar paquete"
            else:
                estado = "Requiere copia local" if item.carpetas else "Instalación externa"
            id_fila = self.tabla.insert("", "end", values=(item.nombre, estado, item.origen, fila.version or "—"))
            self.visibles[id_fila] = fila
            if item in elegidos:
                self.tabla.selection_add(id_fila)
        self.seleccionar()

    def seleccion(self):
        return [self.visibles[clave] for clave in self.tabla.selection() if clave in self.visibles]

    def seleccionar(self, _=None):
        filas = self.seleccion()
        fila = filas[0] if len(filas) == 1 else None
        self.boton_instalar.configure(state="normal" if any(not f.instalado and f.emulador.via_automatica
                                                            for f in filas) else "disabled")
        importar = fila and not fila.instalado and fila.emulador.carpetas and fila.emulador.id != "teknoparrot"
        self.boton_importar.configure(state="normal" if importar else "disabled")
        self.boton_configurar.configure(state="normal" if fila and fila.instalado and fila.emulador.vinculos
                                        else "disabled")
        if fila:
            sistemas = sorted({v.nombre for v in fila.emulador.vinculos}, key=str.casefold)
            aplicados = f" · Seleccionado para {', '.join(fila.configurado)}" if fila.configurado else ""
            archivo = str(fila.instalado.relative_to(self.raiz)) if fila.instalado else fila.emulador.origen
            muestra = ", ".join(sistemas[:5]) + (f" y {len(sistemas) - 5} más" if len(sistemas) > 5 else "")
            self.detalle.set(" · ".join(filter(None, (archivo, muestra))) + aplicados)
        elif filas:
            self.detalle.set(f"{len(filas)} elementos seleccionados.")
        elif self.raiz:
            self.detalle.set(f"{len(self.visibles)} emuladores y núcleos. Usa Ctrl o Mayús para seleccionar varios.")
        else:
            self.detalle.set("Selecciona una instalación de RetroBat en Inicio.")

    def instalar(self):
        emuladores = [f.emulador for f in self.seleccion() if not f.instalado and f.emulador.via_automatica]
        if self.app.ocupado or not emuladores:
            return
        if messagebox.askyesno("Emuladores", f"¿Instalar {len(emuladores)} elementos en RetroBat? "
                               "Cierra RetroBat y los emuladores antes de continuar.", parent=self):
            self.aplicar(emuladores)

    def importar(self, *, carpeta):
        filas = self.seleccion()
        if self.app.ocupado or len(filas) != 1:
            return
        if carpeta:
            origen = filedialog.askdirectory(title="Carpeta del emulador oficial", parent=self)
        else:
            origen = filedialog.askopenfilename(title="Paquete portable del emulador",
                                                filetypes=[("Paquete comprimido", "*.zip *.7z *.rar")], parent=self)
        if origen:
            self.aplicar([filas[0].emulador], Path(origen))

    def aplicar(self, emuladores, local=None):
        def iniciar(raiz):
            if raiz.resolve() != self.raiz:
                self.actualizar()
                return

            def tarea(informar):
                resultados = []
                for item in emuladores:
                    try:
                        exe, detalle = instalar_emulador(raiz, item, local, informar)
                        if not exe:
                            raise ValueError(detalle or "Faltan componentes del emulador.")
                        texto = f"Instalado en {exe.relative_to(raiz.resolve())}"
                        if detalle:
                            texto += f"\n{detalle}"
                    except (OSError, ValueError) as error:
                        texto = str(error)
                    resultados.append(f"{item.nombre} — {texto}")
                return resultados

            def terminar(resultados):
                self.app.informe("Resultado de la instalación", resultados)
                self.actualizar()

            self.app.ejecutar(tarea, terminar, "Preparando emuladores…", con_progreso=True)

        self.app.operar(iniciar)

    def configurar(self):
        filas = self.seleccion()
        if self.app.ocupado or len(filas) != 1 or not filas[0].instalado:
            return
        item = filas[0].emulador
        opciones = {
            f"{v.nombre} [{v.sistema}]" + (f" · {v.emulador}/{v.nucleo}" if v.nucleo else ""): v
            for v in item.vinculos if self.sistema.get() in {TODOS, v.nombre}
        }
        if not opciones:
            return
        dialogo = tk.Toplevel(self)
        dialogo.title(f"Usar {item.nombre} en RetroBat")
        dialogo.transient(self.app)
        dialogo.resizable(False, False)
        panel = ttk.Frame(dialogo, padding=14)
        panel.pack(fill="both", expand=True)
        ttk.Label(panel, text="Sistema que usará este emulador").pack(anchor="w")
        selector = ttk.Combobox(panel, values=list(opciones), state="readonly", width=48)
        selector.current(0)
        selector.pack(fill="x", pady=(6, 8))
        ttk.Label(panel, text="Cierra RetroBat antes de guardar los ajustes.").pack(anchor="w", pady=(0, 8))

        def guardar():
            vinculo = opciones[selector.get()]

            def aplicar(raiz):
                if raiz.resolve() != self.raiz:
                    return
                respaldo = activar_emulador(raiz, item, vinculo)
                texto = f"{vinculo.nombre} usará {item.nombre} al abrir juegos desde RetroBat."
                if respaldo:
                    texto += f"\nRespaldo de los ajustes: {respaldo}"
                self.app.informe("Emulador seleccionado", [texto])
                dialogo.destroy()
                self.actualizar()

            self.app.operar(aplicar)

        ttk.Button(panel, text="Guardar", command=guardar).pack(side="right")
        ttk.Button(panel, text="Cancelar", command=dialogo.destroy).pack(side="right", padx=6)
        dialogo.grab_set()
        selector.focus_set()

    def fuente(self):
        filas = self.seleccion()
        item = filas[0].emulador if len(filas) == 1 else None
        webbrowser.open(EXTERNOS.get(item.id, "https://docs.libretro.com/" if item.nucleo else GUIA)
                        if item else GUIA)
