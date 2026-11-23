"""Preparación de TeknoParrot para el lanzador oficial de RetroBat."""
from collections import Counter
from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

from gestor_core import copiar, nombre_seguro, publicar, publicar_directorio, sistemas_instalados
from gestor_duplicados import clave_titulo

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


def perfiles_locales(emulador):
    perfiles = []
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
        primario = nombres_ejecutables(xml.findtext("ExecutableName", ""))
        secundario = nombres_ejecutables(xml.findtext("ExecutableName2", ""))
        if xml.findtext("HasTwoExecutables", "").lower() == "true" and not secundario:
            secundario = frozenset({""})  # Requiere selección explícita del segundo archivo.
        perfiles.append(Perfil(ruta, titulo or ruta.stem, primario, secundario,
                              xml.findtext("Patreon", "").lower() == "true"))
    return perfiles


def nombres_ejecutables(texto):
    return frozenset(Path(nombre.strip().replace("\\", "/")).name.casefold()
                     for nombre in texto.split(";") if nombre.strip())


def seleccionar_perfil(juego, perfil):
    juego.perfil = perfil
    juego.ejecutable = juego.secundario = None
    if perfil:
        for atributo, nombres in (("ejecutable", perfil.esperado), ("secundario", perfil.secundario)):
            if nombres and nombres != {""}:
                candidatos = [ruta for ruta in juego.origen.rglob("*")
                              if ruta.name.casefold() in nombres and ruta.is_file()
                              and ruta.resolve().is_relative_to(juego.origen)]
                if len(candidatos) == 1:
                    setattr(juego, atributo, candidatos[0])


def revisar_carpetas(carpetas, perfiles):
    ids = {perfil.id.casefold(): perfil for perfil in perfiles}
    titulos = {}
    for perfil in perfiles:
        titulos.setdefault(clave_titulo(perfil.titulo), []).append(perfil)

    juegos = []
    for origen in carpetas:
        origen = origen.resolve()
        juego = Juego(origen)
        nombre = origen.stem if origen.suffix.lower() in FORMATOS else origen.name
        perfil = ids.get(nombre.casefold())
        if perfil is None:
            coincidencias = titulos.get(clave_titulo(nombre), ())
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


def estado_juego(juego, presentes, pendientes):
    if juego.perfil is None:
        return "Elige un perfil"
    if presentes[juego.perfil.id.casefold()]:
        return "Ya está en RetroBat"
    if pendientes[juego.perfil.id.casefold()] > 1:
        return "Perfil repetido en el lote"
    if juego.ejecutable is None or (juego.perfil.secundario and juego.secundario is None):
        return "Revisa los ejecutables"
    return "Listo · requiere licencia" if juego.perfil.suscripcion else "Listo para importar"


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
    extension = next(ext for ext in FORMATOS if ext in sistema.extensiones)
    destino = sistema.carpeta / (nombre_seguro(perfil.id) + extension)
    relativos = {}
    for etiqueta, ruta, requerido in (("GamePath", juego.ejecutable, True),
                                      ("GamePath2", juego.secundario, bool(perfil.secundario))):
        if not requerido:
            continue
        if ruta is None or not ruta.is_file() or not ruta.resolve().is_relative_to(juego.origen):
            raise ValueError(f"Selecciona un ejecutable válido dentro de {juego.origen.name}.")
        relativos[etiqueta] = ruta.relative_to(juego.origen)
    if len(set(relativos.values())) != len(relativos):
        raise ValueError("El ejecutable principal y el secundario deben ser distintos.")
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
        copiar(juego.origen, preparado, informar)
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
