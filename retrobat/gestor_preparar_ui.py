"""Pestaña «Preparar juego»: guía en orden lógico hasta poder probar un juego desde RetroBat."""

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from gestor_emuladores import catalogo_emuladores, instalar_emulador
from gestor_firmware import abrir_emulador, aplicar_firmware
from gestor_preparar import (ACCION_ARCHIVO, ACCION_EMULADOR, ACCION_IMPORTAR, ACCION_PROBAR, ACCION_REQUISITOS,
                             ACCION_TEKNOPARROT, AVISO, ESPERA, HECHO, PENDIENTE, comando_prueba, item_emulador,
                             juegos_instalados, preparar_plan)
from gestor_teknoparrot_instalacion import preparar_instalacion

COLORES = {HECHO: "#14704b", PENDIENTE: "#b35c00", AVISO: "#9a3412", ESPERA: "#6b7280"}
SIMBOLOS = {HECHO: "✔", PENDIENTE: "●", AVISO: "⚠", ESPERA: "○"}
AUTOMATICAS = {"Instalar", "Descarga oficial"}
TITULOS_PASOS = ("Juego", "Emulador", "BIOS y firmware", "Probar")


class PanelPreparar(ttk.Frame):
    def __init__(self, padre, app):
        super().__init__(padre, padding=16)
        self.app = app
        self.raiz = None
        self.juegos = []
        self.visibles = {}
        self.plan = None
        self.buscar = tk.StringVar()
        self.resumen = tk.StringVar(value="Elige un juego de tu biblioteca y sigue los pasos en orden.")

        cabecera = ttk.Frame(self)
        cabecera.pack(fill="x")
        ttk.Label(cabecera, textvariable=self.resumen, wraplength=620).pack(side="left", anchor="w")
        ttk.Button(cabecera, text="Importar un juego nuevo…", command=self.importar_nuevo).pack(side="right")
        ttk.Button(cabecera, text="Actualizar lista", command=self.actualizar).pack(side="right", padx=6)

        division = ttk.PanedWindow(self, orient="horizontal")
        division.pack(fill="both", expand=True, pady=(8, 0))

        # Columna izquierda: biblioteca
        izquierda = ttk.Frame(division)
        filtro = ttk.Frame(izquierda)
        filtro.pack(fill="x", pady=(0, 6))
        ttk.Label(filtro, text="Buscar").pack(side="left")
        entrada = ttk.Entry(filtro, textvariable=self.buscar)
        entrada.pack(side="left", fill="x", expand=True, padx=(6, 0))
        self.buscar.trace_add("write", lambda *_: self.mostrar_juegos())
        tabla = ttk.Frame(izquierda)
        tabla.pack(fill="both", expand=True)
        self.lista = ttk.Treeview(tabla, columns=("juego", "sistema"), show="headings", selectmode="browse")
        for columna, titulo, ancho in (("juego", "Juego", 230), ("sistema", "Sistema", 150)):
            self.lista.heading(columna, text=titulo)
            self.lista.column(columna, width=ancho, minwidth=90)
        barra = ttk.Scrollbar(tabla, command=self.lista.yview)
        self.lista.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.lista.pack(fill="both", expand=True)
        self.lista.bind("<<TreeviewSelect>>", self.elegir)
        division.add(izquierda, weight=2)

        # Columna derecha: pasos
        derecha = ttk.Frame(division, padding=(12, 0, 0, 0))
        division.add(derecha, weight=3)
        pasos = ttk.LabelFrame(derecha, text="Pasos", padding=10)
        pasos.pack(fill="x")
        pasos.columnconfigure(1, weight=1)
        self.filas_pasos = []
        for indice, titulo in enumerate(TITULOS_PASOS):
            ttk.Label(pasos, text=f"{indice + 1}. {titulo}", font=("Segoe UI", 10, "bold")).grid(
                row=indice * 2, column=0, sticky="w", pady=(6 if indice else 0, 0))
            estado = tk.Label(pasos, text="○ —", fg=COLORES[ESPERA], anchor="w")
            estado.grid(row=indice * 2, column=1, sticky="w", padx=8, pady=(6 if indice else 0, 0))
            texto = ttk.Label(pasos, text="", justify="left")
            texto.grid(row=indice * 2 + 1, column=0, columnspan=2, sticky="w", padx=(18, 0))
            self.filas_pasos.append((estado, texto))
        pasos.bind("<Configure>", lambda evento: [texto.configure(wraplength=max(evento.width - 50, 200))
                                                  for _, texto in self.filas_pasos])

        ttk.Label(derecha, text="Requisitos de este juego y de este emulador").pack(anchor="w", pady=(10, 2))
        marco = ttk.Frame(derecha)
        marco.pack(fill="both", expand=True)
        self.requisitos = ttk.Treeview(marco, columns=("archivo", "estado", "ubicacion"), show="headings", height=5)
        for columna, titulo, ancho in (("archivo", "Archivo", 150), ("estado", "Estado", 150),
                                       ("ubicacion", "Se comprueba en", 260)):
            self.requisitos.heading(columna, text=titulo)
            self.requisitos.column(columna, width=ancho, minwidth=80)
        self.requisitos.pack(fill="both", expand=True)

        acciones = ttk.Frame(derecha)
        acciones.pack(fill="x", pady=(8, 0))
        self.boton_siguiente = ttk.Button(acciones, text="Siguiente paso", command=self.siguiente_paso)
        self.boton_siguiente.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.boton_probar = ttk.Button(acciones, text="Probar desde RetroBat",
                                       command=lambda: self.accion(ACCION_PROBAR))
        self.boton_probar.grid(row=0, column=1, sticky="ew")
        self.boton_requisitos = ttk.Button(acciones, text="Instalar requisitos",
                                           command=lambda: self.accion(ACCION_REQUISITOS))
        self.boton_requisitos.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(6, 0))
        self.boton_archivo = ttk.Button(acciones, text="Importar archivo…",
                                        command=lambda: self.accion(ACCION_ARCHIVO))
        self.boton_archivo.grid(row=1, column=1, sticky="ew", pady=(6, 0))
        acciones.columnconfigure((0, 1), weight=1, uniform="acciones")
        self.mostrar_plan()

    # ------------------------------------------------------------------ biblioteca
    def limpiar(self):
        self.raiz = None
        self.juegos = []
        self.plan = None
        self.mostrar_juegos()
        self.mostrar_plan()

    def actualizar(self):
        if not self.app.raiz.get():
            return

        def revisar(raiz):
            raiz = raiz.resolve()
            sistemas = self.app.sistemas.copy()

            def mostrar(juegos):
                if Path(self.app.raiz.get()).resolve() != raiz:
                    return
                self.raiz = raiz
                self.juegos = juegos
                self.mostrar_juegos()
                if self.plan is not None:
                    actual = next((j for j in juegos if j.ruta == self.plan.juego.ruta), None)
                    if actual is None:
                        self.plan = None
                        self.mostrar_plan()

            self.app.ejecutar(lambda: juegos_instalados(raiz, sistemas), mostrar, "Leyendo la biblioteca de RetroBat…")

        self.app.operar(revisar)

    def mostrar_juegos(self):
        texto = self.buscar.get().strip().casefold()
        seleccionado = self.plan.juego.ruta if self.plan else None
        self.lista.delete(*self.lista.get_children())
        self.visibles.clear()
        for juego in self.juegos:
            if texto and texto not in juego.titulo.casefold() and texto not in juego.sistema.nombre.casefold():
                continue
            item = self.lista.insert("", "end", values=(juego.titulo, juego.sistema.nombre))
            self.visibles[item] = juego
            if juego.ruta == seleccionado:
                self.lista.selection_set(item)
                self.lista.see(item)
        if not self.raiz:
            self.resumen.set("Selecciona una instalación de RetroBat en Inicio." if not self.app.raiz.get()
                             else "Pulsa Actualizar lista para leer tu biblioteca.")
        elif not self.juegos:
            self.resumen.set("Tu biblioteca está vacía. Usa «Importar un juego nuevo…».")
        else:
            self.resumen.set(f"{len(self.juegos)} juegos en RetroBat. Elige uno y sigue los pasos en orden.")

    def elegir(self, _=None):
        seleccion = self.lista.selection()
        if not seleccion or seleccion[0] not in self.visibles:
            return
        juego = self.visibles[seleccion[0]]
        if self.plan and self.plan.juego.ruta == juego.ruta:
            return
        self.revisar_juego(juego)

    def revisar_juego(self, juego):
        def revisar(raiz):
            raiz = raiz.resolve()
            sistemas = self.app.sistemas.copy()

            def mostrar(plan):
                if Path(self.app.raiz.get()).resolve() == raiz:
                    self.plan = plan
                    self.mostrar_plan()

            self.app.ejecutar(lambda: preparar_plan(raiz, sistemas, juego), mostrar,
                              f"Revisando {juego.titulo}…")

        self.app.operar(revisar)

    # ------------------------------------------------------------------ pasos
    def mostrar_plan(self):
        plan = self.plan
        self.requisitos.delete(*self.requisitos.get_children())
        for indice, (estado, texto) in enumerate(self.filas_pasos):
            paso = plan.pasos[indice] if plan and indice < len(plan.pasos) else None
            if paso is None:
                estado.configure(text="○ —", fg=COLORES[ESPERA])
                texto.configure(text="Elige un juego." if indice == 0 else "")
            else:
                estado.configure(text=f"{SIMBOLOS[paso.estado]} {paso.estado}", fg=COLORES[paso.estado])
                texto.configure(text=paso.texto)
        if plan:
            for fila in plan.requisitos:
                requisito = fila.requisito
                nombre = requisito.destino.name + (" (opcional)" if requisito.opcional else "")
                lugar = requisito.instalado[0].parent if requisito.instalado else requisito.destino.parent
                if self.raiz and lugar.is_relative_to(self.raiz):
                    lugar = lugar.relative_to(self.raiz)
                self.requisitos.insert("", "end", values=(nombre, fila.estado, str(lugar)))
        siguiente = plan.siguiente if plan else None
        self.boton_siguiente.configure(state="normal" if siguiente else "disabled",
                                       text=f"Siguiente paso: {siguiente.titulo}" if siguiente else "Siguiente paso")
        pendientes = plan.pendientes if plan else []
        self.boton_requisitos.configure(state="normal" if any(f.accion in AUTOMATICAS for f in pendientes)
                                        else "disabled")
        self.boton_archivo.configure(state="normal" if pendientes else "disabled")
        probar = plan.pasos[3] if plan and len(plan.pasos) > 3 else None
        self.boton_probar.configure(state="normal" if probar and probar.estado in (PENDIENTE, HECHO)
                                    else "disabled")

    def siguiente_paso(self):
        if self.plan and self.plan.siguiente:
            self.accion(self.plan.siguiente.accion)

    def accion(self, nombre):
        plan = self.plan
        if plan is None or self.app.ocupado:
            return
        {
            ACCION_IMPORTAR: self.importar_nuevo,
            ACCION_EMULADOR: self.instalar_emulador,
            ACCION_TEKNOPARROT: self.instalar_teknoparrot,
            ACCION_REQUISITOS: self.instalar_requisitos,
            ACCION_ARCHIVO: self.importar_archivo,
            ACCION_PROBAR: self.probar,
        }.get(nombre, lambda: None)()

    def volver_a_revisar(self, *_):
        if self.plan:
            juego = self.plan.juego
            self.plan = None
            self.revisar_juego(juego)

    # ------------------------------------------------------------------ acciones
    def importar_nuevo(self):
        teknoparrot = bool(self.plan and self.plan.juego.sistema.identificador == "teknoparrot")
        destino = self.app.panel_teknoparrot if teknoparrot else self.app.panel_cargar
        nombre = "TeknoParrot" if teknoparrot else "Cargar juegos"
        messagebox.showinfo("Importar un juego",
                            f"Importa el juego desde la pestaña {nombre}. Después vuelve aquí, pulsa "
                            "Actualizar lista y elígelo para seguir con los pasos.", parent=self)
        self.app.pestañas.select(destino)

    def instalar_emulador(self):
        plan = self.plan
        seleccion = plan.seleccion

        def iniciar(raiz):
            raiz = raiz.resolve()
            item = item_emulador(catalogo_emuladores(raiz), seleccion)
            if item is None:
                raise ValueError("El gestor no conoce la ubicación de este emulador. Revísalo en la pestaña Emuladores.")
            if not messagebox.askyesno("Instalar emulador",
                                       f"¿Instalar {item.nombre} desde el repositorio oficial de RetroBat?",
                                       parent=self):
                return

            def terminar(resultado):
                exe, respaldo = resultado
                lineas = [f"{item.nombre}: {exe or 'instalación pendiente'}"]
                if respaldo:
                    lineas.append(f"Copia anterior conservada en {respaldo}")
                self.app.informe("Emulador", lineas)
                self.volver_a_revisar()

            self.app.ejecutar(lambda informar: instalar_emulador(raiz, item, None, informar), terminar,
                              f"Instalando {item.nombre}…", con_progreso=True)

        self.app.operar(iniciar)

    def instalar_teknoparrot(self):
        def iniciar(raiz):
            if not messagebox.askyesno(
                    "Componentes de TeknoParrot",
                    "¿Descargar e instalar los componentes oficiales de TeknoParrot (incluido su RPCS3)?\n\n"
                    "Se conserva una copia de tu configuración. Cierra RetroBat y TeknoParrot antes de continuar.",
                    parent=self):
                return
            self.app.ejecutar(lambda informar: preparar_instalacion(raiz, informar), self.volver_a_revisar,
                              "Instalando los componentes de TeknoParrot…", con_progreso=True)

        self.app.operar(iniciar)

    def aplicar(self, filas, origen=None):
        def iniciar(raiz):
            raiz = raiz.resolve()

            def terminar(resultados):
                self.app.informe("Requisitos del juego", resultados)
                self.volver_a_revisar()

            self.app.ejecutar(lambda informar: aplicar_firmware(raiz, filas, origen, informar), terminar,
                              "Preparando BIOS y firmware…", con_progreso=True)

        self.app.operar(iniciar)

    def instalar_requisitos(self):
        filas = [fila for fila in self.plan.pendientes if fila.accion in AUTOMATICAS]
        if not filas:
            return
        lista = "\n".join(f"• {fila.requisito.destino.name} — {fila.estado}" for fila in filas)
        if messagebox.askyesno("Instalar requisitos",
                               f"Se prepararán estos archivos para {self.plan.juego.titulo}:\n\n{lista}\n\n"
                               "Si ya tienes el paquete guardado se reutiliza. Cierra los emuladores antes de "
                               "continuar.", parent=self):
            self.aplicar(filas)

    def importar_archivo(self):
        filas = [fila for fila in self.plan.pendientes if fila.requisito.tipo not in {"nca", "ryujinx"}]
        if not filas:
            return
        if len(filas) == 1:
            destino = filas[0].requisito.destino
            filtros = [("Requisito", f"*{destino.suffix}")] if destino.suffix else []
            origen = filedialog.askopenfilename(title=f"Selecciona {destino.name}",
                                                filetypes=[*filtros, ("Todos los archivos", "*")], parent=self)
        else:
            origen = filedialog.askdirectory(title="Carpeta con tus copias de BIOS o firmware", parent=self)
        if origen:
            self.aplicar(filas, Path(origen))

    def probar(self):
        plan = self.plan

        def iniciar(raiz):
            comando = comando_prueba(raiz, plan)
            abrir_emulador(comando, cwd=Path(comando[0]).parent)
            messagebox.showinfo("Probar desde RetroBat",
                                f"Se abrió {plan.juego.titulo} con {plan.seleccion.descripcion}, igual que desde el "
                                "menú de RetroBat.\n\nCiérralo como en el arcade para volver.", parent=self)

        self.app.operar(iniciar)
