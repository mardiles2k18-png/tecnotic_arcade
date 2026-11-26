"""Preparación de TeknoParrot para el lanzador oficial de RetroBat."""
from collections import Counter
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from functools import lru_cache
import json
import os
from pathlib import Path
import re
import tempfile
import unicodedata
import xml.etree.ElementTree as ET

from gestor_core import copiar, nombre_seguro, publicar, publicar_directorio, sistemas_instalados
from gestor_duplicados import clave_titulo, marca_archivo
from gestor_teknoparrot_archivos import Contenido, extraer, inicio_archivado, inspeccionar

FORMATOS = (".teknoparrot", ".parrot", ".game")
COMPRIMIDOS = {".zip", ".7z", ".rar"}
BINARIOS = {".exe", ".elf", ".bin", ".x64", ".x86"}
# Referencias de las fichas oficiales para estos perfiles sin ExecutableName.
EJECUTABLES_DE_FICHAS = {
    "bbcf": "game.exe",
    "bbcp": "game.exe",
    "arcanaheart3exboard": "AH30.exe;game.exe",
    "bladestrangers": "himekaku.exe",
}


def carpeta_emulador(raiz):
    return raiz / "emulators" / "teknoparrot"


def sistema_teknoparrot(raiz):
    sistema = sistemas_instalados(raiz).get("teknoparrot")
    if sistema is None or not sistema.extensiones.intersection(FORMATOS):
        raise ValueError("Esta instalación no declara el sistema TeknoParrot. Actualiza RetroBat.")
    return sistema


@dataclass(frozen=True)
class Perfil:
    plantilla: Path
    titulo: str
    esperado: frozenset[str]
    secundario: frozenset[str]
    suscripcion: bool

    @property
    def id(self):
        return self.plantilla.stem


@dataclass(frozen=True)
class RevisionArchivo:
    etiqueta: str
    esperados: frozenset[str]
    elegido: Path | None
    coincidencias: tuple[Path, ...]


@dataclass
class Juego:
    origen: Path
    perfil: Perfil | None = None
    ejecutable: Path | None = None
    secundario: Path | None = None
    contenido: Contenido | None = None
    marca: tuple | None = None
    error: str = ""
    revision: tuple[RevisionArchivo, ...] = ()
    # Lo que el Gestor eligió solo, para avisar al usuario de que conviene revisarlo.
    perfil_por_nombre: bool = False
    deducidos: set = field(default_factory=set)


def ejecutables_retrobat(archivo):
    if archivo is None:
        return {}
    try:
        texto = archivo.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        return {}
    # RetroBat usa bloques de nivel superior por perfil, con el campo executable dentro del bloque.
    ejecutables = {}
    perfil = None
    for linea in texto.splitlines():
        if cabecera := re.fullmatch(r"([^\s#].*?):\s*(?:#.*)?", linea):
            perfil = cabecera[1].strip("\"'").casefold()
        elif perfil and (campo := re.fullmatch(r"\s+executable:\s*(.*?)\s*(?:\s+#.*)?", linea)):
            ejecutables[perfil] = nombres_ejecutables(campo[1].strip("\"'"))
    return ejecutables


def perfiles_locales(emulador, archivo_ejecutables=None):
    perfiles = []
    ejecutables = ejecutables_retrobat(archivo_ejecutables)
    for ruta in sorted((emulador / "GameProfiles").glob("*.xml")):
        try:
            xml = ET.parse(ruta).getroot()
            if xml.tag != "GameProfile" or xml.findtext("DevOnly", "").lower() == "true":
                continue
            nombre_seguro(ruta.stem)
        except (OSError, ValueError, ET.ParseError):
            continue
        titulo = xml.findtext("GameName", "").strip()
        if not titulo:
            try:
                datos = json.loads((emulador / "Metadata" / f"{ruta.stem}.json").read_text(encoding="utf-8-sig"))
                if isinstance(datos, dict) and isinstance(datos.get("game_name"), str):
                    titulo = datos["game_name"]
            except (OSError, ValueError):
                pass
        id_ = ruta.stem.casefold()
        primario = (nombres_ejecutables(xml.findtext("ExecutableName", "")) or ejecutables.get(id_)
                    or nombres_ejecutables(EJECUTABLES_DE_FICHAS.get(id_, "")))
        secundario = nombres_ejecutables(xml.findtext("ExecutableName2", ""))
        if xml.findtext("HasTwoExecutables", "").lower() == "true" and not secundario:
            secundario = frozenset({""})  # Requiere selección explícita del segundo archivo.
        perfiles.append(Perfil(ruta, titulo or ruta.stem, primario, secundario,
                              xml.findtext("Patreon", "").lower() == "true"))
    return perfiles


