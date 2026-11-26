"""Instala los componentes del catálogo oficial de TeknoParrot directamente en RetroBat."""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import ssl
import stat
import tempfile
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from zipfile import BadZipFile, ZipFile

from gestor_core import nombre_seguro, publicar_directorio
from gestor_teknoparrot import carpeta_emulador, perfiles_locales, sistema_teknoparrot

CATALOGO = "https://teknoparrot.com/api/updates/components"
BASE = {
    "TeknoParrotUI": "TeknoParrotUi.exe",
    "TeknoParrot": "TeknoParrot/TeknoParrot.dll",
    "OpenParrotWin32": "OpenParrotWin32/OpenParrot.dll",
    "OpenParrotx64": "OpenParrotx64/OpenParrot64.dll",
    "OpenSegaAPI": "TeknoParrot/Opensegaapi.dll",
}
CARPETAS = {
    "TeknoParrotUI": "", "OpenSegaAPI": "TeknoParrot", "TeknoParrotN2": "N2",
    "OpenSndGaelco": "TeknoParrot", "OpenSndVoyager": "TeknoParrot", "ScoreSubmission": "TeknoParrot",
    "TeknoDraw": "TeknoParrot", "TeknoParrotElfLdr2": "ElfLdr2",
}
# Publicaciones antiguas sin digest en el catálogo. Huellas de los ZIP oficiales por versión.
HUELLAS_FIJADAS = {
    "/teknogods/TeknoParrot/releases/download/TeknoParrotN2/TeknoParrotN2Core_1.0.0.1.zip":
        "1562819df10924d5134522baf46c0ab9e3e6c3996dd7a62015f2a908577bbbb6",
    "/teknogods/OpenSndGaelco/releases/download/OpenSndGaelco/OpenSndGaelco.zip":
        "343144920efe7537f19cf5f2796314f1cf1d43c5b3b4ee064e43b727397c3704",
    "/teknogods/OpenSndVoyager/releases/download/OpenSndVoyager/OpenSndVoyager.zip":
        "21e4b9d2b1658fa847c14751f70015576b825c6f470f9f7d2a545243894a42c5",
}
VERSION_MANUAL = {"TeknoParrotElfLdr2", "CrediarDolphin", "Play"}
DATOS_USUARIO = {"parrotdata.xml", "userprofiles", "inputprofiles", "saves", "logs"}
LIMITE_PAQUETE = 2 * 1024**3


@dataclass(frozen=True)
class Paquete:
    nombre: str
    url: str
    sha256: str
    bytes: int
    version: str


def contexto_tls():
    if os.name == "nt":
        import truststore

        # CryptoAPI puede recuperar certificados intermedios que el servidor omite.
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    return ssl.create_default_context()


def abrir_https(solicitud, *, timeout):
    url = solicitud.full_url if isinstance(solicitud, Request) else solicitud
    host = urlparse(url).hostname
    try:
        return urlopen(solicitud, timeout=timeout, context=contexto_tls())
    except (URLError, ssl.SSLCertVerificationError) as error:
        causa = error.reason if isinstance(error, URLError) else error
        if isinstance(causa, ssl.SSLCertVerificationError):
            raise ValueError(
                f"No se pudo validar el certificado HTTPS de {host}. "
                "Comprueba la fecha y hora de Windows y si esa dirección abre en el navegador."
            ) from error
        raise


def paquetes_oficiales():
    with abrir_https(Request(CATALOGO, headers={"User-Agent": "Tecnotics-Arcade"}), timeout=30) as respuesta:
        datos = json.loads(respuesta.read(2_000_000))
    if not isinstance(datos, list):
        raise ValueError("TeknoParrot devolvió un catálogo inválido.")
    paquetes, pendientes, vistos = [], [], set()
    for entrada in datos:
        nombre = entrada["component"]
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _-]*", nombre) or nombre.casefold() in vistos:
            raise ValueError("El catálogo contiene un nombre de componente inválido o repetido.")
        nombre_seguro(nombre)
        vistos.add(nombre.casefold())
        release = entrada["release"]
        activos = []
        for activo in release.get("assets", ()):
            url = urlparse(activo.get("browser_download_url", ""))
            sha = re.fullmatch(r"sha256:([0-9a-f]{64})", activo.get("digest") or "", re.I)
            huella = sha[1].lower() if sha else HUELLAS_FIJADAS.get(url.path)
            tamanio = activo.get("size")
            if (url.scheme == "https" and url.netloc == "github.com"
                    and re.match(r"^/(?:teknogods|ReaverTeknoGods)/[^/]+/releases/download/", url.path, re.I)
                    and url.path.lower().endswith(".zip") and huella
                    and type(tamanio) is int and 0 < tamanio <= LIMITE_PAQUETE):
                version = re.search(r"\d+(?:\.\d+){1,3}", str(release.get("tag_name", "")) + " "
                                    + str(release.get("name", "")) + " " + url.path.rsplit("/", 1)[-1])
                activos.append(Paquete(nombre, url.geturl(), huella, tamanio,
                                       "v" + version[0] if version else ""))
        if len(activos) == 1 and not release.get("draft") and not release.get("prerelease"):
            paquetes.append(activos[0])
        else:
            pendientes.append(nombre)
    faltan = BASE.keys() - {paquete.nombre for paquete in paquetes}
    if faltan:
        raise ValueError("El catálogo no ofrece paquetes verificables para: " + ", ".join(sorted(faltan)))
    # La interfaz oficial va primero; los demás componentes se añaden en el orden del catálogo.
    return sorted(paquetes, key=lambda paquete: paquete.nombre != "TeknoParrotUI"), pendientes


