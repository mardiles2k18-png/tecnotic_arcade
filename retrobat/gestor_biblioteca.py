"""Edición de nombres y retirada de juegos instalados."""
import io
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

from gestor_core import CARPETAS_MULTIMEDIA, destinos_accesos_windows, discos_mame, requiere_importacion_manual
from gestor_duplicados import clave_titulo, guardar_respaldo, marca_archivo, restaurar_respaldo, validar_entrada


def catalogo_juegos(sistema):
    archivo = sistema.carpeta / "gamelist.xml"
    if archivo.is_symlink():
        raise ValueError("El catálogo es un enlace a otro archivo.")
    original = archivo.read_bytes() if archivo.exists() else None
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True, insert_pis=True))
    lista = ET.fromstring(original, parser=parser) if original is not None else ET.Element("gameList")
    if lista.tag != "gameList":
        raise ValueError("gamelist.xml no contiene una lista de juegos.")
    juegos = {}
    for nodo in lista.findall("game") + lista.findall("folder"):
        texto = nodo.findtext("path", "").strip().replace("\\", "/")
        if texto:
            ruta = sistema.carpeta / texto
            # Las rutas con .. pueden aparecer en metadatos antiguos.
            if ".." in ruta.parts:
                ruta = ruta.resolve()
            juegos.setdefault(ruta, []).append(nodo)
    return archivo, original, lista, juegos


def guardar_catalogo(archivo, original, lista):
    actual = archivo.read_bytes() if archivo.exists() else None
    if actual != original or archivo.is_symlink():
        raise ValueError("RetroBat modificó el catálogo. Actualiza la biblioteca e inténtalo de nuevo.")
    buffer = io.BytesIO()
    ET.ElementTree(lista).write(buffer, encoding="utf-8", xml_declaration=True)
    with tempfile.TemporaryDirectory(dir=archivo.parent) as temporal:
        preparado = Path(temporal) / archivo.name
        preparado.write_bytes(buffer.getvalue())
        preparado.replace(archivo)


def editar_nombre(raiz, entrada, nombre):
    nombre = nombre.strip()
    if not nombre or any(ord(caracter) < 32 for caracter in nombre):
        raise ValueError("Escribe un nombre válido.")
    validar_entrada(raiz, entrada)
    archivo, original, lista, juegos = catalogo_juegos(entrada.sistema)
    nodos = juegos.get(entrada.ruta)
    if not nodos:
        nodo = ET.SubElement(lista, "game")
        ET.SubElement(nodo, "path").text = "./" + entrada.ruta.relative_to(entrada.sistema.carpeta).as_posix()
        nodos = [nodo]
    for nodo in nodos:
        etiqueta = nodo.find("name")
        if etiqueta is None:
            etiqueta = ET.SubElement(nodo, "name")
        etiqueta.text = nombre
    guardar_catalogo(archivo, original, lista)
    return nombre


def archivos_windows(raiz, entrada):
    ruta = entrada.ruta
    accesos = destinos_accesos_windows(entrada.sistema.carpeta)
    es_acceso = ruta.suffix.lower() == ".lnk"
    objetivo = accesos.get(ruta) if es_acceso else ruta
    if objetivo is None:
        return [ruta]

    biblioteca = raiz.resolve() / "library" / "windows"
    roms = entrada.sistema.carpeta.resolve()
    if objetivo.is_relative_to(biblioteca):
        partes = objetivo.relative_to(biblioteca).parts
        paquete = biblioteca / partes[0] if len(partes) > 1 else None
    elif objetivo.is_relative_to(roms):
        paquete = objetivo
        if objetivo.is_file():
            nombre = clave_titulo(ruta.stem)
            for carpeta in objetivo.parents:
                if carpeta == roms:
                    break
                if carpeta.suffix.lower() in {".pc", ".win", ".windows"} or clave_titulo(carpeta.name) == nombre:
                    paquete = carpeta
                    break
        if any(parte.casefold() in CARPETAS_MULTIMEDIA
               for parte in paquete.relative_to(roms).parts):
            return [ruta]
    else:
        # Se puede retirar el acceso sin alterar una instalación externa.
        return [ruta]

    if paquete is None:
        return [ruta]
    if any(otro != ruta and (otro.is_relative_to(paquete) or
                             (destino is not None and destino.is_relative_to(paquete)))
           for otro, destino in accesos.items()):
        if es_acceso:
            return [ruta]
        raise ValueError("Otro acceso directo usa estos archivos. Retira primero el acceso compartido.")
    return [paquete] if ruta.is_relative_to(paquete) else [ruta, paquete]


def plan_eliminar(raiz, entrada):
    validar_entrada(raiz, entrada)
    ruta = entrada.ruta
    rutas = [ruta]
    if entrada.sistema.identificador == "windows" and (
            ruta.is_dir() or ruta.suffix.lower() in {".exe", ".lnk"}):
        rutas = archivos_windows(raiz, entrada)
    elif requiere_importacion_manual(ruta):
        raise ValueError("Este juego utiliza un formato con archivos asociados. Debe eliminarse manualmente.")
    elif entrada.sistema.es_mame and ruta.suffix.lower() in {".zip", ".7z"}:
        for otra in (ruta.with_suffix(".zip"), ruta.with_suffix(".7z")):
            if otra != ruta and otra.exists() and discos_mame(ruta):
                raise ValueError("Otra ROM usa la misma carpeta de discos. Revísala antes de eliminar el juego.")
        rutas.extend(discos_mame(ruta))
    return tuple((archivo, marca_archivo(archivo)) for archivo in rutas)


def eliminar_juego(raiz, entrada, plan):
    if plan_eliminar(raiz, entrada) != plan:
        raise ValueError("Los archivos cambiaron. Vuelve a revisar el juego.")
    archivo, original, lista, juegos = catalogo_juegos(entrada.sistema)
    rutas = [ruta for ruta, _ in plan]
    nodos = [nodo for ruta, entradas in juegos.items()
             if any(ruta.is_relative_to(retirada) for retirada in rutas) for nodo in entradas]
    respaldo = guardar_respaldo(raiz, rutas, mover=True, incluir_windows=True)
    if nodos:
        try:
            for nodo in nodos:
                lista.remove(nodo)
            guardar_catalogo(archivo, original, lista)
        except (OSError, ValueError):
            restaurar_respaldo(raiz, respaldo)
            raise
    return respaldo
