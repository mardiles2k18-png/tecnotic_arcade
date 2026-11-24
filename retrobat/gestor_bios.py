"""Versiones de RetroBat, requisitos de BIOS y copia de archivos verificados."""

from dataclasses import dataclass, replace
import hashlib
import json
import mmap
from pathlib import Path
import os
import re
import tempfile
import xml.etree.ElementTree as ET
from urllib.error import URLError
from urllib.parse import quote, urlencode
from urllib.request import urlopen
from zipfile import BadZipFile, ZipFile

from gestor_biblioteca import catalogo_juegos
from gestor_core import (CARPETAS_MULTIMEDIA, FIRMWARE_PS3_SHA256, catalogo_bios, copiar_archivo, publicar,
                         rutas_bios_sistema)

GUIA_BIOS = "https://wiki.retrobat.org/get-started/adding-bios-files"
MAME_GUIA = "https://wiki.retrobat.org/systems-and-emulators/supported-game-systems/arcade/mame"
FBNEO_GUIA = "https://wiki.retrobat.org/systems-and-emulators/supported-game-systems/arcade/final-burn-neo"
BIOS_OFICIALES = "https://github.com/RetroBat-Official/retrobat-bios"
API_BIOS = "https://api.github.com/repos/RetroBat-Official/retrobat-bios/git/trees/main?recursive=1"
RELEASES_RETROBAT = "https://github.com/RetroBat-Official/retrobat/releases/latest"
NO_REQUIERE_BIOS = {"windows", "psp", "teknoparrot"}
SONY_PS3 = "https://www.playstation.com/es-cl/support/hardware/ps3/system-software/"


@dataclass(frozen=True)
class ArchivoBios:
    destino: Path
    estado: str
    juegos: int = 0
    md5: tuple[str, ...] = ()
    sha256: str = ""
    miembros_zip: tuple[tuple[int, str], ...] = ()
    url: str = ""

    @property
    def verificable(self):
        return bool(self.md5 or self.sha256 or self.miembros_zip)


@dataclass
class InformeBios:
    lineas: list[str]
    enlaces: list[tuple[str, str]]
    contexto: str
    archivos: list[ArchivoBios]


def enlace_busqueda(bios, contexto):
    return "https://www.google.com/search?" + urlencode({"q": f'"{bios.destino.name}" {contexto} BIOS'})


def version_retrobat(raiz):
    try:
        version = (raiz / "system" / "version.info").read_text(encoding="utf-8-sig").strip()
    except (OSError, UnicodeError):
        return None
    return version if re.fullmatch(r"\d+\.\d+\.\d+(?:\.\d+)?(?:-[\w-]+)?", version) else None


def comprobar_actualizacion(raiz):
    actual = version_retrobat(raiz)
    if not actual:
        return "No se identificó la versión local", False
    try:
        with urlopen("https://api.github.com/repos/RetroBat-Official/retrobat/releases/latest", timeout=9) as respuesta:
            publicacion = json.load(respuesta)
        if publicacion.get("prerelease"):
            raise ValueError("La publicación devuelta es una beta.")
        estable = next(
            (m[1] for asset in publicacion.get("assets", [])
             if (m := re.fullmatch(r"RetroBat-v(\d+(?:\.\d+){1,3})-stable-win64-setup\.exe",
                                  asset.get("name", ""), re.IGNORECASE))),
            None,
        )
        if not estable:
            m = re.fullmatch(r"RetroBat v?(\d+(?:\.\d+){1,3})", publicacion.get("name", ""), re.IGNORECASE)
            estable = m[1] if m else None
        if not estable:
            raise ValueError("No se identificó la publicación estable.")
    except (OSError, ValueError, TypeError):
        return f"RetroBat {actual} · No se pudo consultar la versión estable", False

    def numero(version):
        partes = tuple(map(int, version.split("-", 1)[0].split(".")))
        return partes + (0,) * (4 - len(partes))

    disponible = numero(estable) > numero(actual)
    if disponible:
        estado = f"Actualización estable disponible: {estable}"
    elif numero(estable) == numero(actual):
        estado = f"Coincide con la última versión estable publicada: {estable}"
    else:
        estado = f"La versión local es posterior a la última estable: {estable}"
    return f"RetroBat {actual} · {estado}", disponible


