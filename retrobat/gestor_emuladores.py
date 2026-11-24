"""Catálogo, instalación y selección de emuladores en RetroBat."""

from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
import hashlib
from http.client import HTTPException
import json
from pathlib import Path
import re
import shutil
import struct
import tempfile
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit
from urllib.request import Request
from xml.etree import ElementTree as ET

from gestor_bios import version_retrobat
from gestor_core import archivo_sistemas_retrobat, nombre_seguro, publicar, publicar_directorio
from gestor_firmware import ruta_local
from gestor_teknoparrot_archivos import extraer, inspeccionar
from gestor_teknoparrot_instalacion import abrir_https, faltantes, preparar_instalacion
from gestor_teknoparrot_pantalla import guardar_ajustes, leer_ajustes

GUIA = "https://wiki.retrobat.org/systems-and-emulators/supported-game-systems"
SERVIDORES = ("https://www.retrobat.ovh/repo/win64", "https://retrobat.org/repo/win64")
LIBRETRO = "https://buildbot.libretro.com/nightly/windows/x86_64/latest"
NOMBRE = re.compile(r"[a-z0-9][a-z0-9_+.-]*")
LIMITE = 4 * 1024**3
LY = frozenset(("libretro", "angle", "retroarch"))
EXTERNOS = {
    "3dsen": "https://geod.itch.io/3dsen",
    "pico8": "https://www.lexaloffle.com/pico-8.php",
    "amigaforever": "https://www.amigaforever.com/",
    "exodos": "https://www.retro-exo.com/exodos.html",
    "citron": "https://github.com/citron-neo/emulator/releases",
    "teknoparrot": "https://teknoparrot.com/",
    "eden": "https://git.eden-emu.dev/eden-emu/eden/releases",
    "ryujinx": "https://git.ryujinx.app/projects/Ryubing/releases/",
    "redream": "https://redream.io/download",
    "bigpemu": "https://www.richwhitehouse.com/jaguar/",
}
SOLO_LOCAL = {"3dsen", "pico8", "amigaforever", "exodos", "citron", "suyu", "sudachi", "yuzu", "yuzu-early-access"}
EXCLUIDOS = {"windows", "pinballfx", "zaccariapinball"}
PAQUETES_EXTERNOS = {
    "eden": ("https://stable.eden-emu.dev/v0.2.1/Eden-Windows-v0.2.1-amd64-gcc-standard.zip",
             41352380, "b9824ee73d0aa16e783d52c4d1772a84003133fa30cd8968c5edbe4ea435c32f", "0.2.1"),
    "ryujinx": ("https://git.ryujinx.app/projects/Ryubing/releases/download/1.3.3/ryujinx-1.3.3-win_x64.zip",
                33926604, "baa93f48b012eefeca339a78a39844599ccd194c109093f354a4b9d1e03a056e", "1.3.3"),
}
HOSTS = {urlsplit(url).hostname for url in (*SERVIDORES, LIBRETRO)} | {
    "www.retrobat.org", "retrobat.ovh", "stable.eden-emu.dev", "git.ryujinx.app",
}


@dataclass(frozen=True)
class Vinculo:
    sistema: str
    nombre: str
    emulador: str
    nucleo: str = ""


@dataclass(frozen=True)
class Emulador:
    id: str
    nombre: str
    carpetas: tuple[str, ...]
    ejecutables: tuple[str, ...]
    vinculos: tuple[Vinculo, ...]
    nucleo: bool = False

    @property
    def origen(self):
        if self.nucleo:
            return "RetroBat / Libretro"
        if self.id in {"eden", "ryujinx", "teknoparrot"}:
            return {"eden": "Eden", "ryujinx": "Ryubing", "teknoparrot": "TeknoParrot"}[self.id]
        return "Copia local" if self.id in SOLO_LOCAL or not self.carpetas else "RetroBat"

    @property
    def via_automatica(self):
        return bool(self.carpetas and self.id not in SOLO_LOCAL)


@dataclass(frozen=True)
class Revision:
    emulador: Emulador
    instalado: Path | None
    version: str
    configurado: tuple[str, ...]


@dataclass(frozen=True)
class Paquete:
    urls: tuple[str, ...]
    tamano: int = 0
    sha256: str = ""


@lru_cache(maxsize=1)
def rutas_incluidas():
    datos = json.loads(Path(__file__).with_name("gestor_emuladores_rutas.json").read_text(encoding="utf-8"))
    datos["dolphin-triforce"] = datos["triforce"]
    return datos


