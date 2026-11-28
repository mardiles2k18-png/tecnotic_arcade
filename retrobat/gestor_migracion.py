"""Comparación y copia de bibliotecas de RetroBat a otra instalación o a un respaldo."""
from copy import deepcopy
from collections import defaultdict
from dataclasses import dataclass, field, replace
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
import unicodedata
import xml.etree.ElementTree as ET

from gestor_biblioteca import catalogo_juegos
from gestor_core import (ALIAS_SISTEMAS, CARPETAS_MULTIMEDIA, Sistema, catalogo_bios, copiar_archivo, nombre_seguro,
                         publicar, sistemas_instalados, archivo_sistemas_retrobat)
from gestor_duplicados import es_enlace_respaldo, marca_archivo, mismo_archivo, sha256


CAMPOS_MEDIOS = frozenset({
    "image", "thumbnail", "marquee", "video", "manual", "fanart", "titleshot", "screenshot",
    "boxart", "boxback", "box3d", "cartridge", "wheel", "logo", "map", "bezel", "mix",
    "music", "audio", "sounds", "image2", "image3", "physicalmedia",
})
DESCRIPTORES = frozenset({".cue", ".gdi", ".m3u", ".m3u8", ".ccd", ".mds"})
FORMATOS_RESPALDO = {
    "naomi": ".zip .7z .lst .dat",
    "naomi2": ".zip .7z .lst .dat",
    "atomiswave": ".zip .7z .lst .dat",
    "mame": ".zip .7z",
    "fbneo": ".zip .7z",
    "nes": ".nes .fds .zip .7z",
    "snes": ".sfc .smc .zip .7z",
    "n64": ".n64 .z64 .v64 .zip .7z",
    "gb": ".gb .zip .7z",
    "gbc": ".gbc .zip .7z",
    "gba": ".gba .zip .7z",
    "nds": ".nds .zip .7z",
    "megadrive": ".md .gen .smd .bin .zip .7z",
    "dreamcast": ".gdi .cdi .chd .cue .m3u",
    "saturn": ".cue .chd .m3u .ccd .mds",
    "psx": ".cue .chd .m3u .pbp .ccd .mds",
    "ps2": ".iso .chd .cso .gz",
    "psp": ".iso .cso .chd .pbp",
    "gamecube": ".iso .gcm .rvz .gcz",
    "wii": ".iso .wbfs .rvz .gcz",
    "wiiu": ".wua .wud .wux .rpx",
    "xbox": ".iso .xbe .cci",
    "xbox360": ".iso .xex",
}


@dataclass(frozen=True)
class JuegoMigracion:
    clave: str
    nombre: str
    estado: str
    _archivos: tuple = field(default=(), repr=False)
    _catalogo: object = field(default=None, repr=False)
    en_destino: bool = False


@dataclass(frozen=True)
class SistemaMigracion:
    clave: str
    nombre: str
    estado: str
    juegos: tuple
    bios_pendientes: int
    _bios: tuple = field(default=(), repr=False)
    _extra: tuple = field(default=(), repr=False)
    _destino: object = field(default=None, repr=False)
    _catalogo_destino: bytes | None = field(default=None, repr=False)
    _carpetas: tuple = field(default=(), repr=False)
    carpeta_origen: Path | None = None

    @property
    def conteo(self):
        return (
            sum(j.estado != "solo_destino" for j in self.juegos),
            sum(j.en_destino for j in self.juegos),
            sum(not j.en_destino or j.estado == "incompleto" for j in self.juegos),
        )

    @property
    def tiene_faltantes(self):
        return bool(self.bios_pendientes or self._extra or self._carpetas
                    or any(j.estado in {"faltante", "incompleto", "recursos"} for j in self.juegos))


@dataclass(frozen=True)
class Comparacion:
    origen: Path
    destino: Path
    sistemas: tuple
    avisos: tuple
    carpeta_respaldo: bool
    _bios_compartidas: tuple = field(default=(), repr=False)
    origen_retrobat: bool = True

    @property
    def bios_compartidas_pendientes(self):
        return len(self._bios_compartidas)


