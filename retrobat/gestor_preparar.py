"""Asistente «Preparar un juego»: emulador exacto, requisitos y prueba desde RetroBat.

El orden es el que sigue RetroBat al abrir un juego:
1. Juego: entrada de la biblioteca (y, en TeknoParrot, su perfil de usuario).
2. Emulador: el que RetroBat usará según los ajustes del juego, del sistema o el predeterminado.
3. BIOS y firmware: solo los requisitos de ese juego y de esa copia del emulador.
4. Probar: abrirlo con emulatorLauncher, igual que desde el menú del arcade.
"""

from dataclasses import dataclass, field
import os
from pathlib import Path
from xml.etree import ElementTree as ET

from gestor_biblioteca import catalogo_juegos
from gestor_core import CARPETAS_MULTIMEDIA, archivo_sistemas_retrobat
from gestor_emuladores import LY, catalogo_emuladores, familia_emuladores, instalacion, retroarch_base
from gestor_firmware import FALTA, GUARDADO, LISTO, Revision, estado_firmware, requisitos_firmware, ruta_local
from gestor_teknoparrot import FORMATOS, carpeta_emulador
from gestor_teknoparrot_pantalla import leer_ajustes

# Estados de cada paso
HECHO = "Listo"
PENDIENTE = "Pendiente"
ESPERA = "Espera el paso anterior"
AVISO = "Revisar"

# Acciones que el asistente sabe ejecutar
ACCION_IMPORTAR = "importar"
ACCION_EMULADOR = "emulador"
ACCION_TEKNOPARROT = "teknoparrot"
ACCION_REQUISITOS = "requisitos"
ACCION_ARCHIVO = "archivo"
ACCION_PROBAR = "probar"

TEKNOPARROT_RPCS3 = "TeknoParrot · Namco 357/369"
NOMBRES_SWITCH = {"ryujinx": "Ryujinx", "eden": "Eden", "yuzu": "Yuzu", "suyu": "Suyu",
                  "sudachi": "Sudachi", "citron": "Citron"}
# Requisitos que se consideran resueltos o que no bloquean el juego
RESUELTOS = {LISTO, "Verificado", "Presente · sin huella", "Alternativa cubierta",
             "Detectado · validar en emulador"}


@dataclass(frozen=True)
class JuegoRetroBat:
    clave: str          # clave del sistema en el diccionario de sistemas del gestor
    sistema: object     # gestor_core.Sistema
    ruta: Path
    titulo: str


@dataclass(frozen=True)
class Seleccion:
    emulador: str
    nucleo: str
    origen: str

    @property
    def descripcion(self):
        if self.emulador in LY and self.nucleo:
            return f"RetroArch · núcleo {self.nucleo}"
        return self.emulador


@dataclass
class Paso:
    numero: int
    titulo: str
    estado: str
    texto: str
    accion: str = ""


@dataclass
class Plan:
    juego: JuegoRetroBat
    seleccion: Seleccion | None
    emulador_exe: Path | None
    tipo_teknoparrot: str
    requisitos: list = field(default_factory=list)
    pasos: list = field(default_factory=list)

    @property
    def siguiente(self):
        return next((paso for paso in self.pasos if paso.estado in (PENDIENTE, AVISO) and paso.accion), None)

    @property
    def pendientes(self):
        return [fila for fila in self.requisitos
                if not fila.requisito.opcional and fila.estado not in RESUELTOS]


# --------------------------------------------------------------------------- biblioteca

def juegos_instalados(raiz, sistemas):
    """Lista las entradas de juego que RetroBat muestra en cada sistema."""
    juegos = []
    for clave, sistema in sistemas.items():
        if not sistema.carpeta.is_dir():
            continue
        try:
            _, _, _, catalogo = catalogo_juegos(sistema)
        except (OSError, ValueError, ET.ParseError):
            catalogo = {}
        nombres = {ruta: (nodos[0].findtext("name") or "").strip() for ruta, nodos in catalogo.items() if nodos}
        for ruta in entradas_sistema(sistema):
            titulo = nombres.get(ruta) or ruta.stem
            juegos.append(JuegoRetroBat(clave, sistema, ruta, titulo))
    return sorted(juegos, key=lambda j: (j.sistema.nombre.casefold(), j.titulo.casefold()))