def nombres_ejecutables(texto):
    return frozenset(Path(nombre.strip().replace("\\", "/")).name.casefold()
                     for nombre in texto.split(";") if nombre.strip())


def candidatos_ejecutable(juego, segundo=False):
    esperados = juego.perfil.secundario if segundo else juego.perfil.esperado
    return [ruta for ruta in archivos_juego(juego)
            if ruta.suffix.lower() in BINARIOS or ruta.name.casefold() in esperados]


def archivos_juego(juego):
    if juego.contenido is not None:
        return juego.contenido.archivos
    return tuple(ruta for ruta in juego.origen.rglob("*")
                 if ruta.is_file() and ruta.resolve().is_relative_to(juego.origen))


def es_ejecutable_sin_extension(juego, ruta, extensiones):
    try:
        if juego.contenido is None:
            with ruta.open("rb") as entrada:
                cabecera = entrada.read(4096)
        else:
            cabecera = inicio_archivado(juego.origen, ruta, 4096)
    except (OSError, ValueError):
        return False
    if ".elf" in extensiones and cabecera.startswith(b"\x7fELF"):
        return True
    if ".exe" in extensiones and len(cabecera) >= 64 and cabecera.startswith(b"MZ"):
        offset = int.from_bytes(cabecera[60:64], "little")
        return offset >= 64 and cabecera[offset:offset + 4] == b"PE\0\0"
    return False


def resolver_archivo(juego, archivos, esperados, elegido):
    if not esperados:
        return elegido, ()
    coincidencias = tuple(ruta for ruta in archivos if ruta.name.casefold() in esperados)
    if not coincidencias:
        alias = {}
        for nombre in esperados:
            ruta = Path(nombre)
            if ruta.suffix in {".exe", ".elf"}:
                alias.setdefault(ruta.stem, set()).add(ruta.suffix)
        coincidencias = tuple(ruta for ruta in archivos if ruta.name.casefold() in alias
                              and es_ejecutable_sin_extension(juego, ruta, alias[ruta.name.casefold()]))
    if elegido is None and len(coincidencias) == 1:
        elegido = coincidencias[0]
    return elegido, coincidencias


def buscar_arranque(juego, esperados_web=frozenset(), secundarios_web=frozenset(), archivos=None):
    perfil = juego.perfil
    if perfil is None or juego.error:
        juego.revision = ()
        return
    if archivos is None:
        nombres = perfil.esperado | perfil.secundario | esperados_web | secundarios_web
        archivos = archivos_juego(juego) if nombres - {""} or juego.ejecutable or juego.secundario else ()
    revisiones = []
    for atributo, etiqueta, locales, web in (
        ("ejecutable", "Ejecutable principal", perfil.esperado, esperados_web),
        ("secundario", "Segundo archivo", perfil.secundario, secundarios_web),
    ):
        if atributo == "secundario" and not locales:
            continue
        actual = getattr(juego, atributo)
        if actual is not None and actual not in archivos:
            actual = None
        elegido, coincidencias = resolver_archivo(juego, archivos, locales, actual)
        if not coincidencias and elegido is None and web - locales:
            elegido, coincidencias = resolver_archivo(juego, archivos, web - locales, None)
        setattr(juego, atributo, elegido)
        revisiones.append(RevisionArchivo(etiqueta, (locales | web) - {""}, elegido, coincidencias))
    juego.revision = tuple(revisiones)


# --- Reconocer el juego por el nombre de la carpeta ---------------------------------------------
RUIDO = frozenset({"teknoparrot", "tp", "arcade", "pc", "game", "the", "of", "and", "a", "full", "rip", "repack",
                   "fixed", "ver", "version", "jp", "jpn", "japan", "usa", "eur", "english", "eng"})
