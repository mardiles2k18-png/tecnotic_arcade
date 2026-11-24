"""Requisitos de RetroBat e instalación de firmware en los emuladores locales."""

from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import quote
from urllib.request import Request
from xml.etree import ElementTree as ET

from gestor_bios import API_BIOS, ArchivoBios, GUIA_BIOS, SONY_PS3, coincide_bios
from gestor_core import (FIRMWARE_PS3_SHA256, FIRMWARE_PS3_TAMANO, FIRMWARE_PS3_URL,
                         catalogo_bios, copiar_archivo, publicar, publicar_directorio)
from gestor_teknoparrot import carpeta_emulador
from gestor_teknoparrot_instalacion import abrir_https
from gestor_teknoparrot_pantalla import leer_ajustes

SONY_VITA = "https://www.playstation.com/en-us/support/hardware/psvita/system-software/"
GUIA_SWITCH = ("https://wiki.retrobat.org/systems-and-emulators/supported-game-systems/"
               "game-consoles/nintendo-game-consoles/switch")
REPO_BIOS = "https://raw.githubusercontent.com/RetroBat-Official/retrobat-bios/main/"
LIMITE_ARCHIVO = 2 * 1024**3
FALTA = "Falta"
GUARDADO = "Paquete guardado"
LISTO = "Instalado"
LOCAL = "Copia local"
NCA = re.compile(r"(?i)[0-9a-f]{32}\.nca")
PREF_VITA = re.compile(r"^pref-path:[ \t]*([^\r\n]*)", re.MULTILINE)


@dataclass(frozen=True)
class Descarga:
    url: str
    tamano: int
    sha256: str = ""
    blob: str = ""


@dataclass(frozen=True)
class Requisito:
    sistema: str
    archivo: ArchivoBios
    emulador: Path | None = None
    instalado: tuple[Path, ...] = ()
    paquete: Descarga | None = None
    grupo: str = ""
    opcional: bool = False
    tipo: str = "archivo"
    guia: str = GUIA_BIOS
    nombres_locales: tuple[str, ...] = ()

    @property
    def destino(self):
        return self.archivo.destino


@dataclass(frozen=True)
class Revision:
    requisito: Requisito
    estado: str
    accion: str


# Sony publica estos PUP por HTTP. Se verifica el SHA-256 fijado antes de instalar.
PS3 = Descarga(FIRMWARE_PS3_URL, FIRMWARE_PS3_TAMANO, FIRMWARE_PS3_SHA256)
VITA = (
    ("PSP2UPDAT.PUP", "vs0", Descarga(
        "http://dus01.psv.update.playstation.net/update/psv/image/2022_0209/"
        "rel_f2c7b12fe85496ec88a0391b514d6e3b/PSVUPDAT.PUP", 133834240,
        "6ef6dc8da6db026f28647713e473486d770087a605c52a8d751bfca7478386cf"),
     ("PSVUPDAT.PUP",), ()),
    ("PSP2UPDAT_FONT.PUP", "sa0", Descarga(
        "http://dus01.psp2.update.playstation.net/update/psp2/image/2022_0209/"
        "sd_59dcf059d3328fb67be7e51f8aa33418/PSP2UPDAT.PUP?dest=us", 56778752,
        "c3c03fc7363dd573d90e5157629bf11551f434b283cc898d9ffc71dd716b791c"),
     ("PSP2UPDAT.PUP", "font_fresh.pup"), ("8b5f60b56c3da8365b973dba570c53a5",)),
    ("PSP2UPDAT_PREINST.PUP", "pd0", Descarga(
        "http://dus01.psp2.update.playstation.net/update/psp2/image/2022_0209/"
        "pre_efd1ef6c1cc2fe92e72e9e783e421237/PSP2UPDAT.PUP?dest=us", 128798720,
        "339d1439eb329cfbd1a936f0a1563458e0555ef52975486b2844e24b6049e33e"),
     ("PSP2UPDAT.PUP", "preinst_fresh.pup"), ()),
)


def ruta_local(raiz, ruta):
    resuelta = ruta.resolve()
    if resuelta == raiz or not resuelta.is_relative_to(raiz):
        raise ValueError(f"Ruta fuera de la instalación de RetroBat: {ruta}")
    return resuelta