def entradas_sistema(sistema):
    extensiones = set(sistema.extensiones)
    if sistema.identificador == "teknoparrot":
        extensiones |= set(FORMATOS)
    for carpeta, subcarpetas, archivos in os.walk(sistema.carpeta):
        for nombre in sorted(subcarpetas):
            if nombre.startswith(".") or nombre.casefold() in CARPETAS_MULTIMEDIA:
                subcarpetas.remove(nombre)
            elif Path(nombre).suffix.lower() in extensiones:
                # Carpetas con extensión (.teknoparrot, .pc, .ps3…) son un juego completo.
                subcarpetas.remove(nombre)
                yield Path(carpeta) / nombre
        for nombre in sorted(archivos):
            if Path(nombre).suffix.lower() in extensiones and nombre.casefold() != "gamelist.xml":
                yield Path(carpeta) / nombre


# --------------------------------------------------------------------------- emulador

def ajustes_retrobat(raiz):
    _, _, config = leer_ajustes(raiz)
    return {nodo.get("name"): nodo.get("value", "") for nodo in config.findall("string")}


def seleccion_emulador(raiz, juego, ajustes=None):
    """Devuelve el emulador y núcleo que RetroBat usará para este juego."""
    ajustes = ajustes_retrobat(raiz) if ajustes is None else ajustes
    sistema = juego.sistema.identificador
    for prefijo, origen in ((f'{sistema}["{juego.ruta.name}"]', "ajuste de este juego"),
                            (sistema, "ajuste del sistema en RetroBat")):
        emulador = (ajustes.get(f"{prefijo}.emulator") or "").strip()
        if emulador and emulador.casefold() != "auto":
            nucleo = (ajustes.get(f"{prefijo}.core") or "").strip()
            if not nucleo:
                nucleo = nucleo_predeterminado(raiz, sistema, emulador)
            return Seleccion(emulador, nucleo, origen)
    return emulador_predeterminado(raiz, sistema)


def emuladores_declarados(raiz, sistema):
    raiz_xml = ET.parse(archivo_sistemas_retrobat(raiz)).getroot()
    for nodo in raiz_xml.findall("system"):
        if nodo.findtext("name", "").strip().casefold() == sistema:
            return nodo.findall("./emulators/emulator")
    return []


def nucleo_predeterminado(raiz, sistema, emulador):
    for nodo in emuladores_declarados(raiz, sistema):
        if nodo.get("name", "") == emulador:
            nucleos = nodo.findall("./cores/core")
            preferido = next((n for n in nucleos if n.get("default", "").casefold() == "true"), None)
            elegido = preferido if preferido is not None else (nucleos[0] if nucleos else None)
            return (elegido.text or "").strip() if elegido is not None else ""
    return ""


def emulador_predeterminado(raiz, sistema):
    emuladores = emuladores_declarados(raiz, sistema)
    for nodo in emuladores:
        for nucleo in nodo.findall("./cores/core"):
            if nucleo.get("default", "").casefold() == "true":
                return Seleccion(nodo.get("name", ""), (nucleo.text or "").strip(), "predeterminado de RetroBat")
    for nodo in emuladores:
        if nodo.get("default", "").casefold() == "true":
            return Seleccion(nodo.get("name", ""), nucleo_predeterminado(raiz, sistema, nodo.get("name", "")),
                             "predeterminado de RetroBat")
    if emuladores:
        nombre = emuladores[0].get("name", "")
        return Seleccion(nombre, nucleo_predeterminado(raiz, sistema, nombre), "primer emulador declarado")
    return None


def item_emulador(catalogo, seleccion):
    if seleccion.emulador in LY:
        clave = (seleccion.nucleo, True) if seleccion.nucleo else ("retroarch", False)
    else:
        clave = (seleccion.emulador, False)
    return next((e for e in catalogo if (e.id, e.nucleo) == clave), None)


# --------------------------------------------------------------------------- TeknoParrot

def perfil_teknoparrot(raiz, juego):
    """Perfil de usuario y tipo de emulador interno (EmulatorType) de un juego de TeknoParrot."""
    emulador = carpeta_emulador(raiz)
    perfil = juego.ruta.stem
    usuario = emulador / "UserProfiles" / f"{perfil}.xml"
    plantilla = emulador / "GameProfiles" / f"{perfil}.xml"
    for archivo in (usuario, plantilla):
        if archivo.is_file():
            try:
                xml = ET.parse(archivo).getroot()
            except ET.ParseError:
                continue
            return (archivo if archivo == usuario else None), (xml.findtext("EmulatorType") or "").strip(), xml
    return None, "", None


