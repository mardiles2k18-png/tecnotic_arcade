"""Pestaña Biblioteca: juegos por sistema y estado de cada juego (antes «Biblioteca» y «Preparar juego»)."""

from collections import defaultdict
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from xml.etree.ElementTree import ParseError

from gestor_biblioteca import editar_nombre, eliminar_juego, plan_eliminar
from gestor_duplicados import Entrada, guardar_respaldo, marca_archivo
from gestor_preparar import categoria_juego, juegos_instalados
from gestor_preparar_ui import PanelEstado
from gestor_scraping import ControlScraping, buscar_medios
from gestor_scraping_proveedor import ATRIBUCION_ARCADE, categorias_disponibles

TODOS = "Todos los sistemas"


class DialogoScraping(simpledialog.Dialog):
    def __init__(self, padre, sistemas, preferido, juego):
        self.sistemas = sistemas
        self.preferido = preferido
        self.juego = juego
        super().__init__(padre, title="Buscar fichas y medios de juegos")

    def body(self, contenido):
        panel = ttk.Frame(contenido, padding=(16, 10))
        panel.pack(fill="both", expand=True)
        panel.columnconfigure(0, weight=1)

        ttk.Label(panel, text="Sistema instalado").grid(row=0, column=0, sticky="w")
        self.selector = ttk.Combobox(panel, values=tuple(self.sistemas), state="readonly", width=43)
        self.selector.set(self.preferido if self.preferido in self.sistemas else next(iter(self.sistemas)))
        self.selector.grid(row=1, column=0, sticky="ew", pady=(4, 8))
        self.selector.bind("<<ComboboxSelected>>", self.cambiar_sistema)

        self.alcance = tk.StringVar(self, value="sistema")
        self.todos = ttk.Radiobutton(panel, variable=self.alcance, value="sistema")
        self.todos.grid(row=2, column=0, sticky="w")
        if self.juego:
            self.individual = ttk.Radiobutton(panel, text="Solo el juego seleccionado", variable=self.alcance,
                                              value="juego")
            self.individual.grid(row=3, column=0, sticky="w")
            if self.sistemas[self.selector.get()][0] == self.juego.clave:
                self.alcance.set("juego")
        tipos = ttk.LabelFrame(panel, text="Qué descargar por juego", padding=(10, 8))
        tipos.grid(row=4, column=0, sticky="ew", pady=(12, 8))
        self.tipos = {}
        self.casillas = {}
        for i, (clave, etiqueta) in enumerate((("cover", "Carátula"), ("info", "Información"),
                                               ("logo", "Logo"), ("video", "Vídeo"), ("cheats", "Trucos"))):
            marcada = tk.BooleanVar(self, value=clave in {"cover", "info", "logo"})
            self.tipos[clave] = marcada
            casilla = ttk.Checkbutton(tipos, text=etiqueta, variable=marcada, command=self.refrescar_inicio)
            casilla.grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 20))
            self.casillas[clave] = casilla

        ttk.Label(panel, text="Cierra RetroBat durante la búsqueda. El Gestor conservará el material ya guardado.",
                  wraplength=395).grid(row=5, column=0, sticky="w")
        self.proveedor = ttk.Label(panel, wraplength=395)
        self.proveedor.grid(row=6, column=0, sticky="w", pady=(8, 0))
        self.cambiar_sistema()
        return self.selector

    def buttonbox(self):
        botones = ttk.Frame(self, padding=(16, 0, 16, 12))
        botones.pack(fill="x")
        ttk.Button(botones, text="Cancelar", command=self.cancel).pack(side="right")
        self.inicio = ttk.Button(botones, text="Buscar y aplicar", command=self.ok)
        self.inicio.pack(side="right", padx=(0, 8))
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        self.refrescar_inicio()

    def cambiar_sistema(self, _evento=None):
        clave, cantidad = self.sistemas[self.selector.get()]
        self.todos.configure(text=f"Todo el sistema ({cantidad} {'juego' if cantidad == 1 else 'juegos'})")
        if self.juego:
            coincide = self.juego.clave == clave
            self.individual.configure(state="normal" if coincide else "disabled")
            if not coincide:
                self.alcance.set("sistema")

        categorias = categorias_disponibles(clave)
        for tipo, casilla in self.casillas.items():
            casilla.configure(state="normal" if tipo in categorias else "disabled")
        if not categorias:
            fuente = "Todavía no hay un proveedor compatible con este sistema."
        elif "cheats" in categorias:
            fuente = ATRIBUCION_ARCADE + "\nLos trucos disponibles se guardan como archivos de texto."
        else:
            fuente = "Carátulas de Libretro. Se busca por el nombre exacto del archivo de juego."
        self.proveedor.configure(text=fuente)
        if hasattr(self, "inicio"):
            self.refrescar_inicio()

    def categorias_elegidas(self):
        clave, _ = self.sistemas[self.selector.get()]
        disponibles = categorias_disponibles(clave)
        return frozenset(tipo for tipo, valor in self.tipos.items() if tipo in disponibles and valor.get())

    def refrescar_inicio(self):
        self.inicio.configure(state="normal" if self.categorias_elegidas() else "disabled")

    def validate(self):
        return bool(self.selector.get() in self.sistemas and self.categorias_elegidas())

    def apply(self):
        clave, _cantidad = self.sistemas[self.selector.get()]
        self.result = (clave, self.alcance.get(), self.categorias_elegidas())


