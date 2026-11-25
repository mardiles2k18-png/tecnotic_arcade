"""Fuentes públicas de metadatos y medios para la biblioteca del Gestor."""

import gzip
import io
import json
import re
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen

from gestor_teknoparrot_instalacion import contexto_tls

ARCADEITALIA = "https://adb.arcadeitalia.net"
LIBRETRO = "https://thumbnails.libretro.com"
ATRIBUCION_ARCADE = "Arcade Database de motoschifo (https://adb.arcadeitalia.net)"
SISTEMAS_LIBRETRO = {
    "atari2600": "Atari - 2600",
    "dreamcast": "Sega - Dreamcast",
    "gamegear": "Sega - Game Gear",
    "gb": "Nintendo - Game Boy",
    "gba": "Nintendo - Game Boy Advance",
    "gbc": "Nintendo - Game Boy Color",
    "genesis": "Sega - Mega Drive - Genesis",
    "mastersystem": "Sega - Master System - Mark III",
    "megadrive": "Sega - Mega Drive - Genesis",
    "n64": "Nintendo - Nintendo 64",
    "nes": "Nintendo - Nintendo Entertainment System",
    "psx": "Sony - PlayStation",
    "saturn": "Sega - Saturn",
    "snes": "Nintendo - Super Nintendo Entertainment System",
}


def categorias_disponibles(sistema):
    """Capacidades del proveedor, antes de buscar un juego concreto."""
    if sistema.startswith("mame") or sistema in {"arcade", "fba", "fbneo", "fbalpha", "hbmame", "neogeo"}:
        return frozenset({"cover", "info", "logo", "video", "cheats"})
    if sistema in SISTEMAS_LIBRETRO:
        return frozenset({"cover"})
    return frozenset()


def _consulta_arcade(codigo):
    parametros = urlencode({"ajax": "query_mame", "game_name": codigo, "lang": "en"})
    consulta = Request(f"{ARCADEITALIA}/service_scraper.php?{parametros}", headers={
        "User-Agent": "Gestor Arcade Tecnoticis", "Accept": "application/json",
    })
    with urlopen(consulta, timeout=15, context=contexto_tls()) as respuesta:
        if urlsplit(respuesta.geturl()).hostname != "adb.arcadeitalia.net":
            raise ValueError("Arcade Database redirigió la consulta fuera de su servidor.")
        datos = respuesta.read(2 * 1024 * 1024 + 1)
    if len(datos) > 2 * 1024 * 1024:
        raise ValueError("Arcade Database devolvió una respuesta demasiado grande.")
    try:
        if datos.startswith(b"\x1f\x8b"):
            with gzip.GzipFile(fileobj=io.BytesIO(datos)) as comprimido:
                datos = comprimido.read(2 * 1024 * 1024 + 1)
            if len(datos) > 2 * 1024 * 1024:
                raise ValueError("Arcade Database devolvió una ficha demasiado grande.")
        registros = json.loads(datos)["result"]
    except (ValueError, TypeError, KeyError, EOFError, OSError) as error:
        raise ValueError("Arcade Database devolvió una ficha ilegible.") from error
    if not isinstance(registros, list):
        raise ValueError("Arcade Database devolvió un resultado desconocido.")
    return next((ficha for ficha in registros if isinstance(ficha, dict) and ficha.get("game_name") == codigo), {})


def _recurso_arcade(ficha, campo):
    url = str(ficha.get(campo) or "")
    partes = urlsplit(url)
    if partes.scheme == "https" and partes.netloc == "adb.arcadeitalia.net":
        return url
    return ""


def _texto_con_atribucion(texto, ficha):
    credito = ficha.get("history_copyright_long") or ficha.get("history_copyright_short")
    return texto.strip() + "\n\n" + "\n".join(filter(None, (ATRIBUCION_ARCADE, credito)))


def buscar(sistema, codigo, titulo, categorias):
    """Devuelve (campos de catálogo, URLs de medios). Usa «trucos» para texto lateral."""
    categorias = set(categorias) & categorias_disponibles(sistema)
    if not categorias:
        return {}, {}
    if sistema in SISTEMAS_LIBRETRO:
        # El servidor indexa por nombre exacto de la ROM en su catálogo, conservando región.
        nombre = re.sub(r'[&*/:`<>?\\|]', "_", codigo).strip()
        coleccion = quote(SISTEMAS_LIBRETRO[sistema], safe="")
        if not nombre or nombre in {".", ".."}:
            return {}, {}
        return {}, {"thumbnail": f"{LIBRETRO}/{coleccion}/Named_Boxarts/{quote(nombre, safe='')}.png"}

    codigo = codigo.strip().lower()
    if not re.fullmatch(r"[a-z0-9_]{1,64}", codigo):
        return {}, {}
    ficha = _consulta_arcade(codigo)
    if not ficha:
        return {}, {}
    textos, medios = {}, {}
    historial = ficha.get("history") or ""
    if "info" in categorias:
        campos = {"name": "title", "publisher": "manufacturer", "genre": "genre", "players": "players"}
        textos.update({tag: str(ficha[clave]) for tag, clave in campos.items() if ficha.get(clave)})
        ano = str(ficha.get("year", ""))
        if re.fullmatch(r"[0-9]{4}", ano):
            textos["releasedate"] = ano + "0101T000000"
        if historial:
            introduccion = re.split(r"(?m)^- .+ -\s*$", historial, maxsplit=1)[0]
            if introduccion.strip():
                textos["desc"] = _texto_con_atribucion(introduccion, ficha)
    if "cheats" in categorias:
        trucos = re.search(r"(?im)^- TIPS AND TRICKS -\s*\n([\s\S]+?)(?=^- .+ -\s*$|\Z)", historial)
        if trucos and trucos[1].strip():
            textos["trucos"] = _texto_con_atribucion(trucos[1], ficha)
    for categoria, etiqueta, campo in (
        ("cover", "thumbnail", "url_image_flyer"),
        ("logo", "marquee", "url_image_marquee"),
        ("video", "video", "url_video_shortplay"),
    ):
        if categoria in categorias and (url := _recurso_arcade(ficha, campo)):
            medios[etiqueta] = url
    return textos, medios