def version_mame(raiz):
    ajustes = raiz / "emulationstation" / ".emulationstation" / "es_settings.cfg"
    opciones = {}
    if ajustes.is_file():
        # Los ajustes de EmulationStation pueden contener varias etiquetas de primer nivel.
        texto = ajustes.read_text(encoding="utf-8-sig")
        for nombre in ("mame.emulator", "mame.core"):
            valor = re.search(r'name="' + re.escape(nombre) + r'"\s+value="([^"]*)"', texto)
            if valor:
                opciones[nombre] = valor[1]
    emulador = opciones.get("mame.emulator", "").casefold()
    nucleo = opciones.get("mame.core", "").casefold()
    if emulador in ("", "auto", "default"):
        emulador = "libretro"
    if nucleo in ("", "auto", "default"):
        nucleo = "mame"
    if emulador != "libretro" or nucleo != "mame":
        return f"{emulador} / {nucleo}" if emulador == "libretro" else emulador, None
    dll = raiz / "emulators" / "retroarch" / "cores" / "mame_libretro.dll"
    if not dll.is_file() or not dll.stat().st_size:
        return "libretro / mame", None
    with dll.open("rb") as archivo, mmap.mmap(archivo.fileno(), 0, access=mmap.ACCESS_READ) as datos:
        versiones = {v.decode("ascii") for v in re.findall(rb"\x00(0\.\d{2,4}) \([0-9a-f]{7,40}\)\x00", datos)}
    return "libretro / mame", versiones.pop() if len(versiones) == 1 else None


def archivos_publicos_bios():
    with urlopen(API_BIOS, timeout=15) as respuesta:
        datos = json.load(respuesta)
    return [entrada["path"] for entrada in datos["tree"] if entrada["type"] == "blob"]


def firmware_fbneo(raiz):
    info = raiz / "emulators" / "retroarch" / "info" / "fbneo_libretro.info"
    if not info.is_file():
        return None, ()
    contenido = info.read_text(encoding="utf-8-sig")
    version = re.search(r'^display_version\s*=\s*"([^"]+)"', contenido, re.MULTILINE)
    nombres = tuple(dict.fromkeys(re.findall(r'^firmware\d+_path\s*=\s*"fbneo/([\w.-]+\.zip)"',
                                            contenido, re.MULTILINE)))
    return version[1] if version else None, nombres


