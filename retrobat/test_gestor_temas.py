"""Pruebas del intercambio de temas con una instalación temporal de RetroBat."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from gestor_temas import eliminar_tema, exportar_tema, importar_tema, listar_temas


class TemasTest(unittest.TestCase):
    def setUp(self):
        temporal = TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.raiz = Path(temporal.name) / "RetroBat"
        self.raiz.mkdir()
        (self.raiz / "retrobat.exe").touch()
        self.config = self.raiz / "emulationstation" / ".emulationstation"
        self.temas = self.config / "themes"
        self.temas.mkdir(parents=True)
        self.zip = self.raiz.parent / "tema.zip"

    def crear_tema(self, nombre):
        tema = self.temas / nombre
        (tema / "arte").mkdir(parents=True)
        (tema / "theme.xml").write_bytes(b"<theme />")
        (tema / "arte" / "logo.svg").write_bytes(b"<svg />")
        return tema

    def activar(self, nombre):
        ajustes = self.config / "es_settings.cfg"
        ajustes.write_text(f'<config><string name="ThemeSet" value="{nombre}" /></config>', encoding="utf-8")

    def crear_zip(self, archivos):
        with ZipFile(self.zip, "w") as archivo:
            for ruta, contenido in archivos.items():
                archivo.writestr(ruta, contenido)

    def test_lista_temas_y_reconoce_el_activo(self):
        self.crear_tema("AluBrush")
        self.crear_tema("Tema Tecnotics")
        (self.temas / "carpeta sin tema").mkdir()
        self.activar("AluBrush")

        self.assertEqual({tema.nombre: tema.activo for tema in listar_temas(self.raiz)},
                         {"AluBrush": True, "Tema Tecnotics": False})

    def test_exporta_e_importa_como_copia_con_todos_los_recursos(self):
        original = self.crear_tema("AluBrush")
        self.assertEqual(exportar_tema(self.raiz, "AluBrush", self.zip), self.zip)
        with ZipFile(self.zip) as archivo:
            self.assertEqual(archivo.read("AluBrush/theme.xml"), b"<theme />")
            self.assertEqual(archivo.read("AluBrush/arte/logo.svg"), b"<svg />")

        destino = importar_tema(self.raiz, self.zip, "AluBrush Tecnotics")
        self.assertEqual(destino, self.temas / "AluBrush Tecnotics")
        (destino / "arte" / "logo.svg").write_bytes(b"<svg>modificado</svg>")
        self.assertEqual((original / "arte" / "logo.svg").read_bytes(), b"<svg />")

    def test_importa_zip_plano_y_rechaza_colision_sin_sobrescribir(self):
        self.crear_zip({"theme.xml": b"<theme />", "arte/logo.svg": b"<svg />"})
        original = self.crear_tema("AluBrush")
        (original / "theme.xml").write_bytes(b"<theme><!-- original --></theme>")

        with self.assertRaises(FileExistsError):
            importar_tema(self.raiz, self.zip, "AluBrush")
        self.assertEqual((original / "theme.xml").read_bytes(), b"<theme><!-- original --></theme>")
        self.assertEqual(importar_tema(self.raiz, self.zip, "Tecnotics"), self.temas / "Tecnotics")

    def test_rechaza_rutas_invalidas_sin_instalar_un_tema_incompleto(self):
        for ruta in ("../fuera.xml", "/fuera.xml", "C:/fuera.xml", "arte/../fuera.xml", "arte/CON"):
            with self.subTest(ruta=ruta):
                self.crear_zip({"theme.xml": b"<theme />", ruta: b"dato"})
                with self.assertRaises(ValueError):
                    importar_tema(self.raiz, self.zip, "Tecnotics")
                self.assertEqual(list(self.temas.iterdir()), [])
                self.assertFalse((self.config / "fuera.xml").exists())

    def test_rechaza_archivo_sin_tema_y_rutas_que_colisionan_en_windows(self):
        casos = (
            {"arte/logo.svg": b"<svg />"},
            {"theme.xml": b"<theme />", "arte/logo.svg": b"uno", "arte/LOGO.SVG": b"dos"},
        )
        for archivos in casos:
            with self.subTest(archivos=archivos.keys()):
                self.crear_zip(archivos)
                with self.assertRaises(ValueError):
                    importar_tema(self.raiz, self.zip)
                self.assertEqual(list(self.temas.iterdir()), [])

    def test_eliminar_mueve_el_tema_a_respaldo_y_protege_el_activo(self):
        activo = self.crear_tema("AluBrush")
        otro = self.crear_tema("Tecnotics")
        self.activar("AluBrush")

        with self.assertRaises(ValueError):
            eliminar_tema(self.raiz, "AluBrush")
        self.assertTrue(activo.is_dir())

        respaldo = eliminar_tema(self.raiz, "Tecnotics")
        self.assertFalse(otro.exists())
        self.assertTrue(respaldo.is_relative_to(self.raiz / "user" / "tecnotics-gestor" / "temas-retirados"))
        self.assertEqual((respaldo / "arte" / "logo.svg").read_bytes(), b"<svg />")
        self.assertEqual([tema.nombre for tema in listar_temas(self.raiz)], ["AluBrush"])
