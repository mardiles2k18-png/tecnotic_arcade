import tkinter as tk
from unittest import TestCase

from gestor_biblioteca_ui import DialogoScraping


class ScrapingDialogoTest(TestCase):
    def test_elige_sistema_y_solo_habilita_los_tipos_disponibles(self):
        raiz = tk.Tk()
        self.addCleanup(raiz.destroy)
        estados = {}

        def elegir():
            dialogo = next(w for w in raiz.winfo_children() if isinstance(w, DialogoScraping))
            estados["sin_proveedor"] = dialogo.inicio.instate(["disabled"])
            dialogo.selector.set("SNES (1)")
            dialogo.cambiar_sistema()
            estados["solo_caratula"] = dialogo.categorias_elegidas()
            dialogo.selector.set("MAME (2)")
            dialogo.cambiar_sistema()
            for tipo, valor in dialogo.tipos.items():
                valor.set(tipo == "video")
            dialogo.refrescar_inicio()
            dialogo.inicio.invoke()

        raiz.after(0, elegir)
        dialogo = DialogoScraping(raiz, {"Windows (1)": ("windows", 1), "SNES (1)": ("snes", 1),
                                         "MAME (2)": ("mame", 2)}, "Windows (1)", None)
        self.assertTrue(estados["sin_proveedor"])
        self.assertEqual(estados["solo_caratula"], {"cover"})
        self.assertEqual(dialogo.result, ("mame", "sistema", {"video"}))