@dataclass(frozen=True)
class ArchivoMigracion:
    origen: Path
    destino: Path
    marca_origen: tuple
    marca_destino: tuple | None

    @property
    def bytes(self):
        return self.marca_origen[-1]


@dataclass(frozen=True)
class CatalogoMigracion:
    destino: Path
    original: bytes | None
    contenido: bytes


@dataclass(frozen=True)
class PlanMigracion:
    origen: Path
    destino: Path
    archivos: tuple
    catalogos: tuple
    avisos: tuple
    bytes_totales: int
    espacio_disponible: int
    carpeta_respaldo: bool


@dataclass(frozen=True)
class ResultadoMigracion:
    archivos: int
    catalogos: int
    respaldo: Path | None


def _local(base, ruta):
    """Comprueba cada componente sin seguir enlaces ni uniones de Windows."""
    try:
        partes = ruta.relative_to(base).parts
    except ValueError:
        raise ValueError(f"La ruta está fuera de la instalación: {ruta}") from None
    actual = base
    for parte in partes:
        nombre_seguro(parte)
        actual /= parte
        try:
            info = actual.lstat()
        except FileNotFoundError:
            continue
        if es_enlace_respaldo(info) or not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
            raise ValueError(f"La migración no puede usar un enlace o archivo especial: {actual}")
    return ruta


def _clave(ruta):
    return ruta.as_posix().casefold()


def _rutas_instalaciones(origen, destino):
    origen = Path(origen).resolve(strict=True)
    destino = Path(os.path.abspath(destino))
    _local(Path(destino.anchor), destino)
    destino = destino.resolve()
    if origen.is_relative_to(destino) or destino.is_relative_to(origen):
        raise ValueError("El origen y el destino deben ser carpetas distintas y separadas.")
    if destino.exists() and not destino.is_dir():
        raise ValueError("El destino debe ser una carpeta.")
    origen_retrobat = _local(origen, origen / "retrobat.exe").is_file()
    carpeta_respaldo = not _local(destino, destino / "retrobat.exe").is_file()
    for base in (origen, destino):
        _local(base, base / "roms")
        _local(base, base / "bios")
    if origen_retrobat:
        _local(origen, archivo_sistemas_retrobat(origen))
        _local(origen, origen / "system" / "modules" / "rb_gui" / "bios_local.json")
    if not carpeta_respaldo:
        _local(destino, archivo_sistemas_retrobat(destino))
    return origen, destino, carpeta_respaldo, origen_retrobat


def _espacio_disponible(destino):
    for carpeta in (destino, *destino.parents):
        if carpeta.is_dir():
            return shutil.disk_usage(carpeta).free
    raise ValueError(f"No se puede acceder a la unidad de destino: {destino.anchor}")


def _entrada(carpeta, referencia):
    texto = referencia.strip().replace("\\", "/")
    if not texto or "://" in texto or texto.startswith("~/"):
        return None
    candidata = carpeta / texto
    # absolute() no resuelve enlaces. La comprobación de seguridad usa el camino léxico.
    candidata = Path(os.path.abspath(candidata))
    if not candidata.is_relative_to(carpeta) or candidata == carpeta:
        return None
    return _local(carpeta, candidata)


def _leer_catalogo(sistema):
    _local(sistema.carpeta, sistema.carpeta / "gamelist.xml")
    archivo, original, lista, nodos = catalogo_juegos(sistema)
    indice = {}
    for entradas in nodos.values():
        for etiqueta in entradas:
            relativa = _entrada(sistema.carpeta, etiqueta.findtext("path", ""))
            if relativa is not None:
                indice.setdefault(_clave(relativa.relative_to(sistema.carpeta)), []).append(etiqueta)
    return archivo, original, lista, indice


