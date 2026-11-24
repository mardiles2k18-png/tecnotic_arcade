"""Verifica la instalación y selección de emuladores de RetroBat."""
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless
from unittest.mock import patch
import hashlib
import os
import struct
import subprocess

import gestor_emuladores as emu
from gestor_teknoparrot_pantalla import leer_ajustes


def progreso(*_):
    pass


def binario():
    datos = bytearray(68)
    datos[:2] = b"MZ"
    struct.pack_into("<I", datos, 60, 64)
    datos[64:] = b"PE\0\0"
    return datos


SISTEMAS = """<systemList>
<system><name>snes</name><fullname>Super Nintendo</fullname><emulators>
<emulator name="libretro"><cores><core>snes9x</core></cores></emulator><emulator name="snes9x"/>
</emulators></system>
<system><name>nes</name><fullname>Nintendo NES</fullname><emulators>
<emulator name="libretro"><cores><core>fceumm</core></cores></emulator>
</emulators></system>
<system><name>switch</name><fullname>Nintendo Switch</fullname><emulators>
<emulator name="ryujinx"/><emulator name="eden"/><emulator name="yuzu"/>
</emulators></system>
</systemList>"""


class Base(TestCase):
    def setUp(self):
        temporal = TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.raiz = Path(temporal.name).resolve()
        self.escribir("emulationstation/.emulationstation/es_systems.cfg", SISTEMAS)

    def escribir(self, ruta, datos):
        archivo = self.raiz / ruta
        archivo.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(datos, str):
            archivo.write_text(datos, encoding="utf-8")
        else:
            archivo.write_bytes(datos)
        return archivo

    def catalogo(self):
        return {(e.id, e.nucleo): e for e in emu.catalogo_emuladores(self.raiz)}


