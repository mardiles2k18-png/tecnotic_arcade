"""Actualizaciones del portable desde las publicaciones oficiales."""

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.request import Request, urlopen

from gestor_teknoparrot_instalacion import contexto_tls
from gestor_version import NOMBRE, VERSION

API = "https://api.github.com/repos/mardiles2k18-png/tecnotic_arcade"
TAG = re.compile(r"retrobat-manager-preview-([0-9]{1,9})-[0-9a-f]{7}")
MAX_EXE = 512 * 1024 * 1024


def seleccionar(publicaciones, instalada):
    candidatas = []
    for release in publicaciones:
        tag = TAG.fullmatch(release.get("tag_name", ""))
        if release.get("draft") or not tag or int(tag[1]) <= instalada:
            continue
        version = int(tag[1])
        nombre = f"{NOMBRE.replace(' ', '-')}-{version}.exe"
        assets = {a["name"]: a["id"] for a in release.get("assets", ())
                  if isinstance(a.get("id"), int) and a["id"] > 0}
        if nombre in assets and nombre + ".sha256.txt" in assets:
            candidatas.append((version, assets[nombre], assets[nombre + ".sha256.txt"]))
    return max(candidatas, default=None)


def abrir(ruta, aceptar):
    cabeceras = {"Accept": aceptar, "User-Agent": f"Gestor-Arcade-Tecnoticis/{VERSION}"}
    peticion = Request(API + ruta, headers=cabeceras)
    return urlopen(peticion, timeout=15, context=contexto_tls())


def consultar():
    with abrir("/releases?per_page=100", "application/vnd.github+json") as respuesta:
        return seleccionar(json.loads(respuesta.read(8 * 1024 * 1024)), VERSION)


def descargar(candidata, directorio):
    version, exe, suma = candidata
    nombre = f"{NOMBRE.replace(' ', '-')}-{version}.exe"
    with abrir(f"/releases/assets/{suma}", "application/octet-stream") as respuesta:
        registro = respuesta.read(1024).decode("ascii").strip()
    partes = registro.split()
    if len(partes) != 2 or partes[1] != nombre or not re.fullmatch(r"[0-9a-fA-F]{64}", partes[0]):
        raise ValueError("La publicación no contiene una suma SHA-256 válida.")
    with tempfile.NamedTemporaryFile(dir=directorio, prefix=".gestor-", suffix=".exe", delete=False) as salida:
        temporal = Path(salida.name)
        try:
            digest = hashlib.sha256()
            total = 0
            with abrir(f"/releases/assets/{exe}", "application/octet-stream") as respuesta:
                while bloque := respuesta.read(1024 * 1024):
                    total += len(bloque)
                    if total > MAX_EXE:
                        raise ValueError("El portable supera el tamaño máximo permitido.")
                    digest.update(bloque)
                    salida.write(bloque)
            if digest.hexdigest() != partes[0].lower():
                raise ValueError("La descarga no coincide con el SHA-256 de la publicación.")
        except BaseException:
            salida.close()
            temporal.unlink(missing_ok=True)
            raise
    return temporal


_REEMPLAZO = r"""
$ErrorActionPreference = 'Stop'
$actual = $env:TECNOTICS_ACTUAL
$nuevo = $env:TECNOTICS_NUEVO
$respaldo = "$actual.$([Guid]::NewGuid().ToString('N')).anterior"
try {
    for ($i = 0; $i -lt 120; $i++) {
        try {
            [IO.File]::Replace($nuevo, $actual, $respaldo)
            break
        } catch [IO.IOException] {
            if ($i -eq 119) { throw }
            Start-Sleep -Milliseconds 500
        }
    }
    Remove-Item Env:TECNOTICS_ACTUAL,Env:TECNOTICS_NUEVO
    $env:PYINSTALLER_RESET_ENVIRONMENT = '1'
    Start-Process -FilePath $actual -WorkingDirectory (Split-Path -LiteralPath $actual)
} catch {
    if ([IO.File]::Exists($respaldo)) {
        [IO.File]::Replace($respaldo, $actual, $null)
    }
    Add-Type -AssemblyName System.Windows.Forms
    [void][Windows.Forms.MessageBox]::Show(
        $_.Exception.Message, 'No se pudo actualizar Gestor Arcade Tecnoticis')
} finally {
    if ([IO.File]::Exists($nuevo)) { [IO.File]::Delete($nuevo) }
}
"""


def aplicar(actual, nuevo):
    env = dict(os.environ, TECNOTICS_ACTUAL=str(actual), TECNOTICS_NUEVO=str(nuevo))
    comando = base64.b64encode(_REEMPLAZO.encode("utf-16le")).decode("ascii")
    powershell = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    subprocess.Popen([str(powershell), "-NoProfile", "-NonInteractive", "-EncodedCommand", comando],
                     env=env, creationflags=subprocess.CREATE_NO_WINDOW)