def _inventario(sistema):
    juegos = {}
    if sistema is None or not sistema.carpeta.is_dir():
        return juegos
    for carpeta, dirs, archivos in os.walk(sistema.carpeta):
        carpeta = Path(carpeta)
        explorar = []
        elegibles = []
        for nombre in dirs:
            if nombre.startswith(".") or nombre.casefold() in CARPETAS_MULTIMEDIA:
                continue
            ruta = _local(sistema.carpeta, carpeta / nombre)
            if ruta.suffix.casefold() in sistema.extensiones:
                elegibles.append(nombre)
            else:
                explorar.append(nombre)
        dirs[:] = explorar
        for nombre in elegibles + archivos:
            ruta = carpeta / nombre
            if ruta.suffix.casefold() not in sistema.extensiones or nombre.casefold() == "gamelist.xml":
                continue
            _local(sistema.carpeta, ruta)
            clave = _clave(ruta.relative_to(sistema.carpeta))
            if clave in juegos:
                raise ValueError(f"Hay dos juegos con la misma ruta en Windows: {ruta}")
            juegos[clave] = ruta

    componentes = set()
    for ruta in juegos.values():
        if ruta.suffix.casefold() not in DESCRIPTORES:
            continue
        try:
            for archivo in _dependencias(ruta, sistema):
                if not archivo.is_relative_to(ruta):
                    componentes.add(_clave(archivo.relative_to(sistema.carpeta)))
        except (OSError, ValueError):
            # La comparación del juego informará si la copia de origen tiene dependencias incompletas.
            continue
    for clave in componentes:
        juegos.pop(clave, None)
    return juegos


def _archivos(carpeta, base):
    if carpeta.is_file():
        yield _local(base, carpeta)
        return
    for actual, dirs, archivos in os.walk(carpeta):
        actual = Path(actual)
        for nombre in dirs:
            _local(base, actual / nombre)
        for nombre in archivos:
            yield _local(base, actual / nombre)


def _dependencias(ruta, sistema):
    carpeta = sistema.carpeta
    pendientes = [ruta]
    vistos = set()
    while pendientes:
        actual = pendientes.pop()
        if actual in vistos:
            continue
        vistos.add(actual)
        yield from _archivos(actual, carpeta)
        sufijo = actual.suffix.casefold()
        if not actual.is_file():
            continue
        if sistema.es_mame and sufijo in {".zip", ".7z"}:
            discos = _local(carpeta, actual.with_suffix(""))
            if discos.is_dir():
                pendientes.extend(p for p in _archivos(discos, carpeta) if p.suffix.lower() in {".chd", ".img"})
        if sufijo not in DESCRIPTORES:
            continue
        if sufijo in {".ccd", ".mds"}:
            extensiones = (".img", ".sub") if sufijo == ".ccd" else (".mdf",)
            referencias = [actual.with_suffix(ext).name for ext in extensiones if actual.with_suffix(ext).exists()]
        else:
            lineas = actual.read_text(encoding="utf-8-sig", errors="replace").splitlines()
            if sufijo == ".cue":
                referencias = [m[0] or m[1] for m in re.findall(r'^\s*FILE\s+(?:"([^"]+)"|(\S+))', "\n".join(lineas), re.I | re.M)]
            elif sufijo == ".gdi":
                referencias = [m[0] or m[1] for m in re.findall(r'^\s*\d+\s+\d+\s+\d+\s+\d+\s+(?:"([^"]+)"|(\S+))', "\n".join(lineas), re.M)]
            else:
                referencias = [linea.strip().strip('"') for linea in lineas if linea.strip() and not linea.lstrip().startswith("#")]
        for referencia in referencias:
            ruta_ref = Path(referencia.replace("\\", "/"))
            if ruta_ref.is_absolute() or ruta_ref.drive:
                raise ValueError(f"La referencia absoluta de {actual.name} requiere ajuste manual: {referencia}")
            candidato = _entrada(carpeta, str(actual.parent / ruta_ref))
            if not candidato or not candidato.is_file():
                raise ValueError(f"Falta un archivo requerido por {actual.name}: {referencia}")
            pendientes.append(candidato)


def _candidato(origen, destino):
    marca_destino = marca_archivo(destino) if destino.is_file() else None
    if destino.exists() and marca_destino is None:
        raise ValueError(f"El destino está ocupado por una carpeta: {destino}")
    return ArchivoMigracion(origen, destino, marca_archivo(origen), marca_destino)


