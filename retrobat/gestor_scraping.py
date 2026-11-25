"""Importa al catálogo de RetroBat recursos preparados por Skyscraper."""

from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory, NamedTemporaryFile
import xml.etree.ElementTree as ET

from gestor_biblioteca import catalogo_juegos, guardar_catalogo
from gestor_duplicados import guardar_respaldo, validar_entrada

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


def buscar_medios(raiz, entradas, ejecutable, configuracion=None):
    if not entradas:
        return 0
    sistema = entradas[0].sistema
    plataforma = "arcade" if sistema.es_mame or sistema.identificador == "fbneo" else sistema.identificador
    for entrada in entradas:
        if entrada.sistema != sistema:
            raise ValueError("Selecciona juegos de un solo sistema.")
        validar_entrada(raiz, entrada)
    with TemporaryDirectory(prefix="tecnotics-scraping-") as carpeta:
        temporal = Path(carpeta).resolve()
        archivos = temporal / "juegos.txt"
        archivos.write_text("".join(f"{e.ruta.as_posix()}\n" for e in entradas), encoding="utf-8")
        argumentos = [str(ejecutable), "-p", plataforma, "-f", "retrobat", "-i", str(sistema.carpeta),
                      "-g", str(temporal), "-o", str(temporal / "media"), "-t", "1",
                      "--includefrom", str(archivos), "--flags", "videos,unattend,skipped"]
        if configuracion:
            argumentos.extend(("-c", str(configuracion)))
        for fase, extra in (("descarga", ["-s", "screenscraper"]), ("exportación", [])):
            try:
                proceso = subprocess.run(argumentos + extra, cwd=temporal, stdin=subprocess.DEVNULL,
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                                         timeout=3600, check=False)
            except subprocess.TimeoutExpired as error:
                raise ValueError(f"Skyscraper agotó el tiempo de {fase}.") from error
            if proceso.returncode:
                raise ValueError(f"Falló la {fase} en Skyscraper (código {proceso.returncode}). "
                                 "Comprueba el sistema, las credenciales de ScreenScraper y la cuota.")
        if not (temporal / "gamelist.xml").is_file():
            return 0
        return aplicar_exportacion(raiz, entradas, temporal)
