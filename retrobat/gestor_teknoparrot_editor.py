"""Edición, vista previa y guardado de los controles de un juego de TeknoParrot."""
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

import gestor_teknoparrot as tp
import gestor_teknoparrot_controles as tc
from gestor_teknoparrot_diagnostico import leer_texto

MAPA_OFICIAL = "https://raw.githubusercontent.com/RetroBat-Official/retrobat/main/system/resources/inputmapping/teknoparrot.yml"
FAMILIA_DISPAROS = {"contra", "raideniii", "raideniiinesica"}
MAPA_DISPAROS = {"start": "start", "1": "south", "2": "east", **{direccion: direccion for direccion in tc.DIRECCIONES}}
DIRECCIONES_POV = {1: "↑", 2: "→", 4: "↓", 8: "←"}
TEXTO_XINPUT = {
    **{pos: nombre for pos, (_, nombre) in tc.BOTONES_XI.items()},
    "up": "Cruceta ↑", "down": "Cruceta ↓", "left": "Cruceta ←", "right": "Cruceta →",
    "start": "Inicio", "select": "Atrás / Vista", "l3": "Clic izq. (L3)", "r3": "Clic der. (R3)",
    "lefttrigger": "LT", "righttrigger": "RT", "leftshoulder": "LB", "rightshoulder": "RB",
    **{f"{lado}stick{direccion}": f"Palanca {etiqueta} {flecha}"
       for lado, etiqueta in (("left", "izq."), ("right", "der."))
       for direccion, flecha in (("up", "↑"), ("down", "↓"), ("left", "←"), ("right", "→"))},
}
SIN_ASIGNAR = "Sin asignar"


def opcion_fisica(mando, codigo):
    if mando.api == "XInput":
        # Cada código describe un único botón. El fallback de cruceta a palanca se aplica a la plantilla.
        if codigo in tc.BOTONES_XI and not mando.mascarilla & tc.BOTONES_XI[codigo][0]:
            return None
        return tc.xinput(mando, codigo) if codigo in TEXTO_XINPUT else None
    if boton := re.fullmatch(r"b(\d+)", codigo):
        return tc.directinput(mando, tc.EntradaDI("button", int(boton[1]), 1))
    if cruceta := re.fullmatch(r"h(\d+)\.([1248])", codigo):
        return tc.directinput(mando, tc.EntradaDI("hat", int(cruceta[1]), int(cruceta[2])))
    if eje := re.fullmatch(r"a([0-7])([+-])", codigo):
        return tc.directinput(mando, tc.EntradaDI("axis", int(eje[1]), -1 if eje[2] == "-" else 1))
    return None


def opciones_fisicas(mando):
    if mando.api == "XInput":
        return {codigo: nombre for codigo, nombre in TEXTO_XINPUT.items() if opcion_fisica(mando, codigo)}
    opciones = {f"b{i}": f"Botón {i + 1}" for i in range(min(128, mando.botones))}
    for i in range(min(4, mando.crucetas)):
        opciones.update({f"h{i}.{d}": f"Cruceta {i + 1} {flecha}" for d, flecha in DIRECCIONES_POV.items()})
    if mando.ejes:
        for i, nombre in enumerate(("X", "Y", "Z", "RX", "RY", "RZ", "S1", "S2")):
            opciones.update({f"a{i}{signo}": f"Eje {nombre} {signo}" for signo in ("-", "+")})
    return opciones


def codigo_enlace(enlace):
    if not enlace:
        return ""
    api, _, _, datos = enlace
    if api == "XInputButton":
        if datos.get("IsButton") == "true":
            codigo = int(datos.get("ButtonCode", 0)) & 0xFFFF
            return next((pos for pos, (mascara, _) in tc.BOTONES_XI.items() if codigo == mascara), "")
        menos = datos.get("IsAxisMinus") == "true"
        return next((pos for pos, (campo, negativo, _) in tc.EJES_XI.items()
                     if datos.get(campo) == "true" and menos == negativo), "")
    numero = int(datos.get("Button", -1))
    if datos.get("IsAxis") == "true" and numero in range(0, 32, 4):
        return f"a{numero // 4}{'-' if datos.get('IsAxisMinus') == 'true' else '+'}"
    if numero >= 48:
        return f"b{numero - 48}"
    if numero in range(32, 48, 4):
        direccion = {0: 1, 9000: 2, 18000: 4, 27000: 8}.get(int(datos.get("PovDirection", -1)))
        return f"h{(numero - 32) // 4}.{direccion}" if direccion else ""
    return ""


