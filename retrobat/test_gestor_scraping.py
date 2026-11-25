from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import xml.etree.ElementTree as ET

from gestor_core import Sistema
from gestor_duplicados import Entrada, marca_archivo
from gestor_scraping import aplicar_exportacion, buscar_medios


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

    def test_solo_descarga_los_tipos_elegidos_y_reporta_sin_coincidencia(self):
        with TemporaryDirectory() as carpeta:
            raiz = Path(carpeta).resolve()
            roms = raiz / "roms" / "mame"
            roms.mkdir(parents=True)
            sistema = Sistema("mame", "MAME", roms, frozenset({".zip"}))
            entradas = []
            for nombre in ("sf2", "sinmatch"):
                ruta = roms / (nombre + ".zip")
                ruta.touch()
                entradas.append(Entrada(sistema, ruta, None, marca_archivo(ruta)))
            def descargar(_url, _etiqueta, destino):
                destino = destino.with_suffix(".png")
                destino.write_bytes(b"logo")
                return destino
            with patch("gestor_scraping.buscar", side_effect=[
                ({"name": "Street Fighter II"}, {"marquee": "https://ejemplo/logo.png",
                                                "video": "https://ejemplo/demo.mp4"}),
                ({}, {}),
            ]) as consulta, patch("gestor_scraping.descargar_medio", side_effect=descargar) as medio:
                resultado = buscar_medios(raiz, entradas, {"logo"})
                self.assertEqual(resultado["actualizados"], 1)
                self.assertEqual(resultado["sin_resultado"], 1)
                self.assertEqual(consulta.call_count, 2)
                medio.assert_called_once()
            nodo = ET.parse(roms / "gamelist.xml").find("game")
            self.assertIsNone(nodo.find("name"))
            self.assertIsNone(nodo.find("video"))
            self.assertIsNotNone(nodo.find("marquee"))