def catalogo_emuladores(raiz):
    rutas = rutas_incluidas()
    referencias = defaultdict(list)
    for sistema in ET.parse(archivo_sistemas_retrobat(raiz)).getroot().findall("system"):
        clave = sistema.findtext("name", "").strip()
        if not NOMBRE.fullmatch(clave):
            continue
        nombre = sistema.findtext("fullname", clave).strip()
        for declarado in sistema.findall("./emulators/emulator"):
            emulador = declarado.get("name", "")
            if not NOMBRE.fullmatch(emulador) or emulador in EXCLUIDOS:
                continue
            nucleos = [n.text.strip() for n in declarado.findall("./cores/core")
                       if n.text and NOMBRE.fullmatch(n.text.strip())]
            for nucleo in nucleos or [""]:
                con_nucleo = bool(nucleo and emulador in LY)
                identificador = nucleo if con_nucleo else ("retroarch" if emulador in LY else emulador)
                vinculo = Vinculo(clave, nombre, emulador, nucleo)
                referencias[identificador, con_nucleo].append(vinculo)
    referencias.setdefault(("retroarch", False), [])
    salida = []
    for (identificador, nucleo), vinculos in referencias.items():
        if nucleo:
            carpetas, ejecutables = ("retroarch/cores",), (f"{identificador}_libretro.dll",)
            nombre = f"{identificador} · RetroArch"
        else:
            carpetas, ejecutables = rutas.get(identificador, ((), ()))
            nombre = {
                "retroarch": "RetroArch", "dolphin": "Dolphin", "dolphin-triforce": "Dolphin Triforce",
                "pcsx2": "PCSX2", "rpcs3": "RPCS3", "vita3k": "Vita3K", "teknoparrot": "TeknoParrot",
                "eden": "Eden", "ryujinx": "Ryujinx", "mame64": "MAME", "ppsspp": "PPSSPP",
                "pico8": "PICO-8", "3dsen": "3DSen", "snes9x": "Snes9x",
            }.get(identificador, identificador)
        salida.append(Emulador(identificador, nombre, tuple(carpetas), tuple(ejecutables),
                               tuple(dict.fromkeys(vinculos)), nucleo))
    return sorted(salida, key=lambda e: e.nombre.casefold())


def familia_emuladores(raiz):
    # ConfigFile de emulatorLauncher permite definir rutas en su fichero de ajustes.
    base = raiz / "emulationstation"
    archivo = base / "emulatorLauncher.cfg"
    if not archivo.is_file():
        return {}
    valores = {}
    for linea in archivo.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        nombre, sep, valor = linea.partition("=")
        nombre = nombre.strip().casefold()
        if sep and (NOMBRE.fullmatch(nombre) or nombre == "home") and valor.strip():
            valores[nombre] = base / Path(valor.strip().strip('"').replace("\\", "/"))
    return valores


def carpeta_emulador(raiz, emulador, carpeta, rutas):
    if emulador.nucleo:
        candidato = rutas.get("retroarch", raiz / "emulators" / "retroarch") / "cores"
    else:
        candidato = rutas.get(carpeta, raiz / "emulators" / carpeta)
    return ruta_local(raiz, candidato)


def es_binario(ruta):
    if not ruta.is_file() or ruta.is_symlink():
        return False
    with ruta.open("rb") as archivo:
        cabecera = archivo.read(64)
        if len(cabecera) != 64 or not cabecera.startswith(b"MZ"):
            return False
        archivo.seek(struct.unpack_from("<I", cabecera, 60)[0])
        return archivo.read(4) == b"PE\0\0"


def instalacion(raiz, emulador, rutas):
    for carpeta in emulador.carpetas:
        try:
            base = carpeta_emulador(raiz, emulador, carpeta, rutas)
            for nombre in emulador.ejecutables:
                candidato = base / nombre
                if candidato.resolve() == candidato and es_binario(candidato):
                    if emulador.id == "teknoparrot" and faltantes(base):
                        continue
                    return candidato
        except (OSError, ValueError):
            continue
    return None


def canal_retrobat(raiz):
    actual = version_retrobat(raiz) or ""
    return "beta" if "beta" in actual.casefold() else "stable"