ROMANOS = {"ii": "2", "iii": "3", "iv": "4", "vi": "6", "vii": "7", "viii": "8", "ix": "9"}
UMBRAL_PERFIL = 0.75   # Puntaje mínimo para asignar un perfil sin preguntar.
MARGEN_PERFIL = 0.08   # Ventaja mínima sobre el segundo candidato.


@lru_cache(maxsize=16384)
def palabras(texto):
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(letra for letra in texto if not unicodedata.combining(letra))
    # Separa "Daytona3" o "DOA6" en palabra y número, y las palabras pegadas en mayúsculas ("FarCry").
    texto = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", texto)
    texto = re.sub(r"(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])", " ", texto).casefold()
    return tuple(ROMANOS.get(p, p) for p in re.findall(r"[a-z0-9]+", texto) if p not in RUIDO)


def _coinciden(a, b):
    return a == b or (len(a) >= 3 and len(b) >= 3 and (a.startswith(b) or b.startswith(a)))


def similitud(nombre, texto):
    """Parecido entre 0 y 1 de dos nombres de juego, tolerante a espacios, signos y mayúsculas."""
    propias, ajenas = palabras(nombre), palabras(texto)
    if not propias or not ajenas:
        return 0.0
    clave, otra = "".join(propias), "".join(ajenas)
    if clave == otra:
        return 1.0
    ida = sum(any(_coinciden(p, q) for q in ajenas) for p in propias) / len(propias)
    vuelta = sum(any(_coinciden(q, p) for p in propias) for q in ajenas) / len(ajenas)
    comparador = SequenceMatcher(None, clave, otra)
    # Sin palabras en común el puntaje no pasa de 0,3: basta la estimación rápida.
    puntaje = 0.45 * ida + 0.25 * vuelta + 0.30 * (comparador.ratio() if ida or vuelta else comparador.quick_ratio())
    numeros, otros = {p for p in propias if p.isdigit()}, {q for q in ajenas if q.isdigit()}
    if numeros - otros:
        puntaje *= 0.6    # "Daytona 3" no es "Daytona 2".
    elif otros - numeros:
        puntaje *= 0.85
    return puntaje


def puntaje_perfil(nombre, perfil):
    sin_etiquetas = re.split(r"\s*[\[(]", nombre, maxsplit=1)[0] or nombre
    return max(similitud(variante, texto) for variante in {nombre, sin_etiquetas}
               for texto in (perfil.titulo, perfil.id))


def perfiles_parecidos(nombre, perfiles, limite=None):
    """Perfiles ordenados del más al menos parecido, con su puntaje."""
    puntajes = sorted(((puntaje_perfil(nombre, perfil), perfil) for perfil in perfiles),
                      key=lambda par: (-par[0], par[1].titulo.casefold()))
    return puntajes[:limite] if limite else puntajes


def reconocer_perfil(nombre, perfiles):
    """El perfil que corresponde sin dudas al nombre, o None si hay que preguntar."""
    mejores = perfiles_parecidos(nombre, perfiles, 2)
    if not mejores or mejores[0][0] < UMBRAL_PERFIL:
        return None
    if len(mejores) > 1 and mejores[0][0] - mejores[1][0] < MARGEN_PERFIL:
        return None
    return mejores[0][1]


def nombre_juego(origen):
    return origen.stem if origen.suffix.lower() in (*FORMATOS, *COMPRIMIDOS) else origen.name


def es_coleccion(carpeta, perfiles):
    """True si la carpeta contiene varios juegos; False si es la carpeta de un solo juego."""
    try:
        hijos = [ruta for ruta in carpeta.iterdir() if not ruta.name.startswith(".")]
    except OSError:
        return False
    if any(ruta.is_file() and ruta.suffix.lower() in BINARIOS for ruta in hijos):
        return False   # Tiene el ejecutable a la vista: es un juego.
    juegos = [ruta for ruta in hijos if ruta.is_dir() or ruta.suffix.lower() in COMPRIMIDOS]
    if not juegos:
        return False
    propio = max((puntaje for puntaje, _ in perfiles_parecidos(carpeta.name, perfiles, 1)), default=0)
    if propio >= UMBRAL_PERFIL:
        return any(reconocer_perfil(nombre_juego(ruta), perfiles) for ruta in juegos)
    return True


