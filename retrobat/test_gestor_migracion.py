"""Pruebas de migración entre instalaciones temporales de RetroBat."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from xml.etree import ElementTree as ET

from gestor_migracion import aplicar_migracion, comparar_instalaciones, preparar_migracion


SISTEMAS = """<systemList>
<system><name>snes</name><fullname>Super Nintendo</fullname>
<path>~/../roms/snes</path><extension>.sfc</extension></system>
<system><name>megadrive</name><fullname>Mega Drive</fullname>
<path>~/../roms/megadrive</path><extension>.md</extension></system>
</systemList>"""


class MigracionTest(TestCase):
    def setUp(self):
        temporal = TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        base = Path(temporal.name).resolve()
        self.origen = base / "Origen"
        self.destino = base / "Destino"
        for instalacion in (self.origen, self.destino):
            self.escribir(instalacion, "retrobat.exe", b"ejecutable simulado")
            self.escribir(instalacion, "emulationstation/.emulationstation/es_systems.cfg", SISTEMAS)
            self.escribir(instalacion, "system/modules/rb_gui/bios_local.json", json.dumps({
                "snes": {"biosFiles": [{"file": "bios/nueva.bin"}, {"file": "bios/existente.bin"}]},
            }))

    def escribir(self, instalacion, ruta, datos):
        salida = instalacion / ruta
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_bytes(datos.encode("utf-8") if isinstance(datos, str) else datos)
        return salida

    def comparar(self):
        return comparar_instalaciones(self.origen, self.destino)

    def sistema(self, comparacion, clave="snes"):
        return next(sistema for sistema in comparacion.sistemas if sistema.clave == clave)

    def test_conflicto_conserva_destino_y_reemplazo_explicito_crea_respaldo(self):
        ruta = "roms/snes/Mario.sfc"
        datos_origen = b"rom: version A"
        datos_destino = b"rom: version B"
        original = self.escribir(self.origen, ruta, datos_origen)
        existente = self.escribir(self.destino, ruta, datos_destino)
        nuevo = self.escribir(self.origen, "roms/snes/Nuevo.sfc", b"rom nueva")
        comparacion = self.comparar()
        sistema = self.sistema(comparacion)
        self.assertEqual(sistema.estado, "diferente")
        juego = next(juego for juego in sistema.juegos if juego.clave == "mario.sfc")
        self.assertEqual(juego.estado, "conflicto")

        plan = preparar_migracion(comparacion, {"snes": None})
        aplicar_migracion(plan)
        self.assertEqual(existente.read_bytes(), datos_destino)
        self.assertEqual((self.destino / "roms/snes/Nuevo.sfc").read_bytes(), nuevo.read_bytes())

        plan = preparar_migracion(self.comparar(), {"snes": {juego.clave}}, [("snes", juego.clave)])
        resultado = aplicar_migracion(plan)
        self.assertEqual(existente.read_bytes(), datos_origen)
        self.assertEqual(original.read_bytes(), datos_origen)
        self.assertIsNotNone(resultado.respaldo)
        self.assertIn(datos_destino, [archivo.read_bytes() for archivo in resultado.respaldo.rglob("*.sfc")])

    def test_copia_sistema_faltante_y_respeta_los_sistemas_seleccionados(self):
        ruta = "roms/megadrive/Aventura.md"
        original = self.escribir(self.origen, ruta, b"rom de megadrive")
        self.escribir(self.origen, "roms/snes/Otro.sfc", b"rom de snes")
        comparacion = self.comparar()
        sistema = self.sistema(comparacion, "megadrive")
        self.assertEqual(sistema.estado, "faltante")
        self.assertEqual([juego.estado for juego in sistema.juegos], ["faltante"])

        aplicar_migracion(preparar_migracion(comparacion, {"megadrive": None}))
        self.assertEqual((self.destino / ruta).read_bytes(), original.read_bytes())
        self.assertFalse((self.destino / "roms/snes/Otro.sfc").exists())

    def test_distingue_sistema_incompatible_de_sistema_solo_en_destino(self):
        sin_megadrive = SISTEMAS[:SISTEMAS.index('<system><name>megadrive')] + "</systemList>"
        self.escribir(self.destino, "emulationstation/.emulationstation/es_systems.cfg", sin_megadrive)
        self.escribir(self.origen, "roms/megadrive/Aventura.md", b"rom de megadrive")
        self.escribir(self.destino, "roms/snes/Local.sfc", b"solo en destino")

        comparacion = self.comparar()
        self.assertEqual(self.sistema(comparacion, "megadrive").estado, "no_compatible")
        self.assertEqual(self.sistema(comparacion).estado, "solo_destino")

    def test_copia_pista_bin_referenciada_aunque_el_sistema_solo_liste_cue(self):
        sistemas = SISTEMAS.replace(".sfc", ".cue")
        for instalacion in (self.origen, self.destino):
            self.escribir(instalacion, "emulationstation/.emulationstation/es_systems.cfg", sistemas)
        descriptor = "roms/snes/Juego.cue"
        pista = "roms/snes/Pistas/Pista 01.bin"
        self.escribir(self.origen, descriptor, 'FILE "Pistas/Pista 01.bin" BINARY\nTRACK 01 MODE1/2352\n')
        self.escribir(self.origen, pista, b"pista de prueba")

        comparacion = self.comparar()
        self.assertEqual([juego.clave for juego in self.sistema(comparacion).juegos], ["juego.cue"])
        aplicar_migracion(preparar_migracion(comparacion, {"snes": None}))
        self.assertEqual((self.destino / descriptor).read_bytes(), (self.origen / descriptor).read_bytes())
        self.assertEqual((self.destino / pista).read_bytes(), b"pista de prueba")

    def test_catalogo_editado_entre_comparar_y_preparar_se_conserva(self):
        self.escribir(self.origen, "roms/snes/Mario.sfc", b"rom de prueba")
        self.escribir(self.origen, "roms/snes/gamelist.xml", """<gameList><game>
            <path>./Mario.sfc</path><name>Super Mario</name>
        </game></gameList>""")
        catalogo = self.escribir(self.destino, "roms/snes/gamelist.xml", "<gameList />")
        comparacion = self.comparar()
        editado = b"<gameList><game><path>./Mario.sfc</path><name>Edicion local</name></game></gameList>"
        catalogo.write_bytes(editado)

        with self.assertRaises(ValueError):
            preparar_migracion(comparacion, {"snes": None})
        self.assertEqual(catalogo.read_bytes(), editado)
        self.assertFalse((self.destino / "roms/snes/Mario.sfc").exists())

    def test_rom_destino_cambiada_despues_de_preparar_cancela_el_plan(self):
        ruta = "roms/snes/Mario.sfc"
        self.escribir(self.origen, ruta, b"rom de origen")
        existente = self.escribir(self.destino, ruta, b"rom de destino")
        self.escribir(self.origen, "roms/snes/Nuevo.sfc", b"rom faltante")
        plan = preparar_migracion(self.comparar(), {"snes": None}, [("snes", "mario.sfc")])
        actual = b"rom modificada por el usuario luego de preparar el plan"
        existente.write_bytes(actual)

        with self.assertRaises(ValueError):
            aplicar_migracion(plan)
        self.assertEqual(existente.read_bytes(), actual)
        self.assertFalse((self.destino / "roms/snes/Nuevo.sfc").exists())

    def test_copia_fichas_medios_y_bios_sin_recopiar_roms_iguales(self):
        ruta = "roms/snes/Mario.sfc"
        self.escribir(self.origen, ruta, b"rom igual")
        existente = self.escribir(self.destino, ruta, b"rom igual")
        estado_rom = existente.stat()
        self.escribir(self.destino, "roms/snes/Local.sfc", b"solo en destino")
        self.escribir(self.origen, "roms/snes/images/Mario.png", b"caratula simulada")
        self.escribir(self.origen, "roms/snes/gamelist.xml", """<gameList><game>
            <path>./Mario.sfc</path><name>Super Mario</name><image>./images/Mario.png</image>
        </game></gameList>""")
        catalogo = self.escribir(self.destino, "roms/snes/gamelist.xml", """<gameList><game>
            <path>./Local.sfc</path><name>Juego local</name>
        </game></gameList>""")
        self.escribir(self.origen, "bios/nueva.bin", b"bios faltante")
        self.escribir(self.origen, "bios/existente.bin", b"bios del origen")
        bios = self.escribir(self.destino, "bios/existente.bin", b"bios del destino")

        comparacion = self.comparar()
        estados = {juego.clave: juego.estado for juego in self.sistema(comparacion).juegos}
        self.assertEqual(estados, {"mario.sfc": "recursos", "local.sfc": "solo_destino"})
        aplicar_migracion(preparar_migracion(comparacion, {"snes": {"mario.sfc"}}))

        self.assertEqual(existente.read_bytes(), b"rom igual")
        self.assertEqual(existente.stat().st_mtime_ns, estado_rom.st_mtime_ns)
        self.assertEqual(existente.stat().st_ino, estado_rom.st_ino)
        self.assertEqual((self.destino / "roms/snes/Local.sfc").read_bytes(), b"solo en destino")
        self.assertEqual((self.destino / "roms/snes/images/Mario.png").read_bytes(), b"caratula simulada")
        self.assertEqual((self.destino / "bios/nueva.bin").read_bytes(), b"bios faltante")
        self.assertEqual(bios.read_bytes(), b"bios del destino")
        juegos = {juego.findtext("name"): juego for juego in ET.parse(catalogo).findall("game")}
        self.assertEqual(set(juegos), {"Super Mario", "Juego local"})
        self.assertEqual(juegos["Super Mario"].findtext("image"), "./images/Mario.png")
