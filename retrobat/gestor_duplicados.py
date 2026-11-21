"""Comparación e inventario de juegos, con respaldo para cambios de biblioteca."""

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unicodedata
from uuid import uuid4

from gestor_core import (
    Sistema, copiar, copiar_juego_windows, destinos_accesos_windows, discos_mame, requiere_importacion_manual,
    tamanio_copia, ubicacion_juego_windows,
)


@dataclass(frozen=True)
class Entrada:
    sistema: Sistema
    ruta: Path
    archivo: Path | None
    marca: tuple
    bytes: int | None = None


@dataclass(frozen=True)
class Comparacion:
    estado: str
    evidencia: str
    origen: Path
    instalada: Entrada
    marca_origen: tuple
    marca_instalada: tuple | None
    unidades: str
    bytes_origen: int | None
    bytes_instalados: int | None


@dataclass(frozen=True)
class Grupo:
    nombre: str
    evidencia: str
    entradas: tuple[Entrada, ...]


def marca_archivo(ruta):
    info = ruta.stat()
    return info.st_dev, info.st_ino, info.st_mtime_ns, info.st_size


def clave_titulo(nombre):
    texto = unicodedata.normalize("NFKD", nombre.casefold())
    return "".join(letra for letra in texto if letra.isalnum())


def sha256(ruta):
    with ruta.open("rb") as archivo:
        return hashlib.file_digest(archivo, "sha256").digest()


def mismo_archivo(primero, segundo):
    return (primero.is_file() and segundo.is_file()
            and primero.stat().st_size == segundo.stat().st_size and sha256(primero) == sha256(segundo))


def leer_entradas(sistema, accesos=None):
    if sistema.identificador == "windows":
        if accesos is None:
            accesos = destinos_accesos_windows(sistema.carpeta)
        archivos = accesos.items()
    else:
        archivos = ((ruta, ruta) for ruta in sistema.carpeta.rglob("*")
                    if ruta.suffix.lower() in sistema.extensiones and (ruta.is_file() or ruta.is_dir()))
    for ruta, archivo in archivos:
        try:
            tamano = archivo.stat().st_size if archivo and archivo.is_file() else None
            yield Entrada(sistema, ruta, archivo, marca_archivo(ruta), tamano)
        except OSError:
            continue


def candidato_windows(candidatos, instalada):
    if instalada.archivo:
        equivalentes = [ruta for ruta in candidatos if ruta.name.casefold() == instalada.archivo.name.casefold()]
        if len(equivalentes) == 1:
            return equivalentes[0]
    return candidatos[0] if len(candidatos) == 1 else None


def producto_windows(origen, destino):
    script = """
        [Console]::InputEncoding = [Text.UTF8Encoding]::new($false)
        [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
        $rutas = ConvertFrom-Json -InputObject ([Console]::In.ReadToEnd())
        $metadatos = foreach ($ruta in $rutas) {
            $f = (Get-Item -LiteralPath $ruta -ErrorAction Stop).VersionInfo
            [PSCustomObject]@{ Producto = $f.ProductName; Archivo = $f.OriginalFilename }
        }
        ConvertTo-Json -InputObject @($metadatos) -Compress
    """
    resultado = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        input=json.dumps([str(origen), str(destino)]), encoding="utf-8", capture_output=True,
        check=True, creationflags=subprocess.CREATE_NO_WINDOW,
    )
    datos = json.loads(resultado.stdout)
    primero, segundo = (clave_titulo(x["Producto"] or "") for x in datos)
    genericos = {"unrealengine", "unity", "unityplayer", "launcher", "game", "windows", "renpy"}
    if primero and primero == segundo and primero not in genericos:
        return datos[0]["Producto"]
    return ""