def leer_pref_vita(texto):
    valor = PREF_VITA.search(texto)
    anterior = valor[1].strip() if valor else ""
    if anterior.startswith('"'):
        return json.JSONDecoder().raw_decode(anterior)[0]
    if anterior.startswith("'"):
        cadena = re.match(r"^'((?:[^']|'')*)'", anterior)
        if not cadena:
            raise ValueError("La ruta pref-path de Vita3K no se pudo leer.")
        return cadena[1].replace("''", "'")
    return anterior.split(" #", 1)[0] if anterior and anterior != "null" else ""


def ruta_vita(raiz, emulador):
    base = emulador.parent
    portable = base / "portable"
    if portable.is_dir():
        return portable / "config.yml", portable / "fs"
    config = base / "config.yml"
    texto = config.read_text(encoding="utf-8-sig") if config.is_file() else ""
    anterior = leer_pref_vita(texto)
    _, _, ajustes = leer_ajustes(raiz)
    ajustes_vita = {n.get("name"): n.get("value", "") for n in ajustes.findall("string")}
    preferida = ajustes_vita.get("psvita.vita3k_pref_path") or ajustes_vita.get("global.vita3k_pref_path")
    if preferida or anterior:
        ruta = Path(preferida or anterior)
        return config, ruta if ruta.is_absolute() else base / ruta
    return config, raiz / "saves" / "psvita" / "vita3k"


def requisito_pup(sistema, base, emulador, nombre, paquete, instalado, tipo, guia, *,
                  nombres=(), md5=(), opcional=False):
    return Requisito(sistema, ArchivoBios(base / nombre, "", sha256=paquete.sha256, md5=md5),
                     emulador=emulador, instalado=instalado, paquete=paquete, tipo=tipo, guia=guia,
                     nombres_locales=nombres, opcional=opcional)


@lru_cache(maxsize=1)
def catalogo_incluido():
    return json.loads(Path(__file__).with_name("gestor_firmware_catalogo.json").read_text(encoding="utf-8"))


def requisitos_firmware(raiz, sistemas):
    raiz = raiz.resolve()
    bios = raiz / "bios"
    emuladores = raiz / "emulators"
    catalogo = dict(catalogo_incluido())
    catalogo.update(catalogo_bios(raiz))
    for identificador, datos in catalogo.items():
        if not isinstance(datos, dict) or identificador in {"ps3", "psvita", "namco3xx", "switch"}:
            continue
        sistema = sistemas.get(identificador)
        nombre = sistema.nombre if sistema else datos.get("name", identificador)
        requisitos = {}
        for entrada in datos.get("biosFiles", []):
            relativo = Path(entrada["file"])
            if relativo.is_absolute() or ".." in relativo.parts or not relativo.parts:
                continue
            if relativo.parts[0] not in {"bios", "emulators", "roms"} or len(relativo.parts) < 2:
                continue
            huella = entrada.get("md5") or ""
            grupo = entrada.get("group") or ""
            opcional = bool(entrada.get("optional"))
            ruta = raiz / relativo
            valores, _, _ = requisitos.setdefault(ruta, (set(), grupo, opcional))
            if re.fullmatch(r"[0-9a-fA-F]{32}", huella):
                valores.add(huella.lower())
        for ruta, (huellas, grupo, opcional) in requisitos.items():
            yield Requisito(nombre, ArchivoBios(ruta, "", md5=tuple(sorted(huellas))),
                             grupo=grupo, opcional=opcional)

    for sistema, carpeta in (("PlayStation 3", emuladores / "rpcs3"),
                              ("TeknoParrot · Namco 357/369", carpeta_emulador(raiz) / "RPCS3")):
        instalado = (carpeta / "dev_flash" / "vsh" / "etc" / "version.txt",
                     carpeta / "dev_flash" / "vsh" / "module" / "vsh.self")
        yield requisito_pup(sistema, bios, carpeta / "rpcs3.exe", "PS3UPDAT.PUP",
                            PS3, instalado, "rpcs3", SONY_PS3)

    vita = emuladores / "vita3k" / "Vita3K.exe"
    try:
        _, datos_vita = ruta_vita(raiz, vita)
    except (OSError, ValueError, ET.ParseError):
        datos_vita = None  # El instalador mostrará el error de la configuración de Vita3K.
    for nombre, particion, paquete, alternativos, md5 in VITA:
        instalado = (datos_vita / particion,) if datos_vita is not None else ()
        yield requisito_pup("PlayStation Vita", bios / "vita3k", vita, nombre, paquete, instalado,
                            "vita3k", SONY_VITA, nombres=alternativos, md5=md5, opcional=particion == "pd0")

    for nombre in ("Ryujinx", "Eden", "Yuzu", "Suyu", "Sudachi", "Citron"):
        carpeta = emuladores / nombre.lower()
        exe = carpeta / f"{nombre}.exe"
        if nombre != "Ryujinx" and not exe.is_file():
            continue
        if nombre == "Ryujinx":
            datos = raiz / "saves" / "switch" / "ryujinx" / "portable"
            claves = datos / "system"
            contenidos = datos / "bis" / "system" / "Contents" / "registered"
        else:
            datos = carpeta / "user"
            claves = datos / "keys"
            contenidos = datos / "nand" / "system" / "Contents" / "registered"
        sistema = f"Nintendo Switch · {nombre}"
        yield Requisito(sistema, ArchivoBios(claves / "prod.keys", ""), emulador=exe, guia=GUIA_SWITCH)
        yield Requisito(sistema, ArchivoBios(contenidos, ""), emulador=exe, guia=GUIA_SWITCH,
                         tipo="ryujinx" if nombre == "Ryujinx" else "nca")