def buscar_bios_publicas(raiz, sistema, informar):
    version = version_retrobat(raiz) or "versión no identificada"
    lineas = [f"RetroBat: {version}", ""]
    enlaces = [("Guía oficial de BIOS", GUIA_BIOS), ("Archivos de RetroBat", BIOS_OFICIALES)]
    informe = InformeBios(lineas, enlaces, f"{sistema.nombre} RetroBat {version}", [])
    if sistema.identificador in NO_REQUIERE_BIOS:
        lineas.append(f"{sistema.nombre} no requiere BIOS en su configuración estándar.")
        return informe
    if sistema.identificador == "ps3":
        destino = raiz / "bios" / "PS3UPDAT.PUP"
        bios = ArchivoBios(destino, "Por comprobar", sha256=FIRMWARE_PS3_SHA256, url=SONY_PS3)
        informe.archivos.append(replace(bios, estado=estado_bios(bios)))
        informe.contexto = "Sony PlayStation 3 firmware 4.93 RPCS3"
        lineas.append("Instala el firmware de Sony en RPCS3 desde la pestaña Firmware.")
        return informe

    requisitos = {}
    datos = catalogo_bios(raiz)
    base = (raiz / "bios").resolve()
    candidatos = list(rutas_bios_sistema(raiz, sistema.identificador, datos))
    if sistema.identificador == "fbneo":
        version_fbneo, nombres = firmware_fbneo(raiz)
        if version_fbneo:
            informe.contexto = f"FinalBurn Neo {version_fbneo} RetroBat"
            lineas.append(f"Metadatos del núcleo instalado: FBNeo {version_fbneo}")
        lineas.append("Estos archivos son opcionales según el juego y la placa emulada.")
        enlaces.append(("Guía de FBNeo", FBNEO_GUIA))
        candidatos.extend((base / nombre, "") for nombre in nombres)
        for grupo in ("neogeo", "neogeocd"):
            candidatos.extend((ruta, md5) for ruta, md5 in rutas_bios_sistema(raiz, grupo, datos)
                              if ruta.name in nombres)
    for ruta, md5 in candidatos:
        valores = requisitos.setdefault(ruta, set())
        if re.fullmatch(r"[0-9a-fA-F]{32}", md5):
            valores.add(md5.lower())
    for ruta, valores in requisitos.items():
        bios = ArchivoBios(ruta, "Por comprobar", md5=tuple(sorted(valores)))
        estado = estado_bios(bios)
        if sistema.identificador == "fbneo" and estado == "Por buscar":
            alternativo = base / "fbneo" / ruta.name
            estado = estado_bios(replace(bios, destino=alternativo))
        informe.archivos.append(replace(bios, estado=estado))
    if not requisitos:
        lineas.append("El catálogo de esta instalación no especifica BIOS para este sistema. "
                      "Consulta los requisitos del emulador que usas.")
        return informe

    faltantes = [bios for bios in informe.archivos if bios.estado == "Por buscar"]
    if not faltantes:
        return informe
    informar(0, None, "Buscando los archivos que faltan en el repositorio de RetroBat…")
    try:
        publicados = {ruta.casefold(): ruta for ruta in archivos_publicos_bios()}
    except (OSError, ValueError, KeyError) as error:
        lineas.extend(("", f"No se pudo consultar el repositorio público de RetroBat: {error}"))
        return informe
    for indice, bios in enumerate(informe.archivos):
        publicado = publicados.get(bios.destino.relative_to(base).as_posix().casefold())
        if publicado and bios.estado == "Por buscar":
            informe.archivos[indice] = replace(bios, url=f"{BIOS_OFICIALES}/blob/main/{quote(publicado)}")
    return informe


def coincide_bios(archivo, bios):
    if bios.miembros_zip:
        esperados = set(bios.miembros_zip)
        tamanos = {tamano for tamano, _ in esperados}
        with ZipFile(archivo) as zip_bios:
            for info in zip_bios.infolist():
                if info.is_dir() or info.file_size not in tamanos:
                    continue
                with zip_bios.open(info) as miembro:
                    huella = hashlib.file_digest(miembro, "sha1").hexdigest()
                esperados.discard((info.file_size, huella))
                if not esperados:
                    return True
        return False
    if bios.sha256 or bios.md5:
        with archivo.open("rb") as entrada:
            huella = hashlib.file_digest(entrada, "sha256" if bios.sha256 else "md5").hexdigest()
        return huella == bios.sha256 if bios.sha256 else huella in bios.md5
    return False


def estado_bios(bios):
    if not bios.destino.is_file():
        return "Por buscar"
    if not bios.verificable:
        return "Presente · sin huella"
    try:
        return "Verificada" if coincide_bios(bios.destino, bios) else "Presente · no coincide"
    except (OSError, BadZipFile, RuntimeError, NotImplementedError):
        return "Presente · no se pudo verificar"


