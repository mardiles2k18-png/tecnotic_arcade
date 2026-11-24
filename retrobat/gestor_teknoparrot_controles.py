"""Mapea mandos conectados en los perfiles de juego de TeknoParrot."""
from collections import defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
import re
import tempfile
import xml.etree.ElementTree as ET

import gestor_teknoparrot as tp
from gestor_teknoparrot_pantalla import leer_ajustes

YAML_MANDOS = ("user/inputmapping/teknoparrot.yml", "system/resources/inputmapping/teknoparrot.yml")
DOCUMENTACION_MANDOS = "https://wiki.retrobat.org/controllers/specific_mapping/teknoparrot-controller-mapping"
DI_DB = "system/tools/gamecontrollerdb.txt"
ES_INPUT = "emulationstation/.emulationstation/es_input.cfg"
BOTONES_XI = {
    "up": (0x0001, "DPadUp"), "down": (0x0002, "DPadDown"),
    "left": (0x0004, "DPadLeft"), "right": (0x0008, "DPadRight"),
    "start": (0x0010, "Start"), "select": (0x0020, "Back"),
    "l3": (0x0040, "LeftThumb"), "r3": (0x0080, "RightThumb"),
    "leftshoulder": (0x0100, "LeftShoulder"), "rightshoulder": (0x0200, "RightShoulder"),
    "south": (0x1000, "A"), "east": (0x2000, "B"), "west": (0x4000, "X"), "north": (0x8000, "Y"),
}
EJES_XI = {
    "leftstickleft": ("IsLeftThumbX", True, "Left X-"), "leftstickright": ("IsLeftThumbX", False, "Left X+"),
    "leftstickdown": ("IsLeftThumbY", True, "Left Y-"), "leftstickup": ("IsLeftThumbY", False, "Left Y+"),
    "rightstickleft": ("IsRightThumbX", True, "Right X-"), "rightstickright": ("IsRightThumbX", False, "Right X+"),
    "rightstickdown": ("IsRightThumbY", True, "Right Y-"), "rightstickup": ("IsRightThumbY", False, "Right Y+"),
    "lefttrigger": ("IsLeftTrigger", False, "LeftTrigger"), "righttrigger": ("IsRightTrigger", False, "RightTrigger"),
}
POSICIONES = ("south", "east", "west", "north", "leftshoulder", "rightshoulder", "lefttrigger", "righttrigger")
DIRECCIONES = {"up", "down", "left", "right"}
NOMBRES_ES = dict(zip((*POSICIONES, "select", "start", "l3", "r3"),
                      ("a", "b", "y", "x", "pageup", "pagedown", "l2", "r2", "select", "start", "l3", "r3")))
NOMBRES_DB = dict(zip((*POSICIONES, "select", "start", "l3", "r3"),
                      ("a", "b", "x", "y", "leftshoulder", "rightshoulder", "lefttrigger", "righttrigger",
                       "back", "start", "leftstick", "rightstick")))


@dataclass(frozen=True)
class EntradaDI:
    tipo: str
    indice: int
    valor: int


@dataclass(frozen=True)
class Cambio:
    archivo: Path
    original: bytes | None
    nuevo: bytes


def bloques_yml(ruta):
    return leer_bloques_yml(ruta.read_text(encoding="utf-8-sig")) if ruta.is_file() else {}


def leer_bloques_yml(texto):
    bloques = {}
    actual = None
    for linea in texto.splitlines():
        if cabecera := re.fullmatch(r"([^\s#].*?):\s*(?:#.*)?", linea):
            actual = bloques.setdefault(cabecera[1].strip("\"'").casefold(), {})
        elif actual is not None and (campo := re.fullmatch(r"\s+([^\s:#]+):\s*([^#]*)(?:#.*)?", linea)):
            actual[campo[1].casefold()] = campo[2].strip().strip("\"'")
    return bloques


def mandos_configurados(raiz):
    ruta = raiz / ES_INPUT
    if not ruta.is_file():
        return ()
    return tuple(nodo for nodo in ET.parse(ruta).getroot().findall("inputConfig")
                 if nodo.get("type") == "joystick")


def ids_usb_sdl(guid):
    if re.fullmatch(r"[0-9a-f]{32}", guid, re.I):
        datos = bytes.fromhex(guid)
        return int.from_bytes(datos[4:6], "little"), int.from_bytes(datos[8:10], "little")
    return (0, 0)