def comparar_juego(candidato, instalada, origen, *, medir_paquetes=False):
    sistema = instalada.sistema
    es_windows = sistema.identificador == "windows"
    archivo = instalada.archivo
    marca = marca_archivo(candidato)
    unidad = "Ejecutables" if es_windows else "Archivos"
    tam_nuevo = marca[-1] if candidato.is_file() else None
    marca_instalada = marca_archivo(archivo) if archivo and archivo.is_file() else None
    tam_instalado = marca_instalada[-1] if marca_instalada else None
    if archivo is None:
        estado, razon = "Acceso directo roto", "No se encontró el destino del acceso directo instalado."
    elif candidato.resolve() == archivo.resolve():
        estado, razon = "Misma ruta", "RetroBat ya apunta al mismo archivo de origen."
    elif tam_nuevo is not None and tam_nuevo == tam_instalado and mismo_archivo(candidato, archivo):
        estado = "Ejecutable idéntico" if es_windows else "Archivo idéntico"
        razon = "Los SHA-256 coinciden. Esta huella corresponde al ejecutable." if es_windows else "Los SHA-256 del archivo coinciden."
    elif sistema.es_mame and candidato.stem.casefold() == instalada.ruta.stem.casefold():
        estado, razon = "Mismo set MAME · archivo distinto", "El identificador del set es el mismo. Su contenido o compresión difiere."
    else:
        producto = ""
        if es_windows and tam_instalado is not None:
            try:
                producto = producto_windows(candidato, archivo)
            except (OSError, ValueError, subprocess.SubprocessError):
                pass
        if producto:
            estado, razon = "Probable mismo juego · distinto", f"Ambos ejecutables declaran el producto «{producto}»."
        else:
            estado, razon = "Nombre en uso · revisar", "El nombre coincide, pero los archivos difieren o no se pudo comprobar su identidad."

    if medir_paquetes and archivo is not None:
        if es_windows:
            partes = candidato.relative_to(origen).parts
            cola = partes[1:]
            if cola and tuple(p.casefold() for p in cola) == tuple(p.casefold() for p in archivo.parts[-len(cola):]):
                paquete = archivo.parents[len(cola) - 1]
                titulo = clave_titulo(partes[0])
                if titulo and (clave_titulo(paquete.name).startswith(titulo)
                               or clave_titulo(paquete.name) == clave_titulo(instalada.ruta.stem)):
                    unidad = "Carpetas del juego"
                    tam_nuevo = tamanio_copia(origen / partes[0])
                    tam_instalado = tamanio_copia(paquete)
                    razon += " Los tamaños de carpeta por sí solos no prueban que sus archivos sean iguales."
        elif sistema.es_mame:
            discos_nuevos = discos_mame(candidato)
            discos_instalados = discos_mame(archivo)
            if discos_nuevos or discos_instalados:
                unidad = "ROM y discos asociados"
                tam_nuevo = tamanio_copia(candidato) + sum(d.stat().st_size for d in discos_nuevos)
                tam_instalado = tamanio_copia(archivo) + sum(d.stat().st_size for d in discos_instalados)
    return Comparacion(estado, razon, candidato, instalada, marca, marca_instalada, unidad, tam_nuevo, tam_instalado)


def buscar_duplicados(sistemas, informar):
    por_titulo, por_tamano, por_archivo = {}, {}, {}
    for indice, sistema in enumerate(sistemas.values()):
        informar(indice, len(sistemas), "Inventariando títulos de RetroBat…")
        for entrada in leer_entradas(sistema):
            if entrada.ruta in por_archivo:
                continue
            por_archivo[entrada.ruta] = entrada
            titulo = clave_titulo(entrada.ruta.stem)
            if titulo:
                por_titulo.setdefault(titulo, []).append(entrada)
            if entrada.bytes and entrada.archivo:
                por_tamano.setdefault(entrada.bytes, []).append(entrada)

    candidatos = [entrada for entradas in por_tamano.values() if len(entradas) > 1 for entrada in entradas]
    huellas, por_huella = {}, {}
    for indice, entrada in enumerate(candidatos):
        informar(indice, len(candidatos), "Verificando huellas SHA-256 de los archivos…")
        try:
            if entrada.archivo not in huellas:
                huellas[entrada.archivo] = sha256(entrada.archivo)
            por_huella.setdefault(huellas[entrada.archivo], []).append(entrada)
        except OSError:
            continue

    grupos = []
    conjuntos = set()
    for entradas in por_huella.values():
        if len(entradas) > 1:
            conjuntos.add(frozenset(x.ruta for x in entradas))
            evidencia = ("Mismo ejecutable" if any(x.sistema.identificador == "windows" for x in entradas)
                         else "Archivos idénticos")
            grupos.append(Grupo(entradas[0].ruta.stem, evidencia, tuple(entradas)))
    for entradas in por_titulo.values():
        if len(entradas) > 1 and frozenset(x.ruta for x in entradas) not in conjuntos:
            grupos.append(Grupo(entradas[0].ruta.stem, "Nombre coincidente · verificar", tuple(entradas)))
    return unir_coincidencias(grupos)