def _bios(origen, destino, sistema, datos, avisos):
    archivos = []
    for entrada in datos.get(sistema.identificador, {}).get("biosFiles", ()):
        ruta = str(entrada.get("file", "")).replace("\\", "/")
        local = _entrada(origen, ruta)
        if local is None or not local.is_relative_to(origen / "bios"):
            avisos.append(f"{sistema.nombre}: entrada de BIOS fuera de la carpeta bios: {ruta}")
            continue
        relativa = local.relative_to(origen)
        hacia = _local(destino, destino / relativa)
        if local.is_file():
            if not hacia.exists():
                archivos.append(_candidato(local, hacia))
            elif hacia.is_file() and not mismo_archivo(local, hacia):
                avisos.append(f"BIOS conservada en el destino: {relativa.as_posix()}")
    return tuple(archivos)


def _medio_origen(sistema, destino, nodo, campo, archivos, avisos):
    texto = campo.text or ""
    try:
        ruta = _entrada(sistema.carpeta, texto)
    except ValueError:
        ruta = None
    if not ruta or not ruta.is_file() or ruta.name.casefold() == "gamelist.xml":
        avisos.append(f"{nodo.findtext('name') or nodo.findtext('path')}: recurso no disponible: {texto}")
        return False
    relativa = ruta.relative_to(sistema.carpeta)
    nueva = _local(destino.carpeta, destino.carpeta / relativa)
    if nueva.is_dir():
        avisos.append(f"{nodo.findtext('name') or nodo.findtext('path')}: ruta de recurso ocupada: {relativa}")
        return False
    if not nueva.exists():
        archivos.append(_candidato(ruta, nueva))
    campo.text = "./" + relativa.as_posix()
    return True


def _ficha(sistema, destino, ruta, nodos, existentes, archivos, avisos, ruta_destino=None):
    if not nodos:
        return None
    origen = nodos[0]
    anterior = existentes[0] if existentes else None
    nuevo = deepcopy(anterior) if anterior is not None else deepcopy(origen)
    if anterior is None:
        relativa = ruta_destino.relative_to(destino.carpeta) if ruta_destino else ruta.relative_to(sistema.carpeta)
        nuevo.find("path").text = "./" + relativa.as_posix()
        for campo in list(nuevo):
            if campo.tag in CAMPOS_MEDIOS and not _medio_origen(sistema, destino, origen, campo, archivos, avisos):
                nuevo.remove(campo)
        return nuevo
    for campo in origen:
        if campo.tag == "path" or not (campo.text or "").strip():
            continue
        tiene = nuevo.find(campo.tag)
        copia = deepcopy(campo)
        if campo.tag in CAMPOS_MEDIOS:
            texto = (tiene.text or "").strip() if tiene is not None else ""
            referencia = _entrada(destino.carpeta, texto)
            if (referencia is not None and referencia.is_file()) or (texto and referencia is None):
                continue
            if not _medio_origen(sistema, destino, origen, copia, archivos, avisos):
                continue
        elif tiene is not None and (tiene.text or "").strip():
            continue
        if tiene is not None:
            nuevo.remove(tiene)
        nuevo.append(copia)
    return nuevo if ET.tostring(nuevo) != ET.tostring(anterior) else None


def _juego(origen, destino, clave, ruta, otra, fichas, fichas_destino, avisos):
    nodos = fichas.get(clave, ())
    titulo = (nodos[0].findtext("name") or ruta.stem) if nodos else ruta.stem
    if ruta.suffix.casefold() in {".lnk", ".url"}:
        avisos.append(f"{origen.nombre} · {titulo}: el acceso directo requiere migración manual.")
        return JuegoMigracion(clave, titulo, "no_compatible", en_destino=otra is not None)
    if origen.identificador == "teknoparrot":
        avisos.append(f"TeknoParrot · {titulo}: los ejecutables y perfiles deben revisarse en el destino.")
    try:
        paquete = tuple(dict.fromkeys(_dependencias(ruta, origen)))
    except (OSError, ValueError) as error:
        avisos.append(str(error))
        return JuegoMigracion(clave, titulo, "no_compatible", en_destino=otra is not None)
    archivos = []
    conflicto = False
    incompleto = False
    for archivo in paquete:
        hacia = destino.carpeta / archivo.relative_to(origen.carpeta)
        if otra is not None and archivo == ruta:
            hacia = otra
        elif otra is not None and ruta.is_dir() and archivo.is_relative_to(ruta):
            hacia = otra / archivo.relative_to(ruta)
        _local(destino.carpeta, hacia)
        if not hacia.is_file() or not mismo_archivo(archivo, hacia):
            registro = _candidato(archivo, hacia)
            conflicto |= registro.marca_destino is not None
            incompleto |= registro.marca_destino is None
            archivos.append(registro)
    medios = []
    clave_destino = _clave(otra.relative_to(destino.carpeta)) if otra else clave
    ficha = _ficha(origen, destino, ruta, nodos, fichas_destino.get(clave_destino, ()), medios, avisos, otra)
    estado = "conflicto" if conflicto else "faltante" if otra is None else "incompleto" if incompleto else (
        "recursos" if ficha is not None or medios or archivos else "igual")
    return JuegoMigracion(clave_destino, titulo, estado, tuple(archivos + medios), ficha, en_destino=otra is not None)


