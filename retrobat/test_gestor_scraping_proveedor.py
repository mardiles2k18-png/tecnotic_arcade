import gzip
import io
from unittest import TestCase
from unittest.mock import patch

from gestor_scraping_proveedor import _consulta_arcade, buscar, categorias_disponibles


class ProveedorScrapingTest(TestCase):
    def test_arcade_solo_incluye_categorias_elegidas(self):
        ficha = {
            "title": "Mi Arcade",
            "history": "Descripción.\n\n- TIPS AND TRICKS -\nConsejo.\n\n- STAFF -\nOtro.",
            "history_copyright_short": "Autor",
            "url_image_flyer": "https://adb.arcadeitalia.net/?mame=demo&type=flyer",
            "url_image_marquee": "https://otro.example/logo.png",
            "url_video_shortplay": "https://adb.arcadeitalia.net/video",
        }
        with patch("gestor_scraping_proveedor._consulta_arcade", return_value=ficha) as consulta:
            textos, medios = buscar("fbneo", "DEMO", "Nombre en biblioteca", {"cover", "cheats", "logo"})
        consulta.assert_called_once_with("demo")
        self.assertEqual(set(textos), {"trucos"})
        self.assertIn("Consejo.", textos["trucos"])
        self.assertIn("Autor", textos["trucos"])
        self.assertNotIn("Otro.", textos["trucos"])
        self.assertEqual(medios, {"thumbnail": ficha["url_image_flyer"]})

    def test_libretro_respeta_region_y_no_promete_video(self):
        self.assertEqual(categorias_disponibles("snes"), {"cover"})
        textos, medios = buscar("snes", "Demo (USA)", "Demo", {"cover", "video"})
        self.assertEqual(textos, {})
        self.assertTrue(medios["thumbnail"].endswith("/Named_Boxarts/Demo%20%28USA%29.png"))

    def test_sistema_sin_proveedor(self):
        self.assertEqual(buscar("windows", "Demo", "Demo", {"info", "video"}), ({}, {}))

    def test_api_acepta_respuesta_gzip(self):
        class Respuesta(io.BytesIO):
            def geturl(self):
                return "https://adb.arcadeitalia.net/service_scraper.php"

        datos = gzip.compress(b'{"result": [{"game_name": "mslug", "title": "Metal Slug"}]}')
        with patch("gestor_scraping_proveedor.urlopen", return_value=Respuesta(datos)):
            self.assertEqual(_consulta_arcade("mslug")["title"], "Metal Slug")