@lru_cache(maxsize=1)
def descargas_retrobat():
    solicitud = Request(API_BIOS, headers={"User-Agent": "Tecnotics-Arcade"})
    with abrir_https(solicitud, timeout=20) as respuesta:
        datos = json.load(respuesta)
    if datos.get("truncated"):
        raise ValueError("GitHub devolvió un catálogo incompleto de RetroBat.")
    return {
        entrada["path"].casefold(): Descarga(
            REPO_BIOS + quote(entrada["path"]), entrada["size"], blob=entrada["sha"])
        for entrada in datos["tree"]
        if entrada["type"] == "blob" and entrada["mode"] == "100644"
        and 0 < entrada["size"] <= LIMITE_ARCHIVO
    }


def descarga_disponible(raiz, requisito, publicadas):
    relativo = requisito.destino.relative_to(raiz)
    if requisito.paquete:
        return requisito.paquete
    if relativo.parts[0] == "bios":
        return publicadas.get(Path(*relativo.parts[1:]).as_posix().casefold())
    return None


def coincide_firmware(archivo, requisito):
    bios = requisito.archivo
    if bios.sha256 and bios.md5:
        return coincide_bios(archivo, bios) or coincide_bios(archivo, ArchivoBios(archivo, "", md5=bios.md5))
    return coincide_bios(archivo, bios)


def presente(ruta):
    return ruta.is_file() and ruta.stat().st_size > 0


def instalado_en_emulador(requisito):
    if not requisito.instalado:
        return False
    if requisito.tipo == "vita3k":
        particion = requisito.instalado[0]
        return particion.is_dir() and any(p.is_file() and p.stat().st_size for p in particion.rglob("*"))
    return all(presente(ruta) for ruta in requisito.instalado)


def estado_firmware(requisito):
    if requisito.paquete and instalado_en_emulador(requisito):
        return LISTO
    if requisito.tipo in {"nca", "ryujinx"}:
        directorio = requisito.destino
        if directorio.is_dir() and any(
                NCA.fullmatch(r.name) and (presente(r) or
                                           r.is_dir() and any(presente(p) for p in r.iterdir()))
                for r in directorio.iterdir()):
            return "Detectado · validar en emulador"
        return FALTA
    if not requisito.destino.exists():
        return FALTA
    if not presente(requisito.destino):
        return "Archivo inválido"
    if requisito.archivo.verificable:
        if not coincide_firmware(requisito.destino, requisito):
            return "Huella diferente"
        return GUARDADO if requisito.paquete else "Verificado"
    return "Presente · sin huella"


