"""Compila el ejecutable portable de Windows con Python 3.13."""

import argparse
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import subprocess
import sys
import tempfile


DEPENDENCIAS = {"PyInstaller": "6.22.3", "Pillow": "13.0.0"}


def dependencias_faltantes():
    for paquete, requerida in DEPENDENCIAS.items():
        try:
            if version(paquete) == requerida:
                continue
        except PackageNotFoundError:
            pass
        yield f"{paquete}=={requerida}"


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
        imagen = Image.open(repo / "logo" / "tecnotics-vertical.png").convert("RGBA")
        imagen = ImageOps.contain(imagen, (244, 244), Image.Resampling.LANCZOS)
        lienzo = Image.new("RGBA", (256, 256))
        lienzo.alpha_composite(imagen, ((256 - imagen.width) // 2, (256 - imagen.height) // 2))
        icono = trabajo / "tecnotics.ico"
        lienzo.save(icono, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        subprocess.run(
            [
                sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile", "--windowed",
                "--name", "Tecnotics-Arcade-Portable-Preview-9", "--icon", str(icono),
                "--distpath", str(args.salida.resolve()), "--specpath", str(trabajo),
                "--workpath", str(trabajo / "build"),
                "--add-data", f"{repo / 'logo'}:logo",
                "--add-data", f"{repo / 'themes'}:themes",
                "--add-data", f"{repo / 'arranque' / 'splash'}:arranque/splash",
                str(fuente / "gestor-retrobat.pyw"),
            ],
            check=True,
        )


if __name__ == "__main__":
    main()
