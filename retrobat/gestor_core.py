"""Operaciones de archivos del gestor de RetroBat."""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unicodedata
import xml.etree.ElementTree as ET


ALIAS_SISTEMAS = {
    "windows": ("Windows", "Juegos de PC", "PC Games"),
    "nes": ("NES", "Nintendo Entertainment System", "Famicom"),
    "snes": ("Super Nintendo", "SNES", "Super Nintendo Entertainment System", "Super Famicom"),
    "n64": ("Nintendo 64",),
    "gb": ("Game Boy",),
    "gbc": ("Game Boy Color",),
    "gba": ("Game Boy Advance",),
    "nds": ("Nintendo DS",),
    "megadrive": ("Mega Drive", "Genesis", "Sega Genesis", "Sega Mega Drive"),
    "saturn": ("Sega Saturn",),
    "dreamcast": ("Dreamcast", "Sega Dreamcast"),
    "psx": ("PlayStation", "PlayStation 1", "PS1", "PS One"),
    "ps2": ("PlayStation 2", "Sony PlayStation 2"),
    "ps3": ("PlayStation 3", "Sony PlayStation 3"),
    "psp": ("PlayStation Portable",),
    "gamecube": ("GameCube", "Nintendo GameCube", "GCN"),
    "wii": ("Wii", "Nintendo Wii"),
    "wiiu": ("Wii U", "Nintendo Wii U"),
    "xbox": ("Xbox", "Xbox Original", "Microsoft Xbox"),
    "xbox360": ("Xbox 360", "Microsoft Xbox 360"),
}
FORMATOS_MANUALES = {
    ".ccd", ".cue", ".decomp", ".game", ".gdi", ".libretro", ".lnk",
    ".lst", ".m3u", ".m3u8", ".mds", ".rvzlist", ".toc", ".url", ".xex",
}
CARPETAS_MULTIMEDIA = {"images", "videos", "manuals", "media", "downloaded_images", "bezels"}
NUEVO_LISTO = "Nuevo · listo"
NUEVO_PENDIENTE = "Nuevo · elige ejecutable"
YA_INSTALADO = "Ya está en RetroBat"
REPETIDO_ORIGEN = "Repetido en origen"
IMPORTACION_MANUAL = "Requiere revisión manual"
SIN_EJECUTABLE = "Sin ejecutable"
DISCOS = {".iso", ".bin", ".cue", ".mdf", ".mds", ".nrg", ".img", ".ccd", ".chd", ".cdi", ".gdi"}
COMPRIMIDOS_ORIGEN = {".zip", ".rar", ".7z", ".001"}
FIRMWARE_PS3_URL = (
    "http://dus01.ps3.update.playstation.net/update/ps3/image/us/"
    "2026_0318_a2b60b6ac1d2e49e230144345616927c/PS3UPDAT.PUP"
)
FIRMWARE_PS3_TAMANO = 206197916
FIRMWARE_PS3_SHA256 = "158471fd834f8ea8036136b6aab43cd86c7ba73d79ca30e0af3c0fe0001cf365"


@dataclass(frozen=True)
class Sistema:
    identificador: str
    nombre: str
    carpeta: Path
    extensiones: frozenset[str]

    @property
    def es_mame(self):
        return self.identificador.startswith("mame") or self.identificador == "hbmame"


def detectar_sistema_externo(origen, raiz, sistemas):
    carpeta = origen.resolve()
    instalacion = raiz.resolve()
    if carpeta.is_relative_to(instalacion) or instalacion.is_relative_to(carpeta):
        return None

    def clave(nombre):
        texto = unicodedata.normalize("NFKD", nombre.casefold())
        palabras = re.findall(r"[a-z0-9]+", texto)
        if palabras[:1] in (["roms"], ["games"], ["juegos"]) and len(palabras) > 1:
            palabras = palabras[2:] if palabras[1] == "de" else palabras[1:]
        return "".join(palabras)

    nombre = clave(origen.name)
    coincidencias = [id_selector for id_selector, sistema in sistemas.items()
                     if nombre in {clave(id_selector), clave(sistema.carpeta.name)}]
    if len(coincidencias) == 1:
        return coincidencias[0]
    if coincidencias:
        return None
    coincidencias = [
        id_selector for id_selector, sistema in sistemas.items()
        if any(nombre == clave(alias) for alias in (sistema.nombre, *ALIAS_SISTEMAS.get(id_selector, ())))
    ]
    return coincidencias[0] if len(coincidencias) == 1 else None