def url_retrobat(canal, ruta):
    return tuple(f"{base}/{canal}/emulators/{quote(ruta)}" for base in SERVIDORES)


def abrir_oficial(url, *, timeout=35):
    if urlsplit(url).scheme != "https" or urlsplit(url).hostname not in HOSTS:
        raise ValueError("La descarga no apunta a una fuente oficial admitida.")
    respuesta = abrir_https(Request(url, headers={"User-Agent": "Tecnotics-Arcade"}), timeout=timeout)
    final = urlsplit(respuesta.geturl())
    if final.scheme != "https" or final.hostname not in HOSTS:
        respuesta.close()
        raise ValueError("La fuente oficial redirigió a una ubicación no admitida.")
    return respuesta


def indice_versiones(canal):
    sufijo = "-beta" if canal == "beta" else ""
    disponibles = {}
    for ruta, nucleo in ((f"versions{sufijo}.xml", False), (f"cores/coreversions{sufijo}.xml", True)):
        for url in url_retrobat(canal, ruta):
            try:
                with abrir_oficial(url, timeout=12) as respuesta:
                    documento = ET.fromstring(respuesta.read(512 * 1024))
                for sistema in documento.findall("system"):
                    nombre = sistema.get("name", "")
                    if NOMBRE.fullmatch(nombre):
                        disponibles[nombre, nucleo] = sistema.get("version", "")
                break
            except (OSError, ValueError, HTTPException, ET.ParseError):
                continue
    return disponibles


def revisar_emuladores(raiz, informar):
    raiz = raiz.resolve()
    informar(0, None, "Leyendo los emuladores de esta instalación…")
    catalogo = catalogo_emuladores(raiz)
    rutas = familia_emuladores(raiz)
    _, _, configuracion = leer_ajustes(raiz)
    ajustes = {n.get("name"): n.get("value") for n in configuracion.findall("string")}
    informar(0, None, "Consultando el catálogo oficial de RetroBat…")
    versiones = indice_versiones(canal_retrobat(raiz))
    filas = []
    for item in catalogo:
        exe = instalacion(raiz, item, rutas)
        vinculos = tuple(dict.fromkeys(v.nombre for v in item.vinculos
                                      if ajustes.get(f"{v.sistema}.emulator") == v.emulador
                                      and (not v.nucleo or ajustes.get(f"{v.sistema}.core") == v.nucleo)))
        version = PAQUETES_EXTERNOS[item.id][3] if item.id in PAQUETES_EXTERNOS else ""
        if item.via_automatica and not version:
            version = versiones.get((item.carpetas[0] if not item.nucleo else item.id, item.nucleo), "")
        filas.append(Revision(item, exe, version, vinculos))
    return filas


def paquete_oficial(raiz, item):
    if item.id in PAQUETES_EXTERNOS:
        url, tamano, sha256, _ = PAQUETES_EXTERNOS[item.id]
        return Paquete((url,), tamano, sha256)
    canal = canal_retrobat(raiz)
    if item.nucleo:
        nombre = f"{item.id}_libretro.dll.zip"
        return Paquete((*url_retrobat(canal, "cores/" + nombre), f"{LIBRETRO}/{quote(nombre)}"))
    return Paquete(url_retrobat(canal, item.carpetas[0] + ".7z"))


def descargar_paquete(paquete, destino, informar):
    errores = []
    for url in paquete.urls:
        try:
            with abrir_oficial(url) as respuesta:
                longitud = respuesta.headers.get("Content-Length")
                esperado = paquete.tamano or (int(longitud) if longitud and longitud.isdecimal() else 0)
                if esperado > LIMITE or esperado > shutil.disk_usage(destino.parent).free:
                    raise ValueError("El paquete es demasiado grande o no hay espacio suficiente.")
                if respuesta.headers.get("Content-Type", "").split(";")[0] in {"text/html", "text/plain"}:
                    raise ValueError("El servidor devolvió una página en lugar del paquete.")
                huella = hashlib.sha256()
                total = 0
                fase = f"Descargando de {urlsplit(url).hostname}…"
                informar(0, esperado or None, fase)
                with destino.open("wb") as archivo:
                    for bloque in iter(lambda: respuesta.read(1024**2), b""):
                        total += len(bloque)
                        if total > (esperado or LIMITE):
                            raise ValueError("El tamaño supera el anunciado por la fuente.")
                        huella.update(bloque)
                        archivo.write(bloque)
                        informar(total, esperado or None, fase)
                if not total or (esperado and total != esperado):
                    raise ValueError("La descarga está incompleta.")
                if paquete.sha256 and huella.hexdigest() != paquete.sha256:
                    raise ValueError("La descarga no coincide con la huella oficial esperada.")
                return
        except (OSError, ValueError, HTTPException) as error:
            if isinstance(error, HTTPError):
                error.close()
            errores.append(f"{urlsplit(url).hostname}: {error}")
            destino.unlink(missing_ok=True)
    raise ValueError("No se pudo obtener un paquete oficial. " + " · ".join(errores))