def rpcs3_teknoparrot(raiz):
    return carpeta_emulador(raiz) / "RPCS3" / "rpcs3.exe"


# --------------------------------------------------------------------------- requisitos

def nombre_requisitos(juego, seleccion, tipo_teknoparrot):
    sistema = juego.sistema.identificador
    if sistema == "teknoparrot":
        return TEKNOPARROT_RPCS3 if tipo_teknoparrot.casefold() == "rpcs3" else None
    emulador = (seleccion.emulador if seleccion else "").casefold()
    if sistema in {"ps3", "namco3xx"} or emulador == "rpcs3":
        return "PlayStation 3"
    if sistema == "psvita":
        return "PlayStation Vita"
    if sistema == "switch":
        return f"Nintendo Switch · {NOMBRES_SWITCH.get(emulador, 'Ryujinx')}"
    return juego.sistema.nombre


def revisar_requisitos(raiz, sistemas, nombre):
    if not nombre:
        return []
    requisitos = [r for r in requisitos_firmware(raiz, sistemas) if r.sistema == nombre]
    estados = []
    cubiertos = set()
    for requisito in requisitos:
        try:
            ruta_local(raiz, requisito.destino)
            estado = estado_firmware(requisito)
        except (OSError, ValueError):
            estado = "Ruta inaccesible"
        estados.append(estado)
        if requisito.grupo and estado in {"Verificado", "Presente · sin huella"}:
            cubiertos.add(requisito.grupo)
    filas = []
    for requisito, estado in zip(requisitos, estados):
        if requisito.grupo and estado == FALTA and requisito.grupo in cubiertos:
            estado = "Alternativa cubierta"
        if estado == GUARDADO:
            accion = "Instalar" if requisito.emulador and requisito.emulador.is_file() else ""
        elif estado == FALTA and requisito.tipo != "ryujinx":
            accion = "Descarga oficial"
        else:
            accion = ""
        filas.append(Revision(requisito, estado, accion))
    return sorted(filas, key=lambda f: (f.requisito.opcional, f.requisito.destino.name.casefold()))


# --------------------------------------------------------------------------- plan