def entradas_es(configs, mando):
    nombres = {mando.nombre.casefold(), mando.producto.casefold()} - {""}
    por_id = [nodo for nodo in configs if mando.usb != (0, 0)
              and ids_usb_sdl(nodo.get("deviceGUID", "")) == mando.usb]
    por_nombre = [nodo for nodo in (por_id or configs) if nodo.get("deviceName", "").casefold() in nombres]
    coincidencias = por_nombre or por_id
    if len(coincidencias) != 1:
        return {}
    entradas = {}
    for nodo in coincidencias[0].findall("input"):
        try:
            entradas[nodo.get("name", "").casefold()] = EntradaDI(nodo.get("type", ""), int(nodo.get("id", "")),
                                                                    int(nodo.get("value", "")))
        except ValueError:
            continue
    return entradas


def entradas_db(lineas, mando):
    if mando.usb == (0, 0):
        return {}
    for linea in lineas:
        guid, _, campos = linea.partition(",")
        if ids_usb_sdl(guid) != mando.usb or "platform:Windows," not in campos:
            continue
        entradas = {}
        for clave, enlace in re.findall(r"(?:^|,)([a-z0-9]+):([+-]?[abh]\d+(?:\.\d+)?~?)(?=,|$)", campos):
            coincidencia = re.fullmatch(r"([+-]?)([abh])(\d+)(?:\.(\d+))?(~?)", enlace)
            signo, tipo, indice, direccion, invertido = coincidencia.groups()
            if tipo == "h" and direccion is None:
                continue
            valor = int(direccion) if tipo == "h" else -1 if (signo == "-") != bool(invertido) else 1
            entradas[clave] = EntradaDI({"a": "axis", "b": "button", "h": "hat"}[tipo], int(indice), valor)
        return entradas
    return {}


def entrada_directinput(posicion, es, db):
    if posicion in DIRECCIONES:
        return db.get("dp" + posicion) or es.get(posicion) or entrada_directinput("leftstick" + posicion, es, db)
    if posicion in NOMBRES_DB:
        return db.get(NOMBRES_DB[posicion]) or es.get(NOMBRES_ES[posicion])
    eje = re.fullmatch(r"(left|right)stick(up|down|left|right)", posicion)
    if eje:
        lado, sentido = eje.groups()
        horizontal = sentido in {"left", "right"}
        entrada = db.get(lado + ("x" if horizontal else "y"))
        if entrada is None:
            palanca = "1" if lado == "left" else "2"
            entrada = es.get(lado + "analog" + sentido) or es.get("joystick" + palanca + sentido)
            if entrada is not None:
                return entrada
            entrada = (es.get(lado + "analog" + ("left" if horizontal else "up"))
                       or es.get("joystick" + palanca + ("left" if horizontal else "up")))
            if entrada is None or sentido in {"left", "up"}:
                return entrada
            return EntradaDI(entrada.tipo, entrada.indice, -entrada.valor) if entrada.tipo == "axis" else None
        return EntradaDI(entrada.tipo, entrada.indice, entrada.valor * (-1 if sentido in {"up", "left"} else 1))
    return None


def xinput(mando, posicion):
    boton, nombre = BOTONES_XI.get(posicion, (0, ""))
    if boton and not mando.mascarilla & boton:
        return xinput(mando, "leftstick" + posicion) if posicion in DIRECCIONES else None
    datos = dict.fromkeys((campo for campo, _, _ in EJES_XI.values()), "false")
    datos.update(IsAxisMinus="false", ButtonCode=str(boton if boton < 32768 else boton - 65536),
                 IsButton="true" if boton else "false", ButtonIndex="0", XInputIndex=str(mando.indice))
    if not boton:
        eje = EJES_XI.get(posicion)
        if eje is None or eje[0] not in mando.ejes_xinput:
            return None
        campo, menos, nombre = eje
        datos[campo] = "true"
        datos["IsAxisMinus"] = "true" if menos else "false"
    return "XInputButton", "BindNameXi", f"Input Device {mando.indice} {nombre}", datos


def directinput(mando, entrada):
    if entrada is None or entrada.indice < 0:
        return None
    indice, valor = entrada.indice, entrada.valor
    datos = dict(IsAxis="false", IsAxisMinus="false", IsFullAxis="false", IsReverseAxis="false",
                 PovDirection="0", JoystickGuid=mando.guid)
    if entrada.tipo == "button" and indice < mando.botones:
        datos["Button"] = str(indice + 48)
        nombre = f"Buttons{indice}"
    elif entrada.tipo == "hat" and indice < mando.crucetas and valor in {1, 2, 4, 8}:
        direccion, angulo = {1: ("Up", 0), 2: ("Right", 9000), 4: ("Down", 18000), 8: ("Left", 27000)}[valor]
        datos.update(Button=str(32 + 4 * indice), PovDirection=str(angulo))
        nombre = f"PointOfViewControllers{indice} {direccion}"
    elif entrada.tipo == "axis" and indice < 8 and valor in {-1, 1}:
        if mando.ejes == 0:
            return None
        datos.update(Button=str(indice * 4), IsAxis="true", IsAxisMinus="true" if valor < 0 else "false")
        nombre = f"Axis {indice} {'−' if valor < 0 else '+'}"
    else:
        return None
    return "DirectInputButton", "BindNameDi", f"Gamepad {nombre}", datos