def revisar_arbol(carpeta):
    for ruta in carpeta.rglob("*"):
        if ruta.resolve() != ruta.absolute() or ruta.is_symlink() or not (ruta.is_file() or ruta.is_dir()):
            raise ValueError(f"La carpeta contiene un enlace o una ruta no admitida: {ruta.name}")
        nombre_seguro(ruta.name)


def carpeta_paquete(carpeta, nombres):
    nombres = {nombre.casefold() for nombre in nombres}
    candidatos = {ruta.parent for ruta in carpeta.rglob("*") if ruta.name.casefold() in nombres
                  and es_binario(ruta)}
    if not candidatos:
        raise ValueError("El paquete no incluye el ejecutable o núcleo que RetroBat espera.")
    profundidad = min(len(c.relative_to(carpeta).parts) for c in candidatos)
    coincidencias = [c for c in candidatos if len(c.relative_to(carpeta).parts) == profundidad]
    if len(coincidencias) != 1:
        raise ValueError("Elige la carpeta de una sola variante del emulador.")
    return coincidencias[0]


def copiar_configuraciones_existentes(destino, preparado):
    revisar_arbol(destino)
    for origen in destino.rglob("*"):
        hermano = preparado / origen.relative_to(destino)
        if origen.is_dir():
            hermano.mkdir(exist_ok=True, parents=True)
        elif not (hermano.is_file() and origen.suffix.lower() in {".exe", ".dll"}):
            hermano.parent.mkdir(exist_ok=True, parents=True)
            shutil.copy2(origen, hermano)


def ruta_plantilla(texto):
    partes = texto.strip().replace("\\", "/").lstrip("/").split("/")
    for parte in partes:
        nombre_seguro(parte)
    return Path(*partes)


def aplicar_plantillas(raiz, carpeta, preparado, trabajo):
    lista = raiz / "system" / "configgen" / "templates_files.lst"
    if not lista.is_file():
        return
    base = raiz / "system" / "templates"
    for linea in lista.read_text(encoding="utf-8-sig").splitlines():
        izquierdo, sep, derecho = linea.partition("|")
        ruta = derecho.strip().replace("\\", "/").lstrip("/")
        if not sep or not ruta.casefold().startswith(f"emulators/{carpeta.casefold()}/"):
            continue
        plantilla = ruta_local(raiz, raiz / ruta_plantilla(izquierdo))
        if not plantilla.is_relative_to(base) or not plantilla.is_file():
            continue
        relativo = ruta_plantilla(ruta).relative_to(Path("emulators", carpeta))
        destino = preparado / relativo
        if destino.exists():
            continue
        if plantilla.suffix.casefold() == ".zip" and destino.suffix.casefold() != ".zip":
            contenido = inspeccionar(plantilla)
            with tempfile.TemporaryDirectory(dir=trabajo) as temporal:
                descomprimido = Path(temporal) / "plantilla"
                extraer(plantilla, descomprimido, contenido)
                destino.parent.mkdir(parents=True, exist_ok=True)
                descomprimido.rename(destino)
        else:
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(plantilla, destino)


