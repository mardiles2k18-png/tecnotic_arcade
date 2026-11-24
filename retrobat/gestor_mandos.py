"""Ajustes de mandos de RetroBat: orden de jugadores y configuración automática por sistema.

Claves comprobadas en el código de RetroBat (24-11-2026):
- EmulationStation (batocera-emulationstation, es-core/src/InputManager.cpp) asigna los jugadores con
  «INPUT P{n}PATH» (máxima prioridad), después «INPUT P{n}NAME» + «INPUT P{n}GUID» y por último solo el nombre.
- emulatorLauncher (Program.cs) lee «global.X», «<sistema>.X» y «<sistema>["<juego>"].X» de es_settings.cfg.
  Con «disableautocontrollers» = 1 cada emulador conserva su propio mapeo de mandos.
El gestor solo lee es_input.cfg; la asignación de botones se hace en el menú de RetroBat.
"""

from dataclasses import dataclass
import re
import xml.etree.ElementTree as ET

import gestor_teknoparrot_controles as tc
from gestor_teknoparrot_pantalla import leer_ajustes

JUGADORES = 4
AUTOMATICO = "RetroBat configura los mandos"
MANUAL = "Mapeo manual en el emulador"
CLAVE_AUTO = "disableautocontrollers"


@dataclass(frozen=True)
class MandoRetroBat:
    """Mando configurado en RetroBat (es_input.cfg)."""
    nombre: str
    guid: str

    @property
    def etiqueta(self):
        return f"{self.nombre} · {self.guid[:8]}…" if self.guid else self.nombre


@dataclass(frozen=True)
class Jugador:
    numero: int
    nombre: str
    guid: str
    ruta: str


def valores(config):
    return {nodo.get("name", ""): nodo.get("value", "") for nodo in config if nodo.get("name")}


def mandos_retrobat(raiz):
    """Mandos (joystick) que RetroBat ya tiene configurados, sin repetir."""
    vistos = []
    for nodo in tc.mandos_configurados(raiz):
        mando = MandoRetroBat(nodo.get("deviceName", "").strip(), nodo.get("deviceGUID", "").strip())
        if mando.nombre and mando not in vistos:
            vistos.append(mando)
    return vistos


def jugadores(raiz):
    _, _, config = leer_ajustes(raiz)
    datos = valores(config)
    return [Jugador(n, datos.get(f"INPUT P{n}NAME", ""), datos.get(f"INPUT P{n}GUID", ""),
                    datos.get(f"INPUT P{n}PATH", "")) for n in range(1, JUGADORES + 1)]


def gemelos(mandos, mando):
    """Cantidad de mandos con el mismo nombre y GUID: EmulationStation solo los distingue por PATH."""
    return sum(1 for otro in mandos if otro == mando)


def mando_retrobat(mandos, detectado):
    """Mando de es_input.cfg que corresponde a un mando detectado por Windows (por USB o por nombre)."""
    candidatos = [m for m in mandos if detectado.usb != (0, 0) and tc.ids_usb_sdl(m.guid) == detectado.usb]
    nombres = {detectado.nombre.casefold(), detectado.producto.casefold()} - {""}
    por_nombre = [m for m in (candidatos or mandos) if m.nombre.casefold() in nombres]
    elegidos = por_nombre or candidatos
    return elegidos[0] if elegidos else None


def asignar_jugadores(raiz, asignaciones):
    """Fija jugadores: {numero: MandoRetroBat}. Vacía PATH de ese jugador para que prime nombre + GUID."""
    archivo, original, config = leer_ajustes(raiz)
    cambiado = False
    for numero, mando in asignaciones.items():
        if not 1 <= numero <= JUGADORES:
            raise ValueError(f"Jugador fuera de rango: {numero}")
        for clave, valor in ((f"INPUT P{numero}NAME", mando.nombre), (f"INPUT P{numero}GUID", mando.guid),
                             (f"INPUT P{numero}PATH", "")):
            cambiado |= tc.actualizar_opcion(config, clave, valor)
    if not cambiado:
        return None
    nuevo = ET.tostring(config, encoding="utf-8", xml_declaration=True)
    return tc.guardar_cambios(raiz, [tc.Cambio(archivo, original, nuevo)], prefijo="jugadores-")


def autoconfiguracion(raiz, identificadores):
    """Estado de la configuración automática de mandos de cada sistema y el ajuste global."""
    _, _, config = leer_ajustes(raiz)
    datos = {k.casefold(): v for k, v in valores(config).items()}
    global_manual = datos.get(f"global.{CLAVE_AUTO}") == "1"
    estados = {}
    for identificador in identificadores:
        valor = datos.get(f"{identificador}.{CLAVE_AUTO}".casefold())
        if valor == "1":
            estados[identificador] = MANUAL
        elif valor == "0" or not global_manual:
            estados[identificador] = AUTOMATICO
        else:
            estados[identificador] = f"{MANUAL} (ajuste global)"
    return global_manual, estados


def juegos_manuales(raiz, identificador):
    """Juegos con su propio ajuste de mapeo manual (por ejemplo, los guardados por el editor de TeknoParrot)."""
    _, _, config = leer_ajustes(raiz)
    patron = re.compile(rf'{re.escape(identificador)}\["(.+)"\]\.{CLAVE_AUTO}', re.IGNORECASE)
    return sorted(m[1] for k, v in valores(config).items() if v == "1" and (m := patron.fullmatch(k)))


def fijar_autoconfiguracion(raiz, identificador, manual):
    """manual=True guarda «<sistema>.disableautocontrollers = 1»; False devuelve el control a RetroBat."""
    if not re.fullmatch(r"[a-z0-9_\-]+", identificador):
        raise ValueError(f"Sistema no válido: {identificador}")
    archivo, original, config = leer_ajustes(raiz)
    nombre = f"{identificador}.{CLAVE_AUTO}"
    if manual:
        cambiado = tc.actualizar_opcion(config, nombre, "1")
    else:
        nodos = [nodo for nodo in config if nodo.get("name", "").casefold() == nombre.casefold()]
        for nodo in nodos:
            config.remove(nodo)
        cambiado = bool(nodos)
    if not cambiado:
        return None
    nuevo = ET.tostring(config, encoding="utf-8", xml_declaration=True)
    return tc.guardar_cambios(raiz, [tc.Cambio(archivo, original, nuevo)], prefijo="autoconfiguracion-")
