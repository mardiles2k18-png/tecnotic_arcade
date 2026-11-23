"""Consulta guías oficiales de TeknoParrot para identificar archivos de arranque."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import lru_cache
from html import unescape
import re
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request

import gestor_teknoparrot as tp
from gestor_teknoparrot_instalacion import abrir_https

COMPATIBILIDAD = "https://teknoparrot.com/en/Compatibility"
GENERADOR = "https://raw.githubusercontent.com/RetroBat-Official/emulatorlauncher/master/emulatorLauncher/Generators/TeknoParrot.generator.cs"
GENERADOR_WEB = "https://github.com/RetroBat-Official/emulatorlauncher/blob/master/emulatorLauncher/Generators/TeknoParrot.generator.cs"
LIMITE_TEXTO = 1024 * 1024


@dataclass(frozen=True)
class Guia:
    principal: frozenset[str] = frozenset()
    segundo: frozenset[str] = frozenset()
    referencias: frozenset[str] = frozenset()
    notas: tuple[str, ...] = ()
    estado: str = "La ficha no publica instrucciones de arranque."


def ficha_url(perfil):
    return f"{COMPATIBILIDAD}/GameDetail/{quote(perfil, safe='')}"


def leer_texto(url):
    with abrir_https(Request(url, headers={"User-Agent": "Tecnotics-Arcade"}), timeout=8) as respuesta:
        datos = respuesta.read(LIMITE_TEXTO + 1)
    if len(datos) > LIMITE_TEXTO:
        raise ValueError("La referencia oficial supera el tamaño esperado.")
    return datos.decode("utf-8-sig")


def analizar_guia(texto):
    seccion = texto.partition('id="setupAccordion"')[2].split("<!-- Issues Section -->", 1)[0]
    notas = tuple(dict.fromkeys(
        " ".join(unescape(re.sub(r"<[^>]+>", " ", contenido)).split())
        for contenido in re.findall(r"<(?:li|p)\b[^>]*>(.*?)</(?:li|p)>", seccion, flags=re.S)
    ))
    principal, segundo, referencias = set(), set(), set()
    for nota in notas:
        declaracion = re.match(r"(second(?:ary)?\s+)?executable\s+(?:is|file\s+is)\b", nota, re.I)
        if declaracion:
            nombres = [nombre for _, nombre in re.findall(r'''(["'])([^"']+)\1''', nota[declaracion.end():])]
            declarados = tp.nombres_ejecutables(";".join(nombres))
            if declaracion[1]:
                segundo.update(declarados)
            else:
                principal.update(declarados)
        else:
            referencias.update(ruta.casefold() for ruta in re.findall(
                r"(?<![\w.-])[\w-][\w.-]*\.(?:dll|key|bin|chd|elf|dat|ini|iso|exe)\b", nota, re.I))
    notas = tuple(nota[:450] for nota in notas if nota)
    estado = "Instrucciones oficiales de TeknoParrot encontradas." if notas else Guia().estado
    return Guia(frozenset(principal), frozenset(segundo), frozenset(referencias), notas, estado)


@lru_cache(maxsize=512)
def consultar_guia(perfil):
    try:
        return analizar_guia(leer_texto(ficha_url(perfil)))
    except HTTPError as error:
        if error.code == 404:
            return Guia(estado="TeknoParrot no tiene una ficha pública para este perfil.")
        raise


def guia_disponible(perfil):
    try:
        return consultar_guia(perfil)
    except (OSError, ValueError) as error:
        return Guia(estado=f"No se pudo consultar TeknoParrot en línea ({error}).")


@lru_cache(maxsize=1)
def ejecutables_generador():
    texto = leer_texto(GENERADOR)
    bloque = texto.partition("Dictionary<string, string> executables")[2].partition("};")[0]
    entradas = re.findall(r'''\{\s*"([\w.-]+)"\s*,\s*@"([^"\r\n]+)"\s*\}''', bloque)
    if not entradas:
        raise ValueError("RetroBat no publicó la tabla de ejecutables en el formato esperado.")
    return {perfil.casefold(): tp.nombres_ejecutables(ruta) for perfil, ruta in entradas}


def revisar_en_linea(juegos, *, diagnosticar=False):
    elegidos = [juego for juego in juegos if juego.perfil and not juego.error
                and (diagnosticar or tp.problema_arranque(juego))]
    if not elegidos:
        return {}, ""
    ids = list(dict.fromkeys(juego.perfil.id for juego in elegidos))
    with ThreadPoolExecutor(max_workers=6) as executor:
        guias = dict(zip(ids, executor.map(guia_disponible, ids)))
    for juego in elegidos:
        guia = guias[juego.perfil.id]
        tp.buscar_arranque(juego, guia.principal, guia.segundo)
    pendientes = [juego for juego in elegidos if juego.ejecutable is None]
    if not pendientes:
        return guias, ""
    try:
        generador = ejecutables_generador()
    except (OSError, ValueError) as error:
        return guias, f"No se pudo consultar RetroBat en línea ({error})."
    for juego in pendientes:
        alternativos = generador.get(juego.perfil.id.casefold(), frozenset())
        guia = guias[juego.perfil.id]
        if alternativos - guia.principal - juego.perfil.esperado:
            tp.buscar_arranque(juego, guia.principal | alternativos, guia.segundo)
    return guias, "Se consultó la tabla de ejecutables de RetroBat."


def lineas_diagnostico(juego, problema, guia, consulta_generador):
    lineas = [juego.origen.name, f"Ubicación · {juego.origen}", f"Estado · {problema or 'Listo para importar'}"]
    if juego.error:
        return [*lineas, juego.error]
    if juego.perfil is None:
        return [*lineas, "Elige el perfil de la edición en la lista para poder consultar su guía."]

    def ruta_visible(ruta):
        return ruta if juego.contenido is not None else ruta.relative_to(juego.origen)

    lineas.append(f"Perfil · {juego.perfil.titulo} [{juego.perfil.id}]")
    for revision in juego.revision:
        lineas.extend(("", f"{revision.etiqueta} · " + (
            " / ".join(sorted(revision.esperados)) if revision.esperados else "Nombre sin confirmar en el catálogo")))
        if revision.elegido:
            lineas.append(f"  Seleccionado · {ruta_visible(revision.elegido)}")
        elif revision.coincidencias:
            lineas.append("  Hay varias coincidencias. Elige la ruta correspondiente a esta edición.")
            lineas.extend(f"  • {ruta_visible(ruta)}" for ruta in sorted(revision.coincidencias))
        elif revision.esperados:
            lineas.append("  No hay una coincidencia válida en la carpeta o el archivo comprimido.")
    archivos = tp.archivos_juego(juego)
    if tp.problema_arranque(juego):
        candidatos = sorted(ruta for ruta in archivos if ruta.suffix.lower() in tp.BINARIOS or not ruta.suffix)
        if candidatos:
            lineas.extend(("", "Otros archivos para revisar manualmente"))
            lineas.extend(f"  • {ruta_visible(ruta)}" for ruta in candidatos[:12])
            if len(candidatos) > 12:
                lineas.append(f"  Y {len(candidatos) - 12} más.")
        else:
            lineas.append("No se detectaron otros archivos de arranque habituales.")
    if guia:
        lineas.extend(("", guia.estado))
        if guia.notas:
            lineas.extend(f"  • {nota}" for nota in guia.notas[:10])
        ausentes = guia.referencias - {ruta.name.casefold() for ruta in archivos}
        if ausentes:
            lineas.append("Archivos mencionados en la guía y ausentes del origen · " + ", ".join(sorted(ausentes)))
            lineas.append("Consulta la guía para comprobar cuáles corresponden a tu edición o configuración.")
    if consulta_generador:
        lineas.append(consulta_generador)
    lineas.append("El diagnóstico revisa los archivos publicados en los perfiles y guías. El arranque real se comprueba en RetroBat.")
    return lineas
