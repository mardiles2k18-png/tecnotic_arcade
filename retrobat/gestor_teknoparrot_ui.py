"""TeknoParrot: lote de importación (en Cargar sistemas) y sección de instalación (en Emuladores)."""
from collections import Counter
from pathlib import Path
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from xml.etree.ElementTree import ParseError

import gestor_teknoparrot as tp
from gestor_core import tamanio_copia
from gestor_teknoparrot_editor_ui import EditorMandos
from gestor_teknoparrot_diagnostico import (COMPATIBILIDAD, GENERADOR_WEB, ficha_url, lineas_diagnostico,
                                          revisar_en_linea)
from gestor_teknoparrot_instalacion import faltantes, preparar_instalacion

TEXTO_INSTALAR = ("Instala TeknoParrot en la pestaña Emuladores (sección TeknoParrot) para habilitar la carga "
                  "de juegos.")
from gestor_teknoparrot_pantalla import configurar_pantalla, pantalla_oculta


AYUDA_LOTE = ("1. Agrega la carpeta donde tienes tus juegos de TeknoParrot (o tus ZIP, 7z o RAR).  "
              "2. El Gestor reconoce cada juego y busca su ejecutable.  "
              "3. Importa los que digan «Listo». Para los demás, haz doble clic en la fila y el Gestor te "
              "pedirá solo lo que falta.")


class Ayuda:
    """Texto de ayuda que aparece al dejar el ratón sobre un botón."""

    def __init__(self, widget, texto):
        self.widget, self.texto, self.ventana, self.espera = widget, texto, None, None
        widget.bind("<Enter>", self.programar, add="+")
        widget.bind("<Leave>", self.ocultar, add="+")
        widget.bind("<ButtonPress>", self.ocultar, add="+")

    def programar(self, _=None):
        self.ocultar()
        self.espera = self.widget.after(450, self.mostrar)

    def mostrar(self):
        self.espera = None
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.ventana = tk.Toplevel(self.widget)
        self.ventana.wm_overrideredirect(True)
        self.ventana.wm_geometry(f"+{x}+{y}")
        tk.Label(self.ventana, text=self.texto, justify="left", wraplength=360, background="#fffbe6",
                 foreground="#1f2933", relief="solid", borderwidth=1, padx=8, pady=6).pack()

    def ocultar(self, _=None):
        if self.espera:
            self.widget.after_cancel(self.espera)
            self.espera = None
        if self.ventana:
            self.ventana.destroy()
            self.ventana = None