def jugador_y_posicion(clave, nombre, analogico):
    clave = clave.removeprefix("jvstwo")
    if boton := re.fullmatch(r"p([1-6])(?:button|relative)(.+)", clave):
        jugador, accion = int(boton[1]), boton[2]
        if accion.isdecimal() and 1 <= int(accion) <= len(POSICIONES):
            return jugador, POSICIONES[int(accion) - 1]
        if accion in DIRECCIONES | {"start"}:
            return jugador, accion
        return jugador, None
    jugador = re.search(r"(?:\bp(?:layer\s+)?|\bcoin(?:\s+chute)?\s*|\bservice\s*)([1-6])\b", nombre, re.I)
    indice = int(jugador[1]) if jugador else 1
    if moneda := re.fullmatch(r"(?:coin|service)([1-6])", clave):
        return int(moneda[1]), "select" if clave.startswith("coin") else "r3"
    if clave in {"test", "service", "coin"}:
        return indice, {"test": "l3", "service": "r3", "coin": "select"}[clave]
    if analogico in {"wheel", "gas", "brake"}:
        return indice, {"wheel": "leftstickleft", "gas": "righttrigger", "brake": "lefttrigger"}[analogico]
    if analogico.startswith("analogjoystick"):
        if re.search(r"\bx(?:\s+axis)?$", nombre, re.I):
            return indice, "leftstickleft"
        if re.search(r"\by(?:\s+axis)?$", nombre, re.I):
            return indice, "leftstickup"
    return indice, None


def asignar_input(boton, enlace):
    etiqueta, tipo_nombre, nombre, datos = enlace
    actual = boton.find(etiqueta)
    if (actual is not None and {nodo.tag: nodo.text for nodo in actual} == datos
            and boton.findtext(tipo_nombre) == nombre and boton.findtext("BindName") == nombre
            and all(boton.find(campo) is None for campo in {"XInputButton", "DirectInputButton", "RawInputButton"} - {etiqueta})):
        return False
    limpiar_input(boton)
    nodo = ET.SubElement(boton, etiqueta)
    for propiedad, valor in datos.items():
        ET.SubElement(nodo, propiedad).text = valor
    ET.SubElement(boton, tipo_nombre).text = nombre
    ET.SubElement(boton, "BindName").text = nombre
    return True


def limpiar_input(boton):
    retirados = False
    for campo in ("XInputButton", "DirectInputButton", "RawInputButton", "BindNameXi", "BindNameDi", "BindNameRi", "BindName"):
        for existente in boton.findall(campo):
            boton.remove(existente)
            retirados = True
    return retirados


def cargar_perfil(datos, nombre):
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True, insert_pis=True))
    xml = ET.fromstring(datos, parser=parser)
    if xml.tag != "GameProfile":
        raise ValueError(f"{nombre} no es un perfil de TeknoParrot.")
    return xml


def mapa_mando(raiz, mando):
    posiciones = set(BOTONES_XI) | set(EJES_XI)
    if mando.api == "XInput":
        return {posicion: xinput(mando, posicion) for posicion in posiciones}
    ruta_db = raiz / DI_DB
    db = ruta_db.read_text(encoding="utf-8-sig", errors="replace").splitlines() if ruta_db.is_file() else []
    es, entradas = entradas_es(mandos_configurados(raiz), mando), entradas_db(db, mando)
    return {posicion: directinput(mando, entrada_directinput(posicion, es, entradas)) for posicion in posiciones}


def entradas_por_perfil(raiz, perfiles):
    sistema = tp.sistema_teknoparrot(raiz)
    por_nombre = defaultdict(list)
    for perfil in perfiles.values():
        por_nombre[tp.clave_publicacion(perfil.titulo)].append(perfil)
    por_alias = bloques_yml(raiz / "system/tools/teknoparrotInfo.yml")
    juegos, pendientes = defaultdict(list), []
    for ruta in sorted(tp.entradas_instaladas(sistema)):
        perfil = perfiles.get(ruta.stem.casefold())
        if perfil is None:
            alias = por_alias.get(ruta.stem.casefold(), {}).get("profile", "").casefold()
            coincidencias = por_nombre.get(tp.clave_publicacion(ruta.stem), ())
            perfil = perfiles.get(alias) or (coincidencias[0] if len(coincidencias) == 1 else None)
        if perfil is None:
            pendientes.append(f"{ruta.name}: perfil oficial sin identificar.")
        elif ruta.resolve() != ruta:
            pendientes.append(f"{ruta.name}: la entrada apunta a otra ubicación.")
        else:
            juegos[perfil.id.casefold()].append(ruta)
    return juegos, pendientes


