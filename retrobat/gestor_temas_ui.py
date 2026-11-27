"""Gestión de los temas instalados en RetroBat."""

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from gestor_temas import eliminar_tema, exportar_tema, importar_tema, listar_temas


class PanelTemas(ttk.Frame):
    def __init__(self, padre, app):
        super().__init__(padre)
        self.app = app
        self.raiz = None
        self.temas = {}
        self.detalle = tk.StringVar()

        ttk.Label(self, text="Temas instalados", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tabla = ttk.Frame(self)
        tabla.pack(fill="both", expand=True, pady=(4, 6))
        self.tabla = ttk.Treeview(
            tabla, columns=("tema", "estado"), show="headings", selectmode="browse", height=5,
        )
        self.tabla.heading("tema", text="Tema")
        self.tabla.heading("estado", text="Estado")
        self.tabla.column("tema", width=360)
        self.tabla.column("estado", width=100, minwidth=85, stretch=False)
        barra = ttk.Scrollbar(tabla, orient="vertical", command=self.tabla.yview)
        barra.pack(side="right", fill="y")
        self.tabla.configure(yscrollcommand=barra.set)
        self.tabla.pack(fill="both", expand=True)
        self.tabla.bind("<<TreeviewSelect>>", self.seleccionar)

        ttk.Label(self, textvariable=self.detalle, wraplength=650).pack(fill="x", pady=(0, 6))
        acciones = ttk.Frame(self)
        acciones.pack(fill="x")
        self.boton_importar = ttk.Button(acciones, text="Importar ZIP…", command=self.importar)
        self.boton_importar.pack(side="left", padx=(0, 6))
        self.boton_exportar = ttk.Button(acciones, text="Exportar ZIP…", command=self.exportar)
        self.boton_exportar.pack(side="left", padx=(0, 6))
        self.boton_eliminar = ttk.Button(acciones, text="Eliminar tema…", command=self.eliminar)
        self.boton_eliminar.pack(side="left")
        self.boton_actualizar = ttk.Button(acciones, text="Actualizar lista", command=self.actualizar)
        self.boton_actualizar.pack(side="right")
        self.limpiar()

    def limpiar(self):
        self.raiz = None
        self.detalle.set("Selecciona una instalación de RetroBat en Inicio.")
        self.tabla.delete(*self.tabla.get_children())
        self.temas.clear()
        self.seleccionar()

    def actualizar(self):
        if not self.app.raiz.get():
            self.limpiar()
            return

        def mostrar(raiz):
            anterior = self.tema_seleccionado() if raiz == self.raiz else None
            self.limpiar()
            self.detalle.set("No se pudo leer la lista de temas.")
            temas = listar_temas(raiz)
            self.raiz = raiz
            for tema in temas:
                fila = self.tabla.insert("", "end", values=(tema.nombre, "Activo" if tema.activo else "Instalado"))
                self.temas[fila] = tema
                if anterior and anterior.nombre == tema.nombre:
                    self.tabla.selection_set(fila)
            mensaje = "Descarga temas desde RetroBat o importa un ZIP desde aquí."
            if temas:
                mensaje = "Selecciona en RetroBat el tema que quieras usar."
            self.detalle.set(mensaje)
            self.seleccionar()

        self.app.operar(mostrar)

    def tema_seleccionado(self):
        filas = self.tabla.selection()
        return self.temas.get(filas[0]) if filas else None

    def seleccionar(self, _=None):
        tema = self.tema_seleccionado()
        self.boton_importar.state(["!disabled"] if self.raiz else ["disabled"])
        self.boton_exportar.state(["!disabled"] if tema else ["disabled"])
        self.boton_eliminar.state(["!disabled"] if tema and not tema.activo else ["disabled"])
        self.boton_actualizar.state(["!disabled"] if self.app.raiz.get() else ["disabled"])

    def exportar(self):
        tema = self.tema_seleccionado()
        if not tema or self.app.ocupado:
            return
        ruta = filedialog.asksaveasfilename(
            title="Exportar tema", parent=self, initialfile=f"{tema.nombre}.zip",
            defaultextension=".zip", filetypes=[("Tema comprimido", "*.zip")], confirmoverwrite=False,
        )
        if ruta:
            self.operar_en_instalacion(
                lambda raiz: exportar_tema(raiz, tema.nombre, Path(ruta)),
                lambda destino: self.app.estado.set(f"Tema exportado a {destino}"),
                "Exportando el tema…",
            )

    def importar(self):
        if self.app.ocupado:
            return
        ruta = filedialog.askopenfilename(
            title="Importar tema", parent=self, filetypes=[("Tema comprimido", "*.zip")],
        )
        if not ruta:
            return
        nombre = simpledialog.askstring(
            "Nombre del tema",
            "Escribe el nombre de la copia, por ejemplo AluBrush Tecnotics.\n"
            "Deja el campo vacío para usar el nombre del tema del ZIP.",
            parent=self,
        )
        if nombre is None:
            return

        def terminado(destino):
            self.actualizar()
            self.app.estado.set(f"Tema instalado: {destino.name}. Selecciónalo en RetroBat.")

        self.operar_en_instalacion(
            lambda raiz: importar_tema(raiz, Path(ruta), nombre.strip() or None),
            terminado, "Importando el tema…",
        )

    def eliminar(self):
        tema = self.tema_seleccionado()
        if not tema or tema.activo or self.app.ocupado:
            return
        if not messagebox.askyesno(
            "Eliminar tema", f"¿Retirar «{tema.nombre}» de RetroBat?\n\nSe guardará una copia de respaldo.",
            parent=self,
        ):
            return

        def terminado(destino):
            self.actualizar()
            self.app.estado.set(f"Tema retirado. Respaldo: {destino}")

        self.operar_en_instalacion(
            lambda raiz: eliminar_tema(raiz, tema.nombre), terminado, "Retirando el tema…",
        )

    def operar_en_instalacion(self, tarea, terminar, mensaje):
        def ejecutar(raiz):
            if raiz != self.raiz:
                self.actualizar()
                raise ValueError("La instalación seleccionada cambió. Vuelve a elegir el tema.")
            self.app.ejecutar(lambda: tarea(raiz), terminar, mensaje)

        self.app.operar(ejecutar)
