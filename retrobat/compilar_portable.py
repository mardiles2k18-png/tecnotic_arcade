"""Compila el ejecutable portable de Windows con Python 3.13."""

import argparse
import hashlib
import os
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.request import urlopen


DEPENDENCIAS = {"PyInstaller": "6.22.3", "Pillow": "13.0.0", "truststore": "0.10.5"}


def dependencias_faltantes():
    for paquete, requerida in DEPENDENCIAS.items():
        try:
            if version(paquete) == requerida:
                continue
        except PackageNotFoundError:
            pass
        yield f"{paquete}=={requerida}"


def preparar_7zip(trabajo):
    herramientas = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "7-Zip" / "7z.exe"
    if not herramientas.is_file():
        raise FileNotFoundError("Instala 7-Zip en Windows para compilar el portable.")
    url = "https://github.com/ip7z/7zip/releases/download/26.06/7z2606-x64.exe"
    esperado = "9b697f65ecc2d9b0152f5ee96d72dde522a7827690349d9307935dacf40f42ec"
    with urlopen(url, timeout=30) as respuesta:
        datos = respuesta.read(2_000_000)
    if hashlib.sha256(datos).hexdigest() != esperado:
        raise ValueError("El paquete oficial de 7-Zip no coincide con su SHA-256.")
    paquete = trabajo / "7zip-oficial.exe"
    paquete.write_bytes(datos)
    destino = trabajo / "7zip"
    archivos = ("7z.exe", "7z.dll", "License.txt", "readme.txt")
    subprocess.run([str(herramientas), "x", "-y", "-o" + str(destino), str(paquete), *archivos], check=True)
    if not all((destino / archivo).is_file() for archivo in archivos):
        raise ValueError("Faltan componentes de 7-Zip en el portable.")
    return destino


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, default=Path("dist"))
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("Compila el ejecutable en Windows.")
    faltantes = list(dependencias_faltantes())
    if faltantes:
        subprocess.run([sys.executable, "-m", "pip", "install", *faltantes], check=True)

    from PIL import Image, ImageOps

    fuente = Path(__file__).resolve().parent
    repo = fuente.parent
    with tempfile.TemporaryDirectory(prefix="tecnotics-build-") as temporal:
        trabajo = Path(temporal)
        siete_zip = preparar_7zip(trabajo)
        imagen = Image.open(repo / "logo" / "tecnotics-vertical.png").convert("RGBA")
        imagen = ImageOps.contain(imagen, (244, 244), Image.Resampling.LANCZOS)
        lienzo = Image.new("RGBA", (256, 256))
        lienzo.alpha_composite(imagen, ((256 - imagen.width) // 2, (256 - imagen.height) // 2))
        icono = trabajo / "tecnotics.ico"
        lienzo.save(icono, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        subprocess.run(
            [
                sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile", "--windowed",
                "--name", "Tecnotics-Arcade-Portable-Preview-23", "--icon", str(icono),
                "--distpath", str(args.salida.resolve()), "--specpath", str(trabajo),
                "--workpath", str(trabajo / "build"),
                "--add-data", f"{siete_zip}:7zip",
                "--add-data", f"{repo / 'logo'}:logo",
                "--add-data", f"{repo / 'themes'}:themes",
                "--add-data", f"{repo / 'arranque' / 'splash'}:arranque/splash",
                str(fuente / "gestor-retrobat.pyw"),
            ],
            check=True,
        )


if __name__ == "__main__":
    main()
