"""Operaciones de archivos del gestor de RetroBat."""
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET


# Formatos autónomos que el importador puede copiar sin separar archivos asociados.
IMAGENES = {
    "ps2": {".iso", ".cso", ".chd"},
    "ps3": {".iso"},
    "psp": {".iso", ".cso", ".chd"},
    "gamecube": {".iso", ".gcm", ".gcz", ".rvz"},
    "xbox": {".iso", ".chd"},
    "xbox360": {".iso", ".zar", ".xcp"},
    "wii": {".iso", ".gcz", ".ciso", ".rvz", ".wia"},
    "wiiu": {".iso", ".wud", ".wua"},
}
CARPETAS = {"ps3": ".ps3"}


def sistemas_instalados(raiz):
    home = raiz / "emulationstation" / ".emulationstation"
    opciones = (home / "es_systems.cfg",
                raiz / "system" / "templates" / "emulationstation" / "es_systems.cfg")
    archivo = next((ruta for ruta in opciones if ruta.is_file()), None)
    if archivo is None:
        raise ValueError("No se encontró es_systems.cfg en esta instalación de RetroBat.")
    sistemas = {}
    for sistema in ET.parse(archivo).getroot().findall("system"):
        nombre = sistema.findtext("name", "").strip().lower()
        ruta = sistema.findtext("path", "").strip().replace("\\", "/").lower()
        extensiones = set(sistema.findtext("extension", "").lower().split())
        rutas_estandar = {f"~/../roms/{nombre}", f"roms/{nombre}",
                          (raiz / "roms" / nombre).as_posix().lower()}
        if ruta not in rutas_estandar:
            continue
        if nombre == "windows" and ".lnk" in extensiones:
            sistemas[nombre] = {".lnk"}
        elif nombre in IMAGENES:
            formatos = IMAGENES[nombre] | {CARPETAS.get(nombre, "")}
            if extensiones & formatos:
                sistemas[nombre] = extensiones & formatos
    return sistemas


def buscar_juegos(origen, sistema, extensiones):
    if not origen.is_dir():
        raise ValueError("Selecciona una carpeta de juegos válida.")
    juegos = []
    if sistema == "windows":
        # Admite juegos portátiles en la raíz y una subcarpeta por juego.
        for ruta in sorted(origen.iterdir()):
            if ruta.is_file() and ruta.suffix.lower() == ".exe":
                juegos.append((ruta.stem, [ruta]))
            elif ruta.is_dir():
                ejecutables = sorted(
                    p for p in ruta.rglob("*") if p.suffix.lower() == ".exe" and p.is_file()
                )
                if ejecutables:
                    juegos.append((ruta.name, ejecutables))
        return juegos

    sufijo_carpeta = CARPETAS.get(sistema)
    for carpeta, dirs, archivos in os.walk(origen):
        directorio = Path(carpeta)
        if sufijo_carpeta in extensiones and (
                directorio.suffix.lower() == sufijo_carpeta
                or (directorio / "PS3_GAME").is_dir()):
            ejecutable = directorio / "PS3_GAME" / "USRDIR" / "EBOOT.BIN"
            if ejecutable.is_file():
                nombre = (directorio.stem if directorio.suffix.lower() == sufijo_carpeta
                          else directorio.name)
                juegos.append((nombre, [directorio]))
            dirs.clear()
            continue
        for archivo in archivos:
            ruta = directorio / archivo
            if ruta.suffix.lower() in extensiones & IMAGENES[sistema]:
                juegos.append((ruta.stem, [ruta]))
    return sorted(juegos)


def nombre_seguro(nombre):
    if (not nombre or nombre.endswith((" ", ".")) or re.search(r'[<>:"/\\|?*\x00-\x1f]', nombre)
            or re.fullmatch(r"CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³]",
                            nombre.split(".")[0].rstrip(), re.IGNORECASE)):
        raise ValueError(f"Nombre de Windows inválido: {nombre!r}")
    return nombre


def publicar(nuevo, destino):
    """Publica un archivo preparado sin reemplazar un destino existente."""
    if os.name == "nt":
        nuevo.rename(destino)
    else:
        os.link(nuevo, destino)  # También permite verificar copias en Linux.


def publicar_directorio(nuevo, destino):
    if os.name != "nt":
        raise OSError("La instalación de carpetas requiere Windows.")
    nuevo.rename(destino)


