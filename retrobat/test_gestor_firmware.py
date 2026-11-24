"""Regresiones de descarga, rutas de instalación y copias locales de firmware."""

from dataclasses import replace
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from gestor_bios import ArchivoBios
import gestor_firmware as fw


def progreso(*_):
    pass


class FirmwareTest(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.raiz = Path(temporal.name).resolve()

    def escribir(self, ruta, contenido=b"prueba"):
        archivo = self.raiz / ruta
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_bytes(contenido)
        return archivo

    def test_catalogo_agrupa_alternativas_y_respeta_destinos_fuera_de_bios(self):
        self.escribir("system/modules/rb_gui/bios_local.json", json.dumps({
            "prueba": {"name": "Sistema de prueba", "biosFiles": [
                {"file": "emulators/test/cart.bin", "md5": "", "group": "arranque"},
                {"file": "roms/test/alternativa.bin", "md5": "", "group": "arranque"},
                {"file": "bios/../fuera.bin", "md5": ""},
            ]},
        }).encode())
        self.escribir("emulators/test/cart.bin")
        with patch.object(fw, "descargas_retrobat", side_effect=OSError("sin conexión")):
            filas, aviso = fw.revisar_firmware(self.raiz, {}, progreso)
        requisitos = {fila.requisito.destino.name: fila.estado for fila in filas
                      if fila.requisito.sistema == "Sistema de prueba"}
        self.assertIn("sin conexión", aviso)
        self.assertEqual(requisitos, {"cart.bin": "Presente · sin huella", "alternativa.bin": "Alternativa cubierta"})
        self.assertTrue(any(fila.requisito.sistema == "Nintendo DS" for fila in filas))

    def test_ps3_descarga_una_vez_y_verifica_por_separado_las_dos_copias(self):
        paquetes = [r for r in fw.requisitos_firmware(self.raiz, {}) if r.tipo == "rpcs3"]
        for r in paquetes:
            self.escribir(r.emulador)
        payload = b"paquete oficial simulado"
        huella = hashlib.sha256(payload).hexdigest()
        descarga = fw.Descarga("https://example.test/PS3UPDAT.PUP", len(payload), sha256=huella)
        requisitos = [replace(r, paquete=descarga, archivo=replace(r.archivo, sha256=huella)) for r in paquetes]

        def instalar(exe, argumentos):
            self.assertEqual(argumentos[:2], ("--headless", "--installfw"))
            self.assertEqual(argumentos[2].read_bytes(), payload)
            r = next(r for r in requisitos if r.emulador == exe)
            for ruta in r.instalado:
                self.escribir(ruta)
            return 0

        filas = [fw.Revision(r, fw.FALTA, "Descarga oficial") for r in requisitos]
        with patch.object(fw, "abrir_https", return_value=BytesIO(payload)) as servidor:
            with patch.object(fw, "ejecutar_emulador", side_effect=instalar) as emulador:
                resultados = fw.aplicar_firmware(self.raiz, filas, None, progreso)
                self.assertEqual(emulador.call_count, 2)
            self.assertEqual(servidor.call_count, 1)
        self.assertEqual([fw.estado_firmware(r) for r in requisitos], [fw.LISTO, fw.LISTO])
        self.assertTrue(all(resultado.endswith(fw.LISTO) for resultado in resultados))

    def test_importar_pup_por_archivo_aunque_falte_rpcs3(self):
        requisito = next(r for r in fw.requisitos_firmware(self.raiz, {}) if r.sistema == "PlayStation 3")
        contenido = b"firmware de prueba"
        huella = hashlib.sha256(contenido).hexdigest()
        requisito = replace(requisito, archivo=replace(requisito.archivo, sha256=huella))
        revision = fw.Revision(requisito, fw.FALTA, "Descarga oficial")

        invalido = self.escribir("descargas/PS3UPDAT.PUP", b"otro archivo")
        resultado, = fw.aplicar_firmware(self.raiz, [revision], invalido, progreso)
        self.assertIn("no coincide", resultado)
        self.assertFalse(requisito.destino.exists())

        original = self.escribir("descargas/PS3UPDAT (1).PUP", contenido)
        with patch.object(fw, "instalar_pup") as instalar:
            resultado, = fw.aplicar_firmware(self.raiz, [revision], original, progreso)
            instalar.assert_not_called()
        self.assertIn("Falta rpcs3.exe", resultado)
        self.assertEqual(requisito.destino.read_bytes(), contenido)
        self.assertEqual(original.read_bytes(), contenido)
        self.assertEqual(fw.estado_firmware(requisito), fw.GUARDADO)

        self.escribir(requisito.emulador)
        with patch.object(fw, "instalar_pup") as instalar, patch.object(fw, "descargar") as descargar:
            fw.aplicar_firmware(self.raiz, [revision], None, progreso)
        instalar.assert_called_once_with(self.raiz, requisito, requisito.destino, progreso)
        descargar.assert_not_called()

    def test_ofrece_descarga_antes_de_instalar_el_emulador(self):
        with patch.object(fw, "descargas_retrobat", return_value={}):
            filas, _ = fw.revisar_firmware(self.raiz, {}, progreso)
        ps3 = next(f for f in filas if f.requisito.sistema == "PlayStation 3")
        self.assertFalse(ps3.requisito.emulador.exists())
        self.assertEqual((ps3.estado, ps3.accion), (fw.FALTA, "Descarga oficial"))

    def test_descarga_incorrecta_no_se_publica_y_el_lote_continua(self):
        contenido = b"datos"
        huella = hashlib.sha1(b"blob 5\0" + contenido).hexdigest()
        fuente = fw.Descarga("https://example.test/firmware", len(contenido), blob=huella)
        filas = [fw.Revision(fw.Requisito("Prueba", ArchivoBios(self.raiz / "bios" / nombre, "")),
                             fw.FALTA, "Descarga oficial") for nombre in ("malo.bin", "bueno.bin")]
        with patch.object(fw, "descargas_retrobat", return_value={"malo.bin": fuente, "bueno.bin": fuente}):
            with patch.object(fw, "abrir_https", side_effect=[BytesIO(b"falso"), BytesIO(contenido)]):
                resultados = fw.aplicar_firmware(self.raiz, filas, None, progreso)
        self.assertFalse(filas[0].requisito.destino.exists())
        self.assertIn("huella", resultados[0])
        self.assertEqual(filas[1].requisito.destino.read_bytes(), contenido)

    def test_importar_archivo_verificado_preserva_destino_existente(self):
        origen = self.raiz / "mis_bios"
        contenido = b"correcto"
        self.escribir(origen / "a" / "bios.bin", b"distinto")
        self.escribir(origen / "b" / "bios.bin", contenido)
        destino = self.raiz / "bios" / "bios.bin"
        r = fw.Requisito("Prueba", ArchivoBios(destino, "", md5=(hashlib.md5(contenido).hexdigest(),)))
        fila = fw.Revision(r, fw.FALTA, fw.LOCAL)
        fw.aplicar_firmware(self.raiz, [fila], origen, progreso)
        self.assertEqual(destino.read_bytes(), contenido)
        destino.write_bytes(b"mi original")
        resultados = fw.aplicar_firmware(self.raiz, [fila], origen, progreso)
        self.assertEqual(destino.read_bytes(), b"mi original")
        self.assertIn("Huella diferente", resultados[0])

    def test_vita_config_vacia_conserva_el_archivo_original_y_verifica_resultado(self):
        exe = self.escribir("emulators/vita3k/Vita3K.exe")
        config = self.escribir("emulators/vita3k/config.yml", b'pref-path: ""\nbackend-renderer: Vulkan\n')
        destino = self.raiz / "saves" / "psvita" / "vita3k"
        requisitos = [r for r in fw.requisitos_firmware(self.raiz, {}) if r.tipo == "vita3k"]
        self.assertEqual(len(requisitos), 3)
        sistema = requisitos[0]
        pup = self.escribir(sistema.destino)

        def instalar(ejecutable, argumentos):
            self.assertEqual((ejecutable, argumentos), (exe, ("--firmware", pup)))
            self.assertEqual(fw.leer_pref_vita(config.read_text()), destino.as_posix())
            self.escribir(destino / "vs0" / "sys" / "modulo.suprx")
            return 0

        with patch.object(fw, "ejecutar_emulador", return_value=0):
            with self.assertRaisesRegex(ValueError, "no confirmó"):
                fw.instalar_pup(self.raiz, sistema, pup, progreso)
        with patch.object(fw, "ejecutar_emulador", side_effect=instalar):
            fw.instalar_pup(self.raiz, sistema, pup, progreso)
        self.assertIn("backend-renderer: Vulkan", config.read_text())
        respaldo, = config.parent.glob("config-firmware-*.yml.bak")
        self.assertIn('pref-path: ""', respaldo.read_text())
        self.assertTrue(fw.instalado_en_emulador(sistema))
        self.assertFalse(fw.instalado_en_emulador(requisitos[1]))

    def test_ryujinx_usa_los_datos_portables_de_retrobat(self):
        self.escribir("emulators/ryujinx/Ryujinx.exe")
        r = next(r for r in fw.requisitos_firmware(self.raiz, {}) if r.tipo == "ryujinx")
        with patch.object(subprocess, "Popen") as crear:
            fw.abrir_ryujinx(self.raiz, r)
        datos = self.raiz / "saves" / "switch" / "ryujinx" / "portable"
        crear.assert_called_once_with([str(r.emulador), "-r", str(datos)], cwd=r.emulador.parent)
        self.assertTrue(datos.is_dir())


@unittest.skipUnless(os.name == "nt" and os.environ.get("TECNOTICS_PROBAR_FIRMWARE") == "1",
                     "Prueba de integración con descargas oficiales en Windows")
class FirmwareWindows(unittest.TestCase):
    def test_teknoparrot_importa_el_pup_y_lo_instala_sin_interfaz(self):
        # RPCS3 rechaza ejecutarse dentro del TEMP de Windows.
        with tempfile.TemporaryDirectory(prefix="tecnotics-firmware-", dir=Path.cwd()) as temporal:
            raiz = Path(temporal).resolve()
            r = next(r for r in fw.requisitos_firmware(raiz, {}) if r.sistema.startswith("TeknoParrot"))
            paquete = fw.Descarga("https://github.com/ReaverTeknoGods/rpcs3/releases/download/"
                                  "rpcs3x6-windows/RPCS3_1.0.0.8.zip", 56966724,
                                  "5528f1b46c25c1d05571c8d374c599fd36bed0858387c6ad330344012b621eef")
            archivo = raiz / "PS3UPDAT (1).PUP"
            fw.descargar(r, r.paquete, archivo, progreso)
            self.assertFalse(r.emulador.exists())
            resultado, = fw.aplicar_firmware(raiz, [fw.Revision(r, fw.FALTA, fw.LOCAL)], archivo, progreso)
            self.assertIn("Falta rpcs3.exe", resultado)
            self.assertEqual(fw.estado_firmware(r), fw.GUARDADO)

            zip_rpcs3 = raiz / "RPCS3.zip"
            fw.descargar(r, paquete, zip_rpcs3, progreso)
            with ZipFile(zip_rpcs3) as comprimido:
                comprimido.extractall(r.emulador.parent)
            self.assertTrue(r.emulador.is_file())
            self.assertFalse(fw.instalado_en_emulador(r))
            registros = []

            def solo_headless(exe, argumentos, *, en_primer_plano=False):
                self.assertFalse(en_primer_plano, "El RPCS3 de TeknoParrot debe instalar sin pedir confirmación.")
                proceso = subprocess.run([str(exe), *map(str, argumentos)],
                                         cwd=exe.parent, timeout=60, capture_output=True,
                                         creationflags=subprocess.CREATE_NO_WINDOW)
                registro = exe.parent / "log" / "RPCS3.log"
                detalle = registro.read_text(encoding="utf-8", errors="replace")[-4500:] if registro.exists() else ""
                registros.append(f"Salida: {proceso.returncode:#x} {proceso.stdout!r} {proceso.stderr!r}\n{detalle}")
                return proceso.returncode

            with patch.object(fw, "ejecutar_emulador", side_effect=solo_headless):
                resultado, = fw.aplicar_firmware(raiz, [fw.Revision(r, fw.GUARDADO, "Instalar")], None, progreso)
            self.assertTrue(resultado.endswith(fw.LISTO), f"{resultado}\n" + "\n".join(registros))
            self.assertEqual(fw.estado_firmware(r), fw.LISTO)
            self.assertIn("4.93", r.instalado[0].read_text(encoding="ascii"))

    @unittest.skipUnless(os.environ.get("TECNOTICS_RETROBAT_PRUEBA"), "Requiere compilar el portable")
    def test_prepara_rpcs3_para_verificar_el_portable(self):
        from gestor_emuladores import Emulador, instalar_emulador

        raiz = Path(os.environ["TECNOTICS_RETROBAT_PRUEBA"]).resolve()
        r = next(r for r in fw.requisitos_firmware(raiz, {}) if r.sistema == "PlayStation 3")
        emulador = Emulador("rpcs3", "RPCS3", ("rpcs3",), ("rpcs3.exe",), ())
        exe, _ = instalar_emulador(raiz, emulador, None, progreso)
        self.assertEqual(exe, r.emulador)
        self.assertFalse(fw.instalado_en_emulador(r))
        r.destino.parent.mkdir(parents=True, exist_ok=True)
        fw.descargar(r, r.paquete, r.destino, progreso)
        self.assertEqual(fw.estado_firmware(r), fw.GUARDADO)

    def test_vita3k_instala_el_software_y_las_fuentes_oficiales(self):
        with fw.abrir_https("https://api.github.com/repos/Vita3K/Vita3K/releases/tags/continuous",
                           timeout=30) as respuesta:
            activo = next(a for a in json.load(respuesta)["assets"] if a["name"] == "windows-latest.zip")
        url = "https://github.com/Vita3K/Vita3K/releases/download/continuous/windows-latest.zip"
        digest = activo["digest"].removeprefix("sha256:")
        self.assertEqual(activo["browser_download_url"], url)
        self.assertEqual(len(digest), 64)
        paquete = fw.Descarga(url, activo["size"], digest)
        with tempfile.TemporaryDirectory(prefix="tecnotics-vita3k-") as temporal:
            raiz = Path(temporal).resolve()
            requisitos = [r for r in fw.requisitos_firmware(raiz, {}) if r.tipo == "vita3k" and not r.opcional]
            zip_vita = raiz / "Vita3K.zip"
            fw.descargar(requisitos[0], paquete, zip_vita, progreso)
            with ZipFile(zip_vita) as comprimido:
                comprimido.extractall(requisitos[0].emulador.parent)
            filas = [fw.Revision(r, fw.FALTA, "Descarga oficial") for r in requisitos]
            resultados = fw.aplicar_firmware(raiz, filas, None, progreso)
            registro = requisitos[0].emulador.parent / "Vita3K.log"
            detalle = registro.read_text(encoding="utf-8", errors="replace")[-3000:] if registro.exists() else ""
            for resultado in resultados:
                self.assertTrue(resultado.endswith(fw.LISTO), f"{resultado}\n{detalle}")
            self.assertEqual([fw.estado_firmware(r) for r in requisitos], [fw.LISTO, fw.LISTO])


if __name__ == "__main__":
    unittest.main()