def unir_coincidencias(grupos):
    """Deja cada ruta en un solo grupo aunque coincida por nombre y por huella."""
    por_ruta = {}
    for indice, grupo in enumerate(grupos):
        for entrada in grupo.entradas:
            por_ruta.setdefault(entrada.ruta, []).append(indice)

    pendientes = set(range(len(grupos)))
    resultado = []
    for inicio, grupo in enumerate(grupos):
        if inicio not in pendientes:
            continue
        pendientes.remove(inicio)
        relacionados = [inicio]
        entradas = {}
        cantidad = 0
        while relacionados:
            actual = grupos[relacionados.pop()]
            cantidad += 1
            for entrada in actual.entradas:
                if entrada.ruta in entradas:
                    continue
                entradas[entrada.ruta] = entrada
                for vecino in por_ruta[entrada.ruta]:
                    if vecino in pendientes:
                        pendientes.remove(vecino)
                        relacionados.append(vecino)
        if cantidad == 1:
            resultado.append(grupo)
        else:
            copias = tuple(sorted(entradas.values(), key=lambda e: (e.sistema.nombre.casefold(), str(e.ruta).casefold())))
            resultado.append(Grupo(grupo.nombre, "Coincidencias relacionadas · verificar", copias))
    return sorted(resultado, key=lambda g: (g.nombre.casefold(), g.evidencia))


def plan_duplicados(grupos, marcadas):
    """Devuelve un lote con al menos una copia conservada por grupo intervenido."""
    conservar, retirar = [], []
    for grupo in grupos:
        protegidas = [entrada for entrada in grupo.entradas if entrada.ruta in marcadas]
        if protegidas and len(protegidas) < len(grupo.entradas):
            conservar.extend(protegidas)
            retirar.extend(entrada for entrada in grupo.entradas if entrada.ruta not in marcadas)
    return conservar, retirar


def carpeta_respaldos(raiz):
    return raiz / "user" / "tecnotics-gestor" / "respaldos"


def validar_entrada(raiz, entrada):
    ruta = entrada.ruta
    base = (raiz / "roms").resolve()
    resuelta = ruta.resolve()
    if (resuelta == base or not resuelta.is_relative_to(base)
            or not resuelta.is_relative_to(entrada.sistema.carpeta.resolve()) or resuelta != ruta.absolute()):
        raise ValueError(f"Ruta de biblioteca no válida: {ruta}")
    if marca_archivo(ruta) != entrada.marca:
        raise ValueError(f"El archivo cambió desde la verificación: {ruta}")


def guardar_respaldo(raiz, rutas, *, mover, incluir_windows=False):
    base = (raiz / "roms").resolve()
    ruta_respaldo = carpeta_respaldos(raiz) / f"{datetime.now():%Y%m%d-%H%M%S}-{uuid4().hex[:8]}"
    biblioteca = raiz.resolve() / "library" / "windows"
    pares = []
    manifiesto = []
    for ruta in rutas:
        if ruta.resolve() != ruta:
            raise ValueError(f"No se puede respaldar una ruta enlazada: {ruta}")
        if ruta != base and ruta.is_relative_to(base):
            relativo = ruta.relative_to(base).as_posix()
            manifiesto.append({"ruta": relativo})
            copia = ruta_respaldo / "archivos" / relativo
        elif incluir_windows and ruta.parent == biblioteca:
            manifiesto.append({"ruta": ruta.name, "zona": "windows"})
            copia = ruta_respaldo / "windows" / ruta.name
        else:
            raise ValueError(f"No se puede respaldar una ruta fuera de la biblioteca: {ruta}")
        pares.append((ruta, copia))
    ruta_respaldo.mkdir(parents=True)
    (ruta_respaldo / "originales.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2),
                                                   encoding="utf-8")
    completados = []
    try:
        for ruta, copia in pares:
            copia.parent.mkdir(parents=True, exist_ok=True)
            if mover:
                ruta.rename(copia)
                completados.append((ruta, copia))
            else:
                copiar(ruta, copia)
    except OSError:
        for ruta, copia in reversed(completados):
            copia.rename(ruta)
        raise
    return ruta_respaldo


def retirar_entradas(raiz, conservar, retirar):
    if not conservar or not retirar:
        raise ValueError("Debe quedar al menos una copia en la biblioteca.")
    protegidas = {entrada.ruta for entrada in conservar}
    elegidas = {entrada.ruta for entrada in retirar}
    if protegidas & elegidas:
        raise ValueError("Una misma copia figura como conservada y retirada.")
    for entrada in (*conservar, *retirar):
        validar_entrada(raiz, entrada)
    rutas = list(elegidas)
    for entrada in retirar:
        ruta = entrada.ruta
        if entrada.sistema.identificador != "windows" and requiere_importacion_manual(ruta):
            raise ValueError(f"{ruta.name} tiene un formato con archivos asociados. Revísalo manualmente.")
        if entrada.sistema.es_mame and ruta.suffix.lower() in {".zip", ".7z"}:
            otra = ruta.with_suffix(".7z" if ruta.suffix.lower() == ".zip" else ".zip")
            if not otra.exists() or otra in elegidas:
                rutas.extend(discos_mame(ruta))
    return guardar_respaldo(raiz, sorted(set(rutas)), mover=True)


