import unittest

from gestor_version import NOMBRE, NOMBRE_PORTABLE, TITULO, VERSION


class VersionGestorTest(unittest.TestCase):
    def test_identidad_version_44(self):
        self.assertEqual((NOMBRE, VERSION), ("Gestor Arcade Tecnoticis", 44))
        self.assertEqual(TITULO, "Gestor Arcade Tecnoticis 44")
        self.assertEqual(NOMBRE_PORTABLE, "Gestor-Arcade-Tecnoticis-44")