def instalar_emulador(raiz, item, local, informar):
    raiz = raiz.resolve()
    if not item.carpetas:
        raise ValueError("RetroBat no declara una ubicación para este emulador.")
    rutas = familia_emuladores(raiz)
    instalado = instalacion(raiz, item, rutas)
    if instalado:
        return instalado, None
    if item.id == "teknoparrot":
        pendientes = preparar_instalacion(raiz, informar)
        return instalacion(raiz, item, rutas), " · ".join(pendientes) or None
    if local is None and not item.via_automatica:
        raise ValueError("Este emulador requiere una copia local de su distribución oficial.")
    if item.nucleo and not instalacion(raiz, retroarch_base(), rutas):
        instalar_emulador(raiz, retroarch_base(), None, informar)
    primera = item.carpetas[0]
    destino = carpeta_emulador(raiz, item, primera, rutas)
    destino.parent.mkdir(parents=True, exist_ok=True)
    raiz_trabajo = destino.parent
    if local and local.is_dir() and raiz_trabajo.is_relative_to(local.resolve()):
        raise ValueError("Elige la carpeta del emulador descargado.")
    with tempfile.TemporaryDirectory(prefix=".tecnotics-emulador-", dir=raiz_trabajo) as temporal:
        trabajo = Path(temporal)
        if local and local.is_dir():
            origen = local.resolve()
            revisar_arbol(origen)
        else:
            paquete = local
            if paquete is None:
                fuente = paquete_oficial(raiz, item)
                paquete = trabajo / Path(urlsplit(fuente.urls[0]).path).name
                descargar_paquete(fuente, paquete, informar)
            informar(0, None, f"Verificando y extrayendo {item.nombre}…")
            contenido = inspeccionar(paquete)
            if contenido.bytes > LIMITE * 2:
                raise ValueError("El contenido descomprimido supera el tamaño permitido.")
            origen = trabajo / "extraido"
            extraer(paquete, origen, contenido)
        principal = carpeta_paquete(origen, item.ejecutables)
        if item.nucleo:
            destino.mkdir(exist_ok=True)
            ruta = destino / item.ejecutables[0]
            nuevo = trabajo / ruta.name
            shutil.copy2(principal / ruta.name, nuevo)
            publicar(nuevo, ruta)
            return ruta, None

        informar(0, None, f"Preparando las rutas de RetroBat para {item.nombre}…")
        preparado = trabajo / "instalacion"
        shutil.copytree(principal, preparado)
        if destino.is_dir():
            copiar_configuraciones_existentes(destino, preparado)
        aplicar_plantillas(raiz, primera, preparado, trabajo)
        exe = next(preparado / nombre for nombre in item.ejecutables
                   if es_binario(preparado / nombre))
        if item.id == "ryujinx":
            ruta_local(raiz, raiz / "saves" / "switch" / "ryujinx" / "portable").mkdir(parents=True, exist_ok=True)
        respaldo = None
        if destino.is_dir():
            base = ruta_local(raiz, raiz / "user" / "tecnotics-gestor" / "respaldos-emuladores")
            base.mkdir(parents=True, exist_ok=True)
            respaldo = Path(tempfile.mkdtemp(dir=base)) / destino.name
            destino.rename(respaldo)
        try:
            publicar_directorio(preparado, destino)
        except OSError:
            if respaldo and not destino.exists():
                respaldo.rename(destino)
            raise
        return destino / exe.name, respaldo


def retroarch_base():
    carpetas, ejecutables = rutas_incluidas()["retroarch"]
    return Emulador("retroarch", "RetroArch", tuple(carpetas), tuple(ejecutables), ())


def activar_emulador(raiz, item, vinculo):
    raiz = raiz.resolve()
    actual = next((e for e in catalogo_emuladores(raiz) if (e.id, e.nucleo) == (item.id, item.nucleo)), None)
    if not actual or vinculo not in actual.vinculos:
        raise ValueError("Este emulador no está habilitado para el sistema en tu versión de RetroBat.")
    rutas = familia_emuladores(raiz)
    if not instalacion(raiz, actual, rutas) or (actual.nucleo and not instalacion(raiz, retroarch_base(), rutas)):
        raise ValueError("Instala el emulador y el núcleo antes de seleccionarlos para el sistema.")
    archivo, original, config = leer_ajustes(raiz)
    if rutas.get("home", archivo.parent).resolve() != archivo.parent:
        raise ValueError("Esta instalación usa una carpeta personalizada de EmulationStation. Cambia el emulador allí.")
    cambios = False
    for ajuste, valor in (("emulator", vinculo.emulador), ("core", vinculo.nucleo)):
        clave = f"{vinculo.sistema}.{ajuste}"
        nodos = config.findall(f"string[@name='{clave}']")
        if (not valor and not nodos) or (len(nodos) == 1 and nodos[0].get("value") == valor):
            continue
        cambios = True
        for nodo in nodos:
            config.remove(nodo)
        if valor:
            ET.SubElement(config, "string", name=clave, value=valor)
    return guardar_ajustes(raiz, archivo, original, config) if cambios else None
