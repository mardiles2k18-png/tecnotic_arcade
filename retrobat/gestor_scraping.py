"""Completa los medios faltantes del catálogo de RetroBat."""

from pathlib import Path
import shutil
from urllib.parse import urlsplit
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from tempfile import TemporaryDirectory, NamedTemporaryFile
import xml.etree.ElementTree as ET

from gestor_biblioteca import catalogo_juegos, guardar_catalogo
from gestor_duplicados import guardar_respaldo, validar_entrada
from gestor_teknoparrot_instalacion import contexto_tls
from gestor_scraping_proveedor import buscar, categorias_disponibles

TEXTOS = ("name", "desc", "releasedate", "developer", "publisher", "genre", "players", "rating")
IMAGENES = {"image", "thumbnail", "marquee", "fanart", "boxback", "wheel"}
MEDIOS = (*sorted(IMAGENES), "video", "manual")
EXTENSIONES = {
    **dict.fromkeys(IMAGENES, {".png", ".jpg", ".jpeg", ".webp"}),
    "video": {".mp4", ".webm"},
    "manual": {".pdf"},
}


def aplicar_exportacion(raiz, entradas, temporal):
    if not entradas:
        return 0
    sistema = entradas[0].sistema
    elegidos = {entrada.ruta: entrada for entrada in entradas}
    for entrada in entradas:
        if entrada.sistema != sistema:
            raise ValueError("Selecciona juegos de un solo sistema.")
        validar_entrada(raiz, entrada)
    salida = ET.parse(temporal / "gamelist.xml").getroot()
    if salida.tag != "gameList":
        raise ValueError("Skyscraper generó un catálogo desconocido.")
    archivo, original, lista, existentes = catalogo_juegos(sistema)
    creados = []
    cambios = 0
    destino = sistema.carpeta / "media" / "tecnotics"
    try:
        for resultado in salida.findall("game"):
            juego = (sistema.carpeta / resultado.findtext("path", "").replace("\\", "/")).resolve()
            if juego not in elegidos:
                continue
            nodos = existentes.get(juego)
            if nodos is None:
                nodo = ET.Element("game")
                ET.SubElement(nodo, "path").text = "./" + juego.relative_to(sistema.carpeta).as_posix()
                nodos = existentes[juego] = [nodo]
            cambio = False
            for etiqueta in (*TEXTOS, *MEDIOS):
                valor = resultado.findtext(etiqueta, "").strip()
                faltantes = [nodo for nodo in nodos if not nodo.findtext(etiqueta, "").strip()]
                if not valor or not faltantes:
                    continue
                if etiqueta in EXTENSIONES:
                    origen = (temporal / valor.replace("\\", "/")).resolve()
                    extension = origen.suffix.lower()
                    if (not origen.is_relative_to(temporal.resolve())
                            or extension not in EXTENSIONES[etiqueta] or not origen.is_file()
                            or origen.stat().st_size == 0):
                        continue
                    if destino.resolve() != destino.absolute():
                        raise ValueError("La carpeta de medios apunta fuera de su ubicación original.")
                    destino.mkdir(parents=True, exist_ok=True)
                    with NamedTemporaryFile(dir=destino, prefix=f"{etiqueta}-",
                                            suffix=extension, delete=False) as medio:
                        ruta = Path(medio.name)
                        creados.append(ruta)
                        with origen.open("rb") as datos:
                            shutil.copyfileobj(datos, medio)
                    valor = "./" + ruta.relative_to(sistema.carpeta).as_posix()
                for nodo in faltantes:
                    campo = nodo.find(etiqueta)
                    if campo is None:
                        campo = ET.SubElement(nodo, etiqueta)
                    campo.text = valor
                cambio = True
            if cambio:
                for nodo in nodos:
                    if nodo not in lista:
                        lista.append(nodo)
                cambios += 1
        if cambios:
            if original is not None:
                guardar_respaldo(raiz, [archivo], mover=False)
            guardar_catalogo(archivo, original, lista)
    except Exception:
        for ruta in creados:
            ruta.unlink(missing_ok=True)
        raise
    return cambios


CAMPOS = {
    "cover": {"thumbnail"}, "info": set(TEXTOS), "logo": {"marquee"},
    "video": {"video"}, "cheats": {"trucos"},
}
ORIGENES = {"adb.arcadeitalia.net", "thumbnails.libretro.com"}
FORMATOS = {
    "image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp",
    "video/mp4": ".mp4", "video/webm": ".webm",
}


def descargar_medio(url, etiqueta, destino):
    def oficial(ruta):
        partes = urlsplit(ruta)
        return partes.scheme == "https" and partes.hostname in ORIGENES and partes.port in (None, 443)

    if not oficial(url):
        raise ValueError("El medio apunta a un proveedor desconocido.")
    peticion = Request(url, headers={"User-Agent": "Gestor-Arcade-Tecnoticis"})
    with urlopen(peticion, timeout=20, context=contexto_tls()) as respuesta:
        extension = FORMATOS.get(respuesta.headers.get_content_type())
        if not oficial(respuesta.geturl()) or extension not in EXTENSIONES[etiqueta]:
            raise ValueError("El proveedor devolvió un formato inesperado.")
        archivo = destino.with_suffix(extension)
        limite = 128 * 1024 * 1024 if etiqueta == "video" else 16 * 1024 * 1024
        total = 0
        with archivo.open("xb") as salida:
            while bloque := respuesta.read(256 * 1024):
                total += len(bloque)
                if total > limite:
                    raise ValueError("El archivo supera el límite de descarga.")
                salida.write(bloque)
        if not total:
            raise ValueError("El proveedor devolvió un archivo vacío.")
        return archivo