def importar_bios_locales(raiz, origen, requisitos, informar):
    base = (raiz / "bios").resolve()
    if not origen.is_dir():
        raise ValueError("La carpeta de origen de las BIOS no está disponible.")
    nombres = {bios.destino.name.casefold() for bios in requisitos if bios.verificable}
    candidatos = {}
    informar(0, None, "Buscando copias en la carpeta de BIOS…")
    for carpeta, _, archivos in os.walk(origen):
        for nombre in archivos:
            if nombre.casefold() in nombres:
                candidatos.setdefault(nombre.casefold(), []).append(Path(carpeta) / nombre)
    resultados = []
    for indice, bios in enumerate(requisitos, 1):
        destino = bios.destino.resolve()
        informar(indice - 1, len(requisitos), "Comprobando y copiando BIOS…")
        resultado = "No se encontró una copia compatible"
        if not destino.is_relative_to(base) or destino == base:
            resultado = "Ruta de destino inválida"
        elif destino.exists():
            resultado = "Ya existe en RetroBat"
        elif not bios.verificable:
            resultado = "El catálogo no permite verificar este archivo"
        else:
            for archivo in sorted(candidatos.get(destino.name.casefold(), ())):
                try:
                    destino.parent.mkdir(parents=True, exist_ok=True)
                    with tempfile.TemporaryDirectory(dir=destino.parent) as temporal:
                        preparado = Path(temporal) / destino.name
                        copiar_archivo(archivo, preparado, None)
                        if not coincide_bios(preparado, bios):
                            continue
                        publicar(preparado, destino)
                    resultado = "Copiada y verificada"
                    break
                except FileExistsError:
                    resultado = "Ya existe en RetroBat"
                    break
                except (OSError, BadZipFile, RuntimeError, NotImplementedError) as error:
                    resultado = f"No se pudo usar {archivo.name}: {error}"
        resultados.append((bios, resultado))
    informar(len(requisitos), len(requisitos), "Importación de BIOS finalizada.")
    return resultados


def descargar_catalogo(version, destino, informar):
    etiqueta = "mame" + version.replace(".", "")
    nombre = f"{etiqueta}lx.zip"
    consulta = f"https://api.github.com/repos/mamedev/mame/releases/tags/{etiqueta}"
    with urlopen(consulta, timeout=15) as respuesta:
        datos = json.load(respuesta)
    archivo = next((asset for asset in datos["assets"] if asset["name"] == nombre), None)
    url = f"https://github.com/mamedev/mame/releases/download/{etiqueta}/{nombre}"
    if archivo is None or archivo["browser_download_url"] != url:
        raise ValueError("MAME no publicó el catálogo XML de esta versión.")
    digest = archivo.get("digest") or ""
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise ValueError("El catálogo oficial no tiene un SHA-256 verificable.")
    total = archivo["size"]
    if not 0 < total <= 50 * 1024 * 1024:
        raise ValueError("El tamaño del catálogo oficial es inesperado.")
    informar(0, total, f"Descargando catálogo oficial de MAME {version}…")
    huella = hashlib.sha256()
    recibidos = 0
    with urlopen(url + "?download=1", timeout=25) as respuesta, destino.open("wb") as salida:
        for bloque in iter(lambda: respuesta.read(256 * 1024), b""):
            recibidos += len(bloque)
            if recibidos > total:
                raise ValueError("La descarga supera el tamaño publicado.")
            huella.update(bloque)
            salida.write(bloque)
            informar(recibidos, total, f"Descargando catálogo oficial de MAME {version}…")
    if recibidos != total or "sha256:" + huella.hexdigest() != digest:
        raise ValueError("El catálogo descargado no coincide con el archivo publicado.")


