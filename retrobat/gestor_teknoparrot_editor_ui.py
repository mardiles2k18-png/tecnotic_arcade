"""Ventana de controles por juego y comprobación visual del mando."""
from time import monotonic
import tkinter as tk
from tkinter import messagebox, ttk
from xml.etree.ElementTree import ParseError

from controller_studio import VistaMando
from gestor_mandos_lectura import abrir_lector
from gestor_mandos_windows import detectar_mandos
from gestor_teknoparrot_controles import BOTONES_XI, DOCUMENTACION_MANDOS, juegos_con_mandos
from gestor_teknoparrot_diagnostico import ficha_url
import gestor_teknoparrot_editor as editor


class EditorMandos(tk.Toplevel):
    def __init__(self, panel, raiz):
        super().__init__(panel)
        self.app = panel.app
        self.raiz = raiz
        self.title("Configurar mandos por juego · TeknoParrot")
        self.geometry("1060x660")
        self.minsize(875, 570)
        self.transient(panel.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", self.cerrar)
        self.juegos = {}
        self.mandos = {}
        self.edicion = None
        self.lector = None
        self.temporizador = None
        self.proceso = None
        self.captura = None
        self.activas = set()
        self.nombres = {}
        self.borrador = {}
        self.base = {}
        self.guardada = {}
        self.seleccion = ()
        self.instalados_sin_perfil = []

        cuerpo = ttk.Frame(self, padding=15)
        cuerpo.pack(fill="both", expand=True)
        superior = ttk.Frame(cuerpo)
        superior.pack(fill="x")
        superior.columnconfigure(1, weight=3)
        superior.columnconfigure(3, weight=2)
        ttk.Label(superior, text="Juego instalado").grid(row=0, column=0, padx=(0, 7))
        self.juego = ttk.Combobox(superior, state="readonly")
        self.juego.grid(row=0, column=1, sticky="ew", padx=(0, 12))
        ttk.Label(superior, text="Mando").grid(row=0, column=2, padx=(0, 7))
        self.mando = ttk.Combobox(superior, state="readonly")
        self.mando.grid(row=0, column=3, sticky="ew", padx=(0, 12))
        self.jugador = ttk.Combobox(superior, state="readonly", width=10, values=("Jugador 1", "Jugador 2",
                                                                                    "Jugador 3", "Jugador 4"))
        self.jugador.current(0)
        self.jugador.grid(row=0, column=4)
        for selector in (self.juego, self.mando, self.jugador):
            selector.bind("<<ComboboxSelected>>", self.cargar)
        self.fuente = ttk.Label(cuerpo)
        self.fuente.pack(anchor="w", pady=(7, 8))

        contenido = ttk.Frame(cuerpo)
        contenido.pack(fill="both", expand=True)
        contenido.rowconfigure(0, weight=1)
        contenido.columnconfigure(0, weight=3)
        contenido.columnconfigure(1, weight=2)
        izquierda = ttk.Frame(contenido)
        izquierda.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        lista = ttk.Frame(izquierda)
        lista.pack(fill="both", expand=True)
        self.tabla = ttk.Treeview(lista, columns=("accion", "guardado", "asignacion"), show="headings", selectmode="browse")
        for columna, titulo, ancho in (("accion", "Acción del juego", 176), ("guardado", "Guardado", 105),
                                       ("asignacion", "Nueva asignación", 130)):
            self.tabla.heading(columna, text=titulo)
            self.tabla.column(columna, width=ancho, minwidth=70)
        scroll = ttk.Scrollbar(lista, command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tabla.pack(fill="both", expand=True)
        self.tabla.tag_configure("activa", background="#c8f3e5")
        self.tabla.bind("<<TreeviewSelect>>", self.elegir_fila)
        self.tabla.bind("<Double-1>", lambda _: self.armar_captura())

        edicion = ttk.Frame(izquierda)
        edicion.pack(fill="x", pady=(8, 0))
        self.asignacion = ttk.Combobox(edicion, state="readonly", width=24)
        self.asignacion.pack(side="left", fill="x", expand=True)
        self.asignacion.bind("<<ComboboxSelected>>", lambda _: self.asignar(self.por_nombre.get(self.asignacion.get(), "")))
        self.capturar = ttk.Button(edicion, text="Asignar al pulsar", command=self.armar_captura)
        self.capturar.pack(side="left", padx=(7, 0))

        derecha = ttk.LabelFrame(contenido, text="Mando en vivo", padding=8)
        derecha.grid(row=0, column=1, sticky="nsew")
        derecha.columnconfigure(0, weight=1)
        derecha.rowconfigure(0, weight=1)
        self.vista = VistaMando(derecha, self.asignar, width=350, height=200)
        self.vista.grid(row=0, column=0, sticky="nsew")
        self.en_vivo = ttk.Label(derecha, wraplength=345)
        self.en_vivo.grid(row=1, column=0, sticky="w", pady=(7, 10))
        ttk.Button(derecha, text="Volver a detectar mandos", command=self.inventario).grid(row=2, column=0, sticky="w")
        self.proteger = ttk.Checkbutton(derecha, text="Conservar este mapeo al iniciar desde RetroBat")
        self.proteger.grid(row=3, column=0, sticky="w", pady=(10, 0))
        self.proteger.invoke()

        self.estado = ttk.Label(cuerpo, wraplength=810)
        self.estado.pack(anchor="w", pady=(10, 7))
        acciones = ttk.Frame(cuerpo)
        acciones.pack(fill="x")
        self.plantilla = ttk.Button(acciones, text="Aplicar plantilla recomendada", command=self.restablecer)
        self.plantilla.pack(side="left")
        self.guia = ttk.Button(acciones, text="Guías del juego…", command=self.abrir_guias)
        self.guia.pack(side="left", padx=8)
        ttk.Button(acciones, text="Cerrar", command=self.cerrar).pack(side="right")
        self.probar = ttk.Button(acciones, text="Probar juego", command=self.probar_edicion)
        self.probar.pack(side="right", padx=7)
        self.guardar = ttk.Button(acciones, text="Guardar este juego", command=self.guardar_edicion)
        self.guardar.pack(side="right")
        self.refrescar_acciones()
        self.inventario()

    def inventario(self):
        if self.app.ocupado:
            return
        self.estado.configure(text="Buscando juegos instalados y mandos conectados…")

        def revisar():
            juegos, pendientes = juegos_con_mandos(self.raiz)
            try:
                mandos, avisos = detectar_mandos()
            except OSError as error:
                mandos, avisos = [], [str(error)]
            return juegos, pendientes, mandos, avisos

        def mostrar(resultado):
            if not self.winfo_exists():
                return
            juegos, self.instalados_sin_perfil, mandos, avisos = resultado
            self.juegos = {f"{perfil.titulo} [{perfil.id}]": (perfil, rutas) for perfil, rutas in juegos}
            self.mandos = {m.etiqueta: m for m in mandos if not m.especial}
            for selector, opciones in ((self.juego, self.juegos), (self.mando, self.mandos)):
                actual = selector.get()
                selector["values"] = tuple(opciones)
                selector.set(actual if actual in opciones else next(iter(opciones), ""))
            if not self.juegos or not self.mandos:
                detalle = "No se encontraron juegos con perfil." if not self.juegos else "Conecta un mando y vuelve a detectarlo."
                self.estado.configure(text=" ".join([detalle, *avisos, *self.instalados_sin_perfil[:3]]))
                return
            self.cargar()

        self.app.ejecutar(revisar, mostrar, "Buscando juegos y mandos…")

    def cargar(self, _=None):
        pedido = (self.juego.get(), self.mando.get(), self.jugador.get())
        if self.app.ocupado:
            for selector, anterior in zip((self.juego, self.mando, self.jugador), self.seleccion):
                selector.set(anterior)
            return
        if not all(pedido):
            return
        if self.borrador != self.base and pedido != self.seleccion:
            if not messagebox.askyesno("Cambios pendientes", "¿Descartar los cambios de esta asignación?", parent=self):
                for selector, anterior in zip((self.juego, self.mando, self.jugador), self.seleccion):
                    selector.set(anterior)
                return
        juego, mando, jugador = self.juegos[pedido[0]], self.mandos[pedido[1]], int(pedido[2][-1])
        self.seleccion = pedido
        self.detener_lectura()
        self.edicion = None
        self.borrador = self.base = self.guardada = {}
        self.nombres = editor.opciones_fisicas(mando)
        self.por_nombre = {**{nombre: codigo for codigo, nombre in self.nombres.items()}, editor.SIN_ASIGNAR: ""}
        self.asignacion["values"] = tuple(self.por_nombre)
        self.vista.dibujar(mando, self.nombres)
        self.tabla.delete(*self.tabla.get_children())
        self.fuente.configure(text="")
        self.estado.configure(text="Preparando la plantilla para este juego…")
        self.refrescar_acciones()

        def preparar():
            try:
                return editor.abrir_edicion(self.raiz, juego, mando, jugador), ""
            except (OSError, ValueError, ParseError) as error:
                return None, str(error)

        def mostrar(resultado):
            if not self.winfo_exists():
                return
            edicion, error = resultado
            if error:
                self.estado.configure(text=error)
                return
            self.edicion = edicion
            api = edicion.campo_api.findtext("FieldValue", "") if edicion.campo_api is not None else mando.api
            detalle = f" · El perfil guardado usa {api}" if api and api != mando.api else ""
            self.fuente.configure(text=edicion.fuente + detalle)
            if edicion.proteger != self.proteger.instate(["selected"]):
                self.proteger.invoke()
            self.guardada = {a.indice: a.actual for a in edicion.acciones}
            editar_servicio = juego[0].id.casefold() not in editor.FAMILIA_DISPAROS
            self.borrador = {a.indice: (a.actual or a.plantilla) if not a.servicio or editar_servicio else ""
                             for a in edicion.acciones}
            self.base = self.borrador.copy()
            for accion in edicion.acciones:
                self.tabla.insert("", "end", iid=str(accion.indice), values=(accion.nombre, accion.guardado, ""))
            if filas := self.tabla.get_children():
                self.tabla.selection_set(filas[0])
            self.estado.configure(text="" if edicion.acciones else "Este perfil no tiene acciones para ese jugador.")
            self.refrescar_tabla()
            self.iniciar_lectura(mando)

        self.app.ejecutar(preparar, mostrar, "Leyendo el perfil de controles…")

    def iniciar_lectura(self, mando):
        try:
            self.lector = abrir_lector(mando, self.winfo_id())
        except OSError as error:
            self.en_vivo.configure(text=str(error))
        self.leer_mando()
        self.refrescar_acciones()

    def detener_lectura(self):
        if self.temporizador is not None:
            self.after_cancel(self.temporizador)
            self.temporizador = None
        if self.lector:
            self.lector.cerrar()
            self.lector = None
        self.captura = None
        self.activas = set()

    def leer_mando(self):
        self.temporizador = None
        if not self.lector:
            return
        try:
            activas = self.lector.leer() & self.nombres.keys()
        except OSError as error:
            self.detener_lectura()
            self.en_vivo.configure(text=str(error) + " Vuelve a detectar el mando.")
            self.refrescar_tabla()
            return
        if self.captura:
            fila, vence = self.captura
            nuevas = activas - self.activas
            digitales = {c for c in nuevas if c in BOTONES_XI or c.startswith(("b", "h"))}
            if len(digitales or nuevas) == 1:
                self.asignar(next(iter(digitales or nuevas)), fila)
                self.captura = None
            elif monotonic() >= vence:
                self.estado.configure(text="Se agotó el tiempo. Pulsa Asignar al pulsar para intentarlo otra vez.")
                self.captura = None
        if activas != self.activas:
            self.activas = activas
            self.refrescar_tabla()
        texto = "Pulsado · " + ", ".join(self.nombres[c] for c in sorted(activas)) if activas else "Mueve la palanca o pulsa un botón para comprobarlo."
        self.en_vivo.configure(text=texto)
        self.temporizador = self.after(65, self.leer_mando)

    def fila_actual(self):
        filas = self.tabla.selection()
        return int(filas[0]) if filas else None

    def elegir_fila(self, _=None):
        if self.captura and self.captura[0] != self.fila_actual():
            self.captura = None
        self.refrescar_tabla()

    def refrescar_tabla(self):
        for fila in self.tabla.get_children():
            codigo = self.borrador.get(int(fila), "")
            self.tabla.set(fila, "asignacion", self.nombres.get(codigo, editor.SIN_ASIGNAR))
            self.tabla.item(fila, tags=("activa",) if codigo in self.activas else ())
        elegido = self.borrador.get(self.fila_actual(), "")
        self.asignacion.set(self.nombres.get(elegido, editor.SIN_ASIGNAR))
        self.vista.iluminar(self.activas, elegido)
        self.refrescar_acciones()

    def refrescar_acciones(self):
        lista = bool(self.edicion and self.edicion.acciones)
        seleccion = lista and self.fila_actual() is not None
        self.asignacion.configure(state="readonly" if seleccion else "disabled")
        self.capturar.state(["!disabled"] if seleccion and self.lector else ["disabled"])
        self.plantilla.state(["!disabled"] if lista else ["disabled"])
        self.guardar.state(["!disabled"] if lista else ["disabled"])
        puede_probar = (self.edicion and self.edicion.original is not None and any(self.guardada.values())
                        and self.borrador == self.guardada)
        self.probar.state(["!disabled"] if puede_probar else ["disabled"])
        self.guia.state(["!disabled"] if self.edicion else ["disabled"])

    def armar_captura(self):
        fila = self.fila_actual()
        if fila is None or not self.lector or self.app.ocupado:
            return
        self.captura = (fila, monotonic() + 12)
        self.estado.configure(text="Suelta el mando y luego pulsa el botón que quieres asignar.")

    def asignar(self, codigo, fila=None):
        if self.app.ocupado or not self.edicion:
            return
        fila = self.fila_actual() if fila is None else fila
        if fila is None or (codigo and codigo not in self.nombres):
            return
        self.borrador[fila] = codigo
        self.estado.configure(text="Cambio pendiente de guardar.")
        self.refrescar_tabla()

    def restablecer(self):
        if self.app.ocupado or not self.edicion:
            return
        self.borrador = {a.indice: a.plantilla for a in self.edicion.acciones}
        self.estado.configure(text="Plantilla aplicada a la vista. Guarda para actualizar este juego.")
        self.refrescar_tabla()

    def guardar_edicion(self):
        if not self.edicion or self.app.ocupado:
            return
        if self.proceso and self.proceso.poll() is None:
            self.estado.configure(text="Cierra la prueba de TeknoParrot antes de guardar.")
            return
        if not messagebox.askyesno("Guardar controles", f"¿Guardar el mapeo de {self.edicion.perfil.titulo}?\n\n"
                                   "Cierra RetroBat y TeknoParrot. Se guardará un respaldo.", parent=self):
            return
        edicion, cambios = self.edicion, self.borrador.copy()
        proteger = self.proteger.instate(["selected"])

        def guardar():
            return editor.guardar_edicion(self.raiz, edicion, cambios, proteger=proteger)

        def mostrar(respaldo):
            if not self.winfo_exists():
                return
            self.base = cambios.copy()
            self.guardada = cambios.copy()
            for accion in edicion.acciones:
                nombre = self.nombres.get(cambios.get(accion.indice, ""), editor.SIN_ASIGNAR)
                self.tabla.set(str(accion.indice), "guardado", nombre)
            self.estado.configure(text=f"Controles guardados. Respaldo · {respaldo}" if respaldo else "El perfil ya tiene este mapeo.")
            self.fuente.configure(text=edicion.fuente)
            self.refrescar_acciones()

        self.app.ejecutar(guardar, mostrar, "Guardando controles del juego…")

    def probar_edicion(self):
        if not self.edicion or self.app.ocupado or self.borrador != self.guardada:
            return
        if self.proceso and self.proceso.poll() is None:
            self.estado.configure(text="La prueba de TeknoParrot ya está abierta.")
            return
        try:
            self.proceso = editor.probar_juego(self.raiz, self.edicion)
        except (OSError, ValueError, ParseError) as error:
            messagebox.showinfo("Probar juego", str(error), parent=self)
        else:
            self.estado.configure(text="Probando el perfil guardado. Cierra el juego para continuar ajustándolo.")

    def abrir_guias(self):
        if self.edicion:
            self.app.informe("Guías de controles", (self.edicion.perfil.titulo, self.edicion.fuente),
                             (("Ficha del juego · TeknoParrot", ficha_url(self.edicion.perfil.id)),
                              ("Mapas de RetroBat", DOCUMENTACION_MANDOS)))

    def cerrar(self):
        if self.app.ocupado:
            return
        if self.borrador != self.base and not messagebox.askyesno("Cambios pendientes", "¿Descartar los cambios?", parent=self):
            return
        self.destroy()

    def destroy(self):
        self.detener_lectura()
        super().destroy()
