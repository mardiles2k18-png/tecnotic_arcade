"""Pruebas del componente gráfico a través del editor de TeknoParrot."""
from pathlib import Path
from tempfile import TemporaryDirectory
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from controller_studio import TEMA, VistaMando
from gestor_mandos_windows import Mando
from gestor_teknoparrot_editor_ui import EditorMandos


class AplicacionPrueba:
    ocupado = False

    def ejecutar(self, tarea, mostrar, _mensaje):
        mostrar(tarea())


class LectorPrueba:
    def __init__(self):
        self.activas = set()
        self.desconectado = False

    def leer(self):
        if self.desconectado:
            raise OSError("Mando desconectado")
        return self.activas

    def cerrar(self):
        pass


class PruebasControllerStudio(unittest.TestCase):
    def setUp(self):
        temporal = TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.raiz = Path(temporal.name).resolve()
        self.escribir("retrobat.exe", b"")
        self.escribir("system/templates/emulationstation/es_systems.cfg", b"<systemList><system>"
                      b"<name>teknoparrot</name><path>~/../roms/teknoparrot</path>"
                      b"<extension>.teknoparrot</extension></system></systemList>")
        self.ajustes = self.escribir("emulationstation/.emulationstation/es_settings.cfg",
                                    b'<config><bool name="HideWindow" value="true" /></config>')
        self.escribir("system/resources/inputmapping/teknoparrot.yml",
                     b"prueba:\n  P1Button1: south\n  P2Button1: south\n"
                     b"otro:\n  P1Button1: south\n  P2Button1: south\n")
        self.emulador = "emulators/teknoparrot"
        self.escribir(f"{self.emulador}/TeknoParrotUi.exe", b"")
        for id_, titulo in (("Prueba", "A · Juego de prueba"), ("Otro", "B · Segundo juego")):
            xml = ET.Element("GameProfile")
            ET.SubElement(xml, "GameName").text = titulo
            ejecutable = self.escribir(f"roms/teknoparrot/{id_}.teknoparrot/game.exe", b"")
            ET.SubElement(xml, "GamePath").text = str(ejecutable)
            valores = ET.SubElement(xml, "ConfigValues")
            api = ET.SubElement(valores, "ConfigValue")
            ET.SubElement(api, "FieldName").text = "Input API"
            ET.SubElement(api, "FieldValue").text = "XInput"
            opciones = ET.SubElement(api, "FieldOptions")
            for valor in ("XInput", "DirectInput"):
                ET.SubElement(opciones, "string").text = valor
            botones = ET.SubElement(xml, "JoystickButtons")
            for jugador in (1, 2):
                boton = ET.SubElement(botones, "JoystickButtons")
                ET.SubElement(boton, "InputMapping").text = f"P{jugador}Button1"
                ET.SubElement(boton, "ButtonName").text = f"Player {jugador} Shoot"
            datos = ET.tostring(xml, encoding="utf-8", xml_declaration=True)
            for carpeta in ("UserProfiles", "GameProfiles"):
                self.escribir(f"{self.emulador}/{carpeta}/{id_}.xml", datos)

        self.root = tk.Tk()
        self.addCleanup(self.root.destroy)
        self.panel = ttk.Frame(self.root)
        self.panel.app = AplicacionPrueba()
        self.xinput = Mando("Xbox de prueba", "XInput", 2)
        self.directinput = Mando("Encoder de prueba", "DirectInput", 0, botones=40, ejes=4, crucetas=1,
                                 guid="59f8164a-a383-44ae-a2f1-28e360efbccd")
        self.lector = LectorPrueba()
        for reemplazo in (
                patch("gestor_teknoparrot_editor_ui.detectar_mandos",
                      return_value=([self.xinput, self.directinput], [])),
                patch("gestor_teknoparrot_editor_ui.abrir_lector", side_effect=lambda *_: self.lector),
                patch("gestor_teknoparrot_editor_ui.messagebox.askyesno", return_value=True)):
            reemplazo.start()
            self.addCleanup(reemplazo.stop)
        self.ventana = EditorMandos(self.panel, self.raiz)
        self.root.update()

    def escribir(self, nombre, datos):
        archivo = self.raiz / nombre
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_bytes(datos)
        return archivo

    def pulsar(self, codigo):
        vista = self.ventana.vista
        x1, y1, x2, y2 = vista.coords(vista.botones[codigo])
        vista.event_generate("<Button-1>", x=round((x1 + x2) / 2), y=round((y1 + y2) / 2))

    def leer(self, activas):
        ventana = self.ventana
        self.lector.activas = activas
        if ventana.temporizador is not None:
            ventana.after_cancel(ventana.temporizador)
        ventana.leer_mando()

    def test_escalado_y_codigos_xinput_y_directinput(self):
        ventana = self.ventana
        self.assertIs(type(ventana.vista), VistaMando)
        for mando, codigo, nombre in ((self.xinput, "south", "A"), (self.directinput, "b39", "Botón 40")):
            ventana.mando.set(mando.etiqueta)
            ventana.cargar()
            for dpi in (96, 144):
                self.root.tk.call("tk", "scaling", dpi / 72)
                for ancho, alto in ((875, 570), (1060, 660)):
                    with self.subTest(api=mando.api, dpi=dpi, ancho=ancho, alto=alto):
                        ventana.geometry(f"{ancho}x{alto}")
                        self.root.update()
                        vista = ventana.vista
                        x1, y1, x2, y2 = vista.bbox("all")
                        self.assertGreaterEqual(min(x1, y1), 0)
                        self.assertLessEqual(x2, vista.winfo_width())
                        self.assertLessEqual(y2, vista.winfo_height())
                        for widget in (ventana.proteger, ventana.capturar, ventana.guardar):
                            self.assertTrue(widget.winfo_viewable())
                            derecha = widget.winfo_rootx() + widget.winfo_width() - ventana.winfo_rootx()
                            abajo = widget.winfo_rooty() + widget.winfo_height() - ventana.winfo_rooty()
                            self.assertLessEqual(derecha, ventana.winfo_width())
                            self.assertLessEqual(abajo, ventana.winfo_height())
                        self.pulsar(codigo)
                        self.assertEqual(ventana.asignacion.get(), nombre)
                        self.assertEqual(vista.itemcget(vista.botones[codigo], "fill"), TEMA["selected"])
                        self.leer({codigo})
                        self.assertEqual(vista.itemcget(vista.botones[codigo], "fill"), TEMA["active"])
                        self.leer(set())
        ventana.guardar_edicion()
        xml = ET.parse(ventana.edicion.archivo).getroot()
        boton = xml.find("./JoystickButtons/JoystickButtons/DirectInputButton")
        self.assertIsNotNone(boton)
        self.assertEqual(boton.findtext("Button"), "87")
        self.assertEqual(boton.findtext("JoystickGuid"), self.directinput.guid)

    def test_captura_por_jugador_y_respaldo_del_perfil(self):
        ventana = self.ventana
        ventana.jugador.current(1)
        ventana.cargar()
        self.root.update()
        ventana.armar_captura()
        self.leer({"east"})
        perfil = ventana.edicion.archivo
        otro = perfil.with_name("Otro.xml")
        original, original_otro, original_cfg = perfil.read_bytes(), otro.read_bytes(), self.ajustes.read_bytes()
        ventana.guardar_edicion()
        xml = ET.parse(perfil).getroot()
        p1, p2 = xml.findall("./JoystickButtons/JoystickButtons")
        self.assertIsNone(p1.find("XInputButton"))
        self.assertEqual(p2.findtext("XInputButton/ButtonCode"), "8192")
        self.assertEqual(p2.findtext("XInputButton/XInputIndex"), "2")
        self.assertEqual(xml.findtext("GamePath"), ET.fromstring(original).findtext("GamePath"))
        self.assertEqual(otro.read_bytes(), original_otro)
        ajustes = {n.get("name"): n.get("value") for n in ET.parse(self.ajustes).getroot()}
        self.assertEqual(ajustes['teknoparrot["Prueba.teknoparrot"].disableautocontrollers'], "1")
        self.assertEqual(ajustes["HideWindow"], "true")
        base = self.raiz / "user/tecnotics-gestor/respaldos-mandos"
        respaldo, = base.iterdir()
        self.assertEqual((respaldo / perfil.relative_to(self.raiz)).read_bytes(), original)
        self.assertEqual((respaldo / self.ajustes.relative_to(self.raiz)).read_bytes(), original_cfg)

    def test_desconexion_quita_el_resaltado_y_lectura_se_recupera(self):
        ventana = self.ventana
        self.leer({"south"})
        self.assertEqual(ventana.vista.activos, {"south"})
        self.lector.desconectado = True
        self.leer(set())
        self.assertEqual(ventana.vista.activos, set())
        self.assertEqual(ventana.vista.elegido, "south")
        self.assertTrue(ventana.capturar.instate(["disabled"]))
        self.lector = LectorPrueba()
        ventana.inventario()
        self.leer({"east"})
        self.assertEqual(ventana.vista.activos, {"east"})
        self.assertTrue(ventana.capturar.instate(["!disabled"]))