def prefijo_juego(ruta):
    nombre = ruta.name.replace("=", "").replace("#", "")
    return f'teknoparrot["{nombre}"].'


def actualizar_opcion(config, nombre, valor):
    nodos = [nodo for nodo in config if nodo.get("name", "").casefold() == nombre.casefold()]
    if len(nodos) == 1 and nodos[0].get("value") == valor:
        return False
    for nodo in nodos:
        config.remove(nodo)
    ET.SubElement(config, "string", name=nombre, value=valor)
    return True


def juegos_con_mandos(raiz):
    emulador = tp.carpeta_emulador(raiz)
    if not (emulador / "TeknoParrotUi.exe").is_file():
        raise ValueError("Instala TeknoParrot antes de configurar sus mandos.")
    perfiles = {perfil.id.casefold(): perfil for perfil in tp.perfiles_locales(emulador)}
    juegos, pendientes = entradas_por_perfil(raiz, perfiles)
    usuario = emulador / "UserProfiles"
    for archivo in usuario.glob("*.xml"):
        id_ = archivo.stem.casefold()
        if id_ in perfiles and id_ not in juegos:
            try:
                if archivo.resolve() != archivo:
                    continue
                ruta = ET.parse(archivo).getroot().findtext("GamePath", "").strip()
                if ruta and (emulador / ruta).is_file():
                    juegos[id_] = []  # Registrado directamente en TeknoParrot.
            except (OSError, ET.ParseError) as error:
                pendientes.append(f"{archivo.name}: {error}")
    ordenados = sorted(juegos, key=lambda id_: perfiles[id_].titulo.casefold())
    return [(perfiles[id_], tuple(juegos[id_])) for id_ in ordenados], pendientes


def escribir_seguro(archivo, nuevo, esperado):
    if archivo.resolve() != archivo:
        raise ValueError(f"{archivo.name} apunta a una ubicación distinta.")
    if (archivo.read_bytes() if archivo.exists() else None) != esperado:
        raise ValueError(f"{archivo.name} cambió. Cierra RetroBat y TeknoParrot antes de aplicar el mapeo.")
    if nuevo is None:
        archivo.unlink()
    else:
        archivo.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=archivo.parent) as temporal:
            nuevo_archivo = Path(temporal) / archivo.name
            nuevo_archivo.write_bytes(nuevo)
            nuevo_archivo.replace(archivo)


def guardar_cambios(raiz, cambios, prefijo="teknoparrot-"):
    if not cambios:
        return None
    base = raiz / "user" / "tecnotics-gestor" / "respaldos-mandos"
    if base.resolve() != base or any(cambio.archivo.resolve() != cambio.archivo for cambio in cambios):
        raise ValueError("Una de las rutas de mandos apunta a otra ubicación.")
    base.mkdir(parents=True, exist_ok=True)
    respaldo = Path(tempfile.mkdtemp(prefix=prefijo, dir=base))
    rutas = []
    for cambio in cambios:
        relativo = cambio.archivo.relative_to(raiz)
        rutas.append({"ruta": relativo.as_posix(), "creado": cambio.original is None})
        if cambio.original is not None:
            original = respaldo / relativo
            original.parent.mkdir(parents=True, exist_ok=True)
            original.write_bytes(cambio.original)
    (respaldo / "originales.json").write_text(json.dumps(rutas, ensure_ascii=False, indent=2), encoding="utf-8")
    aplicados = []
    try:
        for cambio in cambios:
            escribir_seguro(cambio.archivo, cambio.nuevo, cambio.original)
            aplicados.append(cambio)
    except (OSError, ValueError) as error:
        fallos = []
        for cambio in reversed(aplicados):
            try:
                escribir_seguro(cambio.archivo, cambio.original, cambio.nuevo)
            except (OSError, ValueError):
                fallos.append(cambio.archivo.name)
        detalle = " No se pudo revertir " + ", ".join(fallos) + "." if fallos else ""
        raise ValueError(f"{error}{detalle}\nRespaldo guardado en {respaldo}") from error
    return respaldo
