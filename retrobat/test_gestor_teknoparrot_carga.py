"""TeknoParrot: reconocer juegos por el nombre de la carpeta y elegir su ejecutable sin preguntar."""
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import gestor_teknoparrot as tp


def perfil(id_, titulo, esperado=(), secundario=()):
    return tp.Perfil(Path(f"/perfiles/{id_}.xml"), titulo, frozenset(esperado), frozenset(secundario), False)


PERFILES = (
    perfil("Daytona3", "Daytona Championship USA"),
    perfil("Daytona3NSE", "Daytona Championship USA NSE"),
    perfil("DOA5", "Dead or Alive 5 Ultimate: Arcade"),
    perfil("DOA6", "Dead or Alive 6", {"muscle_apm3.exe"}),
    perfil("GHA", "Guitar Hero Arcade"),
    perfil("GoldenGun", "Golden Gun"),
    perfil("GTIClub3", "GTI Club Supermini Festa"),
    perfil("GGXXACPR", "Guilty Gear XX Accent Core Plus R"),
    perfil("GGXrdSIGN", "Guilty Gear Xrd -SIGN-", {"guiltygearxrd.exe"}),
    perfil("GGXrdAPM3", "Guilty Gear Xrd REV2 (APM3)", {"guiltygearxrd.exe"}),
    perfil("SDR", "Dream Raiders", {"sdaemon.exe"}),
    perfil("Tekken7", "Tekken 7 Fated Retribution"),
    perfil("Tekken7R2", "Tekken 7 Fated Retribution Round 2"),
)


class ReconocerPerfilTest(TestCase):
    def test_reconoce_nombres_parecidos(self):
        for nombre, esperado in (("Daytona 3", "Daytona3"), ("Golden Gun", "GoldenGun"),
                                 ("GTI Club 3", "GTIClub3"), ("Dead or Alive 5", "DOA5"),
                                 ("Guitar Hero Arcade Edition", "GHA"), ("Tekken 7", "Tekken7"),
                                 ("Guilty Gear XX Accent Core Plus", "GGXXACPR")):
            with self.subTest(nombre):
                self.assertEqual(tp.reconocer_perfil(nombre, PERFILES).id, esperado)

    def test_no_adivina_si_no_se_parece(self):
        self.assertIsNone(tp.reconocer_perfil("Ford Racing", PERFILES))

    def test_el_numero_importa(self):
        parecidos = [p.id for _, p in tp.perfiles_parecidos("Dead or Alive 6", PERFILES, 2)]
        self.assertEqual(parecidos[0], "DOA6")

    def test_ordena_primero_los_parecidos(self):
        primeros = {p.id for _, p in tp.perfiles_parecidos("Guilty Gear Xrd", PERFILES, 3)}
        self.assertEqual(primeros, {"GGXrdSIGN", "GGXrdAPM3", "GGXXACPR"})


class CarpetasTest(TestCase):
    def setUp(self):
        temporal = TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.base = Path(temporal.name)

    def crear(self, *rutas, tamanio=1):
        for ruta in rutas:
            archivo = self.base / ruta
            archivo.parent.mkdir(parents=True, exist_ok=True)
            archivo.write_bytes(b"x" * tamanio)

    def test_distingue_coleccion_de_un_juego(self):
        self.crear("Juegos TP/Golden Gun/gun.exe", "Juegos TP/Daytona 3/Data/a.bin",
                   "Golden Gun/gun.exe", "Daytona 3/Data/x.bin", "Daytona 3/Binaries/y.dat")
        self.assertTrue(tp.es_coleccion(self.base / "Juegos TP", PERFILES))
        self.assertFalse(tp.es_coleccion(self.base / "Golden Gun", PERFILES))
        self.assertFalse(tp.es_coleccion(self.base / "Daytona 3", PERFILES))

    def test_revisar_marca_el_perfil_reconocido_por_nombre(self):
        carpeta = "Guitar Hero Arcade Edition"
        self.crear(f"{carpeta}/gh.exe", f"{carpeta}/unins000.exe", f"{carpeta}/Redist/vcredist_x64.exe")
        juego, = tp.revisar_carpetas([self.base / carpeta], PERFILES)
        self.assertEqual(juego.perfil.id, "GHA")
        self.assertTrue(juego.perfil_por_nombre)
        self.assertEqual(tp.problema_juego(juego, Counter(), Counter(gha=1)), "Falta elegir el ejecutable")
        self.assertTrue(tp.deducir_ejecutable(juego))
        self.assertEqual(juego.ejecutable.name, "gh.exe")
        self.assertIn("ejecutable", juego.deducidos)
        self.assertEqual(tp.problema_juego(juego, Counter(), Counter(gha=1)), "")

    def test_prefiere_el_ejecutable_shipping(self):
        self.crear("Tekken 7/TekkenGame/Binaries/Win64/TekkenGame-Win64-Shipping.exe",
                   "Tekken 7/Launcher.exe", "Tekken 7/Engine/Binaries/Win64/CrashReportClient.exe")
        juego, = tp.revisar_carpetas([self.base / "Tekken 7"], PERFILES)
        self.assertTrue(tp.deducir_ejecutable(juego))
        self.assertEqual(juego.ejecutable.name, "TekkenGame-Win64-Shipping.exe")

    def test_no_adivina_entre_dos_ejecutables_iguales(self):
        self.crear("Golden Gun/a.exe", "Golden Gun/b.exe")
        juego, = tp.revisar_carpetas([self.base / "Golden Gun"], PERFILES)
        self.assertFalse(tp.deducir_ejecutable(juego))
        self.assertIsNone(juego.ejecutable)

    def test_varias_copias_del_ejecutable_usa_la_mas_cercana(self):
        self.crear("Dream Raiders/sdaemon.exe", "Dream Raiders/backup/old/sdaemon.exe")
        juego, = tp.revisar_carpetas([self.base / "Dream Raiders"], PERFILES)
        self.assertEqual(tp.problema_juego(juego, Counter(), Counter(sdr=1)), "Hay varios ejecutables · elige uno")
        self.assertTrue(tp.deducir_ejecutable(juego))
        self.assertEqual(juego.ejecutable, (self.base / "Dream Raiders/sdaemon.exe").resolve())

    def test_eleccion_manual_deja_de_ser_deducida(self):
        self.crear("Golden Gun/gun.exe", "Golden Gun/bin/otro.exe")
        juego, = tp.revisar_carpetas([self.base / "Golden Gun"], PERFILES)
        tp.deducir_ejecutable(juego)
        tp.elegir_archivo(juego, juego.origen / "bin" / "otro.exe")
        self.assertFalse(juego.deducidos)
