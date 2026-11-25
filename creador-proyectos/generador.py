#!/usr/bin/env python3
"""
Generador de Proyectos IA Tecnotics.

Crea proyectos nuevos, o mejora proyectos que ya existen, para trabajar en
conjunto con Claude y Codex:

  1. Memoria compartida que leen los dos agentes (AGENTS.md, CLAUDE.md,
     docs/ESTADO.md, docs/BITACORA.md, ...), para retomar "donde quedamos".
  2. Equipo de skills: jefe de proyecto, programador y analista, diseñador
     gráfico e investigador, apoyados en skills open source.
  3. Graphify configurado para Claude Code y para Codex.
  4. Repositorio en GitHub como respaldo constante.
  5. Índice global para decir "vamos a <proyecto>" desde cualquier chat.

En un proyecto existente nunca sobrescribe tus archivos: solo crea lo que
falta y añade bloques marcados a AGENTS.md, CLAUDE.md y .gitignore.

Solo usa la biblioteca estándar de Python (3.10 o superior).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

NOMBRE_HERRAMIENTA = "Generador de Proyectos IA Tecnotics"
AQUI = Path(__file__).resolve().parent
PLANTILLAS = AQUI / "plantillas"
CONFIG = Path.home() / ".proyectos-ia" / "config.json"
CACHE = Path.home() / ".proyectos-ia" / "cache"
CATALOGO = AQUI / "skills.json"
ROLES = PLANTILLAS / "_punto_agents" / "skills"

# Rutas que el generador crea o modifica (lo único que se sube en modo "mejorar").
RUTAS_PROPIAS = [
    "AGENTS.md", "CLAUDE.md", "README.md", ".gitignore", ".graphifyignore",
    "docs", ".agents", ".claude", ".codex", "guardar.bat", "guardar.sh",
    "configurar_graphify.bat", ".gitattributes", "graphify-out",
]

# ---------------------------------------------------------------- utilidades
def info(msg: str) -> None:
    print(f"  {msg}")


def ok(msg: str) -> None:
    print(f"  [ok] {msg}")


def aviso(msg: str) -> None:
    print(f"  [aviso] {msg}")


def error(msg: str) -> None:
    print(f"  [error] {msg}", file=sys.stderr)


def titulo(msg: str) -> None:
    print(f"\n== {msg} ==")


def ejecutar(cmd: list[str], cwd: Path | None = None, mostrar: bool = True) -> subprocess.CompletedProcess:
    if mostrar:
        info("$ " + " ".join(cmd))
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, encoding="utf-8", errors="replace")


def existe(programa: str) -> bool:
    return shutil.which(programa) is not None


def preguntar(texto: str, defecto: str | None = None, obligatorio: bool = True) -> str:
    sufijo = f" [{defecto}]" if defecto else ""
    while True:
        try:
            r = input(f"  {texto}{sufijo}: ").strip()
        except EOFError:
            r = ""
        if not r and defecto is not None:
            return defecto
        if r or not obligatorio:
            return r
        print("    (este dato es obligatorio)")


def preguntar_si(texto: str, defecto: bool = True) -> bool:
    d = "S/n" if defecto else "s/N"
    r = preguntar(f"{texto} ({d})", defecto="", obligatorio=False).lower()
    if not r:
        return defecto
    return r in ("s", "si", "sí", "y", "yes")


def elegir(texto: str, opciones: list[str], defecto: int = 0) -> str:
    print(f"  {texto}")
    for i, o in enumerate(opciones, 1):
        marca = " (por defecto)" if i - 1 == defecto else ""
        print(f"    {i}. {o}{marca}")
    while True:
        r = preguntar("Elige un número", defecto=str(defecto + 1))
        if r.isdigit() and 1 <= int(r) <= len(opciones):
            return opciones[int(r) - 1]
        # Permite escribir un valor que no está en la lista (p. ej. otra org).
        if r and not r.isdigit():
            return r


def a_slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return t or "proyecto"


def leer_config() -> dict:
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def guardar_config(cfg: dict) -> None:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def rellenar(texto: str, datos: dict) -> str:
    for k, v in datos.items():
        texto = texto.replace("{{" + k + "}}", v)
    return texto


def poner_bloque(archivo: Path, bloque: str, clave: str = "proyectos-ia") -> None:
    """Escribe (o reemplaza) un bloque marcado dentro de un archivo, sin tocar el resto."""
    inicio, fin = f"<!-- {clave}:inicio -->", f"<!-- {clave}:fin -->"
    archivo.parent.mkdir(parents=True, exist_ok=True)
    actual = archivo.read_text(encoding="utf-8") if archivo.exists() else ""
    nuevo = f"{inicio}\n{bloque.strip()}\n{fin}"
    if inicio in actual and fin in actual:
        antes, resto = actual.split(inicio, 1)
        _, despues = resto.split(fin, 1)
        actual = antes + nuevo + despues
    else:
        actual = (actual.rstrip() + "\n\n" if actual.strip() else "") + nuevo + "\n"
    archivo.write_text(actual, encoding="utf-8")


# ------------------------------------------------------------- comprobaciones
def comprobar_requisitos(usar_github: bool) -> dict:
    titulo("Comprobando requisitos")
    estado = {"git": existe("git"), "gh": existe("gh"), "graphify": existe("graphify"), "login": None}

    if not estado["git"]:
        error("No encuentro git. Instálalo desde https://git-scm.com y vuelve a ejecutar.")
        sys.exit(1)
    ok("git")

    if usar_github:
        if not estado["gh"]:
            error("No encuentro GitHub CLI (gh). Instálalo desde https://cli.github.com")
            info("y luego ejecuta:  gh auth login")
            sys.exit(1)
        r = ejecutar(["gh", "api", "user", "--jq", ".login"], mostrar=False)
        if r.returncode != 0:
            error("gh no tiene sesión iniciada. Ejecuta:  gh auth login")
            sys.exit(1)
        estado["login"] = r.stdout.strip()
        ok(f"gh (sesión de {estado['login']})")

    if estado["graphify"]:
        ok("graphify")
    else:
        aviso("Graphify no está instalado; te ofreceré instalarlo más adelante.")

    # git necesita nombre y correo para hacer commits
    for clave in ("user.name", "user.email"):
        if not ejecutar(["git", "config", "--global", clave], mostrar=False).stdout.strip():
            valor = preguntar(f"git no tiene {clave} configurado. Escríbelo")
            ejecutar(["git", "config", "--global", clave, valor], mostrar=False)
    return estado


def cuentas_github(login: str) -> list[str]:
    cuentas = [login]
    r = ejecutar(["gh", "api", "user/orgs", "--jq", ".[].login"], mostrar=False)
    if r.returncode == 0:
        cuentas += [o for o in r.stdout.split() if o]
    return cuentas


# ---------------------------------------------------------------- generación
def ruta_final(relativo: Path) -> Path:
    # Los archivos que empiezan por "punto" se guardan como "_punto_xxx"
    # para que no se oculten ni se ignoren dentro de esta herramienta.
    return Path(*[p.replace("_punto_", ".", 1) if p.startswith("_punto_") else p for p in relativo.parts])


def combinar_lineas(archivo: Path, nuevo: str) -> bool:
    """Añade al final las líneas de `nuevo` que aún no estén (para .gitignore y similares)."""
    actual = archivo.read_text(encoding="utf-8").splitlines()
    faltan = [l for l in nuevo.splitlines() if l.strip() and not l.startswith("#") and l not in actual]
    if not faltan:
        return False
    with archivo.open("a", encoding="utf-8") as f:
        f.write(f"\n# Añadido por {NOMBRE_HERRAMIENTA}\n" + "\n".join(faltan) + "\n")
    return True


def generar_archivos(destino: Path, datos: dict, existente: bool) -> None:
    titulo("Memoria compartida del proyecto")
    for origen in sorted(PLANTILLAS.rglob("*")):
        if origen.is_dir():
            continue
        relativo = origen.relative_to(PLANTILLAS)
        if relativo.parts[0] == "_punto_agents":
            continue  # las skills las instala instalar_skills()
        rel = ruta_final(relativo)
        final = destino / rel
        texto = rellenar(origen.read_text(encoding="utf-8"), datos)
        final.parent.mkdir(parents=True, exist_ok=True)

        if not final.exists():
            final.write_text(texto, encoding="utf-8")
            ok(f"{rel}  (creado)")
        elif rel.name in (".gitignore", ".graphifyignore"):
            ok(f"{rel}  ({'completado' if combinar_lineas(final, texto) else 'ya estaba completo'})")
        elif rel.as_posix() == "AGENTS.md":
            poner_bloque(final, texto, "protocolo")
            ok(f"{rel}  (añadido el protocolo de trabajo, tu contenido se conserva)")
        elif rel.as_posix() == "CLAUDE.md":
            if "@AGENTS.md" not in final.read_text(encoding="utf-8"):
                poner_bloque(final, texto, "protocolo")
                ok(f"{rel}  (ahora importa AGENTS.md)")
            else:
                ok(f"{rel}  (ya importaba AGENTS.md)")
        else:
            info(f"[=] {rel}  (ya existía, no se toca)")

def descargar_repo(nombre: str, repo: dict) -> Path | None:
    """Descarga un repositorio de skills en el commit fijado (con caché local)."""
    carpeta = CACHE / f"{nombre}-{repo['commit'][:12]}"
    if (carpeta / ".listo").exists():
        return carpeta
    if carpeta.exists():
        shutil.rmtree(carpeta, ignore_errors=True)
    carpeta.mkdir(parents=True)
    pasos = [
        ["git", "init", "-q"],
        ["git", "fetch", "-q", "--depth", "1", repo["url"], repo["commit"]],
        ["git", "-c", "advice.detachedHead=false", "checkout", "-q", "FETCH_HEAD"],
    ]
    for cmd in pasos:
        r = ejecutar(cmd, cwd=carpeta, mostrar=False)
        if r.returncode != 0:
            aviso(f"No pude descargar {repo['url']}: {(r.stderr or r.stdout).strip()[-300:]}")
            return None
    (carpeta / ".listo").write_text(repo["commit"], encoding="utf-8")
    return carpeta


def instalar_skills(destino: Path) -> None:
    """Instala los 4 roles y las skills open source en .agents/skills (Codex) y .claude/skills (Claude)."""
    titulo("Instalando el equipo de skills")
    catalogo = json.loads(CATALOGO.read_text(encoding="utf-8"))
    agentes = destino / ".agents" / "skills"
    agentes.mkdir(parents=True, exist_ok=True)

    for rol in sorted(ROLES.iterdir()):
        shutil.copytree(rol, agentes / rol.name, dirs_exist_ok=True)
        ok(f"rol {rol.name}")

    fuentes = [
        "# Origen de las skills\n",
        "Los cuatro roles (`jefe-de-proyecto`, `programador-analista`, `disenador-grafico`,",
        f"`investigador`) son de {NOMBRE_HERRAMIENTA}. Las demás son open source:\n",
        "| Skill | Rol | Origen | Licencia |",
        "|---|---|---|---|",
    ]
    repos = catalogo["repositorios"]
    descargados = {n: descargar_repo(n, r) for n, r in repos.items()}
    fallidas = []
    for sk in catalogo["skills"]:
        repo, base = repos[sk["repo"]], descargados[sk["repo"]]
        origen = base / sk["ruta"] if base else None
        if not origen or not (origen / "SKILL.md").exists():
            fallidas.append(sk["nombre"])
            continue
        final = agentes / sk["nombre"]
        shutil.copytree(origen, final, dirs_exist_ok=True)
        licencia = repo.get("archivo_licencia")
        if licencia and not any(final.glob("LICENSE*")):
            shutil.copy2(base / licencia, final / "LICENSE")
        fuentes.append(
            f"| `{sk['nombre']}` | {sk['rol']} | {repo['url']}/tree/{repo['commit'][:12]}/{sk['ruta']} | {repo['licencia']} |"
        )
        ok(f"{sk['nombre']}  ({sk['rol']})")
    (agentes / "FUENTES.md").write_text("\n".join(fuentes) + "\n", encoding="utf-8")

    # Claude Code lee las skills del proyecto en .claude/skills: misma copia.
    claude = destino / ".claude" / "skills"
    shutil.copytree(agentes, claude, dirs_exist_ok=True)
    ok("copiadas también a .claude/skills para Claude")

    # Sección "Equipo" en AGENTS.md (Claude la ve a través de CLAUDE.md).
    poner_bloque(destino / "AGENTS.md", (AQUI / "equipo.md").read_text(encoding="utf-8"), "equipo")
    for carpeta in ("planes", "investigacion", "diseno"):
        lee = destino / "docs" / carpeta / "README.md"
        if not lee.exists():
            lee.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(PLANTILLAS / "docs" / carpeta / "README.md", lee)
    if fallidas:
        aviso("No se instalaron (sin conexión o repo no disponible): " + ", ".join(fallidas))
        aviso(f"Repite luego con:  python generador.py --mejorar \"{destino}\"")


def configurar_graphify(destino: Path, estado: dict, no_interactivo: bool) -> bool:
    titulo("Configurando Graphify")
    if not estado["graphify"]:
        instalar = no_interactivo or preguntar_si("¿Instalo Graphify ahora (pip install graphifyy)?")
        if not instalar:
            aviso("Sin Graphify. Puedes instalarlo luego y ejecutar  configurar_graphify.bat  en el proyecto.")
            return False
        # Preferimos uv o pipx (dejan el comando en el PATH); si no, pip del usuario.
        if existe("uv"):
            cmd = ["uv", "tool", "install", "graphifyy"]
        elif existe("pipx"):
            cmd = ["pipx", "install", "graphifyy"]
        else:
            cmd = [sys.executable, "-m", "pip", "install", "--user", "graphifyy"]
        r = ejecutar(cmd)
        if r.returncode != 0 or not existe("graphify"):
            aviso("No pude dejar 'graphify' listo en el PATH:")
            info((r.stderr or r.stdout).strip()[-600:])
            aviso("Ejecuta luego  configurar_graphify.bat  dentro del proyecto.")
            return False
        ok("Graphify instalado")

    # Instala el skill global (una vez por máquina) y la integración del proyecto
    # para cada asistente. Si un comando no existe en tu versión, se avisa y se sigue.
    pasos = [
        (["graphify", "install"], "skill /graphify para Claude Code"),
        (["graphify", "install", "--platform", "codex"], "skill $graphify para Codex"),
        (["graphify", "claude", "install"], "modo siempre activo en Claude (CLAUDE.md + hook)"),
        (["graphify", "codex", "install"], "modo siempre activo en Codex (AGENTS.md)"),
        (["graphify", "hook", "install"], "hooks de git: el grafo se actualiza solo en cada commit"),
    ]
    todo_bien = True
    for cmd, que in pasos:
        r = ejecutar(cmd, cwd=destino)
        if r.returncode == 0:
            ok(que)
        else:
            todo_bien = False
            aviso(f"No se pudo: {que}. Revisa 'graphify --help'.")
    return todo_bien


def git(destino: Path, *args: str, mostrar: bool = False) -> subprocess.CompletedProcess:
    return ejecutar(["git", *args], cwd=destino, mostrar=mostrar)


def guardar_en_git(destino: Path, datos: dict, visibilidad: str, usar_github: bool, existente: bool) -> None:
    titulo("Git y GitHub")
    if existente:
        rutas = [r for r in RUTAS_PROPIAS if (destino / r).exists()]
        git(destino, "add", "--", *rutas, mostrar=True)
        mensaje = f"Incorpora {NOMBRE_HERRAMIENTA}: memoria compartida, equipo de skills y Graphify"
    else:
        git(destino, "add", "-A", mostrar=True)
        mensaje = f"Inicio del proyecto {datos['NOMBRE']}"

    if not git(destino, "diff", "--cached", "--quiet").returncode:
        info("No hay cambios nuevos que guardar.")
    else:
        r = git(destino, "commit", "-m", mensaje, mostrar=True)
        if r.returncode != 0:
            error(r.stderr.strip() or r.stdout.strip())
            sys.exit(1)
        ok("Commit creado")

    remoto = git(destino, "remote", "get-url", "origin").stdout.strip()
    if remoto:
        rama = git(destino, "branch", "--show-current").stdout.strip() or "main"
        r = git(destino, "push", "-u", "origin", rama, mostrar=True)
        if r.returncode == 0:
            ok(f"Subido a {remoto} (rama {rama})")
        else:
            aviso("No se pudo subir: " + (r.stderr.strip()[-400:] or "error desconocido"))
            info("Cuando lo resuelvas:  git push")
        return

    if not usar_github:
        aviso("Sin GitHub (--sin-github): el repositorio queda solo en tu equipo.")
        return

    r = ejecutar([
        "gh", "repo", "create", datos["REPO"], f"--{visibilidad}",
        "--description", datos["DESCRIPCION"],
        "--source", str(destino), "--remote", "origin", "--push",
    ])
    if r.returncode != 0:
        error("No se pudo crear el repositorio en GitHub:")
        info(r.stderr.strip())
        info("El proyecto local está listo; cuando lo resuelvas ejecuta en su carpeta:")
        info(f"  gh repo create {datos['REPO']} --{visibilidad} --source . --push")
        return
    ok(f"Repositorio creado y subido: {datos['URL']}")


def registrar(base: Path, datos: dict, destino: Path, tocar_global: bool) -> None:
    titulo("Registrando el proyecto")
    base.mkdir(parents=True, exist_ok=True)
    indice = base / "PROYECTOS.md"
    if not indice.exists():
        indice.write_text(
            "# Índice de proyectos\n\n"
            "Lista que usan Claude y Codex para encontrar un proyecto cuando dices "
            "\"vamos a <proyecto>\".\n\n"
            "| Proyecto | Carpeta | Repositorio | Descripción | Alta |\n"
            "|---|---|---|---|---|\n",
            encoding="utf-8",
        )
    if f"`{destino}`" in indice.read_text(encoding="utf-8"):
        ok(f"Ya estaba en {indice}")
    else:
        with indice.open("a", encoding="utf-8") as f:
            f.write(f"| {datos['NOMBRE']} | `{destino}` | {datos['URL']} | {datos['DESCRIPCION']} | {datos['FECHA']} |\n")
        ok(f"Añadido a {indice}")

    if not tocar_global:
        return
    instruccion = rellenar((AQUI / "instruccion_global.md").read_text(encoding="utf-8"), {"INDICE": str(indice)})
    for archivo in (Path.home() / ".claude" / "CLAUDE.md", Path.home() / ".codex" / "AGENTS.md"):
        poner_bloque(archivo, instruccion)
        ok(f"Instrucción \"vamos a <proyecto>\" en {archivo}")


# ---------------------------------------------------------- datos del proyecto
def leer_titulo_readme(destino: Path) -> str | None:
    lee = destino / "README.md"
    if lee.exists():
        for linea in lee.read_text(encoding="utf-8", errors="replace").splitlines():
            if linea.startswith("# "):
                return linea[2:].strip()
    return None


def cuenta_y_repo_de_remoto(remoto: str) -> tuple[str, str] | None:
    m = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$", remoto)
    return (m.group(1), m.group(2)) if m else None

# ---------------------------------------------------------------------- main
TEXTOS_ESTADO = {
    False: (
        "Proyecto recién creado. Aún no hay código.",
        "1. Primera sesión (jefe de proyecto): revisar `docs/PROYECTO.md` con el\n"
        "   usuario y completar objetivo y alcance.\n"
        "2. Construir el grafo de Graphify (`/graphify .` en Claude, `$graphify .` en Codex).\n"
        "3. Proponer la estructura inicial del proyecto.",
    ),
    True: (
        f"Proyecto existente incorporado a {NOMBRE_HERRAMIENTA}. La memoria compartida\n"
        "está recién creada: todavía no describe el código actual.",
        "1. Construir el grafo de Graphify (`/graphify .` en Claude, `$graphify .` en Codex).\n"
        "2. Jefe de proyecto: leer el grafo y el código, y completar `docs/PROYECTO.md`\n"
        "   (qué hace hoy, objetivo, alcance) y este archivo, con el usuario.\n"
        "3. Programador y analista: documentar en `AGENTS.md` cómo ejecutar y probar.",
    ),
}


def main() -> None:
    p = argparse.ArgumentParser(description=f"{NOMBRE_HERRAMIENTA}: crea o mejora proyectos para Claude + Codex.")
    p.add_argument("--crear", action="store_true", help="Crear un proyecto nuevo (sin mostrar el menú)")
    p.add_argument("--mejorar", metavar="CARPETA", help="Incorporar un proyecto existente (no sobrescribe nada)")
    p.add_argument("--mejorar-preguntar", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--nombre")
    p.add_argument("--cuenta", help="Usuario u organización de GitHub")
    p.add_argument("--repo", help="Nombre del repositorio en GitHub")
    p.add_argument("--descripcion")
    p.add_argument("--objetivo", help="Qué debe lograr el proyecto")
    p.add_argument("--tecnologias", help="Lenguajes o herramientas")
    p.add_argument("--visibilidad", choices=["private", "public"])
    p.add_argument("--carpeta-base", help="Dónde están tus proyectos (y su índice PROYECTOS.md)")
    p.add_argument("--sin-github", action="store_true", help="No crear el repositorio remoto")
    p.add_argument("--sin-graphify", action="store_true", help="No configurar Graphify")
    p.add_argument("--sin-global", action="store_true", help="No tocar ~/.claude/CLAUDE.md ni ~/.codex/AGENTS.md")
    p.add_argument("--instalar-skills", metavar="CARPETA", help="Solo instalar o actualizar el equipo de skills")
    p.add_argument("--si", action="store_true", help="No preguntar: usar los datos dados y los valores por defecto")
    a = p.parse_args()

    print(f"\n  {NOMBRE_HERRAMIENTA}")
    print("  " + "-" * len(NOMBRE_HERRAMIENTA))

    if a.instalar_skills:
        destino = Path(a.instalar_skills).expanduser().resolve()
        instalar_skills(destino)
        info("Revisa los cambios y súbelos:  git add -A && git commit -m \"Equipo de skills\" && git push")
        return

    # ¿Crear o mejorar?
    existente = bool(a.mejorar) or a.mejorar_preguntar
    if not existente and not a.crear and not a.nombre and not a.si:
        modo = elegir("¿Qué quieres hacer?", ["Crear un proyecto nuevo", "Mejorar un proyecto existente"])
        existente = modo.startswith("Mejorar")
    destino: Path | None = None
    if existente:
        carpeta = a.mejorar or preguntar("Carpeta del proyecto existente")
        destino = Path(carpeta).expanduser().resolve()
        if not destino.is_dir():
            error(f"No existe la carpeta {destino}")
            sys.exit(1)

    cfg = leer_config()

    # Si el proyecto ya tiene remoto, de ahí salen la cuenta y el repo (y no hace falta gh).
    remoto, url_origen = None, ""
    if existente and (destino / ".git").exists():
        url_origen = ejecutar(["git", "remote", "get-url", "origin"], cwd=destino, mostrar=False).stdout.strip()
        remoto = cuenta_y_repo_de_remoto(url_origen) if url_origen else None
        if url_origen and not remoto:
            aviso(f"El remoto origin no es de GitHub ({url_origen}); se usará tal cual.")
    estado = comprobar_requisitos(not a.sin_github and not url_origen)
    usar_github = not a.sin_github and estado["login"] is not None

    titulo("Datos del proyecto")
    def dato(valor, pregunta, defecto=None, obligatorio=True):
        if valor is not None:
            return valor
        if a.si:
            return defecto or ""
        return preguntar(pregunta, defecto, obligatorio)

    nombre_defecto = (leer_titulo_readme(destino) or destino.name) if existente else None
    nombre = dato(a.nombre, "Nombre del proyecto", nombre_defecto)
    if not nombre:
        error("Falta el nombre (--nombre).")
        sys.exit(1)
    slug = destino.name if existente else a_slug(nombre)

    if remoto:
        cuenta, repo_nombre = remoto
        info(f"Repositorio en GitHub: {cuenta}/{repo_nombre}")
    elif usar_github:
        if a.cuenta:
            cuenta = a.cuenta
        elif a.si:
            cuenta = cfg.get("cuenta") or estado["login"]
        else:
            opciones = cuentas_github(estado["login"])
            previa = cfg.get("cuenta")
            defecto = opciones.index(previa) if previa in opciones else 0
            cuenta = elegir("¿En qué cuenta de GitHub se crea? (o escribe otra)", opciones, defecto)
        repo_nombre = dato(a.repo, "Nombre del repositorio", a_slug(nombre) if existente else slug)
    else:
        cuenta, repo_nombre = cfg.get("cuenta", "local"), a.repo or slug

    descripcion = dato(a.descripcion, "Descripción corta (una línea)")
    objetivo = dato(a.objetivo, "¿Qué debe lograr el proyecto?", "Por definir en la primera sesión", False)
    tecnologias = dato(a.tecnologias, "Tecnologías (opcional)", "Por definir", False)
    if a.visibilidad:
        visibilidad = a.visibilidad
    elif a.si or not usar_github or remoto:
        visibilidad = "private"
    else:
        visibilidad = "public" if elegir("Visibilidad del repositorio", ["privado", "público"]) == "público" else "private"

    base_defecto = cfg.get("carpeta_base") or str(destino.parent if existente else Path.home() / "Proyectos")
    base = Path(dato(a.carpeta_base, "Carpeta donde guardas tus proyectos (índice)", base_defecto)).expanduser()
    if not existente:
        destino = base / slug
        if destino.exists() and any(destino.iterdir()):
            error(f"La carpeta {destino} ya existe y no está vacía. Para incorporarla usa --mejorar.")
            sys.exit(1)

    hay_github = bool(remoto) or (usar_github and not url_origen)
    url = f"https://github.com/{cuenta}/{repo_nombre}" if hay_github else "(solo local)"
    en_que, pasos = TEXTOS_ESTADO[existente]
    datos = {
        "NOMBRE": nombre, "SLUG": slug, "DESCRIPCION": descripcion, "OBJETIVO": objetivo,
        "TECNOLOGIAS": tecnologias, "CUENTA": cuenta, "REPO": f"{cuenta}/{repo_nombre}", "URL": url,
        "VISIBILIDAD": "privado" if visibilidad == "private" else "público",
        "FECHA": dt.date.today().isoformat(), "EN_QUE_ESTAMOS": en_que, "PROXIMOS_PASOS": pasos,
        "HERRAMIENTA": NOMBRE_HERRAMIENTA,
    }

    titulo("Resumen")
    info(f"{'Modo':12} {'mejorar proyecto existente' if existente else 'crear proyecto nuevo'}")
    for k in ("NOMBRE", "DESCRIPCION", "OBJETIVO", "TECNOLOGIAS", "URL"):
        info(f"{k.capitalize():12} {datos[k]}")
    info(f"{'Carpeta':12} {destino}")
    if existente and (destino / ".git").exists():
        sucios = ejecutar(["git", "status", "--porcelain"], cwd=destino, mostrar=False).stdout.strip()
        if sucios:
            aviso("Tienes cambios sin guardar en git. No se incluirán en el commit del generador.")
    if not a.si and not preguntar_si("¿Todo correcto? ¿Sigo?"):
        print("  Cancelado.")
        return

    tocar_global = not a.sin_global
    if tocar_global and not a.si and not cfg.get("global_hecho"):
        tocar_global = preguntar_si(
            "¿Añado a ~/.claude/CLAUDE.md y ~/.codex/AGENTS.md la instrucción para que entiendan "
            "\"vamos a <proyecto>\"? (solo se hace una vez)"
        )

    destino.mkdir(parents=True, exist_ok=True)
    if not (destino / ".git").exists():
        ejecutar(["git", "init", "-b", "main"], cwd=destino, mostrar=False)
    generar_archivos(destino, datos, existente)
    instalar_skills(destino)
    if not a.sin_graphify:
        configurar_graphify(destino, estado, a.si)
    guardar_en_git(destino, datos, visibilidad, usar_github, existente)
    registrar(base, datos, destino, tocar_global)

    cfg.update({"cuenta": cuenta, "carpeta_base": str(base)})
    if tocar_global:
        cfg["global_hecho"] = True
    guardar_config(cfg)

    titulo("Listo")
    info(f"Proyecto en: {destino}")
    info(f"GitHub:      {url}")
    print(
        "\n  Para trabajar:\n"
        f"    1. Abre Claude o Codex y di: \"vamos a {nombre}\".\n"
        "    2. Primera sesión: \"construye el grafo y dime de qué se trata el proyecto\"\n"
        "       (Claude: /graphify .   Codex: $graphify .).\n"
        "    3. Pide el rol que necesites: \"como jefe de proyecto...\", \"como investigador...\",\n"
        "       \"como diseñador...\", \"como programador...\".\n"
        "    4. Al terminar di: \"cerramos sesión\" y el agente guarda el estado y sube a GitHub.\n"
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n  Cancelado.")