def dependencias_mame(archivo, version, juegos, informar):
    entradas = {}
    bios = {}
    fase = "Buscando dependencias de BIOS en el catálogo…"
    with ZipFile(archivo) as comprimido:
        xml = next((item for item in comprimido.infolist() if item.filename.lower().endswith(".xml")), None)
        if xml is None or xml.file_size > 850 * 1024 * 1024:
            raise ValueError("El catálogo no contiene un XML de MAME válido.")
        with comprimido.open(xml) as contenido:
            elementos = ET.iterparse(contenido, events=("start", "end"))
            _, raiz = next(elementos)
            if raiz.tag != "mame" or raiz.get("build", "").split()[:1] != [version]:
                raise ValueError("El XML no corresponde a la versión detectada.")
            informar(0, xml.file_size, fase)
            for evento, elemento in elementos:
                if evento != "end" or elemento.tag != "machine":
                    continue
                nombre = elemento.attrib["name"]
                padre = elemento.get("romof")
                dispositivos = [ref.attrib["name"] for ref in elemento.findall("device_ref")]
                entradas[nombre] = ([padre] if padre else []) + dispositivos
                if elemento.get("isbios") == "yes":
                    opciones = elemento.findall("biosset")
                    inicial = opciones[0].get("name") if opciones else None
                    activa = next((opcion.get("name") for opcion in opciones if opcion.get("default") == "yes"),
                                  inicial)
                    miembros = tuple((int(rom.attrib["size"]), rom.attrib["sha1"])
                                     for rom in elemento.findall("rom")
                                     if "sha1" in rom.attrib and rom.get("optional") != "yes"
                                     and rom.get("bios") in (None, activa))
                    bios[nombre] = miembros
                raiz.clear()
                if len(entradas) % 128 == 0:
                    informar(contenido.tell(), xml.file_size, fase)
            informar(xml.file_size, xml.file_size, fase)

    def dependencias(juego):
        visitados = {juego}
        por_visitar = list(entradas[juego])
        while por_visitar:
            nombre = por_visitar.pop()
            if nombre in visitados:
                continue
            visitados.add(nombre)
            if nombre in bios:
                yield nombre
            por_visitar.extend(entradas.get(nombre, ()))

    resultados = {}
    for juego in sorted(juegos & entradas.keys() - bios.keys()):
        for dependencia in dependencias(juego):
            resultados.setdefault(dependencia, []).append(juego)
    return resultados, bios, len(juegos & entradas.keys())


def revisar_bios_mame(raiz, sistema, informar):
    retrobat = version_retrobat(raiz) or "versión no identificada"
    emulador, version = version_mame(raiz)
    lineas = [f"RetroBat: {retrobat}", f"Emulador configurado: {emulador}"]
    enlaces = [("Guía de BIOS de MAME", MAME_GUIA)]
    informe = InformeBios(lineas, enlaces, f"MAME {version or ''}".strip(), [])
    if not version:
        lineas.append("No se pudo identificar una versión exacta del núcleo MAME activo en esta instalación.")
        return informe
    lineas.append(f"Versión del núcleo: MAME {version}")
    etiqueta = "mame" + version.replace(".", "")
    enlaces.append((f"Catálogo MAME {version}", f"https://github.com/mamedev/mame/releases/tag/{etiqueta}"))
    archivos = [p for p in sistema.carpeta.rglob("*")
                if p.suffix.lower() in {".zip", ".7z"} and p.is_file()]
    juegos = {p.stem.casefold() for p in archivos}
    if not juegos:
        lineas.append("No hay ROMs ZIP o 7z en el destino para comparar.")
        return informe
    try:
        with tempfile.TemporaryDirectory(prefix="tecnotics-mame-") as temporal:
            archivo = Path(temporal) / "catalogo.zip"
            descargar_catalogo(version, archivo, informar)
            requisitos, bios, reconocidos = dependencias_mame(archivo, version, juegos, informar)
    except (OSError, ValueError, BadZipFile, ET.ParseError, KeyError) as error:
        lineas.append(f"No se pudo consultar el catálogo de MAME {version}: {error}")
        return informe

    informar(0, None, "Comprobando archivos locales y fuentes públicas de BIOS…")
    destinos = {}
    for archivo in (*archivos, *(raiz / "bios").glob("*")):
        nombre = archivo.stem.casefold()
        if nombre in requisitos and archivo.suffix.lower() in {".zip", ".7z"} and archivo.is_file():
            destinos.setdefault(nombre, []).append(archivo)
    faltantes = requisitos.keys() - destinos.keys()
    disponibles = {}
    if faltantes:
        try:
            for publicado in archivos_publicos_bios():
                ruta = Path(publicado)
                if ruta.suffix.lower() in {".zip", ".7z"}:
                    nombre = ruta.stem.casefold()
                    if nombre in faltantes:
                        disponibles[nombre] = ruta.as_posix()
            enlaces.append(("Archivos publicados por RetroBat", BIOS_OFICIALES))
        except (URLError, OSError, ValueError, KeyError) as error:
            lineas.append(f"No se pudo consultar el repositorio público de BIOS de RetroBat: {error}")

    lineas.extend(("", f"{reconocidos} de {len(juegos)} nombres reconocidos en MAME {version}.", ""))
    if not requisitos:
        lineas.append("No se detectaron archivos BIOS de placa asociados a los nombres reconocidos.")
    for nombre, relacionados in sorted(requisitos.items()):
        destino = raiz / "bios" / f"{nombre}.zip"
        url = f"{BIOS_OFICIALES}/blob/main/{quote(disponibles[nombre])}" if nombre in disponibles else ""
        bios_archivo = ArchivoBios(destino, "Por buscar", len(relacionados), miembros_zip=bios[nombre], url=url)
        estados = [estado_bios(replace(bios_archivo, destino=archivo)) if archivo.suffix.lower() == ".zip"
                   else "Presente · archivo 7z" for archivo in destinos.get(nombre, ())]
        estado = "Verificada" if "Verificada" in estados else next(iter(estados), "Por buscar")
        informe.archivos.append(replace(bios_archivo, estado=estado))
    pendientes = sum(bios_archivo.estado == "Por buscar" for bios_archivo in informe.archivos)
    if requisitos:
        lineas.extend((f"{pendientes} BIOS por buscar como archivos separados.",
                       "Algunos romsets incluyen estos componentes dentro de cada juego."))
    return informe