def revisar_firmware(raiz, sistemas, informar):
    raiz = raiz.resolve()
    informar(0, None, "Consultando los archivos públicos de RetroBat…")
    try:
        publicadas = descargas_retrobat()
    except (OSError, ValueError, KeyError) as error:
        publicadas, aviso = {}, f"No se pudo consultar RetroBat en línea: {error}"
    else:
        aviso = ""
    requisitos = list(requisitos_firmware(raiz, sistemas))
    estados = []
    cubiertos = set()
    verificados = {}
    for indice, requisito in enumerate(requisitos):
        informar(indice, len(requisitos), "Comprobando el firmware de RetroBat…")
        try:
            ruta_local(raiz, requisito.destino)
            clave = (requisito.archivo, requisito.tipo, requisito.instalado)
            if clave not in verificados:
                verificados[clave] = estado_firmware(requisito)
            estado = verificados[clave]
        except (OSError, ValueError):
            estado = "Ruta inaccesible"
        estados.append(estado)
        if requisito.grupo and estado in {"Verificado", "Presente · sin huella"}:
            cubiertos.add((requisito.sistema, requisito.grupo))

    filas = []
    for requisito, estado in zip(requisitos, estados):
        accion = ""
        if requisito.grupo and estado == FALTA and (requisito.sistema, requisito.grupo) in cubiertos:
            estado = "Alternativa cubierta"
        if estado == GUARDADO:
            accion = "Instalar" if requisito.emulador.is_file() else f"Falta {requisito.emulador.name}"
        elif estado == FALTA:
            if requisito.tipo == "ryujinx":
                accion = "Instalar desde Ryujinx" if requisito.emulador.is_file() else "Falta Ryujinx.exe"
            else:
                accion = "Descarga oficial" if descarga_disponible(raiz, requisito, publicadas) else LOCAL
        filas.append(Revision(requisito, estado, accion))
    return sorted(filas, key=lambda fila: (fila.requisito.sistema.casefold(),
                                           fila.requisito.opcional, fila.requisito.destino.name.casefold())), aviso


def descargar(requisito, descarga, destino, informar):
    solicitud = Request(descarga.url, headers={"User-Agent": "Tecnotics-Arcade"})
    huella = (hashlib.sha256() if descarga.sha256
              else hashlib.sha1(f"blob {descarga.tamano}\0".encode(), usedforsecurity=False))
    total = 0
    fase = f"Descargando {destino.name}…"
    informar(0, descarga.tamano, fase)
    with abrir_https(solicitud, timeout=45) as respuesta, destino.open("wb") as archivo:
        for bloque in iter(lambda: respuesta.read(1024**2), b""):
            total += len(bloque)
            if total > descarga.tamano:
                raise ValueError("La descarga supera el tamaño publicado.")
            huella.update(bloque)
            archivo.write(bloque)
            informar(total, descarga.tamano, fase)
    if total != descarga.tamano or huella.hexdigest() != (descarga.sha256 or descarga.blob):
        raise ValueError("El tamaño o la huella de la descarga no coincide con la fuente oficial.")
    if descarga.blob and requisito.archivo.verificable and not coincide_firmware(destino, requisito):
        raise ValueError("El archivo publicado no coincide con la huella del catálogo de esta instalación.")


def indexar_copias(origen, requisitos, informar):
    nombres = {nombre.casefold() for r in requisitos for nombre in (r.destino.name, *r.nombres_locales)}
    copias = defaultdict(list)
    informar(0, None, "Buscando archivos de firmware en la carpeta seleccionada…")
    for carpeta, _, archivos in os.walk(origen):
        for nombre in archivos:
            if nombre.casefold() in nombres:
                copias[nombre.casefold()].append(Path(carpeta) / nombre)
    return copias


def preparar_archivo(requisito, descarga, copias, destino, informar, *, archivo_local=None):
    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destino.parent, prefix=".tecnotics-firmware-") as temporal:
        preparado = Path(temporal) / destino.name
        if descarga:
            descargar(requisito, descarga, preparado, informar)
        else:
            informar(0, None, f"Comprobando copias de {destino.name}…")
            nombres = tuple(dict.fromkeys(n.casefold() for n in (destino.name, *requisito.nombres_locales)))
            if archivo_local:
                if not requisito.archivo.verificable and archivo_local.name.casefold() not in nombres:
                    raise ValueError(f"Selecciona el archivo {destino.name}.")
                candidatas = [archivo_local]
            else:
                candidatas = [copia for nombre in nombres for copia in copias.get(nombre, ())]
            compatibles = [copia for copia in candidatas if presente(copia)
                           and (not requisito.archivo.verificable or coincide_firmware(copia, requisito))]
            if not compatibles:
                if archivo_local:
                    raise ValueError(f"El archivo seleccionado no coincide con el firmware esperado ({destino.name}).")
                raise ValueError("No se encontró una copia compatible en la carpeta seleccionada.")
            if not requisito.archivo.verificable and len(compatibles) > 1:
                raise ValueError("Hay varias copias con ese nombre. Usa Importar archivo y elige una.")
            copiar_archivo(compatibles[0], preparado, None)
            if requisito.archivo.verificable and not coincide_firmware(preparado, requisito):
                raise ValueError("La copia local cambió durante la importación.")
        publicar(preparado, destino)