def archivo_sistemas_retrobat(raiz):
    raiz = raiz.resolve()
    home = raiz / "emulationstation" / ".emulationstation"
    opciones = (home / "es_systems.cfg",
                raiz / "system" / "templates" / "emulationstation" / "es_systems.cfg")
    archivo = next((ruta for ruta in opciones if ruta.is_file()), None)
    if archivo is None:
        raise ValueError("No se encontró es_systems.cfg en esta instalación de RetroBat.")
    return archivo


def sistemas_instalados(raiz):
    raiz = raiz.resolve()
    archivo = archivo_sistemas_retrobat(raiz)
    directorio_roms = (raiz / "roms").resolve()
    entradas = []
    for sistema in ET.parse(archivo).getroot().findall("system"):
        identificador = sistema.findtext("name", "").strip().casefold()
        nombre = sistema.findtext("fullname", "").strip() or identificador
        ruta = sistema.findtext("path", "").strip().replace("\\", "/")
        extensiones = frozenset(sistema.findtext("extension", "").lower().split())
        if not (identificador and ruta and extensiones):
            continue
        carpeta = (raiz / ruta.removeprefix("~/../")).resolve()
        if carpeta == directorio_roms or not carpeta.is_relative_to(directorio_roms):
            continue
        entradas.append(Sistema(identificador, nombre, carpeta, extensiones))
    sistemas = {}
    for entrada in sorted(entradas, key=lambda x: x.carpeta.name.casefold() != x.identificador):
        clave = entrada.identificador
        if clave in sistemas:
            if entrada.carpeta == sistemas[clave].carpeta:
                continue
            clave = entrada.carpeta.name.casefold()
            if clave in sistemas:
                clave = f"{entrada.identificador} ({entrada.nombre})"
        sistemas[clave] = entrada
    return sistemas


def buscar_juegos(origen, sistema):
    if not origen.is_dir():
        raise ValueError("Selecciona una carpeta de juegos válida.")
    juegos = []
    if sistema.identificador == "windows":
        if ".lnk" not in sistema.extensiones:
            raise ValueError("Este sistema Windows no tiene habilitados los accesos directos .lnk.")
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

    es_ps3 = sistema.identificador == "ps3" and ".ps3" in sistema.extensiones
    for carpeta, dirs, archivos in os.walk(origen):
        directorio = Path(carpeta)
        if es_ps3 and (
                directorio.suffix.lower() == ".ps3"
                or (directorio / "PS3_GAME").is_dir()):
            ejecutable = directorio / "PS3_GAME" / "USRDIR" / "EBOOT.BIN"
            if ejecutable.is_file():
                nombre = (directorio.stem if directorio.suffix.lower() == ".ps3"
                          else directorio.name)
                juegos.append((nombre, [directorio]))
            dirs.clear()
            continue
        for subdir in dirs[:]:
            ruta = directorio / subdir
            if ruta.suffix.lower() in sistema.extensiones and ruta.suffix.lower() != ".ps3":
                juegos.append((ruta.stem, [ruta]))
                dirs.remove(subdir)
        for archivo in archivos:
            ruta = directorio / archivo
            if ruta.suffix.lower() in sistema.extensiones:
                juegos.append((ruta.stem, [ruta]))
    return sorted(juegos)


def clave_juego(sistema, ruta):
    return (ruta.stem if sistema.es_mame else ruta.name).casefold()


def nombres_instalados(sistema):
    return {clave_juego(sistema, ruta) for ruta in sistema.carpeta.rglob("*")
            if ruta.suffix.lower() in sistema.extensiones}