def copiar(origen, destino):
    if destino.exists():
        raise FileExistsError(f"Ya existe: {destino}")
    if origen.is_dir() and destino.resolve().is_relative_to(origen.resolve()):
        raise ValueError("El destino está dentro de la carpeta de origen.")
    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destino.parent) as temporal:
        nuevo = Path(temporal) / destino.name
        if origen.is_dir():
            shutil.copytree(origen, nuevo)
            publicar_directorio(nuevo, destino)
        else:
            shutil.copy2(origen, nuevo)
            publicar(nuevo, destino)


def shortcut(ejecutable, destino):
    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destino.parent) as temporal:
        nuevo = Path(temporal) / destino.name
        env = dict(os.environ, TECNOTICS_EXE=str(ejecutable), TECNOTICS_LNK=str(nuevo))
        script = (
            "$ErrorActionPreference='Stop'; "
            "$shell=New-Object -ComObject WScript.Shell; "
            "$link=$shell.CreateShortcut($env:TECNOTICS_LNK); "
            "$link.TargetPath=$env:TECNOTICS_EXE; "
            "$link.WorkingDirectory=Split-Path -LiteralPath $env:TECNOTICS_EXE; "
            "$link.Save()"
        )
        subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                       check=True, env=env, capture_output=True, text=True,
                       creationflags=subprocess.CREATE_NO_WINDOW)
        publicar(nuevo, destino)


def duplicados(raiz, sistemas):
    nombres = {}
    tamanos = {}
    for sistema, extensiones in sistemas.items():
        for ruta in (raiz / "roms" / sistema).rglob("*"):
            if ruta.suffix.lower() not in extensiones:
                continue
            nombres.setdefault((sistema, ruta.name.casefold()), []).append(ruta)
            if ruta.is_file() and ruta.suffix.lower() != ".lnk":
                tamanos.setdefault(ruta.stat().st_size, []).append(ruta)

    for (_, nombre), rutas in nombres.items():
        if len(rutas) > 1:
            yield f"Nombre repetido: {nombre}"
            yield from map(str, rutas)
            yield ""

    huellas = {}
    for rutas in tamanos.values():
        if len(rutas) > 1:
            for ruta in rutas:
                with ruta.open("rb") as archivo:
                    huella = hashlib.file_digest(archivo, "sha256").digest()
                huellas.setdefault(huella, []).append(ruta)
    for rutas in huellas.values():
        if len(rutas) > 1:
            yield "Contenido idéntico:"
            yield from map(str, rutas)
            yield ""


def revisar_bios(raiz, manifiesto):
    base = (raiz / "bios").resolve()
    resultados = []
    for numero, linea in enumerate(manifiesto.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not linea.strip() or linea.lstrip().startswith("#"):
            continue
        partes = linea.split(maxsplit=1)
        if len(partes) != 2 or not re.fullmatch(r"[a-fA-F0-9]{32}", partes[0]):
            raise ValueError(f"Línea {numero}: usa MD5 seguido por la ruta relativa dentro de bios.")
        esperado, relativo = partes
        ruta = (base / relativo).resolve()
        if not ruta.is_relative_to(base):
            raise ValueError(f"Línea {numero}: ruta fuera de bios.")
        estado = "FALTA"
        if ruta.is_file():
            with ruta.open("rb") as archivo:
                obtenido = hashlib.file_digest(archivo, "md5").hexdigest()
            estado = "OK" if obtenido == esperado.lower() else "MD5 DISTINTO"
        resultados.append(f"{estado}: {relativo}")
    return resultados


def editar_ini(raiz, seccion, valores):
    # La API nativa conserva el formato y las claves ajenas de retrobat.ini.
    import ctypes
    ini = raiz / "retrobat.ini"
    escribir = ctypes.windll.kernel32.WritePrivateProfileStringW
    escribir.argtypes = [ctypes.c_wchar_p] * 4
    with tempfile.TemporaryDirectory(dir=raiz) as temporal:
        nuevo = Path(temporal) / ini.name
        if ini.is_file():
            with tempfile.NamedTemporaryFile(prefix="retrobat-", suffix=".ini.bak",
                                             dir=raiz, delete=False) as respaldo:
                nombre_respaldo = respaldo.name
            shutil.copy2(ini, nombre_respaldo)
            shutil.copy2(nombre_respaldo, nuevo)
        else:
            nuevo.write_text("", encoding="utf-16")
        for clave, valor in valores.items():
            if not escribir(seccion, clave, valor, str(nuevo)):
                raise OSError(f"No se pudo guardar [{seccion}] {clave} en {ini}.")
        escribir(None, None, None, str(nuevo))
        nuevo.replace(ini)