def _comparar_juegos(origen, destino, archivos_o, archivos_d, fichas_o, fichas_d, avisos):
    por_tamano = defaultdict(list)
    huellas = {}
    for clave, ruta in archivos_d.items():
        if ruta.suffix.casefold() not in DESCRIPTORES and ruta.is_file():
            por_tamano[ruta.stat().st_size].append((clave, ruta))

    def huella(ruta):
        if ruta not in huellas:
            huellas[ruta] = sha256(ruta)
        return huellas[ruta]

    usados = set(archivos_o) & set(archivos_d)
    juegos = []
    for clave, ruta in archivos_o.items():
        otra = archivos_d.get(clave)
        if otra is None and ruta.suffix.casefold() not in DESCRIPTORES and ruta.is_file():
            for clave_d, candidata in por_tamano[ruta.stat().st_size]:
                if clave_d not in usados and huella(ruta) == huella(candidata):
                    otra = candidata
                    usados.add(clave_d)
                    break
        juegos.append(_juego(origen, destino, clave, ruta, otra, fichas_o, fichas_d, avisos))
    juegos.extend(JuegoMigracion(k, ruta.stem, "solo_destino", en_destino=True)
                  for k, ruta in archivos_d.items() if k not in usados)
    return juegos


def _medios_sistema(origen, destino):
    for carpeta in origen.carpeta.iterdir():
        if carpeta.name.casefold() not in CARPETAS_MULTIMEDIA:
            continue
        _local(origen.carpeta, carpeta)
        for medio in _archivos(carpeta, origen.carpeta):
            hacia = _local(destino.carpeta, destino.carpeta / medio.relative_to(origen.carpeta))
            if not hacia.exists():
                yield _candidato(medio, hacia)


def _carpeta_faltante(origen, destino, relativa):
    for archivo in _archivos(_local(origen, origen / relativa), origen):
        hacia = _local(destino, destino / archivo.relative_to(origen))
        if not hacia.exists():
            yield _candidato(archivo, hacia)


def _correspondencias(sistemas_o, sistemas_d):
    # es_systems.cfg también declara sistemas cuya carpeta aún no existe.
    por_carpetas = {(s.identificador, s.carpeta.name.casefold()): k for k, s in sistemas_d.items()}
    for clave, sistema in sistemas_o.items():
        destino = por_carpetas.get((sistema.identificador, sistema.carpeta.name.casefold()))
        if destino is None and clave in sistemas_d and sistemas_d[clave].identificador == sistema.identificador:
            destino = clave
        yield clave, destino


def _nombre_sistema(nombre):
    texto = unicodedata.normalize("NFKD", nombre.casefold())
    texto = re.sub(r"^(?:roms|games|juegos)\W+(?:de\W+)?", "", texto)
    return re.sub(r"[^a-z0-9]", "", texto)


