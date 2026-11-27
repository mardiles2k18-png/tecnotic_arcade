"""Interfaz para comparar y migrar bibliotecas de RetroBat."""

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from gestor_migracion import aplicar_migracion, comparar_instalaciones, preparar_migracion


ESTADOS_SISTEMA = {
    "faltante": "Falta en destino",
    "diferente": "Con diferencias",
    "igual": "Igual",
    "solo_destino": "Solo en destino",
    "no_compatible": "No disponible en destino",
}
ESTADOS_JUEGO = {
    "faltante": "Falta en destino",
    "conflicto": "Archivos distintos",
    "recursos": "Faltan ficha o medios",
    "no_compatible": "Requiere revisión",
    "igual": "Igual",
    "solo_destino": "Solo en destino",
}
MIGRABLES = {"faltante", "recursos"}


def _tamano(bytes_totales):
    valor = float(bytes_totales)
    for unidad in ("B", "KiB", "MiB", "GiB"):
        if valor < 1024 or unidad == "GiB":
            return f"{valor:,.1f} {unidad}"
        valor /= 1024


def _tabla(padre, columnas):
    marco = ttk.Frame(padre)
    marco.pack(fill="both", expand=True)
    tabla = ttk.Treeview(marco, columns=tuple(columna[0] for columna in columnas), show="headings", height=8)
    for clave, titulo, ancho, expandir in columnas:
        tabla.heading(clave, text=titulo)
        tabla.column(clave, width=ancho, minwidth=ancho, stretch=expandir,
                     anchor="w" if expandir else "center")
    barra = ttk.Scrollbar(marco, orient="vertical", command=tabla.yview)
    barra.pack(side="right", fill="y")
    tabla.configure(yscrollcommand=barra.set, selectmode="browse")
    tabla.pack(side="left", fill="both", expand=True)
    return tabla