def requiere_importacion_manual(ruta):
    if ruta.suffix.lower() in FORMATOS_MANUALES:
        return True
    # Una pista de disco puede pertenecer a un descriptor situado en la misma carpeta.
    return ruta.suffix.lower() in {".bin", ".img", ".raw"} and any(
        otra.suffix.lower() in {".cue", ".gdi", ".ccd", ".toc", ".mds"} for otra in ruta.parent.iterdir()
    )


def nombre_seguro(nombre):
    if (not nombre or nombre.endswith((" ", ".")) or re.search(r'[<>:"/\\|?*\x00-\x1f]', nombre)
            or re.fullmatch(r"CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³]",
                            nombre.split(".")[0].rstrip(), re.IGNORECASE)):
        raise ValueError(f"Nombre de Windows inválido: {nombre!r}")
    return nombre


def destinos_accesos_windows(carpeta):
    """Lee el destino de cada acceso directo sin ejecutar los juegos."""
    rutas = sorted(ruta for ruta in carpeta.rglob("*.lnk") if ruta.is_file())
    if not rutas:
        return {}

    script = """
        $ErrorActionPreference = 'Stop'
        [Console]::InputEncoding = [Text.UTF8Encoding]::new($false)
        [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
        $shell = New-Object -ComObject WScript.Shell
        $rutas = ConvertFrom-Json -InputObject ([Console]::In.ReadToEnd())
        $destinos = foreach ($ruta in $rutas) {
            try { [string]$shell.CreateShortcut($ruta).TargetPath }
            catch { '' }
        }
        ConvertTo-Json -InputObject @($destinos) -Compress
    """
    resultado = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        input=json.dumps([str(ruta) for ruta in rutas]), encoding="utf-8",
        capture_output=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW,
    )
    accesos = {}
    for ruta, objetivo in zip(rutas, json.loads(resultado.stdout), strict=True):
        destino = Path(objetivo) if objetivo else None
        valido = destino is not None and destino.is_absolute() and destino.is_file()
        accesos[ruta] = destino.resolve() if valido else None
    return accesos


def indexar_accesos(accesos):
    objetivos = {destino for destino in accesos.values() if destino is not None}
    nombres = {}
    for ruta, destino in accesos.items():
        nombre = ruta.name.casefold()
        nombres[nombre] = nombres.get(nombre, False) or destino is not None
    return objetivos, nombres


def accesos_windows(carpeta):
    return indexar_accesos(destinos_accesos_windows(carpeta))


def ubicacion_juego_windows(origen, candidato, biblioteca, nombre):
    partes = candidato.relative_to(origen).parts
    carpeta = biblioteca / nombre
    if len(partes) == 1:
        return candidato, carpeta, carpeta / candidato.name
    return origen / partes[0], carpeta, carpeta.joinpath(*partes[1:])


def tipo_contenido(sufijo):
    sufijo = sufijo.lower()
    if sufijo in DISCOS:
        return "imagen de disco"
    if sufijo in COMPRIMIDOS_ORIGEN or re.fullmatch(r"\.r\d\d", sufijo):
        return "archivo comprimido"
    return ""


def describir_sin_ejecutable(ruta, limite=20000):
    """Explica por qué una carpeta de juego de Windows no tiene un .exe que RetroBat pueda abrir.

    Devuelve (resumen corto, explicación para el usuario).
    """
    tipos, extensiones, errores, total = {}, {}, [], 0
    for carpeta, subcarpetas, archivos in os.walk(ruta, onerror=errores.append):
        for nombre in archivos:
            total += 1
            sufijo = Path(nombre).suffix.lower()
            extensiones[sufijo or "(sin extensión)"] = extensiones.get(sufijo or "(sin extensión)", 0) + 1
            if tipo := tipo_contenido(sufijo):
                tipos.setdefault(tipo, set()).add(sufijo)
            if total >= limite:
                break
        if total >= limite:
            break
    if errores and not total:
        return "no se pudo leer", f"Windows no permitió leer la carpeta: {errores[0]}"
    if not total:
        return "carpeta vacía", "La carpeta no tiene archivos."
    if "imagen de disco" in tipos:
        lista = ", ".join(sorted(tipos["imagen de disco"]))
        return (f"imagen de disco ({lista})",
                f"Contiene una imagen de disco ({lista}). Móntala o instala el juego desde ella y elige la "
                "carpeta del juego instalado.")
    if "archivo comprimido" in tipos:
        lista = ", ".join(sorted(tipos["archivo comprimido"]))
        return (f"comprimido ({lista})",
                f"Contiene archivos comprimidos ({lista}). Descomprímelos y vuelve a verificar la carpeta.")
    comunes = ", ".join(f"{ext} ({n})" for ext, n in sorted(extensiones.items(), key=lambda par: -par[1])[:4])
    return "sin .exe", f"No hay archivos .exe. Contiene {total} archivos: {comunes}."