def _biblioteca_externa(raiz, modelos, avisos, *, inferir=True):
    nombres = defaultdict(set)
    formatos = defaultdict(set)
    for clave, sistema in modelos.items():
        aliases = ALIAS_SISTEMAS.get(sistema.identificador, ())
        for nombre in (clave, sistema.nombre, sistema.carpeta.name, *aliases):
            nombres[_nombre_sistema(nombre)].add(clave)
        for extension in sistema.extensiones:
            formatos[extension].add(clave)

    def error_recorrido(error):
        avisos.append(str(error))

    sistemas = {}
    for directorio, subdirectorios, archivos in os.walk(raiz, onerror=error_recorrido):
        carpeta = Path(directorio)
        subdirectorios[:] = sorted(
            nombre for nombre in subdirectorios
            if not nombre.startswith(".")
            and nombre.casefold() not in CARPETAS_MULTIMEDIA | {"bios", "system", "respaldo_migracion"}
            and not es_enlace_respaldo((carpeta / nombre).lstat())
        )
        coincidencias = nombres.get(_nombre_sistema(carpeta.name), set())
        if not coincidencias and inferir:
            extensiones = {Path(nombre).suffix.casefold() for nombre in archivos}
            # Una extensión compartida por varios sistemas requiere un nombre de carpeta.
            candidatos = [formatos[e] for e in extensiones if e in formatos]
            if any(len(candidatos_extension) == 1 for candidatos_extension in candidatos):
                coincidencias = set.intersection(*candidatos)
        if len(coincidencias) != 1:
            if any(Path(nombre).suffix.casefold() in formatos for nombre in archivos):
                avisos.append(f"Identifica el sistema de «{carpeta}» con el nombre de su carpeta.")
            continue
        clave = next(iter(coincidencias))
        sistema = replace(modelos[clave], carpeta=carpeta)
        if not _inventario(sistema):
            continue
        if clave in sistemas:
            avisos.append(f"Para incorporar también «{carpeta}», selecciónala como origen por separado.")
        else:
            sistemas[clave] = sistema
        subdirectorios.clear()
    return sistemas


def comparar_instalaciones(origen, destino, informar=None, *, referencia=None):
    origen, destino, carpeta_respaldo, origen_retrobat = _rutas_instalaciones(origen, destino)
    avisos = []
    sistemas_d = {} if carpeta_respaldo else sistemas_instalados(destino)
    if origen_retrobat:
        sistemas_o = sistemas_instalados(origen)
    else:
        modelos = sistemas_d
        if carpeta_respaldo:
            modelos = {clave: Sistema(clave, clave, Path(clave), frozenset(formatos.split()))
                       for clave, formatos in FORMATOS_RESPALDO.items()}
            if referencia and (referencia / "retrobat.exe").is_file():
                modelos.update(sistemas_instalados(referencia))
        sistemas_o = _biblioteca_externa(origen, modelos, avisos)
    if carpeta_respaldo:
        existentes = _biblioteca_externa(destino, sistemas_o, avisos, inferir=False) if destino.is_dir() else {}
        sistemas_d = {
            clave: existentes.get(clave) or replace(sistema, carpeta=destino / (
                sistema.carpeta.relative_to(origen) if origen_retrobat else Path("roms") / modelos[clave].carpeta.name))
            for clave, sistema in sistemas_o.items()
        }
    datos_bios = catalogo_bios(origen) if origen_retrobat else {}
    resultados = []
    vistos = set()
    for i, (clave, clave_d) in enumerate(_correspondencias(sistemas_o, sistemas_d)):
        if informar:
            informar(i + 1, len(sistemas_o), "Comparando sistemas y juegos…")
        s = sistemas_o[clave]
        _local(origen, s.carpeta)
        archivos_o = _inventario(s)
        if not archivos_o:
            continue
        d = sistemas_d.get(clave_d)
        if d is None:
            avisos.append(f"{s.nombre}: el sistema no está definido en el RetroBat de destino.")
            juegos = tuple(JuegoMigracion(k, ruta.stem, "no_disponible") for k, ruta in sorted(archivos_o.items()))
            resultados.append(SistemaMigracion(clave, s.nombre, "no_compatible", juegos, 0))
            continue
        _local(destino, d.carpeta)
        vistos.add(clave_d)
        archivos_d = _inventario(d)
        _, _, _, fichas_o = _leer_catalogo(s)
        _, catalogo_d, _, fichas_d = _leer_catalogo(d)
        bios = _bios(origen, destino, s, datos_bios, avisos) if origen_retrobat else ()
        juegos = _comparar_juegos(s, d, archivos_o, archivos_d, fichas_o, fichas_d, avisos)
        extras = list(_medios_sistema(s, d))
        cargas = Path("system") / "loadingscreens"
        extras.extend(_carpeta_faltante(origen, destino, cargas / s.identificador))
        extras.extend(_carpeta_faltante(origen, destino, cargas / (s.identificador + ".mp4")))
        carpetas = []
        for clave_ficha, nodos in fichas_o.items():
            if nodos[0].tag != "folder":
                continue
            ruta = _entrada(s.carpeta, nodos[0].findtext("path", ""))
            if ruta is not None and any(k.startswith(clave_ficha + "/") for k in archivos_o):
                ficha = _ficha(s, d, ruta, nodos, fichas_d.get(clave_ficha, ()), extras, avisos)
                if ficha is not None:
                    carpetas.append((clave_ficha, ficha))
        estado = "faltante" if not archivos_d else (
            "diferente" if bios or extras or carpetas or any(j.estado != "igual" for j in juegos) else "igual")
        resultados.append(SistemaMigracion(clave, s.nombre, estado,
                                           tuple(sorted(juegos, key=lambda j: j.nombre.casefold())),
                                           len(bios), bios, tuple(extras), d, catalogo_d, tuple(carpetas), s.carpeta))
    for clave, d in sistemas_d.items():
        if clave not in vistos:
            _local(destino, d.carpeta)
            archivos = _inventario(d)
            if archivos:
                juegos = tuple(JuegoMigracion(k, r.stem, "solo_destino", en_destino=True) for k, r in sorted(archivos.items()))
                resultados.append(SistemaMigracion(clave, d.nombre, "solo_destino", juegos, 0))
    bios_compartidas = tuple(_carpeta_faltante(origen, destino, Path("bios")))
    return Comparacion(origen, destino, tuple(sorted(resultados, key=lambda s: s.nombre.casefold())),
                       tuple(dict.fromkeys(avisos)), carpeta_respaldo, bios_compartidas, origen_retrobat)