def asignacion_actual(nodo, mando):
    etiqueta = mando.api + "Button"
    actual = nodo.find(etiqueta)
    if actual is None:
        return ""
    datos = {hijo.tag: hijo.text for hijo in actual}
    propiedad = "XInputIndex" if mando.api == "XInput" else "JoystickGuid"
    identidad = str(mando.indice if mando.api == "XInput" else mando.guid).casefold()
    if (datos.get(propiedad) or "").casefold().strip("{}") != identidad:
        return ""
    try:
        return codigo_enlace((etiqueta, "", "", datos))
    except (ValueError, TypeError):
        return ""


@lru_cache(maxsize=1)
def tabla_en_linea():
    return tc.leer_bloques_yml(leer_texto(MAPA_OFICIAL))


def plantilla_juego(raiz, id_, layout):
    datos = {}
    for ruta in reversed(tc.YAML_MANDOS):
        datos.update(tc.bloques_yml(raiz / ruta))
    mapa = datos.get(f"{id_}_{layout}") or datos.get(id_)
    if mapa:
        return mapa, "Mapa de RetroBat de esta instalación"
    try:
        datos = tabla_en_linea()
        mapa = datos.get(f"{id_}_{layout}") or datos.get(id_)
    except (OSError, ValueError):
        mapa = None
    if mapa:
        return mapa, "Mapa oficial de RetroBat consultado en línea"
    if id_ in FAMILIA_DISPAROS:
        mapa = {f"p{j}button{k}": v for j in (1, 2) for k, v in MAPA_DISPAROS.items()}
        if id_ == "contra":
            mapa.update(service1="select", p1button3="west", p2button3="west")
        else:
            mapa.update(coin1="select", coin2="select")
        return mapa, "Plantilla de este juego basada en el mapa oficial de RetroBat"
    return {}, "Plantilla de acciones comunes · ajusta las que necesite el juego"


@dataclass(frozen=True)
class Accion:
    indice: int
    nombre: str
    guardado: str
    actual: str
    plantilla: str
    servicio: bool


@dataclass
class Edicion:
    perfil: tp.Perfil
    entradas: tuple[Path, ...]
    archivo: Path
    original: bytes | None
    xml: ET.Element
    campo_api: ET.Element | None
    mando: object
    acciones: list[Accion]
    fuente: str
    proteger: bool


def abrir_edicion(raiz, juego, mando, jugador):
    perfil, entradas = juego
    archivo = tp.carpeta_emulador(raiz) / "UserProfiles" / perfil.plantilla.name
    if archivo.resolve() != archivo or perfil.plantilla.resolve() != perfil.plantilla:
        raise ValueError("El perfil apunta a una ubicación distinta.")
    original = archivo.read_bytes() if archivo.exists() else None
    xml = tc.cargar_perfil(original if original is not None else perfil.plantilla.read_bytes(), archivo.name)
    botones = xml.findall("./JoystickButtons/JoystickButtons")
    campo = next((nodo for nodo in xml.findall("./ConfigValues/*") if nodo.findtext("FieldName") == "Input API"), None)
    opciones = {n.text for n in campo.findall("./FieldOptions/*")} if campo is not None else {"DirectInput"}
    if mando.api not in opciones and (campo is None or campo.findtext("FieldValue") != mando.api):
        raise ValueError(f"El perfil de {perfil.titulo} no admite {mando.api}. Elige un mando compatible.")
    _, _, config = tc.leer_ajustes(raiz)
    valores = {n.get("name", "").casefold(): n.get("value", "") for n in config}
    niveles = [tc.prefijo_juego(ruta).casefold() for ruta in entradas]
    layouts = {valores.get(prefijo + "controller_layout") or valores.get("teknoparrot.controller_layout")
               or valores.get("global.controller_layout") or "pad" for prefijo in niveles or [""]}
    mapa, fuente = plantilla_juego(raiz, perfil.id.casefold(), sorted(layouts)[0].casefold())
    if len(layouts) > 1:
        fuente += " · las entradas que comparten este perfil usan variantes diferentes"
    mapa_dispositivo = tc.mapa_mando(raiz, mando)
    disponibles = opciones_fisicas(mando)
    oculto = "HideWith" + mando.api
    acciones = []
    vistos = set()
    for indice, boton in enumerate(botones):
        if boton.findtext(oculto, "").casefold() == "true":
            continue
        clave = boton.findtext("InputMapping", "").casefold()
        nombre = boton.findtext("ButtonName", clave)
        j, defecto = tc.jugador_y_posicion(clave, nombre, boton.findtext("AnalogType", "").casefold())
        if j != jugador or clave in vistos:
            continue
        vistos.add(clave)
        # Algunos perfiles llaman Service al ingreso de créditos. Mantener la ficha de Contra.
        moneda = "coin" in nombre.casefold() or re.fullmatch(r"(?:jvstwo)?coin\d*", clave)
        servicio = not moneda and (clave.removeprefix("jvstwo").startswith(("test", "service"))
                                   or re.match(r"^(test|service)\b", nombre, re.I))
        posicion = "" if servicio else mapa.get(clave, "select" if moneda else defecto) or ""
        if posicion.startswith("kb_") and (moneda or defecto == "start"):
            posicion = "select" if moneda else "start"
        esperado = codigo_enlace(mapa_dispositivo.get(posicion))
        if esperado not in disponibles:
            esperado = ""
        actual = asignacion_actual(boton, mando)
        guardado = disponibles.get(actual) or boton.findtext("BindName", "") or SIN_ASIGNAR
        acciones.append(Accion(indice, nombre, guardado, actual if actual in disponibles else "", esperado, bool(servicio)))
    proteger = all(valores.get(prefijo + "disableautocontrollers", "1") != "0" for prefijo in niveles)
    return Edicion(perfil, entradas, archivo, original, xml, campo, mando, acciones, fuente, proteger)