# --- Elegir el ejecutable cuando el perfil no lo dice o hay varios ------------------------------
AUXILIARES = re.compile(
    r"^(unins\w*|setup|install\w*|vc_?redist\w*|vcredist\w*|dxsetup|dxwebsetup|directx\w*|dotnet\w*|"
    r"ndp\d*\w*|oalinst|physx\w*|ue\d?prereq\w*|\w*crash\w*|\w*reporter\w*|unitycrashhandler\w*|"
    r"\w*config\w*|\w*settings?|\w*editor\w*|\w*updater?|\w*patch\w*|7z\w*|winrar|unrar|budgieloader|"
    r"openparrot\w*|teknoparrot\w*|parrotpatcher\w*|\w*injector\w*|\w*keygen\w*|easyanticheat\w*|"
    r"\w*server\w*|\w*benchmark\w*|\w*test\w*|\w*debug\w*|nvidia\w*|amd\w*)$", re.I)
CARPETAS_AUXILIARES = {"redist", "_commonredist", "commonredist", "directx", "vcredist", "support", "tools",
                       "backup", "old", "original", "originals", "crack", "engine", "prerequisites", "installer"}


def _tamanio(juego, ruta):
    if juego.contenido is not None:
        return 0
    try:
        return ruta.stat().st_size
    except OSError:
        return 0


def _relativa(juego, ruta):
    return ruta if juego.contenido is not None else ruta.relative_to(juego.origen)


def orden_ejecutables(juego, rutas):
    """Ordena posibles ejecutables del más al menos probable."""
    nombre = juego.perfil.titulo if juego.perfil else nombre_juego(juego.origen)

    def clave(ruta):
        relativa = _relativa(juego, ruta)
        carpetas = {parte.casefold() for parte in relativa.parts[:-1]}
        parecido = max(similitud(ruta.stem, nombre), similitud(ruta.stem, juego.perfil.id) if juego.perfil else 0)
        return (bool(carpetas & CARPETAS_AUXILIARES), not ruta.stem.casefold().endswith("-shipping"),
                -round(parecido, 1), len(relativa.parts), -_tamanio(juego, ruta), relativa.as_posix().casefold())

    return sorted(rutas, key=clave)


def probables_ejecutables(juego):
    """Ejecutables .exe o .elf del juego que no parecen instaladores ni herramientas."""
    return [ruta for ruta in archivos_juego(juego) if ruta.suffix.lower() in {".exe", ".elf"}
            and not AUXILIARES.match(ruta.stem)]


def deducir_ejecutable(juego):
    """Si falta el ejecutable principal, lo elige cuando hay un candidato claro. Devuelve True si eligió."""
    if juego.perfil is None or juego.error or juego.ejecutable is not None:
        return False
    revision = juego.revision[0] if juego.revision else None
    if revision and revision.coincidencias:
        # El nombre esperado aparece varias veces: se queda con la copia más cercana a la raíz.
        candidatos = orden_ejecutables(juego, revision.coincidencias)
        profundidad = [len(_relativa(juego, ruta).parts) for ruta in candidatos]
        if len(candidatos) > 1 and profundidad[0] == profundidad[1]:
            return False
    elif revision and revision.esperados:
        return False   # El perfil pide un nombre concreto que no está: no conviene adivinar.
    else:
        candidatos = orden_ejecutables(juego, probables_ejecutables(juego))
        if not candidatos:
            return False
        if len(candidatos) > 1:
            primero, segundo = candidatos[0], candidatos[1]
            parecido = [similitud(ruta.stem, juego.perfil.titulo) for ruta in (primero, segundo)]
            if not (primero.stem.casefold().endswith("-shipping")
                    or len(_relativa(juego, primero).parts) < len(_relativa(juego, segundo).parts)
                    or parecido[0] - parecido[1] >= 0.3):
                return False
    juego.ejecutable = candidatos[0]
    juego.deducidos.add("ejecutable")
    return True