class PanelBiblioteca(ttk.Frame):
    def __init__(self, padre, app):
        super().__init__(padre, padding=16)
        self.app = app
        self.raiz = None
        self.sistemas = {}
        self.juegos = []
        self.por_sistema = {}
        self.opciones = {}
        self.filas_juego = {}
        self.filas_sistema = {}
        self.sistema = tk.StringVar(value=TODOS)
        self.buscar = tk.StringVar()
        self.resumen = tk.StringVar(value="Selecciona la instalación de RetroBat en Inicio.")

        barra = ttk.Frame(self)
        barra.pack(fill="x")
        ttk.Label(barra, text="Sistema").pack(side="left")
        self.selector = ttk.Combobox(barra, textvariable=self.sistema, state="readonly", width=34, values=(TODOS,))
        self.selector.pack(side="left", padx=(6, 10))
        self.selector.bind("<<ComboboxSelected>>", lambda _: self.mostrar_juegos())
        ttk.Label(barra, text="Buscar").pack(side="left")
        ttk.Entry(barra, textvariable=self.buscar).pack(side="left", fill="x", expand=True, padx=(6, 10))
        self.buscar.trace_add("write", lambda *_: self.mostrar_juegos())
        ttk.Button(barra, text="Respaldos…", command=app.ver_respaldos).pack(side="right")
        ttk.Button(barra, text="Verificar y gestionar duplicados…", command=app.ver_duplicados).pack(
            side="right", padx=6)
        ttk.Button(barra, text="Actualizar", command=self.actualizar).pack(side="right")
        ttk.Label(self, textvariable=self.resumen).pack(anchor="w", pady=(6, 4))

        self.control_scraping = None
        acciones_medios = ttk.Frame(self)
        acciones_medios.pack(fill="x", pady=(0, 6))
        self.boton_medios = ttk.Button(acciones_medios, text="Buscar fichas y medios…", command=self.buscar_medios)
        self.boton_medios.pack(side="left")
        self.pausa_medios = ttk.Button(acciones_medios, text="Pausar", command=self.pausar_medios, state="disabled")
        self.pausa_medios.pack(side="left", padx=(8, 4))
        self.cancelar_medios = ttk.Button(acciones_medios, text="Cancelar", command=self.detener_medios, state="disabled")
        self.cancelar_medios.pack(side="left")
        self.estado_medios = ttk.Label(acciones_medios)
        self.estado_medios.pack(side="left", padx=8)

        division = ttk.PanedWindow(self, orient="horizontal")
        division.pack(fill="both", expand=True)

        izquierda = ttk.Frame(division)
        tabla = ttk.Frame(izquierda)
        tabla.pack(fill="both", expand=True)
        self.arbol = ttk.Treeview(tabla, columns=("juegos",), show="tree headings", selectmode="browse")
        self.arbol.heading("#0", text="Categoría / juego")
        self.arbol.heading("juegos", text="Juegos")
        self.arbol.column("#0", width=300, minwidth=160)
        self.arbol.column("juegos", width=60, minwidth=50, anchor="center", stretch=False)
        barra_arbol = ttk.Scrollbar(tabla, command=self.arbol.yview)
        self.arbol.configure(yscrollcommand=barra_arbol.set)
        barra_arbol.pack(side="right", fill="y")
        self.arbol.pack(fill="both", expand=True)
        self.arbol.bind("<<TreeviewSelect>>", self.elegir)
        botones = ttk.Frame(izquierda)
        botones.pack(fill="x", pady=(6, 0))
        self.boton_sistema = ttk.Button(botones, text="Eliminar sistema…", command=self.quitar_sistema)
        self.boton_sistema.pack(side="left")
        self.boton_borrar = ttk.Button(botones, text="Eliminar juego…", command=self.quitar_juego)
        self.boton_borrar.pack(side="right")
        self.boton_nombre = ttk.Button(botones, text="Editar nombre…", command=self.editar)
        self.boton_nombre.pack(side="right", padx=6)
        division.add(izquierda, weight=2)

        self.estado = PanelEstado(division, app)
        division.add(self.estado, weight=3)
        self.refrescar_botones()

    # ------------------------------------------------------------------ datos
    def limpiar(self):
        self.raiz = None
        self.sistemas = {}
        self.juegos = []
        self.por_sistema = {}
        self.selector.configure(values=(TODOS,))
        self.sistema.set(TODOS)
        self.estado.limpiar()
        self.mostrar_juegos()

    def actualizar(self, elegir=None):
        if not self.app.raiz.get():
            return

        def revisar(raiz):
            raiz = raiz.resolve()
            sistemas = self.app.sistemas.copy()

            def mostrar(juegos):
                if Path(self.app.raiz.get()).resolve() != raiz:
                    return
                anterior = self.clave_elegida()
                self.raiz, self.sistemas, self.juegos = raiz, sistemas, juegos
                self.por_sistema = defaultdict(list)
                for juego in juegos:
                    self.por_sistema[juego.clave].append(juego)
                self.opciones = {TODOS: None}
                for clave in sorted(self.por_sistema, key=lambda c: sistemas[c].nombre.casefold()):
                    self.opciones[f"{sistemas[clave].nombre} ({len(self.por_sistema[clave])})"] = clave
                self.selector.configure(values=tuple(self.opciones))
                destino = elegir if elegir in self.por_sistema else anterior
                self.sistema.set(next((k for k, v in self.opciones.items() if v == destino), TODOS))
                self.mostrar_juegos()

            self.app.ejecutar(lambda informar: juegos_instalados(raiz, sistemas, informar), mostrar,
                              "Leyendo la biblioteca de RetroBat…", con_progreso=True)

        self.app.operar(revisar)

    def clave_elegida(self):
        return self.opciones.get(self.sistema.get())

    def mostrar_juegos(self):
        consulta = self.buscar.get().strip().casefold()
        clave_sistema = self.clave_elegida()
        seleccionado = self.estado.objetivo
        self.arbol.delete(*self.arbol.get_children())
        self.filas_juego.clear()
        self.filas_sistema.clear()
        claves = [clave_sistema] if clave_sistema else sorted(
            self.por_sistema, key=lambda c: self.sistemas[c].nombre.casefold())
        visibles = 0
        for clave in claves:
            juegos = [j for j in self.por_sistema.get(clave, ())
                      if not consulta or consulta in j.titulo.casefold() or consulta in j.ruta.name.casefold()]
            if not juegos:
                continue
            padre = ""
            if not clave_sistema:
                padre = self.arbol.insert("", "end", text=self.sistemas[clave].nombre, values=(len(juegos),),
                                          open=bool(consulta))
                self.filas_sistema[padre] = clave
            categorias = defaultdict(list)
            for juego in juegos:
                categorias[categoria_juego(juego)].append(juego)
            unica = len(categorias) == 1
            for categoria in sorted(categorias, key=str.casefold):
                nodo = self.arbol.insert(padre, "end", text=categoria, values=(len(categorias[categoria]),),
                                         open=bool(consulta) or (unica and bool(clave_sistema)))
                self.filas_sistema[nodo] = clave
                for juego in categorias[categoria]:
                    fila = self.arbol.insert(nodo, "end", text=juego.titulo)
                    self.filas_juego[fila] = juego
                    visibles += 1
                    if seleccionado is not None and getattr(seleccionado, "ruta", None) == juego.ruta:
                        self.arbol.see(fila)
                        self.arbol.selection_set(fila)
        if not self.app.raiz.get():
            self.resumen.set("Selecciona la instalación de RetroBat en Inicio.")
        elif self.raiz is None:
            self.resumen.set("Pulsa Actualizar para leer tu biblioteca.")
        elif not self.juegos:
            self.resumen.set("Tu biblioteca está vacía. Carga juegos desde la pestaña Cargar sistemas.")
        else:
            total = len(self.juegos) if not clave_sistema else len(self.por_sistema[clave_sistema])
            filtro = f" · {visibles} coinciden con la búsqueda" if consulta else ""
            self.resumen.set(f"{total} juegos{filtro}. Elige un juego para ver su estado; elige un sistema o "
                             "categoría para revisar el sistema.")
        self.refrescar_botones()

    # ------------------------------------------------------------------ selección
    def seleccion(self):
        filas = self.arbol.selection()
        return filas[0] if filas else None

    def elegir(self, _=None):
        fila = self.seleccion()
        if fila in self.filas_juego:
            juego = self.filas_juego[fila]
            if getattr(self.estado.objetivo, "ruta", None) != juego.ruta:
                self.estado.revisar_juego(juego)
        elif fila in self.filas_sistema:
            clave = self.filas_sistema[fila]
            if self.estado.objetivo != clave:
                self.estado.revisar_sistema(clave)
        self.refrescar_botones()

    def refrescar_botones(self):
        fila = self.seleccion()
        juego = "normal" if fila in self.filas_juego else "disabled"
        self.boton_nombre.configure(state=juego)
        self.boton_medios.configure(state="normal" if self.juegos and self.control_scraping is None else "disabled")
        self.boton_borrar.configure(state=juego)
        self.boton_sistema.configure(state="normal" if fila in self.filas_sistema or fila in self.filas_juego
                                     else "disabled")

    def valido(self):
        """La instalación no cambió desde la última lectura."""
        if self.app.ocupado or self.raiz is None:
            return False
        if Path(self.app.raiz.get()).resolve() != self.raiz or self.app.sistemas != self.sistemas:
            messagebox.showinfo("Biblioteca", "La instalación cambió. Pulsa Actualizar.", parent=self)
            return False
        return True

    # ------------------------------------------------------------------ acciones (mismas reglas que la V28)
    def pausar_medios(self):
        if self.control_scraping:
            pausado = self.control_scraping.pausar()
            self.pausa_medios.configure(text="Reanudar" if pausado else "Pausar")
            self.estado_medios.configure(text="En pausa al terminar la descarga en curso." if pausado else "")

    def detener_medios(self):
        if self.control_scraping and self.control_scraping.cancelar():
            self.pausa_medios.configure(state="disabled")
            self.cancelar_medios.configure(state="disabled")
            self.estado_medios.configure(text="Cancelando y guardando los resultados disponibles…")

    def finalizar_medios(self):
        self.control_scraping = None
        self.pausa_medios.configure(text="Pausar", state="disabled")
        self.cancelar_medios.configure(state="disabled")
        self.estado_medios.configure(text="")
        self.refrescar_botones()
    def buscar_medios(self):
        if not self.valido() or not self.juegos:
            return
        fila = self.seleccion()
        juego = self.filas_juego.get(fila)
        preferido = juego.clave if juego else self.filas_sistema.get(fila) or self.clave_elegida()
        sistemas = {nombre: (clave, len(self.por_sistema[clave])) for nombre, clave in self.opciones.items() if clave}
        etiqueta_preferida = next((nombre for nombre, (clave, _) in sistemas.items() if clave == preferido), None)
        dialogo = DialogoScraping(self, sistemas, etiqueta_preferida, juego)
        if not dialogo.result or not self.valido():
            return
        clave, alcance, categorias = dialogo.result
        juegos = [juego] if alcance == "juego" else self.por_sistema[clave]
        raiz = self.raiz

        control = self.control_scraping = ControlScraping()
        self.pausa_medios.configure(state="normal")
        self.cancelar_medios.configure(state="normal")
        self.refrescar_botones()

        def buscar(informar):
            entradas = [Entrada(j.sistema, j.ruta, None, marca_archivo(j.ruta)) for j in juegos]
            return buscar_medios(raiz, entradas, categorias, informar=informar, control=control)

        def mostrar(resultado):
            actualizados = resultado["actualizados"]
            if actualizados:
                self.actualizar(clave)
            texto = "Búsqueda cancelada.\n" if resultado["cancelado"] else ""
            texto += (f"Juegos actualizados: {actualizados} de {len(juegos)}.\n"
                     f"Sin contenido nuevo encontrado: {resultado['sin_resultado']}.\n"
                     f"Ya completos: {resultado['sin_cambios']}.")
            if actualizados:
                texto += "\nActualiza la lista de juegos en RetroBat para ver los cambios."
            avisos = resultado["avisos"]
            if avisos:
                texto += "\n\n" + "\n".join(avisos[:5])
                if len(avisos) > 5:
                    texto += f"\nY {len(avisos) - 5} avisos más."
            messagebox.showinfo("Resultado de fichas y medios", texto, parent=self)

        self.app.ejecutar(buscar, mostrar, "Buscando fichas y medios…", con_progreso=True, al_finalizar=self.finalizar_medios)

    def editar(self):
        fila = self.seleccion()
        if fila not in self.filas_juego or not self.valido():
            return
        juego = self.filas_juego[fila]
        nombre = simpledialog.askstring("Editar nombre", "Nombre que se mostrará en RetroBat",
                                       initialvalue=juego.titulo, parent=self)
        if nombre is None:
            return
        try:
            entrada = Entrada(juego.sistema, juego.ruta, None, marca_archivo(juego.ruta))
            titulo = editar_nombre(self.raiz, entrada, nombre)
        except (OSError, ValueError, ParseError) as error:
            messagebox.showerror("Editar nombre", str(error), parent=self)
            return
        self.arbol.item(fila, text=titulo)
        self.app.estado.set(f"Nombre guardado: {titulo}. Recarga la lista de juegos en RetroBat.")
        self.actualizar(juego.clave)

    def quitar_juego(self):
        fila = self.seleccion()
        if fila not in self.filas_juego or not self.valido():
            return
        juego = self.filas_juego[fila]
        raiz = self.raiz
        try:
            entrada = Entrada(juego.sistema, juego.ruta, None, marca_archivo(juego.ruta))
        except OSError as error:
            messagebox.showerror("Eliminar juego", str(error), parent=self)
            return

        def confirmar(plan):
            if Path(self.app.raiz.get()).resolve() != raiz:
                messagebox.showinfo("Biblioteca", "La instalación cambió.", parent=self)
                return
            archivos = "\n".join(str(archivo) for archivo, _ in plan)
            aviso = ("\nSolo se retirará el acceso directo."
                     if juego.ruta.suffix.lower() == ".lnk" and len(plan) == 1 and plan[0][0] == juego.ruta else "")
            if not messagebox.askyesno(
                "Eliminar juego", f"¿Eliminar {juego.titulo} de RetroBat?\n\n{archivos}{aviso}\n\n"
                "Los archivos se moverán a un respaldo recuperable.", parent=self,
            ):
                return

            def terminar(respaldo):
                self.app.estado.set(f"Juego eliminado de la biblioteca. Respaldo: {respaldo}")
                self.estado.limpiar()
                self.actualizar(juego.clave)

            self.app.ejecutar(lambda: eliminar_juego(raiz, entrada, plan), terminar, "Retirando el juego…")

        self.app.ejecutar(lambda: plan_eliminar(raiz, entrada), confirmar, "Revisando los archivos del juego…")

    def quitar_sistema(self):
        fila = self.seleccion()
        clave = self.filas_sistema.get(fila) or getattr(self.filas_juego.get(fila), "clave", None)
        if clave is None or not self.valido():
            return
        raiz = self.raiz
        sistema = self.sistemas[clave]
        carpeta = sistema.carpeta
        if not messagebox.askyesno(
            "Eliminar sistema", f"¿Retirar todos los juegos de {sistema.nombre}?\n\n{carpeta}"
            "\n\nLa carpeta se moverá a un respaldo. Se conservarán los emuladores, "
            "las partidas guardadas y las instalaciones de Windows fuera de esta carpeta.", parent=self,
        ):
            return

        def retirar():
            base = (raiz / "roms").resolve()
            if carpeta.resolve() != carpeta or carpeta == base or not carpeta.is_relative_to(base):
                raise ValueError("La carpeta ya no está dentro de la biblioteca de RetroBat.")
            return guardar_respaldo(raiz, [carpeta], mover=True)

        def terminado(respaldo):
            self.app.cargar_categorias()
            self.app.estado.set(f"Sistema retirado. Respaldo: {respaldo}")
            self.estado.limpiar()
            self.sistema.set(TODOS)
            self.actualizar()

        self.app.ejecutar(retirar, terminado, "Retirando el sistema…")
