"""Intercambio de temas instalados en RetroBat."""
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import stat
import tempfile
import xml.etree.ElementTree as ET
import zipfile

from gestor_core import nombre_seguro, publicar
from gestor_teknoparrot_pantalla import leer_ajustes


@dataclass(frozen=True)
class Tema:
    nombre: str
    activo: bool


def _enlace(estado):
    return stat.S_ISLNK(estado.st_mode) or bool(
        getattr(estado, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    )


def _carpeta_local(raiz, *partes):
    carpeta = Path(raiz).resolve()
    for parte in partes:
        carpeta /= parte
        try:
            estado = carpeta.lstat()
        except FileNotFoundError:
            continue
        if _enlace(estado) or not stat.S_ISDIR(estado.st_mode):
            raise ValueError(f"No se puede usar la carpeta {carpeta}.")
    return carpeta


def _carpeta_temas(raiz):
    return _carpeta_local(raiz, "emulationstation", ".emulationstation", "themes")


def _carpeta_real(carpeta):
    try:
        estado = carpeta.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISDIR(estado.st_mode) and not _enlace(estado)


def _xml_tema(carpeta):
    archivo = carpeta / "theme.xml"
    try:
        estado = archivo.lstat()
    except FileNotFoundError:
        return None
    if stat.S_ISREG(estado.st_mode) and not _enlace(estado):
        return archivo
    return None


def _archivos_tema(carpeta):
    defecto = _xml_tema(carpeta)
    if defecto is not None:
        return [defecto]
    return [archivo for sistema in carpeta.iterdir() if _carpeta_real(sistema)
            if (archivo := _xml_tema(sistema)) is not None]


def _nombres_instalados(carpeta):
    if not carpeta.is_dir():
        return []
    return sorted(
        (ruta.name for ruta in carpeta.iterdir() if not ruta.name.startswith(".")
         and _carpeta_real(ruta) and _archivos_tema(ruta)),
        key=str.casefold,
    )


def _tema_activo(raiz, nombres):
    _, _, ajustes = leer_ajustes(Path(raiz))
    nodos = ajustes.findall("string[@name='ThemeSet']")
    nombre = nodos[-1].get("value", "") if nodos else ""
    nombres_es = {Path(tema).stem for tema in nombres}
    if nombre.casefold() in {tema.casefold() for tema in nombres_es}:
        return nombre.casefold()
    return min(nombres_es, default="").casefold()


def listar_temas(raiz):
    nombres = _nombres_instalados(_carpeta_temas(raiz))
    activo = _tema_activo(raiz, nombres)
    return tuple(Tema(nombre, Path(nombre).stem.casefold() == activo) for nombre in nombres)


def _nombre_tema(nombre):
    if nombre.startswith("."):
        raise ValueError("El nombre del tema no puede comenzar con un punto.")
    return nombre_seguro(nombre)


def _tema_instalado(raiz, nombre):
    carpeta = _carpeta_temas(raiz)
    ruta = carpeta / _nombre_tema(nombre)
    if not _carpeta_real(ruta) or not _archivos_tema(ruta):
        raise ValueError(f"No se encontró un tema instalado con el nombre {nombre}.")
    return ruta


def _agregar_carpeta(zip_salida, carpeta, prefijo):
    zip_salida.write(carpeta, prefijo)
    for ruta in carpeta.iterdir():
        estado = ruta.lstat()
        nombre = f"{prefijo}/{nombre_seguro(ruta.name)}"
        if _enlace(estado):
            raise ValueError(f"El tema contiene un enlace: {ruta.name}.")
        if stat.S_ISDIR(estado.st_mode):
            _agregar_carpeta(zip_salida, ruta, nombre)
        elif stat.S_ISREG(estado.st_mode):
            zip_salida.write(ruta, nombre)
        else:
            raise ValueError(f"El tema contiene un archivo no compatible: {ruta.name}.")


def exportar_tema(raiz, nombre, archivo_zip):
    origen = _tema_instalado(raiz, nombre)
    destino = Path(archivo_zip).absolute()
    if destino.exists() or destino.is_symlink():
        raise FileExistsError(f"Ya existe un archivo en {destino}.")
    if destino.resolve().is_relative_to(origen.resolve()):
        raise ValueError("Guarda el ZIP fuera de la carpeta del tema.")
    with tempfile.TemporaryDirectory(dir=destino.parent) as carpeta:
        temporal = Path(carpeta) / "tema.zip"
        with zipfile.ZipFile(temporal, "w", compression=zipfile.ZIP_DEFLATED) as comprimido:
            _agregar_carpeta(comprimido, origen, origen.name)
        publicar(temporal, destino)
    return destino


def _entradas_zip(comprimido):
    entradas = []
    rutas = {}
    for entrada in comprimido.infolist():
        nombre = entrada.orig_filename.removesuffix("/") if entrada.is_dir() else entrada.orig_filename
        partes = tuple(nombre_seguro(parte) for parte in nombre.split("/"))
        modo = stat.S_IFMT(entrada.external_attr >> 16)
        if modo not in {0, stat.S_IFREG, stat.S_IFDIR} or entrada.flag_bits & 1:
            raise ValueError("El ZIP contiene enlaces, archivos especiales o archivos cifrados.")
        for longitud in range(1, len(partes) + 1):
            prefijo = partes[:longitud]
            directorio = longitud < len(partes) or entrada.is_dir()
            clave = tuple(parte.casefold() for parte in prefijo)
            anterior = rutas.setdefault(clave, (prefijo, directorio))
            if anterior != (prefijo, directorio):
                raise ValueError("El ZIP contiene nombres de archivo incompatibles entre sí.")
        entradas.append((entrada, partes))
    if len({partes for _, partes in entradas}) != len(entradas):
        raise ValueError("El ZIP contiene archivos duplicados.")
    return entradas


def _extraer(comprimido, entradas, carpeta):
    for entrada, partes in entradas:
        ruta = carpeta.joinpath(*partes)
        if entrada.is_dir():
            ruta.mkdir(parents=True, exist_ok=True)
        else:
            ruta.parent.mkdir(parents=True, exist_ok=True)
            with comprimido.open(entrada) as contenido, ruta.open("xb") as salida:
                shutil.copyfileobj(contenido, salida)


def _tema_extraido(carpeta):
    elementos = list(carpeta.iterdir())
    if len(elementos) == 1 and elementos[0].is_dir() and _archivos_tema(elementos[0]):
        return elementos[0]
    return carpeta


def _validar_tema(carpeta):
    archivos = _archivos_tema(carpeta)
    if not archivos:
        raise ValueError("El ZIP no contiene un theme.xml de EmulationStation.")
    for archivo in archivos:
        try:
            valido = ET.parse(archivo).getroot().tag == "theme"
        except ET.ParseError:
            valido = False
        if not valido:
            raise ValueError(f"El archivo {archivo.parent.name}/theme.xml no es un tema válido.")


def importar_tema(raiz, archivo_zip, nombre=None):
    themes = _carpeta_temas(raiz)
    archivo_zip = Path(archivo_zip)
    themes.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(dir=themes.parent) as temporal:
            extraido = Path(temporal) / "contenido"
            extraido.mkdir()
            with zipfile.ZipFile(archivo_zip) as comprimido:
                _extraer(comprimido, _entradas_zip(comprimido), extraido)
            origen = _tema_extraido(extraido)
            _validar_tema(origen)
            nombre_original = archivo_zip.stem if origen == extraido else origen.name
            nombre_destino = _nombre_tema(nombre_original if nombre is None else nombre)
            themes.mkdir(exist_ok=True)
            destino = themes / nombre_destino
            identificador = destino.stem.casefold()
            if any(ruta.name.casefold() == nombre_destino.casefold()
                   or (_carpeta_real(ruta) and ruta.stem.casefold() == identificador)
                   for ruta in themes.iterdir()):
                raise FileExistsError(f"Ya existe un tema con el nombre {nombre_destino}.")
            origen.rename(destino)
    except (zipfile.BadZipFile, NotImplementedError) as error:
        raise ValueError("El archivo ZIP está dañado o usa una compresión incompatible.") from error
    return destino


def eliminar_tema(raiz, nombre):
    origen = _tema_instalado(raiz, nombre)
    nombres = _nombres_instalados(origen.parent)
    if origen.stem.casefold() == _tema_activo(raiz, nombres):
        raise ValueError("El tema está activo. Elige otro tema en RetroBat antes de eliminarlo.")
    respaldos = _carpeta_local(raiz, "user", "tecnotics-gestor", "temas-retirados")
    respaldos.mkdir(parents=True, exist_ok=True)
    carpeta = Path(tempfile.mkdtemp(dir=respaldos))
    destino = carpeta / origen.name
    try:
        origen.rename(destino)
    except OSError:
        carpeta.rmdir()
        raise
    return destino