def ejecutar_emulador(exe, argumentos, *, en_primer_plano=False):
    comando = [str(exe), *map(str, argumentos)]
    if en_primer_plano:
        proceso = subprocess.Popen(comando, cwd=exe.parent)
        return proceso.wait(timeout=600)
    return subprocess.run(comando, cwd=exe.parent, timeout=600, stdin=subprocess.DEVNULL,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).returncode


def preparar_config_vita(raiz, exe):
    config, datos = ruta_vita(raiz, exe)
    config = ruta_local(raiz, config)
    datos.mkdir(parents=True, exist_ok=True)
    original = config.read_bytes() if config.exists() else None
    texto = original.decode("utf-8-sig") if original is not None else "initial-setup: true\nshow-welcome: false\n"
    anterior = leer_pref_vita(texto)
    if not anterior or (exe.parent / anterior).resolve() != datos.resolve():
        # Vita3K lee su config.yml predeterminado antes de procesar --firmware.
        linea = f"pref-path: {json.dumps(datos.as_posix(), ensure_ascii=False)}"
        texto = PREF_VITA.sub(lambda _: linea, texto, count=1) if PREF_VITA.search(texto) else linea + "\n" + texto
        with tempfile.TemporaryDirectory(dir=config.parent) as temporal:
            preparado = Path(temporal) / config.name
            preparado.write_text(texto, encoding="utf-8")
            if original is None:
                publicar(preparado, config)
            else:
                if config.read_bytes() != original:
                    raise ValueError("La configuración de Vita3K cambió. Cierra el emulador e inténtalo nuevamente.")
                with tempfile.NamedTemporaryFile(prefix="config-firmware-", suffix=".yml.bak",
                                                 dir=config.parent, delete=False) as respaldo:
                    respaldo.write(original)
                preparado.replace(config)
    return datos


def rpcs3_termino(exe):
    for registro in (exe.parent / "log" / "RPCS3.log", exe.parent / "RPCS3.log"):
        if registro.is_file():
            with registro.open("rb") as archivo:
                archivo.seek(max(0, registro.stat().st_size - 65536))
                if b"Successfully installed PS3 firmware version " in archivo.read():
                    return True
    return False


def instalar_pup(raiz, requisito, destino, informar):
    exe = ruta_local(raiz, requisito.emulador)
    if requisito.tipo == "vita3k":
        preparar_config_vita(raiz, exe)
        informar(0, None, f"Vita3K está instalando {destino.name}…")
        codigo = ejecutar_emulador(exe, ("--firmware", destino))
    else:
        for marcador in requisito.instalado:
            ruta_local(raiz, marcador)
        # El RPCS3 de TeknoParrot abre su registro antes de crear la carpeta en el primer inicio.
        ruta_local(raiz, exe.parent / "log").mkdir(exist_ok=True)
        informar(0, None, f"RPCS3 está instalando el firmware de {requisito.sistema}…")
        codigo = ejecutar_emulador(exe, ("--headless", "--installfw", destino))
        if not instalado_en_emulador(requisito):
            informar(0, None, "Confirma el instalador de RPCS3 y cierra su ventana cuando termine…")
            codigo = ejecutar_emulador(exe, ("--installfw", destino), en_primer_plano=True)
    confirmado = instalado_en_emulador(requisito)
    if not confirmado or (codigo and (requisito.tipo != "rpcs3" or not rpcs3_termino(exe))):
        raise ValueError(f"{exe.name} no confirmó la instalación (estado {codigo}). "
                         "Revisa su registro y vuelve a comprobar.")


