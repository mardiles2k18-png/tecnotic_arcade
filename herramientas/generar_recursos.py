#!/usr/bin/env python3
"""Genera las imágenes y el vídeo de arranque de Tecnotics Arcade.

Uso (desde la raíz del repositorio):
    python3 herramientas/generar_recursos.py

Necesita Pillow y ffmpeg. Crea:
    arranque/boot-logo.png                   logo fijo del primer instante de arranque
    arranque/splash/tecnotics-arcade.mp4     vídeo de inicio (va en /userdata/splash)
    themes/es-theme-tecnotics/art/*.png      fondos y piezas del tema
"""
import math
import os
import shutil
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFilter, ImageFont

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_V = os.path.join(RAIZ, "logo", "tecnotics-vertical.png")
LOGO_H = os.path.join(RAIZ, "logo", "tecnotics-horizontal.png")
FUENTE_TITULO = os.path.join(RAIZ, "themes", "es-theme-tecnotics", "art", "fonts", "Anton-Regular.ttf")
ART = os.path.join(RAIZ, "themes", "es-theme-tecnotics", "art")

W, H = 1920, 1080
FONDO = (8, 11, 16)          # negro azulado
CIAN = (110, 198, 216)       # color del logo
NARANJA = (241, 142, 25)     # color del logo

# Composición común: logo centrado y "ARCADE" debajo.
LOGO_ESCALA = 0.9
LOGO_CENTRO_Y = 430
ARCADE_Y = 800
ARCADE_TAM = 120
ARCADE_ESPACIADO = 34


def logo_vertical(escala=LOGO_ESCALA):
    im = Image.open(LOGO_V).convert("RGBA")
    return im.resize((round(im.width * escala), round(im.height * escala)), Image.LANCZOS)


