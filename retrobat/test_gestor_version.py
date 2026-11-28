import unittest

from gestor_version import NOMBRE, NOMBRE_PORTABLE, TITULO, VERSION


class VersionGestorTest(unittest.TestCase):
    def test_identidad_version_43(self):
        self.assertEqual((NOMBRE, VERSION), ("Gestor Arcade Tecnoticis", 43))
        self.assertEqual(TITULO, "Gestor Arcade Tecnoticis 43")
        self.assertEqual(NOMBRE_PORTABLE, "Gestor-Arcade-Tecnoticis-43")