def biblioteca_instalada(raiz, sistemas, informar):
    datos = catalogo_bios(raiz)
    biblioteca = []
    for indice, (clave, sistema) in enumerate(sistemas.items(), 1):
        informar(indice - 1, len(sistemas), "Revisando los sistemas con juegos…")
        categorias = {}
        if not sistema.carpeta.is_dir():
            continue
        for carpeta, subcarpetas, archivos in os.walk(sistema.carpeta):
            subcarpetas[:] = [sub for sub in subcarpetas
                             if not sub.startswith(".") and sub.casefold() not in CARPETAS_MULTIMEDIA]
            directorio = Path(carpeta)
            paquetes = [sub for sub in subcarpetas if Path(sub).suffix.lower() in sistema.extensiones]
            for paquete in paquetes:
                subcarpetas.remove(paquete)
            juegos = [directorio / nombre for nombre in (*paquetes, *archivos)
                      if not nombre.startswith(".") and Path(nombre).suffix.lower() in sistema.extensiones]
            if juegos:
                ruta = directorio.relative_to(sistema.carpeta).parts
                categoria = ruta[0] if ruta else "Sin categoría"
                categorias.setdefault(categoria, []).extend(juegos)
        if not categorias:
            continue
        if sistema.identificador in NO_REQUIERE_BIOS:
            bios = "No requiere BIOS"
        elif sistema.identificador == "mame":
            bios = "Revisar según los juegos"
        elif sistema.identificador == "fbneo":
            _, nombres = firmware_fbneo(raiz)
            base = raiz / "bios"
            encontrados = sum((base / nombre).is_file() or (base / "fbneo" / nombre).is_file()
                              for nombre in nombres)
            bios = f"{encontrados}/{len(nombres)} BIOS opcionales presentes" if nombres else "Revisar según los juegos"
        else:
            rutas = ({raiz / "bios" / "PS3UPDAT.PUP"} if sistema.identificador == "ps3" else
                     {ruta for ruta, _ in rutas_bios_sistema(raiz, sistema.identificador, datos)})
            encontrados = sum(ruta.is_file() for ruta in rutas)
            bios = f"{encontrados}/{len(rutas)} archivos presentes" if rutas else "Sin requisitos en el catálogo"
        try:
            _, _, _, metadatos = catalogo_juegos(sistema)
        except (OSError, ValueError, ET.ParseError):
            metadatos = {}
        titulos = {}
        for categoria, rutas in categorias.items():
            juegos = [(ruta, next((nodo.findtext("name") for nodo in metadatos.get(ruta, ())
                                   if nodo.findtext("name")), ruta.stem)) for ruta in rutas]
            titulos[categoria] = sorted(juegos, key=lambda juego: juego[1].casefold())
        biblioteca.append((clave, sistema.nombre, bios, titulos))
    return sorted(biblioteca, key=lambda fila: fila[1].casefold())
