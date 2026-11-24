"""Panel de estado reutilizable: pasos de un juego (Biblioteca) o de un sistema (Cargar sistemas)."""

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from gestor_emuladores import catalogo_emuladores, instalar_emulador
from gestor_firmware import abrir_emulador, aplicar_firmware
from gestor_preparar import (ACCION_ARCHIVO, ACCION_BIOS, ACCION_EMULADOR, ACCION_IMPORTAR, ACCION_PROBAR,
                             ACCION_REQUISITOS, ACCION_TEKNOPARROT, AVISO, ESPERA, HECHO, PENDIENTE, Plan,
                             comando_prueba, item_emulador, preparar_plan, revisar_sistema)
from gestor_teknoparrot_instalacion import preparar_instalacion

COLORES = {HECHO: "#14704b", PENDIENTE: "#b35c00", AVISO: "#9a3412", ESPERA: "#6b7280"}
SIMBOLOS = {HECHO: "✔", PENDIENTE: "●", AVISO: "⚠", ESPERA: "○"}
AUTOMATICAS = {"Instalar", "Descarga oficial"}
FILAS = 4


class PanelEstado(ttk.Frame):
    """Muestra los pasos de un Plan (juego) o de un EstadoSistema y ejecuta la acción de cada paso.

    compacto=True oculta la tabla de requisitos y la prueba (uso en Cargar sistemas).
    al_revisar(plan) se llama cada vez que se muestra una revisión nueva.
    """

    def __init__(self, padre, app, *, titulo="Estado del juego", compacto=False, al_revisar=None):
        super().__init__(padre)
        self.app = app
        self.compacto = compacto
        self.al_revisar = al_revisar
        self.objetivo = None
        self.plan = None
        self.reintento = None
        self.titulo_base = titulo
        self.titulo = tk.StringVar(value=titulo)
        self.mensaje = tk.StringVar()

        marco = ttk.LabelFrame(self, padding=(10, 6))
        marco.configure(labelwidget=ttk.Label(marco, textvariable=self.titulo, font=("Segoe UI", 10, "bold")))
        marco.pack(fill="both", expand=True)
        pasos = ttk.Frame(marco)
        pasos.pack(fill="x")
        pasos.columnconfigure(1, weight=1)
        self.filas_pasos = []
        for indice in range(FILAS):
            nombre = ttk.Label(pasos, text="", font=("Segoe UI", 10, "bold"))
            estado = tk.Label(pasos, text="", anchor="w")
            texto = ttk.Label(pasos, text="", justify="left")
            if compacto:
                nombre.grid(row=indice, column=0, sticky="nw", pady=1)
                estado.grid(row=indice, column=1, sticky="nw", padx=8, pady=1)
                texto.grid(row=indice, column=2, sticky="nw", pady=1)
            else:
                nombre.grid(row=indice * 2, column=0, sticky="w", pady=(6 if indice else 0, 0))
                estado.grid(row=indice * 2, column=1, sticky="w", padx=8, pady=(6 if indice else 0, 0))
                texto.grid(row=indice * 2 + 1, column=0, columnspan=2, sticky="w", padx=(18, 0))
            self.filas_pasos.append((nombre, estado, texto))
        if compacto:
            pasos.columnconfigure(1, weight=0)
            pasos.columnconfigure(2, weight=1)
        pasos.bind("<Configure>", self.ajustar_texto)

        self.etiqueta_mensaje = tk.Label(marco, textvariable=self.mensaje, anchor="w", justify="left",
                                         font=("Segoe UI", 9, "bold"))
        self.etiqueta_mensaje.pack(fill="x", pady=(6, 0))

        self.requisitos = None
        if not compacto:
            ttk.Label(marco, text="Requisitos de este juego y de este emulador").pack(anchor="w", pady=(8, 2))
            tabla = ttk.Frame(marco)
            tabla.pack(fill="both", expand=True)
            self.requisitos = ttk.Treeview(tabla, columns=("archivo", "estado", "ubicacion"), show="headings",
                                           height=4)
            for columna, titulo_columna, ancho in (("archivo", "Archivo", 150), ("estado", "Estado", 140),
                                                   ("ubicacion", "Se comprueba en", 250)):
                self.requisitos.heading(columna, text=titulo_columna)
                self.requisitos.column(columna, width=ancho, minwidth=80)
            self.requisitos.pack(fill="both", expand=True)

        acciones = ttk.Frame(marco)
        acciones.pack(fill="x", pady=(8, 0))
        self.boton_siguiente = ttk.Button(acciones, text="Siguiente paso", command=self.siguiente_paso)
        self.boton_requisitos = ttk.Button(acciones, text="Instalar requisitos",
                                           command=lambda: self.accion(ACCION_REQUISITOS))
        self.boton_archivo = ttk.Button(acciones, text="Importar archivo…",
                                        command=lambda: self.accion(ACCION_ARCHIVO))
        self.boton_probar = None
        if compacto:
            for columna, boton in enumerate((self.boton_siguiente, self.boton_requisitos, self.boton_archivo)):
                boton.grid(row=0, column=columna, sticky="ew", padx=(0, 6))
            acciones.columnconfigure((0, 1, 2), weight=1, uniform="acciones")
        else:
            self.boton_probar = ttk.Button(acciones, text="Probar desde RetroBat",
                                           command=lambda: self.accion(ACCION_PROBAR))
            self.boton_siguiente.grid(row=0, column=0, sticky="ew", padx=(0, 6))
            self.boton_probar.grid(row=0, column=1, sticky="ew")
            self.boton_requisitos.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(6, 0))
            self.boton_archivo.grid(row=1, column=1, sticky="ew", pady=(6, 0))
            acciones.columnconfigure((0, 1), weight=1, uniform="acciones")
        self.limpiar()

    def ajustar_texto(self, evento):
        ancho = evento.width - (260 if self.compacto else 40)
        for _, _, texto in self.filas_pasos:
            texto.configure(wraplength=max(ancho, 180))

    # ------------------------------------------------------------------ revisiones
    def limpiar(self, texto="Elige un juego para ver sus pasos."):
        if self.reintento is not None:
            self.after_cancel(self.reintento)
            self.reintento = None
        self.objetivo = None
        self.plan = None
        self.titulo.set(self.titulo_base)
        self.mostrar(None, texto)

    def revisar_juego(self, juego):
        self.objetivo = juego
        self.programar()

    def revisar_sistema(self, clave):
        self.objetivo = clave
        self.programar()

    def volver_a_revisar(self, *_):
        if self.objetivo is not None:
            self.programar()

    def programar(self):
        """Revisa el objetivo actual en segundo plano; si el gestor está ocupado, lo intenta después."""
        if self.reintento is not None:
            self.after_cancel(self.reintento)
            self.reintento = None
        if self.app.ocupado:
            self.reintento = self.after(300, self.programar)
            return
        objetivo = self.objetivo
        if objetivo is None or not self.app.raiz.get():
            return
        try:
            raiz = self.app.raiz_retrobat().resolve()
        except ValueError as error:
            self.mostrar(None, str(error))
            return
        sistemas = self.app.sistemas.copy()
        if isinstance(objetivo, str) and objetivo not in sistemas:
            self.mostrar(None, "Elige un sistema.")
            return

        def revisar():
            if isinstance(objetivo, str):
                return revisar_sistema(raiz, sistemas, objetivo)
            return preparar_plan(raiz, sistemas, objetivo)

        def mostrar(plan):
            if self.objetivo is objetivo and self.winfo_exists():
                self.mostrar(plan)

        self.mostrar(None, "Revisando…")
        nombre = objetivo if isinstance(objetivo, str) else objetivo.titulo
        self.app.ejecutar(revisar, mostrar, f"Revisando {nombre}…")

    def mostrar(self, plan, texto=""):
        self.plan = plan
        if self.requisitos is not None:
            self.requisitos.delete(*self.requisitos.get_children())
        pasos = plan.pasos if plan else []
        for indice, (nombre, estado, etiqueta) in enumerate(self.filas_pasos):
            paso = pasos[indice] if indice < len(pasos) else None
            if self.compacto:
                visible = paso is not None or (indice == 0 and not plan)
                for widget in (nombre, estado, etiqueta):
                    widget.grid() if visible else widget.grid_remove()
            if paso is None:
                nombre.configure(text="")
                estado.configure(text="")
                etiqueta.configure(text=texto if indice == 0 and not plan else "")
            else:
                nombre.configure(text=f"{paso.numero}. {paso.titulo}")
                estado.configure(text=f"{SIMBOLOS[paso.estado]} {paso.estado}", fg=COLORES[paso.estado])
                etiqueta.configure(text=paso.texto)
        if plan is None:
            self.mensaje.set("")
        elif isinstance(plan, Plan):
            self.titulo.set(f"Estado del juego · {plan.nombre}")
            self.mensaje.set("")
        else:
            self.titulo.set(f"Preparación del sistema · {plan.nombre}")
            self.mensaje.set(("⛔ " if plan.bloqueado else "✔ ") + plan.mensaje)
            self.etiqueta_mensaje.configure(fg=COLORES[AVISO] if plan.bloqueado else COLORES[HECHO])
        if plan and self.requisitos is not None:
            raiz = Path(self.app.raiz.get()).resolve() if self.app.raiz.get() else None
            for fila in plan.requisitos:
                requisito = fila.requisito
                nombre_archivo = requisito.destino.name + (" (opcional)" if requisito.opcional else "")
                lugar = requisito.instalado[0].parent if requisito.instalado else requisito.destino.parent
                if raiz and lugar.is_relative_to(raiz):
                    lugar = lugar.relative_to(raiz)
                self.requisitos.insert("", "end", values=(nombre_archivo, fila.estado, str(lugar)))
        siguiente = plan.siguiente if plan else None
        self.boton_siguiente.configure(state="normal" if siguiente else "disabled",
                                       text=f"Siguiente paso: {siguiente.titulo}" if siguiente else "Siguiente paso")
        pendientes = plan.pendientes if plan else []
        self.boton_requisitos.configure(state="normal" if any(f.accion in AUTOMATICAS for f in pendientes)
                                        else "disabled")
        self.boton_archivo.configure(state="normal" if any(f.requisito.tipo not in {"nca", "ryujinx"}
                                                           for f in pendientes) else "disabled")
        if self.boton_probar is not None:
            probar = plan.pasos[3] if isinstance(plan, Plan) and len(plan.pasos) > 3 else None
            self.boton_probar.configure(state="normal" if probar and probar.estado in (PENDIENTE, HECHO)
                                        else "disabled")
        if plan is not None and self.al_revisar:
            self.al_revisar(plan)

    # ------------------------------------------------------------------ acciones
    def siguiente_paso(self):
        if self.plan and self.plan.siguiente:
            self.accion(self.plan.siguiente.accion)

    def accion(self, nombre):
        if self.plan is None or self.app.ocupado:
            return
        {
            ACCION_IMPORTAR: self.importar_juego,
            ACCION_EMULADOR: self.instalar_emulador,
            ACCION_TEKNOPARROT: self.instalar_teknoparrot,
            ACCION_REQUISITOS: self.instalar_requisitos,
            ACCION_ARCHIVO: self.importar_archivo,
            ACCION_BIOS: self.revisar_bios,
            ACCION_PROBAR: self.probar,
        }.get(nombre, lambda: None)()

    def importar_juego(self):
        self.app.ir_a_cargar(self.plan.clave)

    def revisar_bios(self):
        clave = self.plan.clave
        self.app.operar(lambda raiz: self.app.preparar_bios(raiz, clave))

    def instalar_emulador(self):
        seleccion = self.plan.seleccion

        def iniciar(raiz):
            raiz = raiz.resolve()
            item = item_emulador(catalogo_emuladores(raiz), seleccion)
            if item is None:
                raise ValueError("El gestor no conoce la ubicación de este emulador. Revísalo en la pestaña Emuladores.")
            if not messagebox.askyesno("Instalar emulador",
                                       f"¿Instalar {item.nombre} desde el repositorio oficial de RetroBat?\n\n"
                                       "Cierra RetroBat y los emuladores antes de continuar.", parent=self):
                return

            def terminar(resultado):
                exe, respaldo = resultado
                lineas = [f"{item.nombre}: {exe or 'instalación pendiente'}"]
                if respaldo:
                    lineas.append(str(respaldo))
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
                self.app.informe("Requisitos", resultados)
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
                               f"Se prepararán estos archivos para {self.plan.nombre}:\n\n{lista}\n\n"
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
        if not isinstance(plan, Plan):
            return

        def iniciar(raiz):
            comando = comando_prueba(raiz, plan)
            abrir_emulador(comando, cwd=Path(comando[0]).parent)
            messagebox.showinfo("Probar desde RetroBat",
                                f"Se abrió {plan.juego.titulo} con {plan.seleccion.descripcion}, igual que desde el "
                                "menú de RetroBat.\n\nCiérralo como en el arcade para volver.", parent=self)

        self.app.operar(iniciar)