class PanelMigracion(ttk.Frame):
    def __init__(self, padre, app):
        super().__init__(padre, padding=16)
        self.app = app
        self.origen = tk.StringVar(master=self)
        self.destino = tk.StringVar(master=self)
        self.detalle = tk.StringVar(master=self)
        self.detalle_juegos = tk.StringVar(master=self)
        self.comparacion = None
        self.sistemas = {}
        self.juegos = {}
        self.sistema_mostrado = None
        self.marcados = {}
        self.reemplazos = set()
        self.generacion = 0
        self.destino_manual = False

        ubicaciones = ttk.Frame(self)
        ubicaciones.pack(fill="x")
        ubicaciones.columnconfigure(1, weight=1)
        for fila, etiqueta, variable in ((0, "Origen", self.origen), (1, "Destino", self.destino)):
            ttk.Label(ubicaciones, text=etiqueta).grid(row=fila, column=0, sticky="w", pady=3)
            ttk.Entry(ubicaciones, textvariable=variable, state="readonly").grid(
                row=fila, column=1, sticky="ew", padx=10, pady=3,
            )
            ttk.Button(ubicaciones, text="Elegir carpeta…", command=lambda v=variable: self.elegir(v)).grid(
                row=fila, column=2, sticky="ew", pady=3,
            )

        acciones = ttk.Frame(self)
        acciones.pack(fill="x", pady=(8, 10))
        ttk.Button(acciones, text="Comparar instalaciones", command=self.comparar).pack(side="left")
        self.boton_faltantes = ttk.Button(acciones, text="Marcar sistemas faltantes", command=self.marcar_faltantes)
        self.boton_faltantes.pack(side="left", padx=8)
        self.boton_limpiar = ttk.Button(acciones, text="Quitar marcas", command=self.quitar_marcas)
        self.boton_limpiar.pack(side="left")

        paneles = ttk.Panedwindow(self, orient="horizontal")
        paneles.pack(fill="both", expand=True)
        panel_sistemas = ttk.Labelframe(paneles, text="Sistemas", padding=8)
        panel_juegos = ttk.Labelframe(paneles, text="Juegos del sistema", padding=8)
        paneles.add(panel_sistemas, weight=2)
        paneles.add(panel_juegos, weight=3)
        self.tabla_sistemas = _tabla(panel_sistemas, (
            ("migrar", "Migrar", 48, False),
            ("nombre", "Sistema", 145, True),
            ("estado", "Estado", 138, False),
        ))
        self.tabla_juegos = _tabla(panel_juegos, (
            ("migrar", "Migrar", 48, False),
            ("nombre", "Juego", 140, True),
            ("estado", "Estado", 145, False),
        ))
        self.tabla_sistemas.bind("<<TreeviewSelect>>", self.mostrar_juegos)
        self.tabla_juegos.bind("<<TreeviewSelect>>", self.actualizar_controles)
        for tabla, accion in ((self.tabla_sistemas, self.alternar_sistema),
                              (self.tabla_juegos, self.alternar_juego)):
            tabla.bind("<ButtonRelease-1>", lambda evento, a=accion: self.marcar_con_clic(evento, a))
            tabla.bind("<space>", lambda evento, a=accion: self.marcar_con_tecla(evento, a))

        ttk.Label(panel_juegos, textvariable=self.detalle_juegos, wraplength=450).pack(
            fill="x", pady=(8, 4),
        )
        self.boton_reemplazar = ttk.Button(
            panel_juegos, text="Reemplazar juego con respaldo…", command=self.reemplazar_juego,
        )
        self.boton_reemplazar.pack(anchor="w")

        pie = ttk.Frame(self)
        pie.pack(fill="x", pady=(10, 0))
        self.boton_preparar = ttk.Button(pie, text="Revisar migración…", command=self.preparar)
        self.boton_preparar.pack(side="right", padx=(10, 0))
        ttk.Label(pie, textvariable=self.detalle, wraplength=650).pack(side="left", fill="x", expand=True)
        self.limpiar()

    def limpiar(self):
        if not self.destino_manual:
            self.destino.set(self.app.raiz.get())
        self.invalidar()

    def invalidar(self):
        self.generacion += 1
        self.comparacion = None
        self.sistema_mostrado = None
        self.sistemas.clear()
        self.juegos.clear()
        self.marcados.clear()
        self.reemplazos.clear()
        self.tabla_sistemas.delete(*self.tabla_sistemas.get_children())
        self.tabla_juegos.delete(*self.tabla_juegos.get_children())
        self.detalle_juegos.set("")
        self.detalle.set("Elige el origen y compara las dos instalaciones.")
        self.actualizar_controles()

    def elegir(self, variable):
        if self.app.ocupado:
            return
        titulo = "RetroBat de origen" if variable is self.origen else "RetroBat de destino"
        ruta = filedialog.askdirectory(title=titulo, initialdir=variable.get() or None, parent=self)
        if ruta:
            variable.set(ruta)
            if variable is self.destino:
                self.destino_manual = True
            self.invalidar()

    def comparar(self):
        if self.app.ocupado:
            return
        if not self.origen.get() or not self.destino.get():
            messagebox.showinfo("Migrar RetroBat", "Elige las carpetas de origen y destino.", parent=self)
            return
        origen, destino = Path(self.origen.get()), Path(self.destino.get())
        self.invalidar()
        generacion = self.generacion

        def mostrar(comparacion):
            if generacion != self.generacion:
                return
            self.comparacion = comparacion
            for indice, sistema in enumerate(comparacion.sistemas):
                fila = str(indice)
                self.sistemas[fila] = sistema
                self.tabla_sistemas.insert("", "end", iid=fila, values=(
                    "☐" if self.puede_migrar(sistema) else "",
                    sistema.nombre,
                    ESTADOS_SISTEMA[sistema.estado],
                ))
            if self.sistemas:
                primera = next(iter(self.sistemas))
                self.tabla_sistemas.selection_set(primera)
                self.tabla_sistemas.focus(primera)
                self.mostrar_juegos()
            self.actualizar_marcas()
            if comparacion.avisos:
                self.app.informe("Avisos de la comparación", comparacion.avisos)

        self.app.ejecutar(
            lambda informar: comparar_instalaciones(origen, destino, informar),
            mostrar, "Comparando instalaciones de RetroBat…", con_progreso=True,
        )

    @staticmethod
    def puede_migrar(sistema):
        return sistema.estado in {"faltante", "diferente"}

    @staticmethod
    def seleccion(tabla):
        filas = tabla.selection()
        return filas[0] if filas else None

    def sistema_actual(self):
        return self.sistemas.get(self.seleccion(self.tabla_sistemas))

    def mostrar_juegos(self, _=None):
        sistema = self.sistema_actual()
        if sistema is self.sistema_mostrado:
            for fila, juego in self.juegos.items():
                self.tabla_juegos.set(fila, "migrar", self.marca_juego(sistema, juego))
                self.tabla_juegos.set(fila, "estado", self.estado_juego(sistema, juego))
            self.actualizar_controles()
            return
        self.sistema_mostrado = sistema
        self.juegos.clear()
        self.tabla_juegos.delete(*self.tabla_juegos.get_children())
        if sistema is not None:
            for indice, juego in enumerate(sistema.juegos):
                fila = str(indice)
                self.juegos[fila] = juego
                self.tabla_juegos.insert("", "end", iid=fila, values=(
                    self.marca_juego(sistema, juego), juego.nombre, self.estado_juego(sistema, juego),
                ))
            self.detalle_juegos.set(
                f"BIOS pendientes: {sistema.bios_pendientes}. Marca la casilla de un juego para copiarlo."
            )
        else:
            self.detalle_juegos.set("")
        self.actualizar_controles()

    def estado_juego(self, sistema, juego):
        if (sistema.clave, juego.clave) in self.reemplazos:
            return "Reemplazar con respaldo"
        return ESTADOS_JUEGO[juego.estado]

    def marca_juego(self, sistema, juego):
        if not self.puede_migrar(sistema) or juego.estado not in MIGRABLES | {"conflicto"}:
            return ""
        seleccion = self.marcados.get(sistema.clave, set())
        marcado = (sistema.clave, juego.clave) in self.reemplazos if juego.estado == "conflicto" else (
            seleccion is None or juego.clave in seleccion
        )
        return "☑" if marcado else "☐"

    def marcar_con_clic(self, evento, accion):
        tabla = evento.widget
        if tabla.identify_region(evento.x, evento.y) == "cell" and tabla.identify_column(evento.x) == "#1":
            fila = tabla.identify_row(evento.y)
            if fila:
                accion(fila)

    def marcar_con_tecla(self, evento, accion):
        fila = self.seleccion(evento.widget)
        if fila is not None:
            accion(fila)
        return "break"

    def alternar_sistema(self, fila):
        sistema = self.sistemas[fila]
        if self.app.ocupado or not self.puede_migrar(sistema):
            return
        if sistema.clave in self.marcados:
            del self.marcados[sistema.clave]
            self.reemplazos = {par for par in self.reemplazos if par[0] != sistema.clave}
        else:
            self.marcados[sistema.clave] = None
        self.actualizar_marcas()

    def marcar_faltantes(self):
        if not self.app.ocupado:
            self.marcados.update({sistema.clave: None for sistema in self.sistemas.values()
                                  if sistema.estado == "faltante"})
            self.actualizar_marcas()

    def quitar_marcas(self):
        if not self.app.ocupado:
            self.marcados.clear()
            self.reemplazos.clear()
            self.actualizar_marcas()

    def alternar_juego(self, fila):
        if self.app.ocupado:
            return
        sistema = self.sistema_actual()
        juego = self.juegos.get(fila)
        if sistema is None or juego is None or not self.puede_migrar(sistema):
            return
        if juego.estado == "conflicto":
            self.reemplazar_juego(juego)
        elif juego.estado in MIGRABLES:
            seleccion = self.seleccion_juegos(sistema)
            if juego.clave in seleccion:
                seleccion.remove(juego.clave)
            else:
                seleccion.add(juego.clave)
            self.guardar_seleccion(sistema, seleccion)

    def seleccion_juegos(self, sistema):
        seleccion = self.marcados.get(sistema.clave, set())
        if seleccion is None:
            return {juego.clave for juego in sistema.juegos if juego.estado in MIGRABLES} | {
                clave for sistema_clave, clave in self.reemplazos if sistema_clave == sistema.clave
            }
        return seleccion.copy()

    def guardar_seleccion(self, sistema, seleccion):
        if seleccion:
            self.marcados[sistema.clave] = seleccion
        else:
            self.marcados.pop(sistema.clave, None)
        self.actualizar_marcas()

    def reemplazar_juego(self, juego=None):
        if self.app.ocupado:
            return
        sistema = self.sistema_actual()
        juego = juego or self.juegos.get(self.seleccion(self.tabla_juegos))
        if sistema is None or juego is None or juego.estado != "conflicto" or not self.puede_migrar(sistema):
            return
        par = (sistema.clave, juego.clave)
        seleccion = self.seleccion_juegos(sistema)
        if par in self.reemplazos:
            self.reemplazos.remove(par)
            seleccion.discard(juego.clave)
        else:
            if not messagebox.askyesno(
                "Reemplazar juego", f"¿Copiar «{juego.nombre}» del origen y guardar un respaldo "
                "de la copia del destino?", parent=self,
            ):
                return
            self.reemplazos.add(par)
            seleccion.add(juego.clave)
        if sistema.clave in self.marcados and self.marcados[sistema.clave] is None:
            self.actualizar_marcas()
        else:
            self.guardar_seleccion(sistema, seleccion)

    def actualizar_marcas(self):
        for fila, sistema in self.sistemas.items():
            marca = ""
            if self.puede_migrar(sistema):
                marca = "☐"
                if sistema.clave in self.marcados:
                    marca = "☑" if self.marcados[sistema.clave] is None else "◩"
            self.tabla_sistemas.set(fila, "migrar", marca)
        self.mostrar_juegos()
        if self.comparacion is not None:
            if not self.sistemas:
                mensaje = "No se encontraron sistemas con juegos."
            else:
                mensaje = (f"{len(self.sistemas)} sistemas comparados · {len(self.marcados)} marcados. "
                           "Los juegos se comparan por ruta relativa y contenido.")
            if self.comparacion.avisos:
                mensaje += f" · {len(self.comparacion.avisos)} avisos."
            self.detalle.set(mensaje)

    def actualizar_controles(self, _=None):
        sistema = self.sistema_actual()
        juego = self.juegos.get(self.seleccion(self.tabla_juegos))
        conflicto = sistema is not None and self.puede_migrar(sistema) and juego and juego.estado == "conflicto"
        if conflicto and (sistema.clave, juego.clave) in self.reemplazos:
            self.boton_reemplazar.configure(text="Conservar juego del destino")
        else:
            self.boton_reemplazar.configure(text="Reemplazar juego con respaldo…")
        for boton, habilitado in (
            (self.boton_preparar, self.marcados),
            (self.boton_limpiar, self.marcados),
            (self.boton_faltantes, any(s.estado == "faltante" for s in self.sistemas.values())),
            (self.boton_reemplazar, conflicto),
        ):
            boton.state(["!disabled"] if habilitado else ["disabled"])

    def preparar(self):
        if self.app.ocupado or not self.marcados:
            return
        comparacion = self.comparacion
        seleccion = {clave: None if juegos is None else juegos.copy() for clave, juegos in self.marcados.items()}
        reemplazos = frozenset(self.reemplazos)
        generacion = self.generacion

        def revisar(plan):
            if self.generacion == generacion:
                self.revisar(plan, comparacion, seleccion, reemplazos)

        self.app.ejecutar(
            lambda: preparar_migracion(comparacion, seleccion, reemplazos),
            revisar, "Preparando la migración…",
        )

    def revisar(self, plan, comparacion, seleccion, reemplazos):
        if not plan.archivos and not plan.catalogos:
            mensaje = ["No hay archivos pendientes en esta selección.", *plan.avisos]
            self.app.informe("Revisar migración", mensaje)
            return
        ventana = tk.Toplevel(self)
        ventana.title("Revisar migración")
        ventana.transient(self.winfo_toplevel())
        ventana.grab_set()
        marco = ttk.Frame(ventana, padding=12)
        marco.pack(fill="both", expand=True)
        texto = tk.Text(marco, width=90, height=16, wrap="word")
        barra = ttk.Scrollbar(marco, orient="vertical", command=texto.yview)
        texto.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        texto.pack(fill="both", expand=True)
        lineas = [
            f"Origen: {comparacion.origen}",
            f"Destino: {comparacion.destino}",
            "",
            f"Copiar {_tamano(plan.bytes_totales)} · Espacio disponible: {_tamano(plan.espacio_disponible)}",
            f"{len(plan.archivos)} archivos y {len(plan.catalogos)} catálogos de fichas.",
        ]
        for sistema in self.sistemas.values():
            if sistema.clave in seleccion:
                juegos = seleccion[sistema.clave]
                detalle = "todos los juegos pendientes" if juegos is None else f"{len(juegos)} juegos"
                lineas.append(f"• {sistema.nombre} · {detalle}")
        if reemplazos:
            lineas.append(f"\nJuegos que autorizaste reemplazar con respaldo: {len(reemplazos)}.")
        if plan.avisos:
            lineas.extend(("", "Avisos:", *plan.avisos))
        lineas.extend(("", "Cierra RetroBat antes de iniciar la copia."))
        if plan.bytes_totales > plan.espacio_disponible:
            lineas.append("Falta espacio en el destino para esta selección.")
        texto.insert("1.0", "\n".join(lineas))
        texto.configure(state="disabled")
        acciones = ttk.Frame(ventana, padding=(12, 0, 12, 12))
        acciones.pack(fill="x")
        ttk.Button(acciones, text="Volver", command=ventana.destroy).pack(side="left")
        copiar = ttk.Button(acciones, text="Iniciar migración", command=lambda: self.aplicar(ventana, plan))
        copiar.pack(side="right")
        if plan.bytes_totales > plan.espacio_disponible:
            copiar.state(["disabled"])
        ventana.bind("<Escape>", lambda _: ventana.destroy())

    def aplicar(self, ventana, plan):
        if self.app.ocupado:
            return
        ventana.destroy()
        self.invalidar()

        def terminado(resultado):
            self.app.actualizar_despues_de_migrar(plan.destino)
            mensaje = f"Migración completada · {resultado.archivos} archivos · {resultado.catalogos} catálogos."
            self.detalle.set(mensaje + " Vuelve a comparar para ver el estado actualizado.")
            self.app.estado.set(mensaje)
            if resultado.respaldo:
                self.app.informe("Respaldo de migración", [str(resultado.respaldo)])

        self.app.ejecutar(
            lambda informar: aplicar_migracion(plan, informar),
            terminado, "Migrando sistemas de RetroBat…", con_progreso=True,
        )
