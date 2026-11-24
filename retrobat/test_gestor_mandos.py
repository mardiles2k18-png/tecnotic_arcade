"""Pruebas de la pestaña Mandos: orden de jugadores y configuración automática por sistema."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
import xml.etree.ElementTree as ET

import gestor_mandos as gm

ES_INPUT = """<?xml version="1.0"?>
<inputList>
  <inputConfig type="keyboard" deviceName="Keyboard" deviceGUID="-1"/>
  <inputConfig type="joystick" deviceName="Xbox 360 Controller" deviceGUID="030000005e0400008e02000000007801"/>
  <inputConfig type="joystick" deviceName="Generic USB Joystick" deviceGUID="03000000790000000600000000000000"/>
</inputList>"""

AJUSTES = """<?xml version="1.0"?>
<config>
  <string name="INPUT P1NAME" value="Generic USB Joystick"/>
  <string name="INPUT P1GUID" value="03000000790000000600000000000000"/>
  <string name="INPUT P1PATH" value="\\\\?\\hid#vid_0079"/>
  <string name="teknoparrot[&quot;BBCF.teknoparrot&quot;].disableautocontrollers" value="1"/>
  <bool name="HideWindow" value="true"/>
</config>"""


class MandosTest(TestCase):
    def setUp(self):
        temporal = TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.raiz = Path(temporal.name).resolve()
        carpeta = self.raiz / "emulationstation" / ".emulationstation"
        carpeta.mkdir(parents=True)
        (carpeta / "es_input.cfg").write_text(ES_INPUT, encoding="utf-8")
        self.ajustes = carpeta / "es_settings.cfg"
        self.ajustes.write_text(AJUSTES, encoding="utf-8")

    def leer(self):
        return {n.get("name"): n.get("value") for n in ET.parse(self.ajustes).getroot()}

    def test_mandos_de_retrobat_sin_teclado(self):
        nombres = [m.nombre for m in gm.mandos_retrobat(self.raiz)]
        self.assertEqual(nombres, ["Xbox 360 Controller", "Generic USB Joystick"])

    def test_lee_jugadores(self):
        p1, p2, *_ = gm.jugadores(self.raiz)
        self.assertEqual((p1.nombre, p1.guid), ("Generic USB Joystick", "03000000790000000600000000000000"))
        self.assertTrue(p1.ruta)
        self.assertEqual(p2.nombre, "")

    def test_asignar_jugadores_vacia_path_y_respalda(self):
        xbox, generico = gm.mandos_retrobat(self.raiz)
        respaldo = gm.asignar_jugadores(self.raiz, {1: xbox, 2: generico})
        datos = self.leer()
        self.assertEqual(datos["INPUT P1NAME"], "Xbox 360 Controller")
        self.assertEqual(datos["INPUT P1GUID"], "030000005e0400008e02000000007801")
        self.assertEqual(datos["INPUT P1PATH"], "")
        self.assertEqual(datos["INPUT P2NAME"], "Generic USB Joystick")
        self.assertEqual(datos["HideWindow"], "true")
        self.assertEqual(datos['teknoparrot["BBCF.teknoparrot"].disableautocontrollers'], "1")
        self.assertTrue((respaldo / "originales.json").is_file())
        self.assertTrue(respaldo.name.startswith("jugadores-"))
        self.assertIsNone(gm.asignar_jugadores(self.raiz, {1: xbox, 2: generico}))

    def test_gemelos(self):
        mando = gm.MandoRetroBat("Zero Delay", "abc")
        self.assertEqual(gm.gemelos([mando, gm.MandoRetroBat("Zero Delay", "abc"), gm.MandoRetroBat("X", "y")],
                                    mando), 2)

    def test_mando_detectado_por_usb(self):
        xbox, generico = gm.mandos_retrobat(self.raiz)
        detectado = SimpleNamespace(usb=(0x0079, 0x0006), nombre="USB Gamepad", producto="")
        self.assertEqual(gm.mando_retrobat([xbox, generico], detectado), generico)
        detectado = SimpleNamespace(usb=(0, 0), nombre="Xbox 360 Controller", producto="")
        self.assertEqual(gm.mando_retrobat([xbox, generico], detectado), xbox)

    def test_autoconfiguracion_por_sistema(self):
        global_manual, estados = gm.autoconfiguracion(self.raiz, ["ps2", "teknoparrot"])
        self.assertFalse(global_manual)
        self.assertEqual(estados, {"ps2": gm.AUTOMATICO, "teknoparrot": gm.AUTOMATICO})
        self.assertEqual(gm.juegos_manuales(self.raiz, "teknoparrot"), ["BBCF.teknoparrot"])
        gm.fijar_autoconfiguracion(self.raiz, "ps2", True)
        self.assertEqual(self.leer()["ps2.disableautocontrollers"], "1")
        self.assertEqual(gm.autoconfiguracion(self.raiz, ["ps2"])[1]["ps2"], gm.MANUAL)
        gm.fijar_autoconfiguracion(self.raiz, "ps2", False)
        self.assertNotIn("ps2.disableautocontrollers", self.leer())
        self.assertIsNone(gm.fijar_autoconfiguracion(self.raiz, "ps2", False))
        with self.assertRaises(ValueError):
            gm.fijar_autoconfiguracion(self.raiz, 'ps2"]', True)

    def test_ajuste_global(self):
        texto = self.ajustes.read_text(encoding="utf-8").replace(
            "</config>", '<string name="global.disableautocontrollers" value="1"/></config>')
        self.ajustes.write_text(texto, encoding="utf-8")
        global_manual, estados = gm.autoconfiguracion(self.raiz, ["snes"])
        self.assertTrue(global_manual)
        self.assertTrue(estados["snes"].startswith(gm.MANUAL))
