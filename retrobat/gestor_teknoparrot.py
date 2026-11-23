"""Preparación de TeknoParrot para el lanzador oficial de RetroBat."""
from collections import Counter
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import tempfile
import xml.etree.ElementTree as ET

from gestor_core import copiar, nombre_seguro, publicar, publicar_directorio, sistemas_instalados
from gestor_duplicados import clave_titulo, marca_archivo
from gestor_teknoparrot_archivos import Contenido, extraer, inspeccionar

FORMATOS = (".teknoparrot", ".parrot", ".game")
COMPRIMIDOS = {".zip", ".7z", ".rar"}
BINARIOS = {".exe", ".elf", ".bin", ".x64", ".x86"}


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


@dataclass
class Juego:
    origen: Path
    perfil: Perfil | None = None
    ejecutable: Path | None = None
    secundario: Path | None = None
    contenido: Contenido | None = None
    marca: tuple | None = None
    error: str = ""


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
        primario = nombres_ejecutables(xml.findtext("ExecutableName", "")) or ejecutables.get(
            ruta.stem.casefold(), frozenset())
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
    if juego.contenido is not None:
        rutas = juego.contenido.archivos
    else:
        rutas = (ruta for ruta in juego.origen.rglob("*")
                 if ruta.is_file() and ruta.resolve().is_relative_to(juego.origen))
    return [ruta for ruta in rutas if ruta.suffix.lower() in BINARIOS or ruta.name.casefold() in esperados]


def seleccionar_perfil(juego, perfil):
    mismo = perfil is not None and juego.perfil is not None and perfil.id == juego.perfil.id
    juego.perfil = perfil
    if not mismo:
        juego.ejecutable = juego.secundario = None
    if perfil and not perfil.secundario:
        juego.secundario = None
    if perfil and not juego.error:
        for atributo, nombres, segundo in (("ejecutable", perfil.esperado, False),
                                           ("secundario", perfil.secundario, True)):
            if not nombres or getattr(juego, atributo) is not None:
                continue
            candidatos = [ruta for ruta in candidatos_ejecutable(juego, segundo)
                          if ruta.name.casefold() in nombres]
            if len(candidatos) == 1:
                setattr(juego, atributo, candidatos[0])


def clave_publicacion(nombre):
    nombre = re.split(r"\s*[\[(]", nombre, maxsplit=1)[0]
    return clave_titulo(nombre)


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
        if origen.is_file():
            try:
                juego.marca = marca_archivo(origen)
                juego.contenido = inspeccionar(origen)
            except (OSError, ValueError) as error:
                juego.error = str(error)
        nombre = origen.stem if origen.suffix.lower() in (*FORMATOS, *COMPRIMIDOS) else origen.name
        perfil = ids.get(nombre.casefold())
        if perfil is None:
            coincidencias = titulos.get(clave_titulo(nombre)) or publicaciones.get(clave_publicacion(nombre), ())
            perfil = coincidencias[0] if len(coincidencias) == 1 else None
        seleccionar_perfil(juego, perfil)
        juegos.append(juego)
    return juegos


def instalados(sistema):
    formatos = set(FORMATOS) | COMPRIMIDOS
    ids = Counter()
    for carpeta, subcarpetas, archivos in os.walk(sistema.carpeta):
        for nombre in subcarpetas[:]:
            ruta = Path(nombre)
            if ruta.suffix.lower() in FORMATOS:
                ids[ruta.stem.casefold()] += 1
                subcarpetas.remove(nombre)
            elif nombre.startswith("."):
                subcarpetas.remove(nombre)
        ids.update(Path(nombre).stem.casefold() for nombre in archivos if Path(nombre).suffix.lower() in formatos)
    return ids


def problema_arranque(juego):
    if juego.ejecutable is None:
        return "Falta el ejecutable principal"
    if juego.perfil.secundario:
        if juego.secundario is None:
            return "Falta el segundo archivo"
        if juego.ejecutable == juego.secundario:
            return "Elige dos archivos distintos"
    return ""


def problema_juego(juego, presentes, pendientes):
    if juego.error:
        return "Archivo ilegible · ver detalle"
    if juego.perfil is None:
        return "Elige un perfil"
    if presentes[juego.perfil.id.casefold()]:
        return "Ya está en RetroBat"
    if pendientes[juego.perfil.id.casefold()] > 1:
        return "Perfil repetido en el lote"
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