def texto_espaciado(texto, fuente, color, espaciado):
    """Devuelve una imagen RGBA con el texto y espacio extra entre letras."""
    anchos = [fuente.getbbox(c)[2] for c in texto]
    total = sum(anchos) + espaciado * (len(texto) - 1)
    asc, desc = fuente.getmetrics()
    im = Image.new("RGBA", (total + 4, asc + desc + 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 2
    for c, a in zip(texto, anchos):
        d.text((x, 2), c, font=fuente, fill=color)
        x += a + espaciado
    return im.crop(im.getbbox())


def con_brillo(capa, color, radio, fuerza):
    """Añade un halo suave del color dado detrás de una capa RGBA."""
    alfa = capa.split()[3]
    halo = Image.new("RGBA", capa.size, color + (0,))
    halo.putalpha(alfa.point(lambda v: int(v * fuerza)))
    margen = radio * 3
    lienzo = Image.new("RGBA", (capa.width + margen * 2, capa.height + margen * 2), (0, 0, 0, 0))
    lienzo.alpha_composite(halo, (margen, margen))
    lienzo = lienzo.filter(ImageFilter.GaussianBlur(radio))
    lienzo.alpha_composite(capa, (margen, margen))
    return lienzo, margen


def fondo_base():
    """Fondo oscuro con un degradado radial muy suave en el centro."""
    im = Image.new("RGB", (W, H), FONDO)
    luz = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(luz)
    for i in range(60, 0, -1):
        r = i * 16
        d.ellipse((W / 2 - r * 1.6, LOGO_CENTRO_Y - r, W / 2 + r * 1.6, LOGO_CENTRO_Y + r), fill=int((60 - i) * 0.55))
    luz = luz.filter(ImageFilter.GaussianBlur(60))
    tinte = Image.new("RGB", (W, H), (20, 40, 52))
    return Image.composite(tinte, im, luz)


def pegar_centrado(base, capa, cx, cy, opacidad=1.0):
    if opacidad < 1.0:
        capa = capa.copy()
        capa.putalpha(capa.split()[3].point(lambda v: int(v * opacidad)))
    base.alpha_composite(capa, (round(cx - capa.width / 2), round(cy - capa.height / 2)))


def preparar_capas():
    logo = logo_vertical()
    logo_halo, m_logo = con_brillo(logo, CIAN, 18, 0.35)
    fuente = ImageFont.truetype(FUENTE_TITULO, ARCADE_TAM)
    arcade = texto_espaciado("ARCADE", fuente, NARANJA, ARCADE_ESPACIADO)
    arcade_halo, _ = con_brillo(arcade, NARANJA, 14, 0.45)
    return logo_halo, arcade_halo


def boot_logo(fondo, logo_halo):
    im = fondo.convert("RGBA")
    pegar_centrado(im, logo_halo, W / 2, LOGO_CENTRO_Y)
    destino = os.path.join(RAIZ, "arranque", "boot-logo.png")
    im.convert("RGB").save(destino, optimize=True)
    return destino


def suavizar(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def fotograma(fondo, logo_halo, arcade_halo, t):
    """t en segundos. Duración total 6 s."""
    im = fondo.convert("RGBA")
    pegar_centrado(im, logo_halo, W / 2, LOGO_CENTRO_Y)

    # "ARCADE" sube y aparece entre 0,4 s y 1,4 s
    p = suavizar((t - 0.4) / 1.0)
    if p > 0:
        pegar_centrado(im, arcade_halo, W / 2, ARCADE_Y + (1 - p) * 40, opacidad=p)

    # Barrido de luz sobre el logo entre 1,8 s y 3,0 s
    q = (t - 1.8) / 1.2
    if 0 < q < 1:
        barrido = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(barrido)
        x = -300 + q * (W + 600)
        d.polygon([(x, 0), (x + 120, 0), (x - 180, H), (x - 300, H)], fill=(255, 255, 255, 38))
        barrido = barrido.filter(ImageFilter.GaussianBlur(40))
        im.alpha_composite(barrido)

    # Línea cian que se dibuja bajo "ARCADE"
    r = suavizar((t - 1.0) / 0.8)
    if r > 0:
        d = ImageDraw.Draw(im)
        mitad = 260 * r
        y = ARCADE_Y + 95
        d.rectangle((W / 2 - mitad, y, W / 2 + mitad, y + 5), fill=CIAN + (255,))

    # Fundido a negro al final (5,3 s a 6 s)
    f = suavizar((t - 5.3) / 0.7)
    if f > 0:
        negro = Image.new("RGBA", (W, H), (0, 0, 0, int(255 * f)))
        im.alpha_composite(negro)
    return im.convert("RGB")


def video(fondo, logo_halo, arcade_halo):
    if not shutil.which("ffmpeg"):
        print("ffmpeg no está instalado: no se genera el vídeo")
        return None
    fps, dur = 30, 6.0
    destino = os.path.join(RAIZ, "arranque", "splash", "tecnotics-arcade.mp4")
    with tempfile.TemporaryDirectory() as tmp:
        for n in range(int(fps * dur)):
            fotograma(fondo, logo_halo, arcade_halo, n / fps).save(os.path.join(tmp, f"f{n:04d}.png"))
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", os.path.join(tmp, "f%04d.png"),
            "-c:v", "libx264", "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p",
            "-crf", "18", "-preset", "slow", "-movflags", "+faststart", destino,
        ], check=True)
    return destino


def arte_tema(fondo, logo_halo, arcade_halo):
    os.makedirs(ART, exist_ok=True)
    # Fondo general del tema: oscuro con rejilla de circuito muy tenue
    bg = Image.new("RGB", (W, H), FONDO)
    d = ImageDraw.Draw(bg)
    for x in range(0, W, 48):
        d.line((x, 0, x, H), fill=(14, 20, 27))
    for y in range(0, H, 48):
        d.line((0, y, W, y), fill=(14, 20, 27))
    luz = Image.new("L", (W, H), 0)
    ImageDraw.Draw(luz).ellipse((W * 0.1, -H * 0.3, W * 0.9, H * 0.8), fill=90)
    luz = luz.filter(ImageFilter.GaussianBlur(160))
    bg = Image.composite(Image.new("RGB", (W, H), (18, 36, 46)), bg, luz)
    bg.save(os.path.join(ART, "bg.png"), optimize=True)

    # Pantalla de carga de EmulationStation (mismo diseño que el arranque)
    carga = fondo.convert("RGBA")
    pegar_centrado(carga, logo_halo, W / 2, LOGO_CENTRO_Y)
    pegar_centrado(carga, arcade_halo, W / 2, ARCADE_Y)
    carga.convert("RGB").save(os.path.join(ART, "splash.png"), optimize=True)

    # Logos para la cabecera
    shutil.copy(LOGO_H, os.path.join(ART, "logo-horizontal.png"))
    shutil.copy(LOGO_V, os.path.join(ART, "logo-vertical.png"))

    # Piezas lisas para colorear desde el tema
    Image.new("RGBA", (8, 8), (255, 255, 255, 255)).save(os.path.join(ART, "white.png"))
    # Degradado vertical (opaco arriba, transparente abajo) para barras
    grad = Image.new("RGBA", (8, 256))
    for y in range(256):
        for x in range(8):
            grad.putpixel((x, y), (255, 255, 255, 255 - y))
    grad.save(os.path.join(ART, "gradient.png"))


def main():
    fondo = fondo_base()
    logo_halo, arcade_halo = preparar_capas()
    print("boot-logo:", boot_logo(fondo, logo_halo))
    arte_tema(fondo, logo_halo, arcade_halo)
    print("arte del tema:", ART)
    v = video(fondo, logo_halo, arcade_halo)
    if v:
        print("vídeo:", v)


if __name__ == "__main__":
    main()
