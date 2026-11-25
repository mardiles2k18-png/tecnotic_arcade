#!/usr/bin/env python3
"""
Creador de proyectos para trabajar en conjunto con Claude y Codex.

Qué hace:
  1. Pregunta nombre, cuenta de GitHub, descripción, visibilidad y objetivo.
  2. Crea la carpeta del proyecto con la "memoria compartida" que leen los dos
     agentes (AGENTS.md, CLAUDE.md, docs/ESTADO.md, docs/BITACORA.md, ...).
  3. Configura Graphify para Claude Code y para Codex.
  4. Crea el repositorio en GitHub y sube el primer commit.
  5. Registra el proyecto en el índice global, para que puedas decir
     "vamos a <proyecto>" desde cualquier chat.

Solo usa la biblioteca estándar de Python (3.10 o superior).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PLANTILLAS = AQUI / "plantillas"
CONFIG = Path.home() / ".proyectos-ia" / "config.json"

MARCA_INICIO = "<!-- proyectos-ia:inicio -->"
MARCA_FIN = "<!-- proyectos-ia:fin -->"


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


def poner_bloque(archivo: Path, bloque: str) -> None:
    """Escribe (o reemplaza) un bloque marcado dentro de un archivo, sin tocar el resto."""
    archivo.parent.mkdir(parents=True, exist_ok=True)
    actual = archivo.read_text(encoding="utf-8") if archivo.exists() else ""
    nuevo = f"{MARCA_INICIO}\n{bloque.strip()}\n{MARCA_FIN}"
    if MARCA_INICIO in actual and MARCA_FIN in actual:
        antes, resto = actual.split(MARCA_INICIO, 1)
        _, despues = resto.split(MARCA_FIN, 1)
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
def generar_archivos(destino: Path, datos: dict) -> None:
    titulo("Creando la memoria compartida del proyecto")
    for origen in sorted(PLANTILLAS.rglob("*")):
        if origen.is_dir():
            continue
        relativo = origen.relative_to(PLANTILLAS)
        # Los archivos que empiezan por "punto" se guardan como "_punto_xxx"
        # para que no se oculten ni se ignoren dentro de esta herramienta.
        partes = [p.replace("_punto_", ".", 1) if p.startswith("_punto_") else p for p in relativo.parts]
        final = destino.joinpath(*partes)
        final.parent.mkdir(parents=True, exist_ok=True)
        final.write_text(rellenar(origen.read_text(encoding="utf-8"), datos), encoding="utf-8")
        ok(str(final.relative_to(destino)))


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


def crear_repo(destino: Path, datos: dict, visibilidad: str, usar_github: bool) -> None:
    titulo("Git y GitHub")
    ejecutar(["git", "add", "-A"], cwd=destino)
    r = ejecutar(["git", "commit", "-m", f"Inicio del proyecto {datos['NOMBRE']}"], cwd=destino)
    if r.returncode != 0:
        error(r.stderr.strip())
        sys.exit(1)
    ok("Primer commit creado")

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
    indice = base / "PROYECTOS.md"
    if not indice.exists():
        indice.write_text(
            "# Índice de proyectos\n\n"
            "Lista que usan Claude y Codex para encontrar un proyecto cuando dices "
            "\"vamos a <proyecto>\".\n\n"
            "| Proyecto | Carpeta | Repositorio | Descripción | Creado |\n"
            "|---|---|---|---|---|\n",
            encoding="utf-8",
        )
    with indice.open("a", encoding="utf-8") as f:
        f.write(f"| {datos['NOMBRE']} | `{destino}` | {datos['URL']} | {datos['DESCRIPCION']} | {datos['FECHA']} |\n")
    ok(f"Añadido a {indice}")

    if not tocar_global:
        return

    instruccion = rellenar((AQUI / "instruccion_global.md").read_text(encoding="utf-8"), {"INDICE": str(indice)})
    destinos = [Path.home() / ".claude" / "CLAUDE.md", Path.home() / ".codex" / "AGENTS.md"]
    for archivo in destinos:
        poner_bloque(archivo, instruccion)
        ok(f"Instrucción \"vamos a <proyecto>\" en {archivo}")


# ---------------------------------------------------------------------- main
def main() -> None:
    p = argparse.ArgumentParser(description="Crea un proyecto para trabajar con Claude y Codex.")
    p.add_argument("--nombre")
    p.add_argument("--cuenta", help="Usuario u organización de GitHub")
    p.add_argument("--descripcion")
    p.add_argument("--objetivo", help="Qué debe lograr el proyecto (primera versión)")
    p.add_argument("--tecnologias", help="Lenguajes o herramientas previstas")
    p.add_argument("--visibilidad", choices=["private", "public"])
    p.add_argument("--carpeta-base", help="Dónde se crean los proyectos")
    p.add_argument("--sin-github", action="store_true", help="No crear el repositorio remoto")
    p.add_argument("--sin-graphify", action="store_true", help="No configurar Graphify")
    p.add_argument("--sin-global", action="store_true", help="No tocar ~/.claude/CLAUDE.md ni ~/.codex/AGENTS.md")
    p.add_argument("--si", action="store_true", help="No preguntar: usar los datos dados y los valores por defecto")
    a = p.parse_args()

    print("\n  Creador de proyectos Claude + Codex")
    print("  -----------------------------------")
    cfg = leer_config()
    usar_github = not a.sin_github
    estado = comprobar_requisitos(usar_github)

    titulo("Datos del proyecto")
    def dato(valor, pregunta, defecto=None, obligatorio=True):
        if valor is not None:
            return valor
        if a.si:
            return defecto or ""
        return preguntar(pregunta, defecto, obligatorio)

    nombre = dato(a.nombre, "Nombre del proyecto")
    if not nombre:
        error("Falta el nombre (--nombre).")
        sys.exit(1)
    slug = a_slug(nombre)

    if usar_github:
        if a.cuenta:
            cuenta = a.cuenta
        elif a.si:
            cuenta = cfg.get("cuenta") or estado["login"]
        else:
            opciones = cuentas_github(estado["login"])
            previa = cfg.get("cuenta")
            defecto = opciones.index(previa) if previa in opciones else 0
            cuenta = elegir("¿En qué cuenta de GitHub se crea? (o escribe otra)", opciones, defecto)
        repo_nombre = dato(None, "Nombre del repositorio", slug)
    else:
        cuenta, repo_nombre = cfg.get("cuenta", "local"), slug

    descripcion = dato(a.descripcion, "Descripción corta (una línea)")
    objetivo = dato(a.objetivo, "¿Qué debe lograr la primera versión?", "Por definir en la primera sesión", False)
    tecnologias = dato(a.tecnologias, "Tecnologías previstas (opcional)", "Por definir", False)
    if a.visibilidad:
        visibilidad = a.visibilidad
    elif a.si or not usar_github:
        visibilidad = "private"
    else:
        visibilidad = "public" if elegir("Visibilidad del repositorio", ["privado", "público"]) == "público" else "private"

    base_defecto = cfg.get("carpeta_base") or str(Path.home() / "Proyectos")
    base = Path(dato(a.carpeta_base, "Carpeta donde guardas tus proyectos", base_defecto)).expanduser()
    destino = base / slug
    if destino.exists() and any(destino.iterdir()):
        error(f"La carpeta {destino} ya existe y no está vacía.")
        sys.exit(1)

    url = f"https://github.com/{cuenta}/{repo_nombre}" if usar_github else "(solo local)"
    datos = {
        "NOMBRE": nombre,
        "SLUG": slug,
        "DESCRIPCION": descripcion,
        "OBJETIVO": objetivo,
        "TECNOLOGIAS": tecnologias,
        "CUENTA": cuenta,
        "REPO": f"{cuenta}/{repo_nombre}",
        "URL": url,
        "VISIBILIDAD": "privado" if visibilidad == "private" else "público",
        "FECHA": dt.date.today().isoformat(),
    }

    titulo("Resumen")
    for k in ("NOMBRE", "DESCRIPCION", "OBJETIVO", "TECNOLOGIAS", "URL", "VISIBILIDAD"):
        info(f"{k.capitalize():12} {datos[k]}")
    info(f"{'Carpeta':12} {destino}")
    if not a.si and not preguntar_si("¿Todo correcto? ¿Lo creo?"):
        print("  Cancelado.")
        return

    tocar_global = not a.sin_global
    if tocar_global and not a.si and not cfg.get("global_hecho"):
        tocar_global = preguntar_si(
            "¿Añado a ~/.claude/CLAUDE.md y ~/.codex/AGENTS.md la instrucción para que entiendan "
            "\"vamos a <proyecto>\"? (solo se hace una vez)"
        )

    destino.mkdir(parents=True, exist_ok=True)
    generar_archivos(destino, datos)
    ejecutar(["git", "init", "-b", "main"], cwd=destino, mostrar=False)
    if not a.sin_graphify:
        configurar_graphify(destino, estado, a.si)
    crear_repo(destino, datos, visibilidad, usar_github)
    registrar(base, datos, destino, tocar_global)

    cfg.update({"cuenta": cuenta, "carpeta_base": str(base)})
    if tocar_global:
        cfg["global_hecho"] = True
    guardar_config(cfg)

    titulo("Listo")
    info(f"Proyecto en: {destino}")
    if usar_github:
        info(f"GitHub:      {url}")
    print(
        "\n  Para empezar a trabajar:\n"
        f"    1. Abre Claude o Codex en la carpeta {destino}\n"
        f"       (o en {base} y di: \"vamos a {nombre}\").\n"
        "    2. En la primera sesión pide: \"lee el proyecto y construye el grafo\"\n"
        "       (Claude: /graphify .   Codex: $graphify .).\n"
        "    3. Al terminar di: \"cerramos sesión\" y el agente guarda el estado y sube a GitHub.\n"
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n  Cancelado.")
