"""Carga de juegos de Windows: carpetas sin ejecutable visibles con su motivo."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import gestor_core as core


class SinEjecutableTest(TestCase):
    def setUp(self):
        temporal = TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.origen = Path(temporal.name)
        for ruta in ("goldenaxed/GAXD.exe", "Contra/a.exe", "Contra/b.exe", "Toki-TiNYiSO/toki.iso",
                     "Ghosts/ghosts.part1.rar", "Ghosts/ghosts.r00", "Strider/data.pak", "Strider/readme.txt",
                     "Pack.zip", "notas.txt", "Juego suelto.exe"):
            archivo = self.origen / ruta
            archivo.parent.mkdir(parents=True, exist_ok=True)
            archivo.write_bytes(b"x")
        (self.origen / "Vacia").mkdir()

    def test_lista_lo_que_no_es_juego_con_su_motivo(self):
        sistema = core.Sistema("windows", "Windows", self.origen, frozenset({".lnk"}))
        juegos = core.buscar_juegos(self.origen, sistema)
        self.assertEqual({nombre for nombre, _ in juegos}, {"goldenaxed", "Contra", "Juego suelto"})
        extras = {nombre: (corto, largo) for nombre, _, corto, largo in core.sin_ejecutable_windows(self.origen, juegos)}
        self.assertEqual(set(extras), {"Toki-TiNYiSO", "Ghosts", "Strider", "Vacia", "Pack"})
        self.assertEqual(extras["Toki-TiNYiSO"][0], "imagen de disco (.iso)")
        self.assertIn("comprimido", extras["Ghosts"][0])
        self.assertIn(".r00", extras["Ghosts"][0])
        self.assertEqual(extras["Strider"][0], "sin .exe")
        self.assertIn(".pak", extras["Strider"][1])
        self.assertEqual(extras["Vacia"][0], "carpeta vacía")
        self.assertEqual(extras["Pack"][0], "archivo comprimido (.zip)")