def centrar(ventana, padre):
    ventana.update_idletasks()
    x = padre.winfo_rootx() + max(0, (padre.winfo_width() - ventana.winfo_width()) // 2)
    y = padre.winfo_rooty() + max(0, (padre.winfo_height() - ventana.winfo_height()) // 3)
    ventana.geometry(f"+{x}+{y}")


def boton(padre, texto, comando, ayuda):
    nuevo = ttk.Button(padre, text=texto, command=comando)
    Ayuda(nuevo, ayuda)
    return nuevo


class PanelTeknoParrot(ttk.Frame):
    def __init__(self, padre, app):
        super().__init__(padre)
        self.app = app
        self.juegos = {}
        self.perfiles = {}
        self.presentes = Counter()
        self.raiz = None

        # La instalación, la pantalla de carga y los mandos se movieron a Emuladores y Mandos (Vista previa 29).
        self.estado = tk.StringVar(value="Selecciona la instalación de RetroBat en Inicio.")
        ttk.Label(self, textvariable=self.estado, wraplength=900).pack(anchor="w", pady=(0, 4))
        ttk.Label(self, text=AYUDA_LOTE, wraplength=1100, foreground="#52606d").pack(anchor="w", pady=(0, 6))

        acciones = ttk.Frame(self)
        acciones.pack(fill="x", pady=(0, 8))
        carpeta = boton(acciones, "Agregar carpeta de juegos…", self.elegir_carpeta,
                        "Elige la carpeta donde están tus juegos. Si tiene una subcarpeta por juego, se agregan "
                        "todos; si es la carpeta de un solo juego, se agrega ese juego.")
        carpeta.pack(side="left", padx=(0, 6))
        comprimidos = boton(acciones, "Agregar juegos comprimidos…", self.elegir_comprimidos,
                            "Elige uno o varios juegos en ZIP, 7z o RAR. Se descomprimen al importarlos.")
        comprimidos.pack(side="left")
        importar = boton(acciones, "Importar a RetroBat", self.importar,
                         "Copia a RetroBat los juegos que digan «Listo». Si seleccionas filas, importa solo "
                         "esas; si no seleccionas ninguna, importa todos los listos.")
        importar.pack(side="right")
        self.botones_juegos = (carpeta, comprimidos, importar)
        for elemento in self.botones_juegos:
            elemento.state(["disabled"])

        lista = ttk.Frame(self)
        lista.pack(fill="both", expand=True)
        self.tabla = ttk.Treeview(lista, show="headings", columns=("origen", "perfil", "ejecutable", "estado"))
        for id_, titulo, ancho in (("origen", "Juego en tu disco", 225), ("perfil", "Juego de TeknoParrot", 240),
                                   ("ejecutable", "Ejecutable", 175), ("estado", "Estado", 200)):
            self.tabla.heading(id_, text=titulo)
            self.tabla.column(id_, width=ancho, minwidth=90)
        self.tabla.tag_configure("listo", foreground="#1b7f3b")
        self.tabla.tag_configure("revisar", foreground="#9a5b00")
        self.tabla.tag_configure("falta", foreground="#b42318")
        self.tabla.tag_configure("instalado", foreground="#7b8794")
        barra = ttk.Scrollbar(lista, command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.tabla.pack(fill="both", expand=True)
        self.tabla.bind("<<TreeviewSelect>>", self.mostrar_seleccion)
        self.tabla.bind("<Double-1>", self.resolver)
        self.tabla.bind("<Return>", self.resolver)
        self.tabla.bind("<Delete>", lambda _: self.quitar_seleccion())

        detalle = ttk.LabelFrame(self, text="Juego seleccionado", padding=8)
        detalle.pack(fill="x", pady=(8, 0))
        self.detalle = tk.StringVar(value="Selecciona un juego de la lista para ver qué le falta.")
        ttk.Label(detalle, textvariable=self.detalle, wraplength=1100, justify="left").pack(anchor="w")
        botones = ttk.Frame(detalle)
        botones.pack(fill="x", pady=(6, 0))
        self.boton_perfil = boton(botones, "Elegir juego de TeknoParrot…", self.elegir_perfil,
                                  "Indica a qué juego de TeknoParrot corresponde esta carpeta. La lista muestra "
                                  "primero los nombres más parecidos y puedes escribir para buscar.")
        self.boton_ejecutable = boton(botones, "Elegir ejecutable…", self.elegir_ejecutable,
                                      "El ejecutable es el archivo .exe que abre el juego. El Gestor lo busca "
                                      "solo; usa este botón si no lo encontró o si eligió otro.")
        self.boton_segundo = boton(botones, "Elegir segundo ejecutable…", lambda: self.elegir_ejecutable(True),
                                   "Algunos juegos de TeknoParrot necesitan dos archivos para arrancar. Este "
                                   "botón solo se activa en esos juegos.")
        self.boton_guia = boton(botones, "Ver guía del juego…", self.diagnosticar,
                                "Muestra lo que pide la ficha oficial de TeknoParrot para este juego y lo que "
                                "el Gestor encontró en tu carpeta. Útil cuando un juego no queda listo.")
        self.boton_quitar = boton(botones, "Quitar de la lista", self.quitar_seleccion,
                                  "Saca el juego de esta lista. No borra nada de tu disco.")
        for elemento in (self.boton_perfil, self.boton_ejecutable, self.boton_segundo, self.boton_guia):
            elemento.pack(side="left", padx=(0, 6))
        self.boton_quitar.pack(side="right")
        self.mostrar_seleccion()

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
            try:
                instalado = not faltantes(emulador)
            except PermissionError as error:
                return error
            mapeo = any((raiz / carpeta / "teknoparrot.yml").is_file()
                        for carpeta in ("system/resources/inputmapping", "user/inputmapping"))
            archivo_ejecutables = raiz / "system" / "tools" / "teknoparrotInfo.yml"
            perfiles = tp.perfiles_locales(emulador, archivo_ejecutables) if instalado else []
            return instalado, mapeo, perfiles, tp.instalados(sistema)

        def mostrar(resultado):
            if Path(self.app.raiz.get()).resolve() != raiz:
                return
            if isinstance(resultado, PermissionError):
                for elemento in self.botones_juegos:
                    elemento.state(["disabled"])
                self.estado.set(f"Acceso denegado: {resultado.filename or resultado}")
                return
            instalado, mapeo, perfiles, self.presentes = resultado
            self.perfiles = {f"{p.titulo} [{p.id}]": p for p in perfiles}
            por_id = {p.id: p for p in perfiles}
            for juego in self.juegos.values():
                if juego.perfil:
                    nuevo = por_id.get(juego.perfil.id)
                    if nuevo != juego.perfil:
                        tp.seleccionar_perfil(juego, nuevo)
            listo = instalado and bool(perfiles)
            for elemento in self.botones_juegos:
                elemento.state(["!disabled"] if listo else ["disabled"])
            if listo:
                estado = f"Listo para cargar juegos · {len(perfiles)} perfiles · {sum(self.presentes.values())} juegos registrados."
            else:
                estado = TEXTO_INSTALAR
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
        for elemento in self.botones_juegos:
            elemento.state(["disabled"])
        self.mostrar_seleccion()

    def mandos_automaticos(self):
        def abrir(raiz):
            raiz = raiz.resolve()
            if not (tp.carpeta_emulador(raiz) / "TeknoParrotUi.exe").is_file():
                raise ValueError("Instala TeknoParrot antes de configurar los mandos.")
            ventana = getattr(self, "ventana_mandos", None)
            if ventana and ventana.winfo_exists():
                ventana.lift()
                ventana.focus_set()
            else:
                self.ventana_mandos = EditorMandos(self, raiz)

        self.app.operar(abrir)

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
                self.refrescar_seccion()
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
            def terminar(pendientes):
                self.refrescar_seccion()
                self.actualizar(pendientes)
                if hasattr(self.app, "revisar_preparacion"):
                    self.app.revisar_preparacion()

            self.app.ejecutar(lambda informar: preparar_instalacion(raiz, informar), terminar,
                              "Instalando y configurando TeknoParrot…", con_progreso=True)
        self.app.operar(iniciar)

    def refrescar_seccion(self):
        seccion = getattr(self.app, "seccion_teknoparrot", None)
        if seccion is not None:
            seccion.actualizar()

    def elegir_carpeta(self):
        def elegir(raiz):
            if raiz.resolve() != self.raiz or not self.perfiles:
                raise ValueError(TEXTO_INSTALAR)
            elegida = filedialog.askdirectory(title="Carpeta con tus juegos de TeknoParrot", parent=self)
            if not elegida:
                return
            carpeta = Path(elegida)
            perfiles = tuple(self.perfiles.values())

            def buscar():
                if not tp.es_coleccion(carpeta, perfiles):
                    return [carpeta]
                return sorted(ruta for ruta in carpeta.iterdir()
                              if not ruta.name.startswith(".") and
                              (ruta.is_dir() or ruta.suffix.lower() in tp.COMPRIMIDOS))

            self.revisar_origenes(buscar)
        self.app.operar(elegir)

    def elegir_comprimidos(self):
        def elegir(raiz):
            if raiz.resolve() != self.raiz or not self.perfiles:
                raise ValueError(TEXTO_INSTALAR)
            elegidas = filedialog.askopenfilenames(
                title="Selecciona juegos comprimidos",
                filetypes=[("Juegos comprimidos", "*.zip *.7z *.rar")], parent=self)
            if elegidas:
                self.revisar_origenes(lambda: [Path(ruta) for ruta in elegidas])
        self.app.operar(elegir)

    def revisar_origenes(self, buscar):
        perfiles = tuple(self.perfiles.values())
        presentes = self.presentes.copy()

        def revisar(informar):
            informar(0, None, "Buscando juegos en la carpeta…")
            carpetas = buscar()
            if not carpetas:
                raise ValueError("No hay carpetas de juegos ni archivos ZIP, 7z o RAR en esta ubicación.")
            informar(0, None, f"Reconociendo {len(carpetas)} juegos…")
            juegos = tp.revisar_carpetas(carpetas, perfiles)
            informar(0, None, "Consultando archivos de arranque en línea…")
            revisar_en_linea([juego for juego in juegos
                              if juego.perfil and not presentes[juego.perfil.id.casefold()]])
            for juego in juegos:
                tp.deducir_ejecutable(juego)
            return juegos

        self.app.ejecutar(revisar, self.agregar_juegos, "Buscando juegos y ejecutables…", con_progreso=True)

    def agregar_juegos(self, juegos):
        origenes = {juego.origen for juego in self.juegos.values()}
        nuevos = 0
        for juego in juegos:
            if juego.origen not in origenes:
                self.juegos[self.tabla.insert("", "end")] = juego
                origenes.add(juego.origen)
                nuevos += 1
        self.refrescar_lote()
        problemas = self.problemas_lote()
        listos = sum(not problema for problema in problemas.values())
        self.app.estado.set(f"{nuevos} juegos agregados · {listos} listos para importar · "
                            f"{len(problemas) - listos} necesitan revisión.")

    def problemas_lote(self):
        repetidos = Counter(juego.perfil.id.casefold() for juego in self.juegos.values() if juego.perfil)
        return {fila: tp.problema_juego(juego, self.presentes, repetidos) for fila, juego in self.juegos.items()}

    def estado_fila(self, juego, problema):
        if problema:
            return problema, ("instalado" if problema == "Ya está en RetroBat" else "falta")
        texto = "Listo · requiere licencia" if juego.perfil.suscripcion else "Listo para importar"
        if juego.perfil_por_nombre or juego.deducidos:
            return texto + " (revisa)", "revisar"
        return texto, "listo"

    def refrescar_lote(self):
        problemas = self.problemas_lote()
        for fila, juego in self.juegos.items():
            arranque = " · ".join(ruta.name for ruta in (juego.ejecutable, juego.secundario) if ruta is not None)
            estado, etiqueta = self.estado_fila(juego, problemas[fila])
            self.tabla.item(fila, values=(juego.origen.name, juego.perfil.titulo if juego.perfil else "",
                                          arranque, estado), tags=(etiqueta,))
        self.mostrar_seleccion()

    def seleccionado(self):
        seleccion = self.tabla.selection()
        return self.juegos.get(seleccion[0]) if len(seleccion) == 1 else None

    def ruta_visible(self, juego, ruta):
        return (ruta if juego.contenido is not None else ruta.relative_to(juego.origen)).as_posix()

    def texto_detalle(self, juego, problema):
        nombre = juego.origen.name
        if juego.error:
            return f"No se pudo leer «{nombre}»: {juego.error}"
        if juego.perfil is None:
            return (f"El Gestor no reconoció «{nombre}». Pulsa «Elegir juego de TeknoParrot…» (o haz doble clic "
                    "en la fila): verás primero los nombres más parecidos.")
        lineas = [f"«{nombre}» es {juego.perfil.titulo} [{juego.perfil.id}]"
                  + (" · reconocido por el nombre, comprueba que sea el correcto." if juego.perfil_por_nombre else ".")]
        if problema == "Ya está en RetroBat":
            lineas.append("Este juego ya está en RetroBat. No hace falta importarlo otra vez.")
            return "\n".join(lineas)
        if juego.ejecutable is not None:
            lineas.append(f"Ejecutable: {self.ruta_visible(juego, juego.ejecutable)}"
                          + (" · elegido por el Gestor, comprueba que sea el que abre el juego."
                             if "ejecutable" in juego.deducidos else ""))
        if juego.perfil.secundario and juego.secundario is not None:
            lineas.append(f"Segundo ejecutable: {self.ruta_visible(juego, juego.secundario)}")
        pasos = {
            "Falta elegir el ejecutable": "TeknoParrot no indica qué archivo abre este juego. Pulsa «Elegir "
                                          "ejecutable…»: la lista muestra primero los más probables.",
            "Hay varios ejecutables · elige uno": "Hay más de un archivo con el nombre que pide TeknoParrot. Pulsa "
                                                  "«Elegir ejecutable…» y elige el de esta versión.",
            "No se encontró el ejecutable": "La carpeta no tiene el archivo que pide TeknoParrot "
                                            f"({', '.join(sorted(juego.perfil.esperado - {''})) or 'sin nombre'}). "
                                            "Puede que la versión no sea la correcta. Pulsa «Ver guía del juego…».",
            "Falta el segundo ejecutable": "Este juego necesita dos archivos para arrancar. Pulsa «Elegir segundo "
                                           "ejecutable…».",
            "Hay varios segundos ejecutables · elige uno": "Pulsa «Elegir segundo ejecutable…» y elige el de esta "
                                                           "versión.",
            "Los dos ejecutables no pueden ser el mismo": "Elige un segundo ejecutable distinto del principal.",
            "Repetido en la lista": "Hay otra fila con el mismo juego de TeknoParrot. Quita la que sobre o "
                                    "elige otro juego.",
        }
        if problema:
            lineas.append(pasos.get(problema, problema))
        else:
            lineas.append("Listo: pulsa «Importar a RetroBat».")
        return "\n".join(lineas)

    def mostrar_seleccion(self, _=None):
        filas = [fila for fila in self.tabla.selection() if fila in self.juegos]
        juego = self.juegos[filas[0]] if len(filas) == 1 else None
        if juego:
            self.detalle.set(self.texto_detalle(juego, self.problemas_lote()[filas[0]]))
        elif filas:
            self.detalle.set(f"{len(filas)} juegos seleccionados. «Importar a RetroBat» copiará los que estén listos.")
        elif self.juegos:
            self.detalle.set("Selecciona un juego de la lista para ver qué le falta. Doble clic para resolverlo.")
        else:
            self.detalle.set("Todavía no hay juegos en la lista. Pulsa «Agregar carpeta de juegos…».")
        uno = juego is not None and not juego.error
        self.boton_perfil.state(["!disabled"] if uno else ["disabled"])
        self.boton_ejecutable.state(["!disabled"] if uno and juego.perfil else ["disabled"])
        self.boton_segundo.state(["!disabled"] if uno and juego.perfil and juego.perfil.secundario else ["disabled"])
        self.boton_guia.state(["!disabled"] if filas else ["disabled"])
        self.boton_quitar.state(["!disabled"] if filas else ["disabled"])

    def resolver(self, _=None):
        """Doble clic: abre lo que la fila necesita."""
        juego = self.seleccionado()
        if juego is None or self.app.ocupado:
            return
        fila = self.tabla.selection()[0]
        problema = self.problemas_lote()[fila]
        if juego.error:
            messagebox.showerror(juego.origen.name, juego.error, parent=self)
        elif juego.perfil is None or problema == "Repetido en la lista":
            self.elegir_perfil()
        elif problema in {"Falta elegir el ejecutable", "Hay varios ejecutables · elige uno"}:
            self.elegir_ejecutable()
        elif "segundo" in problema or problema == "Los dos ejecutables no pueden ser el mismo":
            self.elegir_ejecutable(True)
        else:
            self.diagnosticar()

    def elegir_perfil(self):
        juego = self.seleccionado()
        if juego is None or self.app.ocupado or juego.error:
            return
        SelectorPerfil(self, juego, tuple(self.perfiles.values()), self.presentes, self.aplicar_perfil)

    def aplicar_perfil(self, juego, perfil):
        def revisar():
            tp.releer_origen(juego)
            tp.seleccionar_perfil(juego, perfil)
            juego.perfil_por_nombre = False
            revisar_en_linea([juego])
            tp.deducir_ejecutable(juego)

        self.app.ejecutar(revisar, lambda _: self.refrescar_lote(), "Buscando el ejecutable del juego…")

    def diagnosticar(self, _=None):
        if self.app.ocupado:
            return
        juegos = {fila: self.juegos[fila] for fila in self.tabla.selection() if fila in self.juegos}
        if not juegos:
            messagebox.showinfo("TeknoParrot", "Selecciona un juego para ver su guía.", parent=self)
            return

        def revisar():
            for juego in juegos.values():
                tp.releer_origen(juego)
            guias, consulta_generador = revisar_en_linea(juegos.values(), diagnosticar=True)
            problemas = self.problemas_lote()
            lineas = []
            for fila, juego in juegos.items():
                guia = guias.get(juego.perfil.id) if juego.perfil else None
                if lineas:
                    lineas.append("\n" + "─" * 32 + "\n")
                lineas.extend(lineas_diagnostico(juego, problemas[fila], guia, consulta_generador))
            return lineas

        def mostrar(lineas):
            self.refrescar_lote()
            juego = next(iter(juegos.values()))
            enlace = ficha_url(juego.perfil.id) if len(juegos) == 1 and juego.perfil else COMPATIBILIDAD
            self.app.informe("Guía del juego en TeknoParrot", lineas,
                             (("Ficha oficial de TeknoParrot", enlace), ("Catálogo de RetroBat", GENERADOR_WEB)))

        self.app.ejecutar(revisar, mostrar, "Consultando la guía oficial de TeknoParrot…")

    def elegir_ejecutable(self, segundo=False):
        juego = self.seleccionado()
        if self.app.ocupado or not juego:
            return
        if juego.error:
            messagebox.showerror(juego.origen.name, juego.error, parent=self)
            return
        if not juego.perfil:
            self.elegir_perfil()
            return
        if segundo and not juego.perfil.secundario:
            messagebox.showinfo("TeknoParrot", "Este juego usa un solo ejecutable.", parent=self)
            return

        def buscar():
            esperados = (juego.perfil.secundario if segundo else juego.perfil.esperado) - {""}
            archivos = tp.archivos_juego(juego)
            coinciden = [ruta for ruta in archivos if ruta.name.casefold() in esperados]
            probables = tp.orden_ejecutables(juego, [ruta for ruta in tp.probables_ejecutables(juego)
                                                     if ruta not in coinciden])
            return esperados, tp.orden_ejecutables(juego, coinciden) + probables, archivos

        self.app.ejecutar(buscar, lambda datos: SelectorEjecutable(self, juego, segundo, *datos),
                          "Buscando ejecutables en el juego…")

    def usar_ejecutable(self, juego, ruta, segundo):
        tp.elegir_archivo(juego, ruta, segundo)
        self.refrescar_lote()

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
            problemas = self.problemas_lote()
            seleccion = [fila for fila in self.tabla.selection() if fila in self.juegos]
            if not seleccion:
                seleccion = [fila for fila, problema in problemas.items() if not problema]
                if not seleccion:
                    messagebox.showinfo("TeknoParrot", "Todavía no hay juegos listos. Haz doble clic en una fila "
                                        "para ver qué le falta.", parent=self)
                    return
            filas = [fila for fila in seleccion if not problemas[fila]]
            pendientes = [f"{self.juegos[fila].origen.name} — {problemas[fila]}"
                          for fila in seleccion if problemas[fila]]
            detalle = "\n".join(pendientes[:5])
            if len(pendientes) > 5:
                detalle += f"\nY {len(pendientes) - 5} juegos más."
            if not filas:
                self.diagnosticar()
                return
            aviso = f"\n\nJuegos que quedarán pendientes:\n{detalle}" if pendientes else ""
            copias = "un juego y preparar su perfil" if len(filas) == 1 else f"{len(filas)} juegos y preparar sus perfiles"
            if not messagebox.askyesno("TeknoParrot",
                f"¿Copiar {copias}? Cierra RetroBat y TeknoParrot antes de continuar.{aviso}", parent=self):
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
                if completados and hasattr(self.app, "panel_biblioteca"):
                    self.app.panel_biblioteca.raiz = None
                self.app.estado.set(f"{len(completados)} juegos importados · {len(errores)} errores. "
                                    "Actualiza la lista de juegos en RetroBat.")
                if errores:
                    self.app.informe("Importación de TeknoParrot", errores)

            self.app.ejecutar(copiar, terminar, "Importando juegos de TeknoParrot…", con_progreso=True)
        self.app.operar(aplicar)


class SelectorPerfil(tk.Toplevel):
    """Lista de juegos de TeknoParrot con buscador; primero los más parecidos al nombre de la carpeta."""

    def __init__(self, panel, juego, perfiles, presentes, al_elegir):
        super().__init__(panel)
        self.juego, self.perfiles, self.presentes, self.al_elegir = juego, perfiles, presentes, al_elegir
        self.visibles, self.espera = [], None
        self.title(f"¿Qué juego es «{juego.origen.name}»?")
        self.transient(panel.winfo_toplevel())
        self.geometry("720x480")
        cuerpo = ttk.Frame(self, padding=10)
        cuerpo.pack(fill="both", expand=True)
        ttk.Label(cuerpo, wraplength=680, justify="left",
                  text="Elige el juego de TeknoParrot que corresponde a esta carpeta. Arriba aparecen los más "
                       "parecidos a su nombre. Si no está, escribe parte del nombre para buscarlo.").pack(anchor="w")
        self.busqueda = tk.StringVar(self, value=re.split(r"\s*[\[(]", tp.nombre_juego(juego.origen), maxsplit=1)[0])
        entrada = ttk.Entry(cuerpo, textvariable=self.busqueda)
        entrada.pack(fill="x", pady=(8, 6))
        lista = ttk.Frame(cuerpo)
        lista.pack(fill="both", expand=True)
        self.lista = tk.Listbox(lista, exportselection=False, activestyle="dotbox")
        barra = ttk.Scrollbar(lista, command=self.lista.yview)
        self.lista.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.lista.pack(fill="both", expand=True)
        self.aviso = tk.StringVar(self)
        ttk.Label(cuerpo, textvariable=self.aviso, foreground="#52606d").pack(anchor="w", pady=(6, 0))
        pie = ttk.Frame(cuerpo)
        pie.pack(fill="x", pady=(8, 0))
        ttk.Button(pie, text="Cancelar", command=self.destroy).pack(side="right")
        ttk.Button(pie, text="Usar este juego", command=self.confirmar).pack(side="right", padx=6)
        self.busqueda.trace_add("write", lambda *_: self.programar())
        entrada.bind("<Down>", lambda _: self.lista.focus_set())
        entrada.bind("<Return>", self.confirmar)
        self.lista.bind("<Double-1>", self.confirmar)
        self.lista.bind("<Return>", self.confirmar)
        self.bind("<Escape>", lambda _: self.destroy())
        self.filtrar()
        centrar(self, panel.winfo_toplevel())
        self.grab_set()
        entrada.focus_set()
        entrada.select_range(0, "end")

    def programar(self):
        if self.espera:
            self.after_cancel(self.espera)
        self.espera = self.after(180, self.filtrar)

    def filtrar(self):
        self.espera = None
        texto = self.busqueda.get().strip()
        if texto:
            parecidos = tp.perfiles_parecidos(texto, self.perfiles)
            self.visibles = [perfil for puntaje, perfil in parecidos if puntaje >= 0.35][:150]
        else:
            self.visibles = sorted(self.perfiles, key=lambda perfil: perfil.titulo.casefold())
        self.lista.delete(0, "end")
        for perfil in self.visibles:
            marca = "   · ya está en RetroBat" if self.presentes[perfil.id.casefold()] else ""
            self.lista.insert("end", f"{perfil.titulo}   [{perfil.id}]{marca}")
        if self.visibles:
            self.lista.selection_set(0)
            self.lista.see(0)
        self.aviso.set(f"{len(self.visibles)} juegos" if self.visibles
                       else "Sin resultados. Prueba con otra palabra; con el cuadro vacío verás todos.")

    def confirmar(self, _=None):
        seleccion = self.lista.curselection()
        if not seleccion:
            return
        perfil = self.visibles[seleccion[0]]
        self.destroy()
        self.al_elegir(self.juego, perfil)


class SelectorEjecutable(tk.Toplevel):
    """Lista de ejecutables del juego, los más probables primero."""

    def __init__(self, panel, juego, segundo, esperados, candidatos, archivos):
        super().__init__(panel)
        self.panel, self.juego, self.segundo = panel, juego, segundo
        self.candidatos, self.archivos, self.visibles = candidatos, archivos, []
        que = "segundo ejecutable" if segundo else "ejecutable"
        self.title(f"Elegir {que} · {juego.perfil.titulo}")
        self.transient(panel.winfo_toplevel())
        self.geometry("720x440")
        cuerpo = ttk.Frame(self, padding=10)
        cuerpo.pack(fill="both", expand=True)
        if esperados:
            texto = (f"TeknoParrot espera un archivo llamado {' o '.join(sorted(esperados))}. Los que coinciden "
                     "aparecen arriba.")
        else:
            texto = ("TeknoParrot no indica qué archivo abre este juego. Arriba están los más probables: "
                     "suelen llevar el nombre del juego o terminar en «-Shipping.exe». Se ocultan instaladores "
                     "y herramientas.")
        ttk.Label(cuerpo, text=texto, wraplength=680, justify="left").pack(anchor="w")
        self.todos = tk.BooleanVar(self, value=not candidatos)
        ttk.Checkbutton(cuerpo, text="Mostrar todos los archivos del juego", variable=self.todos,
                        command=self.cargar).pack(anchor="w", pady=(6, 4))
        lista = ttk.Frame(cuerpo)
        lista.pack(fill="both", expand=True)
        self.lista = tk.Listbox(lista, exportselection=False)
        barra = ttk.Scrollbar(lista, command=self.lista.yview)
        self.lista.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.lista.pack(fill="both", expand=True)
        pie = ttk.Frame(cuerpo)
        pie.pack(fill="x", pady=(8, 0))
        ttk.Button(pie, text="Cancelar", command=self.destroy).pack(side="right")
        ttk.Button(pie, text="Usar este archivo", command=self.confirmar).pack(side="right", padx=6)
        if juego.contenido is None:
            ttk.Button(pie, text="Buscar en la carpeta…", command=self.examinar).pack(side="left")
        self.lista.bind("<Double-1>", self.confirmar)
        self.lista.bind("<Return>", self.confirmar)
        self.bind("<Escape>", lambda _: self.destroy())
        self.cargar()
        centrar(self, panel.winfo_toplevel())
        self.grab_set()
        self.lista.focus_set()

    def cargar(self):
        self.visibles = (sorted(self.archivos, key=lambda ruta: self.panel.ruta_visible(self.juego, ruta).casefold())
                         if self.todos.get() else self.candidatos)
        actual = self.juego.secundario if self.segundo else self.juego.ejecutable
        self.lista.delete(0, "end")
        for ruta in self.visibles:
            marca = "   · elegido ahora" if ruta == actual else ""
            self.lista.insert("end", self.panel.ruta_visible(self.juego, ruta) + marca)
        if self.visibles:
            indice = self.visibles.index(actual) if actual in self.visibles else 0
            self.lista.selection_set(indice)
            self.lista.see(indice)

    def confirmar(self, _=None):
        seleccion = self.lista.curselection()
        if seleccion:
            ruta = self.visibles[seleccion[0]]
            self.destroy()
            self.panel.usar_ejecutable(self.juego, ruta, self.segundo)

    def examinar(self):
        nombre = filedialog.askopenfilename(title="Ejecutable del juego", initialdir=self.juego.origen, parent=self)
        if not nombre:
            return
        ruta = Path(nombre).resolve()
        if not ruta.is_relative_to(self.juego.origen) or not ruta.is_file():
            messagebox.showerror("TeknoParrot", "Elige un archivo dentro de la carpeta del juego.", parent=self)
            return
        self.destroy()
        self.panel.usar_ejecutable(self.juego, ruta, self.segundo)


class SeccionTeknoParrot(ttk.LabelFrame):
    """Instalación de TeknoParrot y pantalla de carga, dentro de la pestaña Emuladores."""

    def __init__(self, padre, app):
        super().__init__(padre, text="TeknoParrot", padding=8)
        self.app = app
        self.estado = tk.StringVar(value="Selecciona la instalación de RetroBat en Inicio.")
        ttk.Label(self, textvariable=self.estado, wraplength=900, justify="left").pack(anchor="w", pady=(0, 6))
        acciones = ttk.Frame(self)
        acciones.pack(fill="x")
        ttk.Button(acciones, text="Instalar y configurar TeknoParrot",
                   command=lambda: app.panel_teknoparrot.instalar()).pack(side="left")
        ttk.Button(acciones, text="Pantalla de carga…",
                   command=lambda: app.panel_teknoparrot.configurar_pantalla()).pack(side="left", padx=8)

    def actualizar(self):
        try:
            raiz = self.app.raiz_retrobat().resolve()
            emulador = tp.carpeta_emulador(raiz)
            faltan = faltantes(emulador)
            rpcs3 = (emulador / "RPCS3" / "rpcs3.exe").is_file()
            oculta = pantalla_oculta(raiz)
        except (OSError, ValueError, ParseError) as error:
            self.estado.set(str(error))
            return
        if faltan:
            estado = f"Faltan componentes de TeknoParrot ({len(faltan)}). Pulsa Instalar y configurar TeknoParrot."
        else:
            estado = "TeknoParrot instalado" + (" · incluye su RPCS3 (Namco 357/369)." if rpcs3
                                                else " · falta su RPCS3: reinstala los componentes.")
        pantalla = ("EmulationStation se oculta al iniciar un juego." if oculta
                    else "EmulationStation se muestra durante la carga de los juegos.")
        self.estado.set(f"{estado}\nPantalla de carga: {pantalla} Carpeta: {emulador}")