def faltantes(emulador):
    resultado = []
    for nombre, relativa in BASE.items():
        ruta = emulador / relativa
        try:
            modo = ruta.stat().st_mode
        except (FileNotFoundError, NotADirectoryError):
            resultado.append(nombre)
        else:
            if not stat.S_ISREG(modo):
                resultado.append(nombre)
    return resultado


def descargar(paquete, archivo, informar):
    huella = hashlib.sha256()
    hecho = 0
    with abrir_https(paquete.url, timeout=45) as entrada, archivo.open("wb") as salida:
        for bloque in iter(lambda: entrada.read(1024 * 1024), b""):
            hecho += len(bloque)
            if hecho > paquete.bytes:
                raise ValueError(f"{paquete.nombre}: la descarga supera el tamaño publicado.")
            huella.update(bloque)
            salida.write(bloque)
            informar(hecho, paquete.bytes, f"Descargando {paquete.nombre}…")
    if hecho != paquete.bytes or huella.hexdigest() != paquete.sha256:
        raise ValueError(f"{paquete.nombre}: la descarga no coincide con el tamaño o SHA-256 oficial.")


def extraer(paquete, archivo, preparado):
    carpeta = preparado / CARPETAS.get(paquete.nombre, paquete.nombre)
    try:
        with ZipFile(archivo) as zip_:
            if sum(info.file_size for info in zip_.infolist()) > 3 * LIMITE_PAQUETE:
                raise ValueError(f"{paquete.nombre}: tamaño extraído inesperado.")
            for info in zip_.infolist():
                nombre = info.filename.replace("\\", "/")
                partes = PurePosixPath(nombre).parts
                if not partes or nombre.startswith("/") or stat.S_ISLNK(info.external_attr >> 16):
                    raise ValueError(f"{paquete.nombre}: entrada ZIP no válida: {info.filename}")
                for parte in partes:
                    nombre_seguro(parte)
                destino = carpeta.joinpath(*partes)
                if destino.resolve() != destino or not destino.is_relative_to(preparado):
                    raise ValueError(f"{paquete.nombre}: ruta ZIP fuera del destino.")
                if destino.relative_to(preparado).parts[0].casefold() in DATOS_USUARIO and destino.exists():
                    continue
                if info.is_dir() or nombre.endswith("/"):
                    destino.mkdir(parents=True, exist_ok=True)
                else:
                    destino.parent.mkdir(parents=True, exist_ok=True)
                    with zip_.open(info) as entrada, destino.open("wb") as salida:
                        shutil.copyfileobj(entrada, salida)
            if paquete.nombre in VERSION_MANUAL and paquete.version:
                (carpeta / ".version").write_text(paquete.version, encoding="utf-8")
    except BadZipFile as error:
        raise ValueError(f"Archivo ZIP inválido para {paquete.nombre}.") from error


def preparar_instalacion(raiz, informar):
    raiz = raiz.resolve()
    sistema = sistema_teknoparrot(raiz)
    emulador = carpeta_emulador(raiz)
    if emulador.resolve() != emulador:
        raise ValueError("La carpeta de TeknoParrot apunta fuera de su ubicación local.")
    informar(0, None, "Consultando los componentes oficiales…")
    paquetes, pendientes = paquetes_oficiales()
    emulador.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".tecnotics-tp-", dir=emulador.parent) as temporal:
        trabajo = Path(temporal)
        preparado = trabajo / "instalacion"
        if emulador.exists():
            informar(0, None, "Preparando una copia de tu configuración…")
            shutil.copytree(emulador, preparado, symlinks=True)
        else:
            preparado.mkdir()
        archivo = trabajo / "componente.zip"
        for indice, paquete in enumerate(paquetes, 1):
            descargar(paquete, archivo, informar)
            informar(indice - 1, len(paquetes), f"Instalando {paquete.nombre} ({indice}/{len(paquetes)})…")
            extraer(paquete, archivo, preparado)
            archivo.unlink()
        if faltantes(preparado) or not perfiles_locales(preparado):
            raise ValueError("La instalación preparada no contiene todos los componentes base y perfiles.")
        sistema.carpeta.mkdir(parents=True, exist_ok=True)
        (preparado / "UserProfiles").mkdir(exist_ok=True)
        informar(0, None, "Activando TeknoParrot en RetroBat…")
        anterior = None
        if emulador.exists():
            base = raiz / "user" / "tecnotics-gestor" / "teknoparrot-respaldos"
            base.mkdir(parents=True, exist_ok=True)
            anterior = Path(tempfile.mkdtemp(dir=base)) / emulador.name
            emulador.rename(anterior)
        try:
            publicar_directorio(preparado, emulador)
        except OSError:
            if anterior is not None and not emulador.exists():
                anterior.rename(emulador)
            raise
    return pendientes