def sin_ejecutable_windows(origen, juegos):
    """Elementos de la carpeta de origen que no se detectaron como juego de Windows, con su motivo."""
    detectados = {nombre.casefold() for nombre, _ in juegos}
    try:
        elementos = sorted(origen.iterdir(), key=lambda ruta: ruta.name.casefold())
    except OSError:
        return []
    resultado = []
    for ruta in elementos:
        if ruta.name.startswith(".") or ruta.name.casefold() in {"desktop.ini", "thumbs.db"}:
            continue
        if ruta.is_dir() and ruta.name.casefold() not in detectados:
            resultado.append((ruta.name, ruta, *describir_sin_ejecutable(ruta)))
        elif ruta.is_file() and (tipo := tipo_contenido(ruta.suffix)) and ruta.stem.casefold() not in detectados:
            resultado.append((ruta.stem, ruta, f"{tipo} ({ruta.suffix.lower()})",
                              f"Es un {tipo}. Descomprímelo o instala el juego y elige la carpeta resultante."))
    return resultado


def estado_windows(candidatos, salida, objetivos, nombres, origen, biblioteca):
    for candidato in candidatos:
        if candidato.resolve() in objetivos:
            return candidato, YA_INSTALADO
        _, _, copia = ubicacion_juego_windows(origen, candidato, biblioteca, salida.stem)
        if copia.resolve() in objetivos:
            return copia, YA_INSTALADO
    nombre = salida.name.casefold()
    if nombre in nombres:
        estado = "Nombre en uso" if nombres[nombre] else "Acceso directo roto"
        return None, estado
    if salida.exists():
        return None, "Destino en uso"
    if len(candidatos) == 1:
        return candidatos[0], NUEVO_LISTO
    return None, NUEVO_PENDIENTE


def inspeccionar_tema(raiz, origen):
    archivo = origen / "theme.xml"
    if not archivo.is_file():
        raise ValueError("Selecciona la carpeta que contiene theme.xml de EmulationStation.")
    tema = ET.parse(archivo).getroot()
    if tema.tag != "theme":
        raise ValueError("theme.xml debe contener un tema de EmulationStation.")

    destino = raiz / "emulationstation" / ".emulationstation" / "themes" / nombre_seguro(origen.name)
    if destino.exists():
        raise FileExistsError(f"Ya existe un tema en {destino}.")
    if destino.resolve().is_relative_to(origen):
        raise ValueError("El destino está dentro de la carpeta del tema.")

    extensiones = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")
    rutas = [carpeta / (nombre + extension)
             for nombre in ("preview", "screenshot", "splash")
             for carpeta in (origen, origen / "art", origen / "_inc")
             for extension in extensiones]
    for elemento in tema.iter("image"):
        if elemento.get("name", "").casefold() in {"background", "splash"}:
            recurso = elemento.findtext("path", "").strip()
            if recurso:
                rutas.append(origen / recurso.replace("\\", "/"))
    imagenes = tuple(dict.fromkeys(
        ruta for ruta in rutas if ruta.suffix.lower() in extensiones and ruta.is_file()
        and ruta.resolve().is_relative_to(origen)
    ))
    return destino, imagenes


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


def tamanio_copia(origen):
    if origen.is_dir():
        return sum(ruta.stat().st_size for ruta in origen.rglob("*") if ruta.is_file())
    return origen.stat().st_size


