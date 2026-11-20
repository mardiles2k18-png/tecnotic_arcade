"""Gestor de escritorio Tecnotics para RetroBat."""
from concurrent.futures import ThreadPoolExecutor
import filecmp
import os
from pathlib import Path
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from xml.etree.ElementTree import ParseError

from gestor_core import (CARPETAS, buscar_juegos, copiar, duplicados, editar_ini, nombre_seguro,
                         revisar_bios, shortcut, sistemas_instalados)

REPO = Path(__file__).resolve().parents[1]


class Gestor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tecnotics Arcade · Gestor de RetroBat")
        self.geometry("980x630")
        self.minsize(740, 500)
        self.raiz = tk.StringVar()
        self.origen = tk.StringVar()
        self.categoria = tk.StringVar()
        self.sistema = tk.StringVar()
        self.estado = tk.StringVar(value="Selecciona tu instalación de RetroBat.")
        self.candidato = tk.StringVar()
        self.sistemas = {}
        self.filas = {}
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.ocupado = False

        panel = ttk.Frame(self, padding=16)
        panel.pack(fill="both", expand=True)
        panel.columnconfigure(1, weight=1)
        panel.rowconfigure(4, weight=1)
        self.carpeta(panel, 0, "RetroBat", self.raiz, self.cargar_sistemas)
        self.carpeta(panel, 1, "Carpeta de juegos", self.origen)
        ttk.Label(panel, text="Sistema").grid(row=2, column=0, sticky="w")
        self.selector = ttk.Combobox(panel, textvariable=self.sistema, state="readonly")
        self.selector.grid(row=2, column=1, sticky="ew", padx=8, pady=4)
        ttk.Label(panel, text="Categoría (opcional)").grid(row=3, column=0, sticky="w")
        ttk.Entry(panel, textvariable=self.categoria).grid(row=3, column=1, sticky="ew", padx=8, pady=4)
        ttk.Button(panel, text="Vista previa", command=self.previsualizar).grid(row=3, column=2)

        tabla = ttk.Frame(panel)
        tabla.grid(row=4, column=0, columnspan=3, sticky="nsew", pady=8)
        self.lista = ttk.Treeview(tabla, columns=("juego", "archivo", "estado"), show="headings")
        for columna, titulo, ancho in (("juego", "Juego", 190), ("archivo", "Archivo seleccionado", 450),
                                       ("estado", "Estado", 180)):
            self.lista.heading(columna, text=titulo)
            self.lista.column(columna, width=ancho)
        scroll = ttk.Scrollbar(tabla, command=self.lista.yview)
        self.lista.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.lista.pack(fill="both", expand=True)
        self.lista.bind("<<TreeviewSelect>>", self.mostrar_candidatos)

        ttk.Label(panel, text="Ejecutable de la fila").grid(row=5, column=0, sticky="w")
        self.ejecutables = ttk.Combobox(panel, textvariable=self.candidato, state="readonly")
        self.ejecutables.grid(row=5, column=1, sticky="ew", padx=8)
        self.ejecutables.bind("<<ComboboxSelected>>", self.elegir_ejecutable)
        ttk.Button(panel, text="Importar seleccionados", command=self.importar).grid(row=5, column=2)

        herramientas = ttk.Frame(panel)
        herramientas.grid(row=6, column=0, columnspan=3, sticky="w", pady=12)
        for titulo, accion in (("Duplicados", self.ver_duplicados), ("Verificar BIOS", self.bios),
                               ("Instalar intro", self.intro), ("Crear tema", self.tema),
                               ("Editar tema", self.editar_tema), ("Configurar RetroBat", self.configurar)):
            ttk.Button(herramientas, text=titulo, command=accion).pack(side="left", padx=(0, 6))
        ttk.Label(panel, textvariable=self.estado).grid(row=7, column=0, columnspan=3, sticky="w")
        for variable in (self.raiz, self.origen, self.sistema, self.categoria):
            variable.trace_add("write", self.limpiar)

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

    def limpiar(self, *_):
        self.lista.delete(*self.lista.get_children())
        self.filas.clear()
        self.mostrar_candidatos()

    def raiz_retrobat(self):
        raiz = Path(self.raiz.get())
        if not self.raiz.get() or not (raiz / "retrobat.exe").is_file():
            raise ValueError("Selecciona la carpeta que contiene retrobat.exe.")
        return raiz

    def ejecutar(self, tarea, al_terminar):
        if self.ocupado:
            return
        self.ocupado = True
        self.estado.set("Procesando…")
        futuro = self.executor.submit(tarea)

        def consultar():
            if not futuro.done():
                self.after(75, consultar)
                return
            self.ocupado = False
            self.estado.set("Listo")
            try:
                al_terminar(futuro.result())
            except Exception as error:
                messagebox.showerror("RetroBat", str(error), parent=self)
        self.after(75, consultar)

    def cargar_sistemas(self):
        self.sistema.set("")
        self.selector["values"] = ()
        self.sistemas = {}
        try:
            self.sistemas = sistemas_instalados(self.raiz_retrobat())
        except (OSError, ValueError, ParseError) as error:
            messagebox.showerror("Sistemas", str(error), parent=self)
            return
        self.selector["values"] = sorted(self.sistemas)
        self.estado.set("Elige la carpeta de juegos y el sistema para crear la vista previa.")

    def previsualizar(self):
        if self.ocupado:
            return
        try:
            raiz = self.raiz_retrobat()
            sistema = self.sistema.get()
            if not self.origen.get() or sistema not in self.sistemas:
                raise ValueError("Elige la carpeta de juegos y el sistema.")
            origen = Path(self.origen.get())
            categoria = self.categoria.get().strip()
            carpeta_sistema = raiz / "roms" / sistema
            destino = carpeta_sistema / nombre_seguro(categoria) if categoria else carpeta_sistema
            extensiones = self.sistemas[sistema]
        except ValueError as error:
            messagebox.showerror("Vista previa", str(error), parent=self)
            return

        def buscar():
            existentes = {p.name.casefold() for p in carpeta_sistema.rglob("*")
                          if p.suffix.lower() in extensiones}
            return buscar_juegos(origen, sistema, extensiones), existentes

        def mostrar(resultado):
            if (self.raiz.get(), self.origen.get(), self.sistema.get(), self.categoria.get().strip()) != (
                    str(raiz), str(origen), sistema, categoria):
                return
            self.limpiar()
            juegos, existentes = resultado
            for nombre, candidatos in juegos:
                elegido = candidatos[0] if len(candidatos) == 1 else None
                if sistema == "windows":
                    sufijo = ".lnk"
                elif candidatos[0].is_dir():
                    sufijo = CARPETAS[sistema]
                else:
                    sufijo = candidatos[0].suffix.lower()
                salida = destino / (nombre + sufijo)
                estado = "Elige un ejecutable" if elegido is None else "Listo"
                try:
                    nombre_seguro(nombre + sufijo)
                except ValueError:
                    estado = "Nombre inválido"
                if salida.name.casefold() in existentes or salida.exists():
                    estado = "Ya existe en el sistema"
                item = self.lista.insert("", "end", values=(nombre, elegido or "", estado))
                self.filas[item] = (candidatos, elegido, salida, estado)
            self.estado.set(f"{len(juegos)} juegos encontrados. Selecciona las filas que quieres importar.")

        self.ejecutar(buscar, mostrar)

    def mostrar_candidatos(self, _=None):
        seleccion = self.lista.selection()
        fila = self.filas.get(seleccion[0]) if len(seleccion) == 1 else None
        self.ejecutables["values"] = tuple(map(str, fila[0])) if fila else ()
        self.candidato.set(str(fila[1]) if fila and fila[1] else "")

    def elegir_ejecutable(self, _):
        seleccion = self.lista.selection()
        if len(seleccion) != 1:
            return
        item = seleccion[0]
        candidatos, _, salida, estado = self.filas[item]
        elegido = Path(self.candidato.get())
        if elegido not in candidatos:
            return
        if estado == "Elige un ejecutable":
            estado = "Listo"
        self.filas[item] = (candidatos, elegido, salida, estado)
        self.lista.set(item, "archivo", str(elegido))
        self.lista.set(item, "estado", estado)

    def importar(self):
        if self.ocupado:
            return
        seleccion = self.lista.selection()
        filas = [(item, self.filas[item]) for item in seleccion if self.filas[item][3] == "Listo"]
        if not filas:
            messagebox.showinfo("Importar", "Selecciona al menos un juego con estado Listo.", parent=self)
            return
        es_windows = self.sistema.get() == "windows"
        accion = "Crear accesos directos" if es_windows else "Copiar juegos"
        if not messagebox.askyesno("Importar", f"¿{accion} para {len(filas)} juegos seleccionados?",
                                  parent=self):
            return

        def importar_filas():
            resultados = []
            for item, (_, elegido, destino, _) in filas:
                try:
                    (shortcut if es_windows else copiar)(elegido, destino)
                    resultados.append((item, "Importado", None))
                except (OSError, ValueError, subprocess.SubprocessError) as error:
                    resultados.append((item, "Error", f"{destino.name}: {error}"))
            return resultados

        def terminar(resultados):
            errores = []
            for item, estado, detalle in resultados:
                if item in self.filas:
                    candidatos, elegido, destino, _ = self.filas[item]
                    self.filas[item] = candidatos, elegido, destino, estado
                    self.lista.set(item, "estado", estado)
                if detalle:
                    errores.append(detalle)
            self.estado.set(f"{len(resultados) - len(errores)} importados · {len(errores)} errores")
            if errores:
                self.informe("Errores de importación", errores)

        self.ejecutar(importar_filas, terminar)

    def informe(self, titulo, lineas):
        ventana = tk.Toplevel(self)
        ventana.title(titulo)
        ventana.geometry("780x380")
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
            self.ejecutar(lambda: list(duplicados(raiz, sistemas)),
                         lambda lineas: self.informe("Juegos repetidos", lineas))
        self.operar(revisar)

    def bios(self):
        def revisar(raiz):
            archivo = filedialog.askopenfilename(title="Manifiesto de BIOS (MD5 y ruta relativa)")
            if archivo:
                self.ejecutar(lambda: revisar_bios(raiz, Path(archivo)),
                             lambda lineas: self.informe("Verificación de BIOS", lineas))
        self.operar(revisar)

    def intro(self):
        def instalar(raiz):
            archivo = filedialog.askopenfilename(title="Video de intro", filetypes=[("Video MP4", "*.mp4")],
                                                 initialdir=REPO / "arranque" / "splash")
            if not archivo:
                return
            archivo = Path(archivo)
            if archivo.suffix.lower() != ".mp4":
                raise ValueError("Selecciona un video MP4.")
            destino = raiz / "emulationstation" / ".emulationstation" / "video" / archivo.name
            if not messagebox.askyesno("Intro", "¿Copiar el video y activarlo en retrobat.ini?", parent=self):
                return

            def aplicar():
                if destino.exists():
                    if not filecmp.cmp(archivo, destino, shallow=False):
                        raise FileExistsError(f"Ya existe otro video con ese nombre: {destino}")
                else:
                    copiar(archivo, destino)
                editar_ini(raiz, "SplashScreen", {"EnableIntro": "1", "RandomVideo": "0",
                                                "FilePath": "default", "FileName": archivo.name})
            self.ejecutar(aplicar, lambda _: self.estado.set(f"Intro configurada: {archivo.name}"))
        self.operar(instalar)

    def tema(self):
        def crear(raiz):
            plantilla = filedialog.askdirectory(title="Tema base", initialdir=REPO / "themes")
            if not plantilla:
                return
            plantilla = Path(plantilla)
            if not (plantilla / "theme.xml").is_file():
                raise ValueError("La carpeta del tema base debe contener theme.xml.")
            nombre = simpledialog.askstring("Crear tema", "Nombre de carpeta del nuevo tema", parent=self)
            if nombre:
                destino = raiz / "emulationstation" / ".emulationstation" / "themes" / nombre_seguro(nombre)
                self.ejecutar(lambda: copiar(plantilla, destino),
                             lambda _: self.estado.set(f"Tema creado: {nombre}. Selecciónalo en RetroBat."))
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
        self.operar(lambda raiz: subprocess.Popen(["notepad.exe", str(raiz / "retrobat.ini")]))


if __name__ == "__main__":
    if os.name != "nt":
        raise SystemExit("El gestor se ejecuta en Windows.")
    Gestor().mainloop()