def elegir_archivo(juego, ruta, segundo=False):
    """Elección manual del usuario: deja de considerarse deducida."""
    atributo = "secundario" if segundo else "ejecutable"
    setattr(juego, atributo, ruta)
    juego.deducidos.discard(atributo)


def seleccionar_perfil(juego, perfil):
    mismo = perfil is not None and juego.perfil is not None and perfil.id == juego.perfil.id
    juego.perfil = perfil
    if not mismo:
        juego.ejecutable = juego.secundario = None
        juego.deducidos.clear()
    if perfil and not perfil.secundario:
        juego.secundario = None
    buscar_arranque(juego)


def clave_publicacion(nombre):
    nombre = re.split(r"\s*[\[(]", nombre, maxsplit=1)[0]
    return clave_titulo(nombre)


def releer_origen(juego):
    try:
        marca = None if juego.origen.is_dir() else marca_archivo(juego.origen)
        if marca is None:
            juego.contenido = None
        elif marca != juego.marca or juego.contenido is None:
            juego.contenido = inspeccionar(juego.origen)
            if marca_archivo(juego.origen) != marca:
                raise ValueError("El comprimido cambió durante la lectura. Vuelve a comprobarlo.")
        juego.marca = marca
        juego.error = ""
    except (OSError, ValueError) as error:
        juego.marca = juego.contenido = None
        juego.error = str(error)


def revisar_carpetas(carpetas, perfiles):
    ids = {perfil.id.casefold(): perfil for perfil in perfiles}
    titulos, publicaciones = {}, {}
    for perfil in perfiles:
        titulos.setdefault(clave_titulo(perfil.titulo), []).append(perfil)
        publicaciones.setdefault(clave_publicacion(perfil.titulo), []).append(perfil)

    juegos = []
    for origen in carpetas:
        origen = origen.resolve()
        juego = Juego(origen)
        releer_origen(juego)
        nombre = nombre_juego(origen)
        perfil = ids.get(nombre.casefold())
        if perfil is None:
            coincidencias = titulos.get(clave_titulo(nombre)) or publicaciones.get(clave_publicacion(nombre), ())
            perfil = coincidencias[0] if len(coincidencias) == 1 else None
        if perfil is None:
            perfil = reconocer_perfil(nombre, perfiles)
            juego.perfil_por_nombre = perfil is not None
        seleccionar_perfil(juego, perfil)
        juegos.append(juego)
    return juegos


def entradas_instaladas(sistema):
    formatos = set(FORMATOS) | COMPRIMIDOS
    for carpeta, subcarpetas, archivos in os.walk(sistema.carpeta):
        for nombre in subcarpetas[:]:
            ruta = Path(nombre)
            if ruta.suffix.lower() in FORMATOS:
                yield Path(carpeta) / ruta
                subcarpetas.remove(nombre)
            elif nombre.startswith("."):
                subcarpetas.remove(nombre)
        yield from (Path(carpeta) / nombre for nombre in archivos if Path(nombre).suffix.lower() in formatos)


def instalados(sistema):
    return Counter(ruta.stem.casefold() for ruta in entradas_instaladas(sistema))


def problema_arranque(juego):
    if juego.ejecutable is None:
        if juego.revision and not juego.revision[0].esperados:
            return "Falta elegir el ejecutable"
        if juego.revision and len(juego.revision[0].coincidencias) > 1:
            return "Hay varios ejecutables · elige uno"
        return "No se encontró el ejecutable"
    if juego.perfil.secundario:
        if juego.secundario is None:
            if len(juego.revision) > 1 and len(juego.revision[1].coincidencias) > 1:
                return "Hay varios segundos ejecutables · elige uno"
            return "Falta el segundo ejecutable"
        if juego.ejecutable == juego.secundario:
            return "Los dos ejecutables no pueden ser el mismo"
    return ""


def problema_juego(juego, presentes, pendientes):
    if juego.error:
        return "No se pudo leer el archivo"
    if juego.perfil is None:
        return "No reconocido · elige el juego"
    if presentes[juego.perfil.id.casefold()]:
        return "Ya está en RetroBat"
    if pendientes[juego.perfil.id.casefold()] > 1:
        return "Repetido en la lista"
    return problema_arranque(juego)