def copiar_archivo(origen, destino, avanzar):
    if avanzar is None:
        return shutil.copy2(origen, destino)
    with open(origen, "rb") as entrada, open(destino, "wb") as salida:
        for bloque in iter(lambda: entrada.read(1024 * 1024), b""):
            salida.write(bloque)
            avanzar(len(bloque))
    return shutil.copystat(origen, destino)


def copiar(origen, destino, avanzar=None):
    if destino.exists():
        raise FileExistsError(f"Ya existe: {destino}")
    if origen.is_dir() and destino.resolve().is_relative_to(origen.resolve()):
        raise ValueError("El destino está dentro de la carpeta de origen.")
    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destino.parent) as temporal:
        nuevo = Path(temporal) / destino.name
        if origen.is_dir():
            shutil.copytree(origen, nuevo, copy_function=lambda a, b: copiar_archivo(a, b, avanzar))
            publicar_directorio(nuevo, destino)
        else:
            copiar_archivo(origen, nuevo, avanzar)
            publicar(nuevo, destino)


def discos_mame(rom):
    carpeta = rom.with_suffix("")
    return sorted(disco for disco in carpeta.rglob("*")
                  if disco.suffix.lower() in {".chd", ".img"} and disco.is_file())


def copiar_rom(sistema, origen, destino, avanzar=None):
    if not sistema.es_mame or origen.suffix.lower() not in {".zip", ".7z"}:
        copiar(origen, destino, avanzar)
        return
    discos = discos_mame(origen)
    if not discos:
        copiar(origen, destino, avanzar)
        return

    carpeta_discos = origen.with_suffix("")
    destino_discos = destino.with_suffix("")
    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destino.parent) as temporal:
        preparado = Path(temporal)
        rom = preparado / destino.name
        carpeta = preparado / destino_discos.name
        copiar_archivo(origen, rom, avanzar)
        for disco in discos:
            copia = carpeta / disco.relative_to(carpeta_discos)
            copia.parent.mkdir(parents=True, exist_ok=True)
            copiar_archivo(disco, copia, avanzar)
        publicar_directorio(carpeta, destino_discos)
        try:
            publicar(rom, destino)
        except OSError:
            destino_discos.rename(carpeta)
            raise


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


def copiar_juego_windows(origen, ejecutable, biblioteca, acceso, avanzar=None):
    paquete, carpeta, ejecutable_copiado = ubicacion_juego_windows(
        origen, ejecutable, biblioteca, nombre_seguro(acceso.stem)
    )
    if carpeta.exists():
        raise FileExistsError(f"Ya existe una copia en {carpeta}.")
    carpeta.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=carpeta.parent) as temporal:
        preparado = Path(temporal) / carpeta.name
        if paquete.is_dir():
            shutil.copytree(paquete, preparado, copy_function=lambda a, b: copiar_archivo(a, b, avanzar))
        else:
            preparado.mkdir()
            copiar_archivo(paquete, preparado / paquete.name, avanzar)
        publicar_directorio(preparado, carpeta)
        try:
            shortcut(ejecutable_copiado, acceso)
        except (OSError, subprocess.SubprocessError):
            carpeta.rename(preparado)
            raise
    return ejecutable_copiado


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
        resultados.append(f"{estado_archivo_bios(ruta, esperado)}: {relativo}")
    return resultados


def estado_archivo_bios(ruta, esperado):
    if not ruta.is_file():
        return "FALTA"
    if not esperado:
        return "PRESENTE"
    with ruta.open("rb") as archivo:
        obtenido = hashlib.file_digest(archivo, "md5").hexdigest()
    return "OK" if obtenido == esperado.lower() else "MD5 DISTINTO"


def catalogo_bios(raiz):
    catalogo = raiz / "system" / "modules" / "rb_gui" / "bios_local.json"
    if not catalogo.is_file():
        return {}
    return json.loads(catalogo.read_text(encoding="utf-8-sig"))


def rutas_bios_sistema(raiz, sistema, datos):
    base = (raiz / "bios").resolve()
    for entrada in datos.get(sistema, {}).get("biosFiles", []):
        ruta = (raiz / entrada["file"]).resolve()
        if ruta != base and ruta.is_relative_to(base):
            yield ruta, entrada.get("md5") or ""


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
