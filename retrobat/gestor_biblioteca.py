"""Edición de nombres y retirada de juegos instalados."""
import io
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

from gestor_core import destinos_accesos_windows, discos_mame, requiere_importacion_manual
from gestor_duplicados import guardar_respaldo, marca_archivo, restaurar_respaldo, validar_entrada


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


def plan_eliminar(raiz, entrada):
    validar_entrada(raiz, entrada)
    ruta = entrada.ruta
    rutas = [ruta]
    if entrada.sistema.identificador == "windows" and ruta.suffix.lower() == ".lnk":
        accesos = destinos_accesos_windows(entrada.sistema.carpeta)
        ejecutable = accesos.get(ruta)
        biblioteca = raiz.resolve() / "library" / "windows"
        if ejecutable is None or not ejecutable.is_relative_to(biblioteca):
            raise ValueError("Este acceso no apunta a un juego instalado en la biblioteca del gestor. "
                             "Para eliminarlo por completo, usa su desinstalador o revisa su carpeta de origen.")
        relativo = ejecutable.relative_to(biblioteca)
        paquete = biblioteca / relativo.parts[0]
        if len(relativo.parts) < 2 or not paquete.is_dir() or paquete.resolve() != paquete:
            raise ValueError("No se encontró una carpeta de juego administrada por el gestor.")
        if any(otro != ruta and objetivo is not None and objetivo.is_relative_to(paquete)
               for otro, objetivo in accesos.items()):
            raise ValueError("Otro acceso directo usa esta misma carpeta. Revísalo antes de eliminar el juego.")
        rutas.append(paquete)
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
    nodos = juegos.get(entrada.ruta, ())
    respaldo = guardar_respaldo(raiz, [ruta for ruta, _ in plan], mover=True, incluir_windows=True)
    if nodos:
        try:
            for nodo in nodos:
                lista.remove(nodo)
            guardar_catalogo(archivo, original, lista)
        except (OSError, ValueError):
            restaurar_respaldo(raiz, respaldo)
            raise
    return respaldo