def importar_juego(raiz, juego, informar):
    sistema = sistema_teknoparrot(raiz)
    emulador = carpeta_emulador(raiz)
    perfil = juego.perfil
    if not (emulador / "TeknoParrotUi.exe").is_file() or perfil is None:
        raise ValueError("Instala TeknoParrot y selecciona un perfil disponible.")
    if perfil.plantilla.parent != emulador / "GameProfiles" or not perfil.plantilla.is_file():
        raise ValueError("El perfil ya no está en GameProfiles. Actualiza la lista.")
    if instalados(sistema)[perfil.id.casefold()]:
        raise FileExistsError(f"Ya existe un juego con el perfil {perfil.id} en RetroBat.")
    if problema := problema_arranque(juego):
        raise ValueError(problema)
    extension = next(ext for ext in FORMATOS if ext in sistema.extensiones)
    destino = sistema.carpeta / (nombre_seguro(perfil.id) + extension)
    if juego.contenido is not None and marca_archivo(juego.origen) != juego.marca:
        raise ValueError("El archivo comprimido cambió. Vuelve a seleccionarlo.")

    relativos = {}
    for etiqueta, ruta, requerido in (("GamePath", juego.ejecutable, True),
                                      ("GamePath2", juego.secundario, bool(perfil.secundario))):
        if not requerido:
            continue
        if juego.contenido is not None:
            if ruta not in juego.contenido.archivos:
                raise ValueError("Selecciona un ejecutable del archivo comprimido.")
            relativos[etiqueta] = ruta
        else:
            if ruta is None or not ruta.is_file() or not ruta.resolve().is_relative_to(juego.origen):
                raise ValueError(f"Selecciona un ejecutable válido dentro de {juego.origen.name}.")
            relativos[etiqueta] = ruta.relative_to(juego.origen)
    if destino.resolve().is_relative_to(juego.origen):
        raise ValueError("La carpeta seleccionada contiene el destino de RetroBat.")

    usuario = emulador / "UserProfiles" / perfil.plantilla.name
    original = usuario.read_bytes() if usuario.exists() else None
    plantilla = perfil.plantilla.read_bytes() if original is None else original
    xml = ET.fromstring(plantilla)
    if xml.tag != "GameProfile":
        raise ValueError(f"Perfil de usuario inválido: {usuario.name}")
    for etiqueta, valor in (("ProfileName", perfil.id), *(
            (clave, str(destino / relativo)) for clave, relativo in relativos.items())):
        nodo = xml.find(etiqueta)
        if nodo is None:
            nodo = ET.SubElement(xml, etiqueta)
        nodo.text = valor

    sistema.carpeta.mkdir(parents=True, exist_ok=True)
    usuario.parent.mkdir(parents=True, exist_ok=True)
    with (tempfile.TemporaryDirectory(prefix=".tecnotics-", dir=sistema.carpeta) as temporal,
          tempfile.TemporaryDirectory(dir=usuario.parent) as config):
        preparado = Path(temporal) / destino.name
        if juego.contenido is None:
            copiar(juego.origen, preparado, informar)
        else:
            extraer(juego.origen, preparado, juego.contenido)
            if marca_archivo(juego.origen) != juego.marca:
                raise ValueError("El archivo comprimido cambió durante la extracción.")
        if any(not (preparado / relativo).is_file() for relativo in relativos.values()):
            raise ValueError("Falta un ejecutable en la copia preparada.")
        perfil_preparado = Path(config) / usuario.name
        ET.ElementTree(xml).write(perfil_preparado, encoding="utf-8", xml_declaration=True)
        if instalados(sistema)[perfil.id.casefold()]:
            raise FileExistsError(f"Apareció otra copia de {perfil.id} durante la importación.")
        if (usuario.read_bytes() if usuario.exists() else None) != original:
            raise ValueError("TeknoParrot cambió el perfil durante la importación. Cierra el emulador y vuelve a intentar.")
        publicar_directorio(preparado, destino)
        try:
            if original is None:
                publicar(perfil_preparado, usuario)
            else:
                perfil_preparado.replace(usuario)
        except OSError:
            destino.rename(preparado)
            raise
    return destino