def preparar_plan(raiz, sistemas, juego):
    raiz = raiz.resolve()
    pasos = []
    seleccion = seleccion_emulador(raiz, juego)
    tipo_tp = ""
    exe = None

    # 1. Juego
    if not juego.ruta.exists():
        pasos.append(Paso(1, "Juego", PENDIENTE, "La entrada ya no existe en RetroBat. Actualiza la lista.",
                          ACCION_IMPORTAR))
    elif juego.sistema.identificador == "teknoparrot":
        usuario, tipo_tp, xml = perfil_teknoparrot(raiz, juego)
        if xml is None:
            pasos.append(Paso(1, "Juego", PENDIENTE,
                              f"TeknoParrot no tiene el perfil «{juego.ruta.stem}». Impórtalo desde la pestaña TeknoParrot.",
                              ACCION_IMPORTAR))
        elif usuario is None:
            pasos.append(Paso(1, "Juego", PENDIENTE,
                              "El juego no tiene perfil de usuario en TeknoParrot: impórtalo desde la pestaña TeknoParrot.",
                              ACCION_IMPORTAR))
        else:
            ruta = Path((xml.findtext("GamePath") or "").strip())
            if not ruta.is_file():
                pasos.append(Paso(1, "Juego", AVISO,
                                  f"El perfil apunta a un ejecutable que no existe: {ruta}. Vuelve a importar el juego.",
                                  ACCION_IMPORTAR))
            else:
                pasos.append(Paso(1, "Juego", HECHO,
                                  f"En RetroBat · perfil {juego.ruta.stem}"
                                  + (f" · usa {tipo_tp} de TeknoParrot" if tipo_tp else "")))
    else:
        pasos.append(Paso(1, "Juego", HECHO, f"En RetroBat · {juego.sistema.nombre} · {juego.ruta.name}"))

    # 2. Emulador
    if seleccion is None:
        pasos.append(Paso(2, "Emulador", AVISO,
                          "RetroBat no declara un emulador para este sistema. Revisa es_systems.cfg."))
    else:
        catalogo = catalogo_emuladores(raiz)
        rutas = familia_emuladores(raiz)
        item = item_emulador(catalogo, seleccion)
        if item is not None:
            exe = instalacion(raiz, item, rutas)
            if exe and item.nucleo and not instalacion(raiz, retroarch_base(), rutas):
                exe = None
        texto = f"{seleccion.descripcion} ({seleccion.origen})"
        if item is None:
            pasos.append(Paso(2, "Emulador", AVISO,
                              f"{texto}: el gestor no conoce su ubicación. Ábrelo desde la pestaña Emuladores."))
        elif exe is None:
            pasos.append(Paso(2, "Emulador", PENDIENTE, f"Falta el emulador: {texto}.",
                              ACCION_TEKNOPARROT if item.id == "teknoparrot" else ACCION_EMULADOR))
        elif juego.sistema.identificador == "teknoparrot" and tipo_tp.casefold() == "rpcs3" \
                and not rpcs3_teknoparrot(raiz).is_file():
            pasos.append(Paso(2, "Emulador", PENDIENTE,
                              "Falta el RPCS3 de TeknoParrot (emulators/teknoparrot/RPCS3). "
                              "Instala los componentes de TeknoParrot.", ACCION_TEKNOPARROT))
        else:
            detalle = exe.relative_to(raiz) if exe.is_relative_to(raiz) else exe
            if juego.sistema.identificador == "teknoparrot" and tipo_tp.casefold() == "rpcs3":
                detalle = f"{detalle} + {rpcs3_teknoparrot(raiz).relative_to(raiz)}"
            pasos.append(Paso(2, "Emulador", HECHO, f"{texto} · instalado en {detalle}"))

    # 3. BIOS y firmware
    nombre = nombre_requisitos(juego, seleccion, tipo_tp)
    requisitos = revisar_requisitos(raiz, sistemas, nombre)
    pendientes = [f for f in requisitos if not f.requisito.opcional and f.estado not in RESUELTOS]
    if not requisitos:
        pasos.append(Paso(3, "BIOS y firmware", HECHO,
                          "Según el catálogo de RetroBat, este juego no necesita BIOS ni firmware."))
    elif not pendientes:
        opcionales = sum(1 for f in requisitos if f.requisito.opcional and f.estado not in RESUELTOS)
        pasos.append(Paso(3, "BIOS y firmware", HECHO, f"Requisitos de {nombre} completos"
                          + (f" · {opcionales} opcionales sin instalar" if opcionales else "")))
    else:
        automaticos = [f for f in pendientes if f.accion in {"Instalar", "Descarga oficial"}]
        guardados = [f for f in pendientes if f.estado == GUARDADO]
        if guardados and pasos[1].estado != HECHO:
            texto = (f"Firmware guardado, pero falta instalarlo en el emulador de {nombre}. "
                     "Completa primero el paso 2.")
        elif guardados:
            texto = f"Firmware guardado · falta instalarlo en el emulador de {nombre}."
        else:
            texto = f"Faltan {len(pendientes)} archivo(s) de {nombre}."
        pasos.append(Paso(3, "BIOS y firmware", PENDIENTE, texto,
                          ACCION_REQUISITOS if automaticos else ACCION_ARCHIVO))

    # 4. Probar
    anteriores = not any(paso.estado == PENDIENTE for paso in pasos)
    lanzador = raiz / "emulationstation" / "emulatorlauncher.exe"
    if not lanzador.is_file():
        pasos.append(Paso(4, "Probar", AVISO, "No se encontró emulationstation/emulatorlauncher.exe."))
    elif anteriores:
        pasos.append(Paso(4, "Probar", PENDIENTE,
                          "Listo para probar con la misma configuración que usará el arcade.", ACCION_PROBAR))
    else:
        pasos.append(Paso(4, "Probar", ESPERA, "Completa los pasos anteriores antes de probar.", ACCION_PROBAR))

    return Plan(juego, seleccion, exe, tipo_tp, requisitos, pasos)


def comando_prueba(raiz, plan):
    """Comando de emulatorLauncher equivalente al que usa EmulationStation."""
    raiz = raiz.resolve()
    lanzador = ruta_local(raiz, raiz / "emulationstation" / "emulatorlauncher.exe")
    seleccion = plan.seleccion
    if seleccion is None:
        raise ValueError("RetroBat no declara un emulador para este sistema.")
    return [str(lanzador), "-system", plan.juego.sistema.identificador,
            "-emulator", seleccion.emulador, "-core", seleccion.nucleo or seleccion.emulador,
            "-rom", str(plan.juego.ruta)]