def _mezclar_catalogo(sistema, fichas):
    destino, original, lista, existentes = _leer_catalogo(sistema._destino)
    if original != sistema._catalogo_destino:
        raise ValueError(f"RetroBat modificó {destino}. Vuelve a comparar antes de migrar.")
    for clave, nueva in fichas:
        candidatas = existentes.get(clave, ())
        if candidatas:
            anterior = candidatas[0]
            indice = list(lista).index(anterior)
            lista.remove(anterior)
            lista.insert(indice, nueva)
        else:
            lista.append(nueva)
    return CatalogoMigracion(destino, original, ET.tostring(lista, encoding="utf-8", xml_declaration=True))


def preparar_migracion(comparacion, seleccion, reemplazos=(), *, incluir_bios_compartidas=False):
    archivos = {}
    catalogos = []
    avisos = list(comparacion.avisos)
    reemplazos = set(reemplazos)

    def agregar(registro):
        clave = _clave(registro.destino)
        anterior = archivos.setdefault(clave, registro)
        if registro != anterior and not mismo_archivo(anterior.origen, registro.origen):
            raise ValueError(f"Dos archivos seleccionados compiten por {registro.destino}.")

    for sistema in comparacion.sistemas:
        if sistema.clave not in seleccion or sistema.estado in {"no_compatible", "solo_destino"}:
            continue
        elegidos = seleccion[sistema.clave]
        fichas = []
        for juego in sistema.juegos:
            if elegidos is not None and juego.clave not in elegidos:
                continue
            if juego.estado == "conflicto" and (sistema.clave, juego.clave) not in reemplazos:
                avisos.append(f"{sistema.nombre} · {juego.nombre}: se conserva el archivo del destino.")
                continue
            if juego.estado not in {"faltante", "incompleto", "conflicto", "recursos"}:
                continue
            for archivo in juego._archivos:
                agregar(archivo)
            if juego._catalogo is not None:
                fichas.append((juego.clave, juego._catalogo))
        for bios in sistema._bios:
            agregar(bios)
        if elegidos is None:
            for medio in sistema._extra:
                agregar(medio)
            fichas.extend(sistema._carpetas)
        if fichas:
            catalogos.append(_mezclar_catalogo(sistema, fichas))
    if incluir_bios_compartidas:
        for bios in comparacion._bios_compartidas:
            agregar(bios)
    archivos = tuple(archivos.values())
    bytes_totales = sum(a.bytes + (a.marca_destino[-1] if a.marca_destino else 0) for a in archivos)
    bytes_totales += sum(len(c.contenido) + len(c.original or b"") for c in catalogos)
    return PlanMigracion(comparacion.origen, comparacion.destino, archivos, tuple(catalogos),
                         tuple(dict.fromkeys(avisos)), bytes_totales, _espacio_disponible(comparacion.destino),
                         comparacion.carpeta_respaldo)