def falta_texto(nodos, etiqueta):
    return not nodos or any(not nodo.findtext(etiqueta, "").strip() for nodo in nodos)


def ruta_trucos(entrada):
    nombre = entrada.ruta.relative_to(entrada.sistema.carpeta)
    base = entrada.sistema.carpeta / "media" / "tecnotics" / "trucos"
    return base / nombre.parent / (nombre.name + ".txt")


def buscar_medios(raiz, entradas, categorias, informar=None):
    resultado = {"actualizados": 0, "sin_resultado": 0, "avisos": [], "sin_cambios": 0}
    if not entradas:
        return resultado
    sistema = entradas[0].sistema
    categorias = set(categorias) & categorias_disponibles(sistema.identificador)
    etiquetas = set().union(*(CAMPOS[categoria] for categoria in categorias))
    if not etiquetas:
        raise ValueError("Elige un tipo de contenido disponible para este sistema.")
    for entrada in entradas:
        if entrada.sistema != sistema:
            raise ValueError("Selecciona juegos de un solo sistema.")
        validar_entrada(raiz, entrada)
    _, _, _, existentes = catalogo_juegos(sistema)
    avisos = resultado["avisos"]
    trucos = []
    actualizados = set()
    with TemporaryDirectory(prefix="tecnotics-scraping-") as carpeta:
        temporal = Path(carpeta).resolve()
        lista = ET.Element("gameList")
        for indice, entrada in enumerate(entradas):
            if informar:
                informar(indice, len(entradas), f"Buscando · {entrada.ruta.stem}")
            nodos = existentes.get(entrada.ruta, ())
            faltantes = {e for e in etiquetas - {"trucos"} if falta_texto(nodos, e)}
            if "trucos" in etiquetas and not ruta_trucos(entrada).exists():
                faltantes.add("trucos")
            if not faltantes:
                resultado["sin_cambios"] += 1
                continue
            titulo = next((n.findtext("name") for n in nodos if n.findtext("name")), entrada.ruta.stem)
            tipos = {tipo for tipo, campos in CAMPOS.items() if faltantes & campos}
            try:
                textos, medios = buscar(sistema.identificador, entrada.ruta.stem, titulo, tipos)
            except (OSError, ValueError) as error:
                avisos.append(f"{entrada.ruta.name}: consulta fallida ({getattr(error, 'code', type(error).__name__)}).")
                if isinstance(error, HTTPError) and error.code in (403, 429, 503):
                    avisos.append("El proveedor rechazó nuevas consultas. Se pausó la búsqueda.")
                    break
                continue
            nodo = ET.Element("game")
            ET.SubElement(nodo, "path").text = "./" + entrada.ruta.relative_to(sistema.carpeta).as_posix()
            for etiqueta, valor in textos.items():
                if etiqueta in faltantes and etiqueta in TEXTOS and valor:
                    ET.SubElement(nodo, etiqueta).text = valor
            fallo_descarga = False
            for etiqueta, url in medios.items():
                if etiqueta not in faltantes or etiqueta not in EXTENSIONES:
                    continue
                try:
                    ruta = descargar_medio(url, etiqueta, temporal / f"{indice}-{etiqueta}")
                except HTTPError as error:
                    if error.code != 404:
                        fallo_descarga = True
                        avisos.append(f"{entrada.ruta.name}: {etiqueta} no disponible (HTTP {error.code}).")
                    continue
                except (OSError, ValueError):
                    fallo_descarga = True
                    avisos.append(f"{entrada.ruta.name}: no se pudo descargar {etiqueta}.")
                    continue
                ET.SubElement(nodo, etiqueta).text = ruta.name
            if len(nodo) > 1:
                lista.append(nodo)
                actualizados.add(entrada.ruta)
            if "trucos" in faltantes and (consejos := textos.get("trucos")):
                trucos.append((entrada, consejos))
            elif len(nodo) == 1 and not fallo_descarga:
                resultado["sin_resultado"] += 1
        if informar:
            informar(len(entradas), len(entradas), "Guardando en RetroBat")
        if len(lista):
            ET.ElementTree(lista).write(temporal / "gamelist.xml", encoding="utf-8", xml_declaration=True)
            if not aplicar_exportacion(raiz, entradas, temporal):
                actualizados.clear()
        for entrada, consejos in trucos:
            ruta = ruta_trucos(entrada)
            try:
                if ruta.resolve() != ruta.absolute():
                    raise ValueError("Ruta de trucos no válida.")
                ruta.parent.mkdir(parents=True, exist_ok=True)
                with ruta.open("x", encoding="utf-8") as archivo:
                    archivo.write(consejos)
                actualizados.add(entrada.ruta)
            except FileExistsError:
                continue
            except (OSError, ValueError):
                avisos.append(f"{entrada.ruta.name}: no se pudieron guardar los trucos.")
    resultado["actualizados"] = len(actualizados)
    return resultado