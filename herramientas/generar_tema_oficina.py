#!/usr/bin/env python3
"""Genera las imágenes del tema discreto "es-theme-oficina".

Uso (desde la raíz del repositorio):
    python3 herramientas/generar_tema_oficina.py
"""
import os

from PIL import Image, ImageDraw, ImageFont

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(RAIZ, "themes", "es-theme-oficina", "art")
FUENTE = os.path.join(ART, "fonts", "IBMPlexSans-SemiBold.ttf")
FUENTE_REG = os.path.join(ART, "fonts", "IBMPlexSans-Regular.ttf")

W, H = 1920, 1080
FONDO = (243, 244, 246)
AZUL = (43, 108, 176)
GRIS = (107, 114, 128)
BORDE = (217, 221, 227)


def icono_app(tam):
    """Icono genérico de "gestor de documentos": hoja con líneas sobre cuadrado azul."""
    im = Image.new("RGBA", (tam, tam), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = tam // 6
    d.rounded_rectangle((0, 0, tam - 1, tam - 1), radius=r, fill=AZUL + (255,))
    m = tam * 0.25
    d.rectangle((m, tam * 0.18, tam - m, tam * 0.82), fill=(255, 255, 255, 255))
    for i in range(4):
        y = tam * (0.32 + i * 0.12)
        d.rectangle((m + tam * 0.08, y, tam - m - tam * (0.08 if i < 3 else 0.2), y + tam * 0.04), fill=AZUL + (255,))
    return im


def icono_carpeta(tam):
    im = Image.new("RGBA", (tam, int(tam * 0.8)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    h = im.height
    d.rounded_rectangle((0, 0, tam * 0.45, h * 0.3), radius=tam // 12, fill=(230, 185, 80, 255))
    d.rounded_rectangle((0, h * 0.15, tam - 1, h - 1), radius=tam // 12, fill=(245, 200, 90, 255))
    return im


def main():
    os.makedirs(ART, exist_ok=True)

    Image.new("RGB", (W, H), FONDO).save(os.path.join(ART, "bg.png"))
    Image.new("RGBA", (8, 8), (255, 255, 255, 255)).save(os.path.join(ART, "white.png"))
    icono_app(256).save(os.path.join(ART, "icono-app.png"))
    icono_carpeta(256).save(os.path.join(ART, "carpeta.png"))

    # Pantalla de carga: icono + "Cargando espacio de trabajo..."
    carga = Image.new("RGBA", (W, H), FONDO + (255,))
    ico = icono_app(160)
    carga.alpha_composite(ico, ((W - 160) // 2, 380))
    d = ImageDraw.Draw(carga)
    f1 = ImageFont.truetype(FUENTE, 44)
    f2 = ImageFont.truetype(FUENTE_REG, 28)
    t1, t2 = "Gestor de Documentos", "Cargando espacio de trabajo..."
    d.text(((W - d.textlength(t1, font=f1)) / 2, 580), t1, font=f1, fill=(31, 41, 51))
    d.text(((W - d.textlength(t2, font=f2)) / 2, 645), t2, font=f2, fill=GRIS)
    carga.convert("RGB").save(os.path.join(ART, "splash.png"), optimize=True)
    print("Imágenes generadas en", ART)


if __name__ == "__main__":
    main()
