import unittest

from gestor_version import NOMBRE, NOMBRE_PORTABLE, TITULO, VERSION


class VersionGestorTest(unittest.TestCase):
    def test_identidad_version_42(self):
        self.assertEqual((NOMBRE, VERSION), ("Gestor Arcade Tecnoticis", 42))
        self.assertEqual(TITULO, "Gestor Arcade Tecnoticis 42")
        self.assertEqual(NOMBRE_PORTABLE, "Gestor-Arcade-Tecnoticis-42")