def se_puede_reemplazar(comparacion):
    entrada, candidato = comparacion.instalada, comparacion.origen
    if not candidato.is_file() or candidato.resolve() == (entrada.archivo or entrada.ruta).resolve():
        return False
    if entrada.sistema.identificador == "windows":
        return entrada.ruta.suffix.lower() == ".lnk" and candidato.suffix.lower() == ".exe"
    return (entrada.ruta.is_file() and entrada.ruta.suffix.casefold() == candidato.suffix.casefold()
            and not requiere_importacion_manual(entrada.ruta) and not requiere_importacion_manual(candidato)
            and not (entrada.sistema.es_mame and (discos_mame(candidato) or discos_mame(entrada.ruta))))


def reemplazar_entrada(raiz, origen, comparacion, informar):
    entrada, candidato = comparacion.instalada, comparacion.origen

    def validar_comparacion():
        validar_entrada(raiz, entrada)
        if marca_archivo(candidato) != comparacion.marca_origen:
            raise ValueError("El juego de origen cambió desde la comparación.")
        if comparacion.marca_instalada and marca_archivo(entrada.archivo) != comparacion.marca_instalada:
            raise ValueError("El archivo instalado cambió desde la comparación.")

    validar_comparacion()
    if not se_puede_reemplazar(comparacion):
        raise ValueError("Este formato o paquete requiere un reemplazo manual.")
    es_windows = entrada.sistema.identificador == "windows"
    biblioteca = (raiz / "library" / "windows").resolve()
    sufijo = uuid4().hex[:8]
    nombre = f"{entrada.ruta.stem[:72]}-{sufijo}"
    fuente = ubicacion_juego_windows(origen, candidato, biblioteca, nombre)[0] if es_windows else candidato
    total = tamanio_copia(fuente) + 1
    copiado = 0

    def avanzar(cantidad):
        nonlocal copiado
        copiado += cantidad
        informar(min(copiado, total - 1), total, "Preparando el reemplazo…")

    informar(0, total, "Preparando el reemplazo…")
    con_copia = False
    with tempfile.TemporaryDirectory(dir=entrada.ruta.parent) as temporal:
        preparado = Path(temporal) / (nombre + entrada.ruta.suffix)
        if es_windows:
            copiar_juego_windows(origen, candidato, biblioteca, preparado, avanzar)
            con_copia = True
        else:
            copiar(candidato, preparado, avanzar)
        try:
            validar_comparacion()
            respaldo = guardar_respaldo(raiz, [entrada.ruta], mover=False)
            validar_comparacion()
            preparado.replace(entrada.ruta)
        except (OSError, ValueError):
            if con_copia:
                nueva = biblioteca / nombre
                if nueva.resolve().parent == biblioteca and nueva.resolve() == nueva:
                    with tempfile.TemporaryDirectory(dir=biblioteca) as deshacer:
                        nueva.rename(Path(deshacer) / nombre)
            raise
    return respaldo


def restaurar_respaldo(raiz, respaldo):
    base = (raiz / "roms").resolve()
    zona = carpeta_respaldos(raiz).resolve()
    respaldo = respaldo.resolve()
    if respaldo.parent != zona:
        raise ValueError("Selecciona una carpeta de respaldo creada por el gestor.")
    registros = json.loads((respaldo / "originales.json").read_text(encoding="utf-8"))
    pares = []
    for registro in registros:
        if registro.get("zona") == "windows":
            destino_base = raiz.resolve() / "library" / "windows"
            origen_base = respaldo / "windows"
            if Path(registro["ruta"]).name != registro["ruta"]:
                raise ValueError("Ruta inválida en el respaldo de Windows.")
        else:
            destino_base, origen_base = base, respaldo / "archivos"
        destino = (destino_base / registro["ruta"]).resolve()
        copia = (origen_base / registro["ruta"]).resolve()
        if destino == destino_base or not destino.is_relative_to(destino_base) or not copia.is_relative_to(origen_base):
            raise ValueError("El respaldo tiene una ruta que sale de la biblioteca.")
        if not copia.exists():
            raise FileNotFoundError(f"No queda una copia para restaurar: {copia}")
        if destino.exists():
            raise FileExistsError(f"Hay una copia en {destino}. Se conserva el respaldo.")
        pares.append((copia, destino))
    restaurados = []
    try:
        for copia, destino in pares:
            destino.parent.mkdir(parents=True, exist_ok=True)
            copia.rename(destino)
            restaurados.append((copia, destino))
    except OSError:
        for copia, destino in reversed(restaurados):
            destino.rename(copia)
        raise
    return len(pares)