class EmuladoresTest(Base):
    def test_distingue_snes9x_standalone_y_nucleo_segun_catalogo_local(self):
        catalogo = self.catalogo()
        self.assertEqual(catalogo["snes9x", False].ejecutables, ("snes9x-x64.exe",))
        self.assertEqual(catalogo["snes9x", True].ejecutables, ("snes9x_libretro.dll",))
        self.assertEqual(catalogo["snes9x", True].vinculos[0].emulador, "libretro")
        self.assertTrue(catalogo["eden", False].via_automatica)
        self.assertFalse(catalogo["yuzu", False].via_automatica)

    def test_importacion_de_ryujinx_acepta_carpeta_publish_y_conserva_ajustes(self):
        item = self.catalogo()["ryujinx", False]
        exe = self.escribir("fuente/publish/Ryujinx.exe", binario())
        previo = self.escribir("emulators/ryujinx/portable.ini", "mis ajustes")
        self.escribir("fuente/publish/portable.ini", "ajustes del paquete")
        self.escribir("system/templates/ryujinx/Configure Ryujinx.bat", "plantilla")
        self.escribir("system/configgen/templates_files.lst",
                      r"\system\templates\ryujinx\Configure Ryujinx.bat|\emulators\ryujinx\Configure Ryujinx.bat")
        with patch.object(emu, "publicar_directorio", lambda origen, destino: origen.rename(destino)):
            destino, respaldo = emu.instalar_emulador(self.raiz, item, self.raiz / "fuente", progreso)
        self.assertEqual(destino, previo.parent / exe.name)
        self.assertEqual(previo.read_text(), "mis ajustes")
        self.assertEqual((respaldo / "portable.ini").read_text(), "mis ajustes")
        self.assertTrue((previo.parent / "Configure Ryujinx.bat").is_file())
        self.assertTrue((self.raiz / "saves/switch/ryujinx/portable").is_dir())
        self.assertEqual(emu.instalar_emulador(self.raiz, item, None, progreso), (destino, None))

    def test_falla_sin_cambiar_si_el_paquete_no_tiene_el_ejecutable_esperado(self):
        item = self.catalogo()["snes9x", False]
        original = self.escribir("emulators/snes9x/config.ini", "original")
        self.escribir("fuente/invalido.exe", binario())
        with self.assertRaisesRegex(ValueError, "ejecutable o núcleo"):
            emu.instalar_emulador(self.raiz, item, self.raiz / "fuente", progreso)
        self.assertEqual(original.read_text(), "original")

    def test_activa_nucleo_y_standalone_sin_modificar_los_ajustes_de_otros_sistemas(self):
        catalogo = self.catalogo()
        self.escribir("emulators/retroarch/retroarch.exe", binario())
        self.escribir("emulators/retroarch/cores/snes9x_libretro.dll", binario())
        self.escribir("emulators/snes9x/snes9x-x64.exe", binario())
        anterior = '<config><bool name="HideWindow" value="true"/><string name="psx.core" value="mednafen_psx"/></config>'
        self.escribir("emulationstation/.emulationstation/es_settings.cfg", anterior)
        nucleo = catalogo["snes9x", True]
        respaldo = emu.activar_emulador(self.raiz, nucleo, nucleo.vinculos[0])
        self.assertEqual(respaldo.read_text(), anterior)
        _, _, cfg = leer_ajustes(self.raiz)
        self.assertEqual(cfg.find("string[@name='snes.core']").get("value"), "snes9x")
        standalone = catalogo["snes9x", False]
        emu.activar_emulador(self.raiz, standalone, standalone.vinculos[0])
        _, _, cfg = leer_ajustes(self.raiz)
        self.assertIsNone(cfg.find("string[@name='snes.core']"))
        self.assertEqual(cfg.find("string[@name='snes.emulator']").get("value"), "snes9x")
        self.assertEqual(cfg.find("string[@name='psx.core']").get("value"), "mednafen_psx")

    def test_rechaza_descarga_con_sha256_incorrecto(self):
        class Respuesta(BytesIO):
            headers = {"Content-Length": "4", "Content-Type": "application/zip"}

        destino = self.raiz / "emulador.zip"
        paquete = emu.Paquete(("https://retrobat.org/archivo.zip",), 4, hashlib.sha256(b"real").hexdigest())
        with patch.object(emu, "abrir_oficial", return_value=Respuesta(b"otro")):
            with self.assertRaisesRegex(ValueError, "huella"):
                emu.descargar_paquete(paquete, destino, progreso)
        self.assertFalse(destino.exists())


@skipUnless(os.name == "nt" and os.environ.get("TECNOTICS_PROBAR_EMULADORES") == "1",
            "Requiere Windows y los repositorios oficiales")
class EmuladoresWindows(Base):
    def test_instala_snes9x_y_un_nucleo_desde_retrobat(self):
        catalogo = self.catalogo()
        standalone = catalogo["snes9x", False]
        exe, _ = emu.instalar_emulador(self.raiz, standalone, None, progreso)
        self.assertTrue(emu.es_binario(exe))
        emu.activar_emulador(self.raiz, standalone, standalone.vinculos[0])
        fceumm = catalogo["fceumm", True]
        dll, _ = emu.instalar_emulador(self.raiz, fceumm, None, progreso)
        self.assertEqual(dll, self.raiz / "emulators" / "retroarch" / "cores" / "fceumm_libretro.dll")
        self.assertTrue(emu.es_binario(dll))
        exe_ra = self.raiz / "emulators" / "retroarch" / "retroarch.exe"
        self.assertTrue(emu.es_binario(exe_ra))
        emu.activar_emulador(self.raiz, fceumm, fceumm.vinculos[0])
        _, _, cfg = leer_ajustes(self.raiz)
        self.assertEqual(cfg.find("string[@name='nes.core']").get("value"), "fceumm")
        salida = subprocess.run([str(exe_ra), "--version"], cwd=exe_ra.parent, timeout=20,
                                 capture_output=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertIn(b"RetroArch", salida.stdout + salida.stderr)
