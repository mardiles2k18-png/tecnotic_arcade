"""Pestaña Mandos: mandos conectados con prueba en vivo, orden de jugadores, autoconfiguración y TeknoParrot."""

from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from controller_studio import VistaMando
import gestor_mandos as gm
from gestor_mandos_lectura import abrir_lector
from gestor_mandos_windows import detectar_mandos
from gestor_preparar import ajustes_retrobat, entradas_sistema, seleccion_sistema
import gestor_teknoparrot_editor as editor

SIN_CAMBIO = "(sin cambios)"
GUIA_MANDOS = "https://wiki.retrobat.org/controllers/controller-configuration"


class PanelMandos(ttk.Frame):
    def __init__(self, padre, app):
        super().__init__(padre, padding=16)
        self.app = app
        self.raiz = None
        self.detectados = {}
        self.retrobat = []
        self.filas_sistemas = {}
        self.lector = None
        self.temporizador = None
        self.nombres = {}
        self.activas = set()
        self.resumen = tk.StringVar(value="Selecciona la instalación de RetroBat en Inicio.")

        cabecera = ttk.Frame(self)
        cabecera.pack(fill="x")
        ttk.Label(cabecera, textvariable=self.resumen, wraplength=820, justify="left").pack(side="left", anchor="w")
        ttk.Button(cabecera, text="Actualizar", command=self.actualizar).pack(side="right")
        secciones = ttk.Notebook(self)
        secciones.pack(fill="both", expand=True, pady=(8, 0))
        self.secciones = secciones

        # 1. Mandos conectados y prueba en vivo
        conectados = ttk.Frame(secciones, padding=10)
        secciones.add(conectados, text="Mandos conectados")
        conectados.columnconfigure(0, weight=3)
        conectados.columnconfigure(1, weight=2)
        conectados.rowconfigure(0, weight=1)
        izquierda = ttk.Frame(conectados)
        izquierda.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.tabla_mandos = ttk.Treeview(izquierda, columns=("mando", "api", "retrobat"), show="headings",
                                         selectmode="browse", height=6)
        for columna, titulo, ancho in (("mando", "Mando detectado por Windows", 230), ("api", "API", 90),
                                       ("retrobat", "Configurado en RetroBat", 200)):
            self.tabla_mandos.heading(columna, text=titulo)
            self.tabla_mandos.column(columna, width=ancho, minwidth=70)
        self.tabla_mandos.pack(fill="both", expand=True)
        self.tabla_mandos.bind("<<TreeviewSelect>>", self.elegir_mando)
        ttk.Label(izquierda, wraplength=470, justify="left", text=(
            "Elige un mando y pulsa sus botones: se iluminan en el dibujo. Si un mando no está configurado en "
            "RetroBat, asígnale los botones desde el menú de RetroBat (CONTROLLER SETTINGS). Ese mapa es el que "
            "RetroBat copia a la mayoría de los emuladores al abrir un juego.")).pack(anchor="w", pady=(8, 0))
        vivo = ttk.LabelFrame(conectados, text="Prueba en vivo", padding=8)
        vivo.grid(row=0, column=1, sticky="nsew")
        vivo.columnconfigure(0, weight=1)
        vivo.rowconfigure(0, weight=1)
        self.vista = VistaMando(vivo, lambda _: None, width=330, height=200)
        self.vista.grid(row=0, column=0, sticky="nsew")
        self.en_vivo = ttk.Label(vivo, wraplength=320, text="Elige un mando de la lista para probarlo.")
        self.en_vivo.grid(row=1, column=0, sticky="w", pady=(6, 0))

        # 2. Orden de jugadores
        orden = ttk.Frame(secciones, padding=10)
        secciones.add(orden, text="Orden de jugadores")
        orden.columnconfigure(1, weight=1)
        ttk.Label(orden, wraplength=880, justify="left", text=(
            "RetroBat asigna los jugadores por la ruta USB del mando y, si no la encuentra, por su nombre y GUID. "
            "Fija aquí el mando del Jugador 1 y del Jugador 2 para que no se intercambien al reiniciar. "
            "Si las dos placas son idénticas (mismo nombre y GUID) usa el menú de RetroBat: "
            "CONTROLLER SETTINGS → CONTROLLERS PRIORITY.")).grid(row=0, column=0, columnspan=3, sticky="w")
        self.actuales = tk.StringVar()
        ttk.Label(orden, textvariable=self.actuales, justify="left").grid(row=1, column=0, columnspan=3,
                                                                           sticky="w", pady=8)
        self.selectores = {}
        for fila, numero in enumerate((1, 2), start=2):
            ttk.Label(orden, text=f"Jugador {numero}").grid(row=fila, column=0, sticky="w", pady=3)
            selector = ttk.Combobox(orden, state="readonly", values=(SIN_CAMBIO,))
            selector.set(SIN_CAMBIO)
            selector.grid(row=fila, column=1, sticky="ew", padx=8, pady=3)
            self.selectores[numero] = selector
        ttk.Button(orden, text="Guardar orden…", command=self.guardar_orden).grid(row=4, column=1, sticky="w",
                                                                                  padx=8, pady=(8, 0))

        # 3. Configuración automática por sistema
        sistemas = ttk.Frame(secciones, padding=10)
        secciones.add(sistemas, text="Configuración por sistema")
        self.global_texto = tk.StringVar()
        ttk.Label(sistemas, textvariable=self.global_texto, wraplength=880, justify="left").pack(anchor="w")
        tabla = ttk.Frame(sistemas)
        tabla.pack(fill="both", expand=True, pady=8)
        self.tabla_sistemas = ttk.Treeview(tabla, columns=("sistema", "emulador", "estado", "juegos"),
                                           show="headings", selectmode="extended")
        for columna, titulo, ancho in (("sistema", "Sistema", 190), ("emulador", "Emulador", 170),
                                       ("estado", "Mandos", 230), ("juegos", "Juegos con mapeo propio", 220)):
            self.tabla_sistemas.heading(columna, text=titulo)
            self.tabla_sistemas.column(columna, width=ancho, minwidth=80)
        barra = ttk.Scrollbar(tabla, command=self.tabla_sistemas.yview)
        self.tabla_sistemas.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.tabla_sistemas.pack(fill="both", expand=True)
        acciones = ttk.Frame(sistemas)
        acciones.pack(fill="x")
        ttk.Button(acciones, text=gm.AUTOMATICO, command=lambda: self.fijar(False)).pack(side="left")
        ttk.Button(acciones, text=gm.MANUAL + "…", command=lambda: self.fijar(True)).pack(side="left", padx=6)

        # 4. TeknoParrot
        teknoparrot = ttk.Frame(secciones, padding=10)
        secciones.add(teknoparrot, text="TeknoParrot")
        ttk.Label(teknoparrot, wraplength=880, justify="left", text=(
            "Cada juego de TeknoParrot tiene sus propios controles (palanca, botones, monedas, servicio). "
            "El editor asigna cada acción al pulsar el botón del mando, guarda el perfil del juego y, si lo "
            "marcas, evita que RetroBat reemplace ese mapeo al abrir el juego.")).pack(anchor="w")
        ttk.Button(teknoparrot, text="Editor de mandos por juego de TeknoParrot…",
                   command=lambda: app.panel_teknoparrot.mandos_automaticos()).pack(anchor="w", pady=10)

    # ------------------------------------------------------------------ datos
    def limpiar(self):
        self.detener_lectura()
        self.raiz = None
        self.detectados = {}
        self.retrobat = []
        self.tabla_mandos.delete(*self.tabla_mandos.get_children())
        self.tabla_sistemas.delete(*self.tabla_sistemas.get_children())
        self.actuales.set("")
        self.global_texto.set("")
        for selector in self.selectores.values():
            selector.configure(values=(SIN_CAMBIO,))
            selector.set(SIN_CAMBIO)
        self.resumen.set("Selecciona la instalación de RetroBat en Inicio.")

    def actualizar(self):
        if not self.app.raiz.get():
            self.resumen.set("Selecciona la instalación de RetroBat en Inicio.")
            return

        def iniciar(raiz):
            raiz = raiz.resolve()
            sistemas = self.app.sistemas.copy()

            def revisar():
                retrobat = gm.mandos_retrobat(raiz)
                actuales = gm.jugadores(raiz)
                con_juegos = [(clave, s) for clave, s in sorted(sistemas.items(), key=lambda par: par[1].nombre.casefold())
                              if s.carpeta.is_dir() and next(entradas_sistema(s), None) is not None]
                global_manual, estados = gm.autoconfiguracion(raiz, [s.identificador for _, s in con_juegos])
                ajustes = ajustes_retrobat(raiz)
                filas = []
                for clave, sistema in con_juegos:
                    seleccion = seleccion_sistema(raiz, sistema.identificador, ajustes)
                    filas.append((clave, sistema, seleccion.descripcion if seleccion else "—",
                                  estados[sistema.identificador], gm.juegos_manuales(raiz, sistema.identificador)))
                try:
                    detectados, avisos = detectar_mandos()
                except OSError as error:
                    detectados, avisos = [], [str(error)]
                return retrobat, actuales, global_manual, filas, detectados, avisos

            def mostrar(resultado):
                if Path(self.app.raiz.get()).resolve() != raiz:
                    return
                self.raiz = raiz
                self.retrobat, actuales, global_manual, filas, detectados, avisos = resultado
                self.mostrar_mandos(detectados)
                self.mostrar_jugadores(actuales)
                self.global_texto.set(
                    ("El ajuste global de RetroBat desactiva la configuración automática en todos los sistemas. "
                     if global_manual else
                     "RetroBat configura los mandos de cada emulador al abrir un juego, salvo en los sistemas "
                     "marcados como mapeo manual. ")
                    + "Usa mapeo manual solo si un emulador no responde bien con la configuración automática "
                      "(por ejemplo, algunos juegos de TeknoParrot, PS2 o PS3) y configúralo dentro del emulador.")
                self.tabla_sistemas.delete(*self.tabla_sistemas.get_children())
                self.filas_sistemas.clear()
                for clave, sistema, emulador, estado, manuales in filas:
                    juegos = f"{len(manuales)} juego(s)" if manuales else ""
                    item = self.tabla_sistemas.insert("", "end", values=(sistema.nombre, emulador, estado, juegos))
                    self.filas_sistemas[item] = sistema
                aviso = f" · {' '.join(avisos)}" if avisos else ""
                self.resumen.set(f"{len(detectados)} mandos detectados por Windows · {len(self.retrobat)} "
                                 f"configurados en RetroBat{aviso}")

            self.app.ejecutar(revisar, mostrar, "Revisando mandos y ajustes de RetroBat…")

        self.app.operar(iniciar)

    def mostrar_mandos(self, detectados):
        self.detener_lectura()
        self.tabla_mandos.delete(*self.tabla_mandos.get_children())
        self.detectados.clear()
        for mando in detectados:
            if mando.especial:
                continue
            asociado = gm.mando_retrobat(self.retrobat, mando)
            item = self.tabla_mandos.insert("", "end", values=(
                mando.nombre, f"{mando.api} {mando.indice + 1}",
                "Sí" if asociado else "No · configúralo en RetroBat"))
            self.detectados[item] = mando

    def mostrar_jugadores(self, actuales):
        lineas = []
        for jugador in actuales:
            if jugador.nombre or jugador.ruta:
                detalle = jugador.nombre or "(sin nombre)"
                if jugador.ruta:
                    detalle += " · fijado por ruta USB"
                lineas.append(f"Jugador {jugador.numero}: {detalle}")
            else:
                lineas.append(f"Jugador {jugador.numero}: automático (primer mando libre)")
        self.actuales.set("Asignación actual en RetroBat:\n" + "\n".join(lineas))
        opciones = (SIN_CAMBIO, *(m.etiqueta for m in self.retrobat))
        for numero, selector in self.selectores.items():
            selector.configure(values=opciones)
            selector.set(SIN_CAMBIO)

    # ------------------------------------------------------------------ prueba en vivo
    def elegir_mando(self, _=None):
        filas = self.tabla_mandos.selection()
        mando = self.detectados.get(filas[0]) if filas else None
        self.detener_lectura()
        if mando is None:
            self.vista.dibujar(None, {})
            return
        self.nombres = editor.opciones_fisicas(mando)
        self.vista.dibujar(mando, self.nombres)
        try:
            self.lector = abrir_lector(mando, self.winfo_toplevel().winfo_id())
        except OSError as error:
            self.en_vivo.configure(text=str(error))
            return
        self.leer_mando()

    def leer_mando(self):
        self.temporizador = None
        if not self.lector:
            return
        try:
            activas = self.lector.leer() & self.nombres.keys()
        except OSError as error:
            self.detener_lectura()
            self.en_vivo.configure(text=f"{error} Pulsa Actualizar para volver a detectarlo.")
            return
        if activas != self.activas:
            self.activas = activas
            self.vista.iluminar(activas)
        texto = ("Pulsado · " + ", ".join(self.nombres[c] for c in sorted(activas)) if activas
                 else "Mueve la palanca o pulsa un botón para comprobarlo.")
        self.en_vivo.configure(text=texto)
        self.temporizador = self.after(65, self.leer_mando)

    def detener_lectura(self):
        if self.temporizador is not None:
            self.after_cancel(self.temporizador)
            self.temporizador = None
        if self.lector:
            self.lector.cerrar()
            self.lector = None
        self.activas = set()

    def destroy(self):
        self.detener_lectura()
        super().destroy()

    # ------------------------------------------------------------------ guardar
    def guardar_orden(self):
        por_etiqueta = {m.etiqueta: m for m in self.retrobat}
        asignaciones = {n: por_etiqueta[s.get()] for n, s in self.selectores.items() if s.get() in por_etiqueta}
        if not asignaciones or self.raiz is None:
            messagebox.showinfo("Orden de jugadores", "Elige el mando de al menos un jugador.", parent=self)
            return
        if len(set(asignaciones.values())) != len(asignaciones):
            messagebox.showerror("Orden de jugadores", "Elige un mando distinto para cada jugador.", parent=self)
            return
        avisos = [f"{m.nombre} tiene un mando idéntico conectado: usa CONTROLLERS PRIORITY en RetroBat."
                  for m in asignaciones.values() if gm.gemelos(self.retrobat, m) > 1]
        resumen = "\n".join(f"Jugador {n}: {m.nombre}" for n, m in sorted(asignaciones.items()))
        if not messagebox.askyesno("Orden de jugadores",
                                   f"{resumen}\n\nSe guardará en es_settings.cfg con un respaldo. "
                                   "Cierra RetroBat antes de continuar." + ("\n\n" + "\n".join(avisos) if avisos else ""),
                                   parent=self):
            return
        raiz = self.raiz

        def terminar(respaldo):
            texto = "Orden de jugadores guardado." if respaldo else "El orden ya estaba guardado."
            self.app.informe("Orden de jugadores", [texto, *([f"Respaldo: {respaldo}"] if respaldo else []),
                                                    "Abre RetroBat para aplicarlo."])
            self.actualizar()

        self.app.ejecutar(lambda: gm.asignar_jugadores(raiz, asignaciones), terminar, "Guardando el orden…")

    def fijar(self, manual):
        sistemas = [self.filas_sistemas[i] for i in self.tabla_sistemas.selection() if i in self.filas_sistemas]
        if not sistemas or self.raiz is None:
            messagebox.showinfo("Mandos", "Selecciona uno o más sistemas en la tabla.", parent=self)
            return
        nombres = ", ".join(s.nombre for s in sistemas)
        texto = (f"¿Desactivar la configuración automática de mandos en {nombres}?\n\nRetroBat dejará de "
                 "escribir los controles en ese emulador: configúralos dentro del emulador." if manual else
                 f"¿Dejar que RetroBat configure los mandos en {nombres}?")
        if not messagebox.askyesno("Mandos", texto + "\n\nSe crea un respaldo. Cierra RetroBat antes de continuar.",
                                   parent=self):
            return
        raiz = self.raiz

        def aplicar():
            return [gm.fijar_autoconfiguracion(raiz, s.identificador, manual) for s in sistemas]

        def terminar(respaldos):
            lineas = [f"{s.nombre}: {gm.MANUAL if manual else gm.AUTOMATICO}" for s in sistemas]
            lineas += [f"Respaldo: {r}" for r in respaldos if r]
            self.app.informe("Mandos por sistema", lineas)
            self.actualizar()

        self.app.ejecutar(aplicar, terminar, "Guardando ajustes de mandos…")