def guardar_edicion(raiz, edicion, asignaciones, *, proteger=True):
    controles = defaultdict(list)
    for accion in edicion.acciones:
        if codigo := asignaciones.get(accion.indice):
            controles[codigo].append(accion)
    if not controles:
        raise ValueError("Asigna al menos un control antes de guardar.")
    for acciones in controles.values():
        if any(accion.servicio for accion in acciones) and len(acciones) > 1:
            nombres = ", ".join(accion.nombre for accion in acciones)
            raise ValueError(f"Asigna un botón exclusivo para el menú de servicio. Coinciden {nombres}.")
    nodos = edicion.xml.findall("./JoystickButtons/JoystickButtons")
    cambios = []
    for accion in edicion.acciones:
        codigo = asignaciones.get(accion.indice, "")
        if codigo:
            enlace = opcion_fisica(edicion.mando, codigo)
            if enlace is None:
                raise ValueError(f"No se pudo asignar {accion.nombre} al mando seleccionado.")
            tc.asignar_input(nodos[accion.indice], enlace)
        else:
            tc.limpiar_input(nodos[accion.indice])
    if edicion.campo_api is not None:
        campo = edicion.campo_api.find("FieldValue")
        if campo is None:
            campo = ET.SubElement(edicion.campo_api, "FieldValue")
        campo.text = edicion.mando.api
    datos = ET.tostring(edicion.xml, encoding="utf-8", xml_declaration=True)
    if datos != edicion.original:
        cambios.append(tc.Cambio(edicion.archivo, edicion.original, datos))
    if edicion.entradas:
        archivo, original, config = tc.leer_ajustes(raiz)
        cambios_ajuste = False
        for ruta in edicion.entradas:
            cambios_ajuste |= tc.actualizar_opcion(config, tc.prefijo_juego(ruta) + "disableautocontrollers",
                                                  "1" if proteger else "0")
        if cambios_ajuste:
            cambios.append(tc.Cambio(archivo, original, ET.tostring(config, encoding="utf-8", xml_declaration=True)))
    respaldo = tc.guardar_cambios(raiz, cambios)
    edicion.original = datos
    edicion.proteger = proteger
    return respaldo


def probar_juego(raiz, edicion):
    if os.name != "nt":
        raise OSError("La prueba del juego se ejecuta en Windows.")
    emulador = tp.carpeta_emulador(raiz)
    if not edicion.archivo.is_file():
        raise ValueError("Guarda los controles antes de probar el juego.")
    lanzador = raiz / "emulationstation" / "emulatorLauncher.exe"
    if edicion.entradas and lanzador.is_file():
        ruta_juego = edicion.entradas[0]
        if not ruta_juego.exists():
            raise ValueError("RetroBat ya no encuentra esta entrada. Actualiza la lista de juegos.")
        return subprocess.Popen([str(lanzador), "-system", "teknoparrot", "-emulator", "teknoparrot",
                                 "-rom", str(ruta_juego)], cwd=lanzador.parent)
    xml = ET.parse(edicion.archivo).getroot()
    ruta = xml.findtext("GamePath", "").strip()
    if not ruta or not (emulador / ruta).is_file():
        raise ValueError("El perfil no tiene una ruta de arranque lista. Inicia este juego desde el menú de RetroBat.")
    exe = emulador / "TeknoParrotUi.exe"
    return subprocess.Popen([str(exe), f"--profile={edicion.archivo.name}"], cwd=emulador)
