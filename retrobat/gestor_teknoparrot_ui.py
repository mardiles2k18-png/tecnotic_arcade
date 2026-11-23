"""Pestaña de instalación e importación de TeknoParrot."""
from collections import Counter
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from xml.etree.ElementTree import ParseError

import gestor_teknoparrot as tp
from gestor_core import tamanio_copia
from gestor_teknoparrot_instalacion import faltantes, preparar_instalacion
from gestor_teknoparrot_pantalla import configurar_pantalla, pantalla_oculta


class PanelTeknoParrot(ttk.Frame):
    def __init__(self, padre, app):
        super().__init__(padre, padding=16)
        self.app = app
        self.juegos = {}
        self.perfiles = {}
        self.presentes = Counter()
        self.raiz = None

        instalacion = ttk.LabelFrame(self, text="Emulador y requisitos", padding=8)
        instalacion.pack(fill="x", pady=(0, 10))
        self.estado = tk.StringVar(value="Selecciona la instalación de RetroBat en Inicio.")
        ttk.Label(instalacion, textvariable=self.estado, wraplength=810).pack(anchor="w", pady=(0, 6))
        acciones = ttk.Frame(instalacion)
        acciones.pack(fill="x")
        ttk.Button(acciones, text="Instalar y configurar TeknoParrot", command=self.instalar).pack(side="left")
        ttk.Button(acciones, text="Pantalla de carga…", command=self.configurar_pantalla).pack(side="left", padx=8)

        acciones = ttk.Frame(self)
        acciones.pack(fill="x", pady=(0, 8))
        varios = ttk.Button(acciones, text="Elegir carpeta con varios juegos…",
                            command=lambda: self.elegir_carpetas(varios=True))
        varios.pack(side="left", padx=(0, 6))
        uno = ttk.Button(acciones, text="Carpeta de un juego…", command=self.elegir_carpetas)
        uno.pack(side="left", padx=(0, 6))
        archivo = ttk.Button(acciones, text="Elegir archivo comprimido…",
                             command=lambda: self.elegir_carpetas(comprimido=True))
        archivo.pack(side="left")
        importar = ttk.Button(acciones, text="Importar seleccionados", command=self.importar)
        importar.pack(side="right")
        self.botones_juegos = (varios, uno, archivo, importar)
        for boton in self.botones_juegos:
            boton.state(["disabled"])

        lista = ttk.Frame(self)
        lista.pack(fill="both", expand=True)
        self.tabla = ttk.Treeview(lista, show="headings", columns=("origen", "perfil", "ejecutable", "estado"))
        for id_, titulo, ancho in (("origen", "Carpeta o archivo", 225), ("perfil", "Perfil oficial", 240),
                                   ("ejecutable", "Archivo de arranque", 175), ("estado", "Estado", 175)):
            self.tabla.heading(id_, text=titulo)
            self.tabla.column(id_, width=ancho, minwidth=90)
        barra = ttk.Scrollbar(lista, command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.tabla.pack(fill="both", expand=True)
        self.tabla.bind("<<TreeviewSelect>>", self.mostrar_seleccion)
        self.tabla.bind("<Double-1>", self.ver_error)

        edicion = ttk.Frame(self)
        edicion.pack(fill="x", pady=(8, 0))
        edicion.columnconfigure(1, weight=1)
        ttk.Label(edicion, text="Perfil de la fila").grid(row=0, column=0, sticky="w")
        self.selector = ttk.Combobox(edicion, state="readonly")
        self.selector.grid(row=0, column=1, sticky="ew", padx=8)
        self.selector.bind("<<ComboboxSelected>>", self.cambiar_perfil)
        ttk.Button(edicion, text="Ejecutable…", command=self.elegir_ejecutable).grid(row=0, column=2, padx=(0, 6))
        ttk.Button(edicion, text="Segundo archivo…", command=lambda: self.elegir_ejecutable(True)).grid(
            row=0, column=3, padx=(0, 6))
        ttk.Button(edicion, text="Quitar del lote", command=self.quitar_seleccion).grid(row=0, column=4)

    def actualizar(self, pendientes=()):
        if self.app.ocupado:
            return
        try:
            raiz = self.app.raiz_retrobat().resolve()
        except ValueError as error:
            self.estado.set(str(error))
            self.limpiar()
            self.raiz = None
            return
        if raiz != self.raiz:
            self.limpiar()
            self.raiz = raiz
        try:
            sistema = tp.sistema_teknoparrot(raiz)
        except (OSError, ValueError, ParseError) as error:
            self.limpiar()
            self.estado.set(str(error))
            return

        def revisar():
            emulador = tp.carpeta_emulador(raiz)
            instalado = not faltantes(emulador)
            mapeo = any((raiz / carpeta / "teknoparrot.yml").is_file()
                        for carpeta in ("system/resources/inputmapping", "user/inputmapping"))
            perfiles = tp.perfiles_locales(emulador) if instalado else []
            return instalado, mapeo, perfiles, tp.instalados(sistema)

        def mostrar(resultado):
            if Path(self.app.raiz.get()).resolve() != raiz:
                return
            instalado, mapeo, perfiles, self.presentes = resultado
            self.perfiles = {f"{p.titulo} [{p.id}]": p for p in perfiles}
            por_id = {p.id: p for p in perfiles}
            for juego in self.juegos.values():
                if juego.perfil:
                    nuevo = por_id.get(juego.perfil.id)
                    if nuevo != juego.perfil:
                        tp.seleccionar_perfil(juego, nuevo)
            self.selector["values"] = sorted(self.perfiles, key=str.casefold)
            listo = instalado and bool(perfiles)
            for boton in self.botones_juegos:
                boton.state(["!disabled"] if listo else ["disabled"])
            if listo:
                estado = f"Listo para cargar juegos · {len(perfiles)} perfiles · {sum(self.presentes.values())} juegos registrados."
            else:
                estado = "Pulsa Instalar y configurar TeknoParrot para preparar los componentes y habilitar la carga de juegos."
            controles = "Mapeo de RetroBat detectado." if mapeo else "RetroBat no incluye un mapa de controles."
            adicionales = f" No disponibles en el catálogo verificable: {', '.join(pendientes)}." if pendientes else ""
            self.estado.set(f"{estado}\n{controles} Destino: {sistema.carpeta}.{adicionales}")
            self.refrescar_lote()

        self.app.ejecutar(revisar, mostrar, "Comprobando TeknoParrot…")

    def limpiar(self):
        self.tabla.delete(*self.tabla.get_children())
        self.juegos.clear()
        self.perfiles.clear()
        self.presentes.clear()
        self.selector["values"] = ()
        self.selector.set("")
        for boton in self.botones_juegos:
            boton.state(["disabled"])

    def configurar_pantalla(self):
        def configurar(raiz):
            ocultar = not pantalla_oculta(raiz)
            if ocultar:
                texto = ("¿Ocultar EmulationStation al iniciar un juego?\n\n"
                         "Así la pantalla de carga no quedará delante del juego. El ajuste se aplica "
                         "a todos los sistemas. Cierra RetroBat antes de continuar.")
            else:
                texto = ("EmulationStation ya está configurado para ocultarse durante los juegos.\n\n"
                         "¿Volver a mostrar la pantalla de carga? Cierra RetroBat antes de continuar.")
            if not messagebox.askyesno("Pantalla de carga de RetroBat", texto, parent=self):
                return

            def terminar(respaldo):
                estado = ("Pantalla de carga oculta durante los juegos." if ocultar
                          else "Pantalla de carga restaurada.")
                self.app.estado.set(estado)
                detalle = f"\n\nRespaldo: {respaldo}" if respaldo else ""
                messagebox.showinfo("Pantalla de carga", estado + " Abre RetroBat para aplicar el cambio." + detalle,
                                    parent=self)

            self.app.ejecutar(lambda: configurar_pantalla(raiz, ocultar), terminar, "Guardando el ajuste de pantalla…")
        self.app.operar(configurar)

    def instalar(self):
        def iniciar(raiz):
            raiz = raiz.resolve()
            tp.sistema_teknoparrot(raiz)
            emulador = tp.carpeta_emulador(raiz)
            if not messagebox.askyesno(
                "Instalar y configurar TeknoParrot",
                f"¿Preparar TeknoParrot en esta instalación?\n\n{emulador}\n\n"
                "Se descargarán los componentes oficiales. Cierra RetroBat y TeknoParrot antes de continuar.",
                parent=self,
            ):
                return
            self.app.ejecutar(lambda informar: preparar_instalacion(raiz, informar), self.actualizar,
                              "Instalando y configurando TeknoParrot…", con_progreso=True)
        self.app.operar(iniciar)

    def elegir_carpetas(self, *, varios=False, comprimido=False):
        def elegir(raiz):
            if raiz.resolve() != self.raiz or not self.perfiles:
                raise ValueError("Pulsa Instalar y configurar TeknoParrot antes de cargar juegos.")
            if comprimido:
                elegidas = filedialog.askopenfilenames(
                    title="Selecciona juegos comprimidos",
                    filetypes=[("Juegos comprimidos", "*.zip *.7z *.rar")], parent=self)
                carpetas = [Path(ruta) for ruta in elegidas]
                if not carpetas:
                    return
            else:
                elegida = filedialog.askdirectory(title="Carpeta de juegos" if varios else "Carpeta del juego",
                                                   parent=self)
                if not elegida:
                    return
                carpeta = Path(elegida)
                carpetas = (sorted(ruta for ruta in carpeta.iterdir()
                                    if not ruta.name.startswith(".") and
                                    (ruta.is_dir() or ruta.suffix.lower() in tp.COMPRIMIDOS))
                            if varios else [carpeta])
                if not carpetas:
                    raise ValueError("No hay carpetas de juegos ni archivos ZIP, 7z o RAR en esta ubicación.")
            perfiles = tuple(self.perfiles.values())
            self.app.ejecutar(lambda: tp.revisar_carpetas(carpetas, perfiles), self.agregar_juegos,
                              "Buscando perfiles y ejecutables…")
        self.app.operar(elegir)

    def agregar_juegos(self, juegos):
        origenes = {juego.origen for juego in self.juegos.values()}
        for juego in juegos:
            if juego.origen not in origenes:
                self.juegos[self.tabla.insert("", "end")] = juego
                origenes.add(juego.origen)
        self.refrescar_lote()

    def refrescar_lote(self):
        pendientes = Counter(juego.perfil.id.casefold() for juego in self.juegos.values() if juego.perfil)
        for fila, juego in self.juegos.items():
            self.tabla.item(fila, values=(juego.origen.name, juego.perfil.id if juego.perfil else "",
                                          juego.ejecutable.name if juego.ejecutable else "",
                                          tp.estado_juego(juego, self.presentes, pendientes)))
        self.mostrar_seleccion()

    def seleccionado(self):
        seleccion = self.tabla.selection()
        return self.juegos.get(seleccion[0]) if len(seleccion) == 1 else None

    def mostrar_seleccion(self, _=None):
        juego = self.seleccionado()
        perfil = juego.perfil if juego else None
        self.selector.set(f"{perfil.titulo} [{perfil.id}]" if perfil else "")

    def cambiar_perfil(self, _):
        juego = self.seleccionado()
        if juego and not self.app.ocupado:
            perfil = self.perfiles.get(self.selector.get())
            if perfil is None:
                return
            self.app.ejecutar(lambda: tp.seleccionar_perfil(juego, perfil), lambda _: self.refrescar_lote(),
                              "Buscando los archivos del perfil…")

    def ver_error(self, _):
        juego = self.seleccionado()
        if juego and juego.error:
            messagebox.showerror(juego.origen.name, juego.error, parent=self)

    def elegir_ejecutable(self, segundo=False):
        juego = self.seleccionado()
        if self.app.ocupado or not juego:
            return
        if juego.error:
            self.ver_error(None)
            return
        if not juego.perfil:
            return
        if segundo and not juego.perfil.secundario:
            messagebox.showinfo("TeknoParrot", "Este perfil usa un solo archivo de arranque.", parent=self)
            return
        if juego.contenido is not None:
            self.elegir_dentro_del_archivo(juego, segundo)
            return
        nombre = filedialog.askopenfilename(title="Archivo de arranque del perfil", initialdir=juego.origen, parent=self)
        if not nombre:
            return
        ruta = Path(nombre).resolve()
        esperados = juego.perfil.secundario if segundo else juego.perfil.esperado
        if (not ruta.is_relative_to(juego.origen)
                or not (ruta.suffix.lower() in tp.BINARIOS or ruta.name.casefold() in esperados)):
            messagebox.showerror("TeknoParrot", "Elige un ejecutable del perfil dentro de la carpeta del juego.",
                                 parent=self)
            return
        setattr(juego, "secundario" if segundo else "ejecutable", ruta)
        self.refrescar_lote()

    def elegir_dentro_del_archivo(self, juego, segundo):
        candidatos = tp.candidatos_ejecutable(juego, segundo)
        if not candidatos:
            messagebox.showinfo("TeknoParrot", "No se encontraron ejecutables en el archivo comprimido.", parent=self)
            return
        ventana = tk.Toplevel(self)
        ventana.title("Ejecutable dentro del archivo")
        ventana.transient(self.winfo_toplevel())
        ventana.geometry("640x360")
        lista = tk.Listbox(ventana, exportselection=False)
        barra = ttk.Scrollbar(ventana, command=lista.yview)
        lista.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        lista.pack(fill="both", expand=True, padx=8, pady=8)
        lista.insert("end", *(ruta.as_posix() for ruta in candidatos))
        lista.selection_set(0)

        def confirmar(_=None):
            seleccion = lista.curselection()
            if seleccion:
                setattr(juego, "secundario" if segundo else "ejecutable", candidatos[seleccion[0]])
                self.refrescar_lote()
                ventana.destroy()

        ttk.Button(ventana, text="Usar ejecutable", command=confirmar).pack(pady=(0, 8))
        lista.bind("<Double-1>", confirmar)
        lista.bind("<Return>", confirmar)
        ventana.grab_set()
        lista.focus_set()

    def quitar_seleccion(self):
        if self.app.ocupado:
            return
        for fila in self.tabla.selection():
            self.juegos.pop(fila, None)
            self.tabla.delete(fila)
        self.refrescar_lote()

    def importar(self):
        def aplicar(raiz):
            raiz = raiz.resolve()
            if raiz != self.raiz:
                raise ValueError("La instalación cambió. Actualiza el estado antes de importar.")
            filas = [fila for fila in self.tabla.selection() if self.tabla.set(fila, "estado").startswith("Listo")]
            if not filas:
                raise ValueError("Selecciona uno o más juegos listos en la tabla.")
            if not messagebox.askyesno("TeknoParrot",
                f"¿Copiar {len(filas)} juegos y preparar sus perfiles? Cierra RetroBat y TeknoParrot antes de continuar.",
                parent=self):
                return
            juegos = [(fila, self.juegos[fila]) for fila in filas]

            def copiar(informar):
                completados, errores = [], []
                for fila, juego in juegos:
                    fase = (f"Extrayendo {juego.origen.name}…" if juego.contenido is not None
                            else f"Copiando {juego.origen.name}…")
                    hecho = 0

                    def avance(cantidad):
                        nonlocal hecho
                        hecho += cantidad
                        informar(min(hecho, total - 1), total, fase)

                    informar(0, None, fase)
                    try:
                        if juego.contenido is None:
                            total = tamanio_copia(juego.origen) + 1
                            avance(0)
                        tp.importar_juego(raiz, juego, avance)
                    except (OSError, ValueError, ParseError) as error:
                        errores.append(f"{juego.origen.name}: {error}")
                    else:
                        completados.append(fila)
                return completados, errores

            def terminar(resultado):
                completados, errores = resultado
                for fila in completados:
                    juego = self.juegos.pop(fila)
                    self.tabla.delete(fila)
                    self.presentes[juego.perfil.id.casefold()] += 1
                self.refrescar_lote()
                self.app.estado.set(f"{len(completados)} juegos importados · {len(errores)} errores. "
                                    "Actualiza la lista de juegos en RetroBat.")
                if errores:
                    self.app.informe("Importación de TeknoParrot", errores)

            self.app.ejecutar(copiar, terminar, "Importando juegos de TeknoParrot…", con_progreso=True)
        self.app.operar(aplicar)