def importar_nca(origen, destino, informar):
    archivos = [ruta for ruta in sorted(origen.iterdir()) if NCA.fullmatch(ruta.name) and presente(ruta)]
    if not archivos:
        raise ValueError("Selecciona la carpeta que contiene los archivos .nca extraídos de tu consola.")
    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destino.parent, prefix=".tecnotics-firmware-") as temporal:
        preparado = Path(temporal) / destino.name
        preparado.mkdir()
        for indice, archivo in enumerate(archivos, 1):
            informar(indice - 1, len(archivos), "Copiando el firmware de Switch…")
            copiar_archivo(archivo, preparado / archivo.name, None)
        if destino.exists():
            destino.rmdir()  # Solo se permite retirar el directorio vacío que crea el emulador.
        publicar_directorio(preparado, destino)


def aplicar_firmware(raiz, filas, origen, informar):
    raiz = raiz.resolve()
    archivo_local = origen if origen and origen.is_file() else None
    if archivo_local and (len(filas) != 1 or filas[0].requisito.tipo in {"nca", "ryujinx"}):
        raise ValueError("Para importar un archivo elige una sola fila de firmware compatible.")
    if origen and not archivo_local and not origen.is_dir():
        raise ValueError("El archivo o la carpeta que elegiste ya no está disponible.")
    copias = {}
    if origen and not archivo_local:
        copias = indexar_copias(origen, [fila.requisito for fila in filas], informar)
    if origen or all(fila.requisito.paquete for fila in filas):
        publicadas = {}
    else:
        try:
            publicadas = descargas_retrobat()
        except (OSError, ValueError, KeyError):
            publicadas = {}
    resultados = []
    instalados = set()
    for fila in filas:
        requisito = fila.requisito
        nombre = requisito.destino.name
        try:
            destino = ruta_local(raiz, requisito.destino)
            estado = estado_firmware(requisito)
            if estado in {LISTO, "Verificado", "Presente · sin huella", "Detectado · validar en emulador"}:
                resultado = estado
            elif estado not in {FALTA, GUARDADO}:
                raise ValueError(f"{estado} en {destino}. Conserva una copia y resuelve el conflicto antes de reintentar.")
            elif requisito.grupo and (requisito.sistema, requisito.grupo) in instalados:
                resultado = "Alternativa cubierta"
            elif requisito.tipo == "nca" and origen:
                importar_nca(origen, destino, informar)
                resultado = "Copiado · valida el firmware en el emulador"
            elif requisito.tipo == "ryujinx":
                raise ValueError("Usa Abrir Ryujinx y el menú Tools → Install Firmware.")
            else:
                if estado == FALTA:
                    descarga = None if origen else descarga_disponible(raiz, requisito, publicadas)
                    if not (descarga or origen):
                        raise ValueError("No hay descarga oficial. Elige una copia local.")
                    preparar_archivo(requisito, descarga, copias, destino, informar, archivo_local=archivo_local)
                if requisito.paquete:
                    if requisito.emulador.is_file():
                        instalar_pup(raiz, requisito, destino, informar)
                        resultado = LISTO
                    else:
                        resultado = (f"{GUARDADO} en {destino.relative_to(raiz)}. "
                                     f"Falta {requisito.emulador.name} para instalarlo.")
                else:
                    resultado = "Copiado y verificado" if requisito.archivo.verificable else "Copiado"
            if requisito.grupo:
                instalados.add((requisito.sistema, requisito.grupo))
        except subprocess.TimeoutExpired:
            resultado = "El emulador agotó el tiempo de espera. Ciérralo y vuelve a comprobar."
        except (OSError, ValueError, ET.ParseError, subprocess.SubprocessError) as error:
            resultado = str(error)
        resultados.append(f"{requisito.sistema} · {nombre} — {resultado}")
    return resultados


def abrir_ryujinx(raiz, requisito):
    raiz = raiz.resolve()
    exe = ruta_local(raiz, requisito.emulador)
    datos = ruta_local(raiz, raiz / "saves" / "switch" / "ryujinx" / "portable")
    datos.mkdir(parents=True, exist_ok=True)
    subprocess.Popen([str(exe), "-r", str(datos)], cwd=exe.parent)
