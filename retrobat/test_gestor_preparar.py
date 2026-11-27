"""Verifica el asistente «Preparar un juego» con Dragon Ball (TeknoParrot RPCS3) como caso principal."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from xml.sax.saxutils import quoteattr
import struct

from gestor_core import sistemas_instalados
import gestor_firmware as fw
import gestor_preparar as prep

SISTEMAS = """<systemList>
<system><name>teknoparrot</name><fullname>TeknoParrot</fullname><path>~/../roms/teknoparrot</path>
<extension>.teknoparrot .parrot</extension><emulators><emulator name="teknoparrot"/></emulators></system>
<system><name>ps3</name><fullname>Sony PlayStation 3</fullname><path>~/../roms/ps3</path>
<extension>.ps3 .m3u</extension><emulators><emulator name="rpcs3"/></emulators></system>
<system><name>snes</name><fullname>Super Nintendo</fullname><path>~/../roms/snes</path>
<extension>.sfc .zip</extension><emulators>
<emulator name="libretro"><cores><core>bsnes</core><core default="true">snes9x</core></cores></emulator>
<emulator name="snes9x"/></emulators></system>
</systemList>"""

PERFIL = """<?xml version="1.0"?><GameProfile><GameName>Dragon Ball Zenkai Battle Royale</GameName>
<EmulatorType>RPCS3</EmulatorType><GamePath>{ruta}</GamePath></GameProfile>"""


def binario():
    datos = bytearray(68)
    datos[:2] = b"MZ"
    struct.pack_into("<I", datos, 60, 64)
    datos[64:] = b"PE\0\0"
    return bytes(datos)


class Instalacion(TestCase):
    def setUp(self):
        temporal = TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.raiz = Path(temporal.name).resolve()
        self.escribir("retrobat.exe", binario())
        self.escribir("emulationstation/.emulationstation/es_systems.cfg", SISTEMAS)
        self.escribir("emulationstation/emulatorlauncher.exe", binario())
        tp = "emulators/teknoparrot"
        for ruta in ("TeknoParrot/TeknoParrot.dll", "OpenParrotWin32/OpenParrot.dll",
                     "OpenParrotx64/OpenParrot64.dll", "TeknoParrot/Opensegaapi.dll"):
            self.escribir(f"{tp}/{ruta}", b"dll")
        self.escribir(f"{tp}/TeknoParrotUi.exe", binario())
        self.escribir(f"{tp}/RPCS3/rpcs3.exe", binario())
        juego = self.escribir("roms/teknoparrot/DBZ.teknoparrot/PS3_GAME/USRDIR/EBOOT.BIN", b"elf")
        self.escribir(f"{tp}/GameProfiles/DBZ.xml", PERFIL.format(ruta=juego))
        self.escribir(f"{tp}/UserProfiles/DBZ.xml", PERFIL.format(ruta=juego))
        self.escribir("roms/ps3/Juego.ps3/PS3_GAME/PARAM.SFO", b"sfo")
        self.escribir("roms/snes/Mario.sfc", b"rom")
        self.escribir("roms/snes/gamelist.xml",
                      "<gameList><game><path>./Mario.sfc</path><name>Super Mario World</name></game></gameList>")
        self.sistemas = sistemas_instalados(self.raiz)

    def escribir(self, ruta, datos):
        archivo = self.raiz / ruta
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_bytes(datos.encode() if isinstance(datos, str) else datos)
        return archivo

    def ajustes(self, valores):
        nodos = "".join(f'<string name={quoteattr(k)} value={quoteattr(v)}/>' for k, v in valores.items())
        self.escribir("emulationstation/.emulationstation/es_settings.cfg", f"<config>{nodos}</config>")

    def juego(self, nombre):
        return next(j for j in prep.juegos_instalados(self.raiz, self.sistemas) if j.ruta.name == nombre)

    def instalar_firmware(self, carpeta):
        for ruta in ("vsh/etc/version.txt", "vsh/module/vsh.self"):
            self.escribir(f"{carpeta}/{ruta}", b"4.92")


class PrepararTest(Instalacion):
    def test_biblioteca_lista_juegos_con_su_nombre(self):
        juegos = {j.ruta.name: j for j in prep.juegos_instalados(self.raiz, self.sistemas)}
        self.assertEqual(set(juegos), {"DBZ.teknoparrot", "Juego.ps3", "Mario.sfc"})
        self.assertEqual(juegos["Mario.sfc"].titulo, "Super Mario World")

    def test_emulador_predeterminado_ajuste_del_sistema_y_del_juego(self):
        mario = self.juego("Mario.sfc")
        self.assertEqual(prep.seleccion_emulador(self.raiz, mario),
                         prep.Seleccion("libretro", "snes9x", "predeterminado de RetroBat"))
        self.ajustes({"snes.emulator": "snes9x"})
        self.assertEqual(prep.seleccion_emulador(self.raiz, mario).emulador, "snes9x")
        self.ajustes({"snes.emulator": "snes9x", 'snes["Mario.sfc"].emulator': "libretro",
                      'snes["Mario.sfc"].core': "bsnes"})
        self.assertEqual(prep.seleccion_emulador(self.raiz, mario),
                         prep.Seleccion("libretro", "bsnes", "ajuste de este juego"))

    def test_dragon_ball_usa_el_rpcs3_de_teknoparrot(self):
        plan = prep.preparar_plan(self.raiz, self.sistemas, self.juego("DBZ.teknoparrot"))
        self.assertEqual(plan.tipo_teknoparrot, "RPCS3")
        self.assertEqual([p.estado for p in plan.pasos[:2]], [prep.HECHO, prep.HECHO])
        self.assertEqual({f.requisito.sistema for f in plan.requisitos}, {prep.TEKNOPARROT_RPCS3})
        self.assertEqual(plan.requisitos[0].requisito.emulador,
                         self.raiz / "emulators/teknoparrot/RPCS3/rpcs3.exe")
        self.assertEqual(plan.pasos[2].estado, prep.PENDIENTE)
        self.assertEqual(plan.siguiente.accion, prep.ACCION_REQUISITOS)
        self.assertEqual(plan.pasos[3].estado, prep.ESPERA)

    def test_firmware_en_otro_rpcs3_no_cuenta_para_dragon_ball(self):
        self.instalar_firmware("emulators/rpcs3/dev_flash")
        plan = prep.preparar_plan(self.raiz, self.sistemas, self.juego("DBZ.teknoparrot"))
        self.assertEqual(plan.pasos[2].estado, prep.PENDIENTE)
        self.instalar_firmware("emulators/teknoparrot/RPCS3/dev_flash")
        plan = prep.preparar_plan(self.raiz, self.sistemas, self.juego("DBZ.teknoparrot"))
        self.assertEqual(plan.pasos[2].estado, prep.HECHO)
        self.assertEqual(plan.siguiente.accion, prep.ACCION_PROBAR)

    def test_firmware_guardado_pide_instalarlo_en_el_rpcs3_correcto(self):
        self.escribir("bios/PS3UPDAT.PUP", b"pup")
        with patch.object(fw, "coincide_firmware", return_value=True):
            plan = prep.preparar_plan(self.raiz, self.sistemas, self.juego("DBZ.teknoparrot"))
        self.assertEqual(plan.requisitos[0].estado, fw.GUARDADO)
        self.assertEqual(plan.requisitos[0].accion, "Instalar")
        self.assertIn("falta instalarlo", plan.pasos[2].texto)

    def test_vfs_yml_cambia_la_carpeta_dev_flash(self):
        rpcs3 = "emulators/teknoparrot/RPCS3"
        self.escribir(f"{rpcs3}/config/vfs.yml", '$(EmulatorDir): ""\n/dev_flash/: $(EmulatorDir)datos/flash/\n')
        self.instalar_firmware(f"{rpcs3}/dev_flash")
        plan = prep.preparar_plan(self.raiz, self.sistemas, self.juego("DBZ.teknoparrot"))
        self.assertEqual(plan.pasos[2].estado, prep.PENDIENTE)
        self.instalar_firmware(f"{rpcs3}/datos/flash")
        plan = prep.preparar_plan(self.raiz, self.sistemas, self.juego("DBZ.teknoparrot"))
        self.assertEqual(plan.pasos[2].estado, prep.HECHO)

    def test_juego_de_ps3_usa_el_rpcs3_de_retrobat(self):
        plan = prep.preparar_plan(self.raiz, self.sistemas, self.juego("Juego.ps3"))
        self.assertEqual(plan.pasos[1].estado, prep.PENDIENTE)
        self.assertEqual(plan.pasos[1].accion, prep.ACCION_EMULADOR)
        self.assertEqual({f.requisito.sistema for f in plan.requisitos}, {"PlayStation 3"})

    def test_falta_rpcs3_de_teknoparrot(self):
        (self.raiz / "emulators/teknoparrot/RPCS3/rpcs3.exe").unlink()
        plan = prep.preparar_plan(self.raiz, self.sistemas, self.juego("DBZ.teknoparrot"))
        self.assertEqual(plan.pasos[1].estado, prep.PENDIENTE)
        self.assertEqual(plan.pasos[1].accion, prep.ACCION_TEKNOPARROT)
        self.assertEqual(plan.siguiente.numero, 2)

    def test_perfil_sin_importar(self):
        (self.raiz / "emulators/teknoparrot/UserProfiles/DBZ.xml").unlink()
        plan = prep.preparar_plan(self.raiz, self.sistemas, self.juego("DBZ.teknoparrot"))
        self.assertEqual(plan.pasos[0].estado, prep.PENDIENTE)
        self.assertEqual(plan.siguiente.accion, prep.ACCION_IMPORTAR)

    def test_comando_igual_que_emulationstation(self):
        juego = self.juego("DBZ.teknoparrot")
        plan = prep.preparar_plan(self.raiz, self.sistemas, juego)
        comando = prep.comando_prueba(self.raiz, plan)
        self.assertEqual(Path(comando[0]).name, "emulatorlauncher.exe")
        self.assertEqual(comando[1:], ["-system", "teknoparrot", "-emulator", "teknoparrot",
                                       "-core", "teknoparrot", "-rom", str(juego.ruta)])

    def test_titulo_de_teknoparrot_desde_el_perfil(self):
        juego = self.juego("DBZ.teknoparrot")
        self.assertEqual(juego.titulo, "Dragon Ball Zenkai Battle Royale")
        self.assertEqual(prep.categoria_juego(juego), "Sin categoría")


class SistemaTest(Instalacion):
    """Verificación previa de «Cargar sistemas»: emulador primero, después firmware; las BIOS solo avisan."""

    def test_ps3_bloquea_sin_emulador_y_luego_sin_firmware(self):
        estado = prep.revisar_sistema(self.raiz, self.sistemas, "ps3")
        self.assertTrue(estado.bloqueado)
        self.assertEqual(estado.siguiente.accion, prep.ACCION_EMULADOR)
        self.assertIn("emulador", estado.mensaje)
        self.escribir("emulators/rpcs3/rpcs3.exe", binario())
        estado = prep.revisar_sistema(self.raiz, self.sistemas, "ps3")
        self.assertTrue(estado.bloqueado)
        self.assertEqual(estado.pasos[0].estado, prep.HECHO)
        self.assertEqual(estado.siguiente.accion, prep.ACCION_REQUISITOS)
        self.assertIn("firmware", estado.mensaje)
        self.instalar_firmware("emulators/rpcs3/dev_flash")
        estado = prep.revisar_sistema(self.raiz, self.sistemas, "ps3")
        self.assertFalse(estado.bloqueado)
        self.assertEqual([p.estado for p in estado.pasos[:2]], [prep.HECHO, prep.HECHO])

    def test_firmware_del_rpcs3_de_teknoparrot_no_desbloquea_ps3(self):
        self.escribir("emulators/rpcs3/rpcs3.exe", binario())
        self.instalar_firmware("emulators/teknoparrot/RPCS3/dev_flash")
        self.assertTrue(prep.revisar_sistema(self.raiz, self.sistemas, "ps3").bloqueado)

    def test_teknoparrot_instalado_permite_cargar(self):
        estado = prep.revisar_sistema(self.raiz, self.sistemas, "teknoparrot")
        self.assertFalse(estado.bloqueado)
        self.assertEqual(estado.pasos[1].estado, prep.HECHO)
        self.assertEqual(estado.pasos[2].texto, "Este sistema no usa BIOS.")

    def test_teknoparrot_sin_permiso_no_ofrece_instalar(self):
        ruta = self.raiz / "emulators/teknoparrot/TeknoParrotUi.exe"
        with patch("gestor_emuladores.es_binario", side_effect=PermissionError(13, "denegado", str(ruta))):
            estado = prep.revisar_sistema(self.raiz, self.sistemas, "teknoparrot")
        self.assertTrue(estado.bloqueado)
        self.assertIn("Acceso denegado", estado.pasos[0].texto)
        self.assertIn(str(ruta), estado.pasos[0].texto)
        self.assertIsNone(estado.siguiente)

    def test_teknoparrot_sin_instalar_bloquea(self):
        (self.raiz / "emulators/teknoparrot/TeknoParrotUi.exe").unlink()
        estado = prep.revisar_sistema(self.raiz, self.sistemas, "teknoparrot")
        self.assertTrue(estado.bloqueado)
        self.assertEqual(estado.siguiente.accion, prep.ACCION_TEKNOPARROT)

    def test_bios_faltantes_solo_avisan(self):
        catalogo = {"snes": {"name": "Super Nintendo", "biosFiles": [{"file": "bios/sgb.sfc", "md5": ""}]}}
        self.escribir("emulators/retroarch/retroarch.exe", binario())
        self.escribir("emulators/retroarch/cores/snes9x_libretro.dll", binario())
        with patch.object(fw, "catalogo_incluido", return_value=catalogo):
            estado = prep.revisar_sistema(self.raiz, self.sistemas, "snes")
        self.assertEqual(estado.pasos[0].estado, prep.HECHO, estado.pasos[0].texto)
        self.assertEqual(estado.pasos[2].estado, prep.AVISO)
        self.assertEqual(estado.pasos[2].accion, prep.ACCION_BIOS)
        self.assertFalse(estado.bloqueado)
        self.assertIn("BIOS", estado.mensaje)
