"""Verifica y extrae juegos comprimidos en una carpeta temporal."""
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys

from gestor_core import nombre_seguro


@dataclass(frozen=True)
class Contenido:
    archivos: tuple[Path, ...]
    bytes: int


def siete_zip():
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "7zip" / "7z.exe"
    encontrado = shutil.which("7z") or shutil.which("7zz")
    if encontrado:
        return Path(encontrado)
    if sys.platform == "win32":
        return Path("C:/Program Files/7-Zip/7z.exe")
    raise ValueError("Para revisar archivos comprimidos desde el código fuente, instala 7-Zip.")


def ejecutar_7zip(*argumentos):
    ejecutable = siete_zip()
    if not ejecutable.is_file():
        raise ValueError("No se encontró 7-Zip para abrir los archivos comprimidos.")
    proceso = subprocess.run(
        [str(ejecutable), *argumentos], stdin=subprocess.DEVNULL, capture_output=True,
        encoding="utf-8", errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if proceso.returncode:
        detalle = proceso.stderr.strip() or proceso.stdout.strip()
        raise ValueError("7-Zip no pudo leer el archivo. " + detalle[-380:])
    return proceso.stdout


def inicio_archivado(archivo, ruta, cantidad):
    ejecutable = siete_zip()
    with subprocess.Popen(
        [str(ejecutable), "x", "-so", "-spd", "-sccUTF-8", "-p-", "--", str(archivo), str(ruta)],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    ) as proceso:
        try:
            return proceso.stdout.read(cantidad)
        finally:
            proceso.kill()


def inspeccionar(archivo):
    texto = ejecutar_7zip("l", "-slt", "-ba", "-sccUTF-8", "-p-", "--", str(archivo))
    archivos, nombres, total = [], set(), 0
    for bloque in re.split(r"\n\s*\n", texto.strip("\n")):
        campos = {}
        for linea in bloque.splitlines():
            clave, separador, valor = linea.partition(" = ")
            if not separador or clave in campos:
                raise ValueError("El archivo contiene un nombre o metadatos de entrada no válidos.")
            campos[clave] = valor
        nombre = campos.get("Path", "").replace("\\", "/")
        partes = PurePosixPath(nombre).parts
        if not partes or nombre.startswith("/") or "\ufffd" in nombre:
            raise ValueError(f"Ruta comprimida no válida: {nombre!r}")
        for parte in partes:
            nombre_seguro(parte)
        atributos = campos.get("Attributes", "").split()
        if (any(campos.get(clave, "") not in {"", "-"} for clave in
                ("Symbolic Link", "Hard Link", "Copy Link", "Reparse Point", "Alternate Stream"))
                or any(re.fullmatch(r"[lbcps][rwxstST-]{9}", x) for x in atributos)
                or any("L" in x for x in atributos if re.fullmatch(r"[A-Z_]+", x))):
            raise ValueError(f"El ZIP, 7z o RAR incluye un enlace o flujo no admitido: {nombre}")
        if campos.get("Encrypted") == "+":
            raise ValueError("El archivo comprimido está protegido con contraseña.")
        clave = "/".join(partes).casefold()
        if clave in nombres:
            raise ValueError(f"El archivo contiene rutas repetidas: {nombre}")
        nombres.add(clave)
        if campos.get("Folder") == "+" or any(x.startswith(("D", "d")) for x in atributos):
            continue
        tamanio = campos.get("Size", "")
        if not tamanio.isdecimal():
            raise ValueError(f"No se pudo verificar el tamaño de {nombre}.")
        total += int(tamanio)
        archivos.append(Path(*partes))
    if not archivos:
        raise ValueError("El archivo comprimido está vacío.")
    return Contenido(tuple(archivos), total)


def extraer(archivo, destino, contenido):
    if contenido.bytes > shutil.disk_usage(destino.parent).free:
        raise ValueError("No hay espacio libre suficiente para extraer el juego.")
    destino.mkdir()
    ejecutar_7zip("x", "-y", "-sccUTF-8", "-p-", "-o" + str(destino), "--", str(archivo))
    esperados = set(contenido.archivos)
    for ruta in destino.rglob("*"):
        if ruta.resolve() != ruta.absolute() or (not ruta.is_file() and not ruta.is_dir()):
            raise ValueError("La extracción contiene enlaces o rutas no válidas.")
        if ruta.is_file():
            esperado = ruta.relative_to(destino)
            if esperado not in esperados:
                raise ValueError(f"La extracción produjo un archivo inesperado: {esperado}")
            esperados.remove(esperado)
    if esperados:
        raise ValueError("La extracción no contiene todos los archivos del juego.")