def aplicar_migracion(plan, informar=None):
    origen, destino, carpeta_respaldo, _ = _rutas_instalaciones(plan.origen, plan.destino)
    if carpeta_respaldo != plan.carpeta_respaldo:
        raise ValueError("Cambió el tipo de destino. Vuelve a comparar antes de copiar.")
    if _espacio_disponible(destino) < plan.bytes_totales:
        raise OSError("El destino no tiene espacio suficiente para la migración y sus respaldos.")
    if not plan.archivos and not plan.catalogos:
        return ResultadoMigracion(0, 0, None)

    def comprobar(archivo):
        actual = _local(destino, archivo.destino)
        if ((marca_archivo(actual) if actual.exists() else None) != archivo.marca_destino
                or marca_archivo(_local(origen, archivo.origen)) != archivo.marca_origen):
            raise ValueError(f"Un archivo cambió después de comparar: {archivo.destino}. Vuelve a comparar.")

    def comprobar_catalogo(catalogo):
        ruta = _local(destino, catalogo.destino)
        actual = ruta.read_bytes() if ruta.exists() else None
        if actual != catalogo.original:
            raise ValueError(f"El catálogo cambió después de preparar la copia: {ruta}. Vuelve a comparar.")

    hechos = 0

    def avanzar(n):
        nonlocal hechos
        hechos += n
        if informar:
            informar(hechos, plan.bytes_totales, "Copiando archivos de RetroBat…")

    respaldo = None
    publicados = []
    destino.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".migracion-", dir=destino) as temporal:
        preparados = []
        for archivo in plan.archivos:
            comprobar(archivo)
            ruta = Path(temporal) / str(len(preparados))
            copiar_archivo(archivo.origen, ruta, avanzar)
            comprobar(archivo)
            preparados.append((archivo.destino, ruta, archivo.marca_destino is not None, comprobar, archivo))
        for catalogo in plan.catalogos:
            comprobar_catalogo(catalogo)
            ruta = Path(temporal) / str(len(preparados))
            ruta.write_bytes(catalogo.contenido)
            avanzar(len(catalogo.contenido))
            preparados.append((catalogo.destino, ruta, catalogo.original is not None, comprobar_catalogo, catalogo))
        try:
            for actual, nuevo, reemplazar, validar, dato in preparados:
                validar(dato)
                actual.parent.mkdir(parents=True, exist_ok=True)
                copia = None
                if reemplazar:
                    if respaldo is None:
                        carpeta = _local(destino, destino / "user" / "tecnotics-gestor" / "respaldos-migracion")
                        carpeta.mkdir(parents=True, exist_ok=True)
                        respaldo = Path(tempfile.mkdtemp(prefix="migracion-", dir=carpeta))
                    copia = respaldo / actual.relative_to(destino)
                    copia.parent.mkdir(parents=True, exist_ok=True)
                    copiar_archivo(actual, copia, avanzar)
                    validar(dato)
                    nuevo.replace(actual)
                else:
                    publicar(nuevo, actual)
                publicados.append((actual, copia))
        except (OSError, ValueError):
            for actual, copia in reversed(publicados):
                if copia:
                    copia.replace(actual)
                else:
                    actual.unlink()
            raise
    return ResultadoMigracion(len(plan.archivos), len(plan.catalogos), respaldo)
