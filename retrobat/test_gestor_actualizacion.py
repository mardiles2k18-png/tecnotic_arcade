import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from gestor_actualizacion import descargar, seleccionar


class ActualizacionTest(unittest.TestCase):
    def test_version_numerica_y_artefactos(self):
        def release(n):
            nombre = f"Gestor-Arcade-Tecnoticis-{n}.exe"
            return {"tag_name": f"retrobat-manager-preview-{n}-abcdef0", "assets": [
                {"name": nombre, "id": n},
                {"name": nombre + ".sha256.txt", "id": n + 1000},
            ]}
        self.assertEqual(seleccionar([release(9), release(33), release(100)], 33), (100, 100, 1100))
        self.assertIsNone(seleccionar([release(33)], 33))
        self.assertIsNone(seleccionar([{"tag_name": "retrobat-manager-preview-34-abcdef0"}], 33))

    def test_descarga_integra_y_limpieza_si_no_coincide(self):
        binario = b"MZ ejecutable de prueba"
        suma = hashlib.sha256(binario).hexdigest()
        registro = f"{suma}  Gestor-Arcade-Tecnoticis-34.exe\n".encode("ascii")
        with tempfile.TemporaryDirectory() as directorio:
            with patch("gestor_actualizacion.abrir", side_effect=[io.BytesIO(registro), io.BytesIO(binario)]):
                archivo = descargar((34, 12, 13), directorio)
                self.assertEqual(archivo.read_bytes(), binario)
                archivo.unlink()
            with patch("gestor_actualizacion.abrir", side_effect=[io.BytesIO(registro), io.BytesIO(b"MZ incompleto")]):
                with self.assertRaisesRegex(ValueError, "SHA-256"):
                    descargar((34, 12, 13), directorio)
            self.assertEqual(list(Path(directorio).iterdir()), [])
