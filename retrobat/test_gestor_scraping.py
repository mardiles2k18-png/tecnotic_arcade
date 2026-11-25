from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
import xml.etree.ElementTree as ET

from gestor_core import Sistema
from gestor_duplicados import Entrada, marca_archivo
from gestor_scraping import aplicar_exportacion


class ScrapingTest(TestCase):
    def test_completa_catalogo_y_conserva_personalizaciones(self):
        with TemporaryDirectory() as carpeta:
            raiz = Path(carpeta).resolve()
            roms = raiz / "roms" / "snes"
            roms.mkdir(parents=True)
            juego = roms / "Demo.sfc"
            juego.touch()
            sistema = Sistema("snes", "Super Nintendo", roms, frozenset({".sfc"}))
            entrada = Entrada(sistema, juego, None, marca_archivo(juego))
            catalogo = roms / "gamelist.xml"
            catalogo.write_text("<gameList><game><path>./Demo.sfc</path>"
                                "<name>Mi juego</name><favorite>true</favorite></game></gameList>")
            temporal = raiz / "exportar"
            temporal.mkdir()
            (temporal / "logo.png").write_bytes(b"logo")
            (temporal / "gamelist.xml").write_text(
                "<gameList><game><path>./Demo.sfc</path><name>Otro</name>"
                "<marquee>./logo.png</marquee><video>../fuera.mp4</video></game></gameList>")
            (raiz / "fuera.mp4").write_bytes(b"no importar")
            self.assertEqual(aplicar_exportacion(raiz, [entrada], temporal), 1)
            nodo = ET.parse(catalogo).find("game")
            self.assertEqual(nodo.findtext("name"), "Mi juego")
            self.assertEqual(nodo.findtext("favorite"), "true")
            self.assertEqual((roms / nodo.findtext("marquee")).read_bytes(), b"logo")
            self.assertIsNone(nodo.find("video"))
            self.assertEqual(aplicar_exportacion(raiz, [entrada], temporal), 0)
