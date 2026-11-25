"""Pruebas de Controller Studio y de la adaptación de perfiles de TeknoParrot."""
import ctypes as c
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from controller_studio import TEMA, VistaMando
from gestor_mandos_ui import PanelMandos
from gestor_mandos_windows import CapacidadesXInput, Mando, mandos_xinput
import gestor_teknoparrot_controles as controles
import gestor_teknoparrot_editor as editor
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

    def test_la_ilustracion_frontal_conserva_los_controles_interactivos(self):
        vista = self.ventana.vista
        self.assertTrue(vista.find_withtag("carcasa_mando"))
        self.assertTrue(vista.find_withtag("agarres_mando"))
        self.pulsar("south")
        self.assertEqual(self.ventana.asignacion.get(), "A")

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
                        for widget in (ventana.movimiento, ventana.proteger, ventana.capturar, ventana.adaptar, ventana.guardar):
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

    def test_dibuja_y_lee_todos_los_botones_con_capacidades_xinput_parciales(self):
        def estado(indice, _):
            return 0 if indice <= 1 else 1167

        def capacidades(indice, _, puntero):
            datos = c.cast(puntero, c.POINTER(CapacidadesXInput)).contents
            datos.subtipo = 1 if indice == 0 else 3
            datos.mando.botones = 0x8006  # Y, abajo e izquierda, como en la captura de la V30.
            datos.mando.lx = datos.mando.ly = 1
            return 0

        dll = SimpleNamespace(XInputGetState=estado, XInputGetCapabilities=capacidades)
        with patch("gestor_mandos_windows.biblioteca_xinput", return_value=dll):
            xbox, palanca = mandos_xinput()
        self.assertEqual(len(editor.opciones_fisicas(xbox)), 24)
        self.assertNotIn("south", editor.opciones_fisicas(palanca))
        self.assertIn("north", editor.opciones_fisicas(palanca))
        self.assertFalse(palanca.especial)

        ventana = self.ventana
        ventana.mandos[xbox.etiqueta] = xbox
        ventana.mando.set(xbox.etiqueta)
        ventana.cargar()
        self.root.update()
        self.assertEqual(set(ventana.vista.botones), set(editor.opciones_fisicas(xbox)))
        for codigo, etiqueta in (("south", "A"), ("east", "B"), ("west", "X"), ("north", "Y")):
            self.pulsar(codigo)
            self.assertEqual(ventana.asignacion.get(), etiqueta)
            self.leer({codigo})
            self.assertEqual(ventana.vista.itemcget(ventana.vista.botones[codigo], "fill"), TEMA["active"])

        panel = PanelMandos(self.root, self.panel.app)
        self.addCleanup(panel.destroy)
        panel.pack(fill="both", expand=True)
        fila = panel.tabla_mandos.insert("", "end")
        panel.detectados[fila] = xbox
        panel.tabla_mandos.selection_set(fila)
        with patch("gestor_mandos_ui.abrir_lector", return_value=self.lector):
            self.root.update()
        self.assertEqual(set(panel.vista.botones), set(ventana.vista.botones))

    def preparar_acciones(self, acciones, mapa, api="DirectInput"):
        ventana = self.ventana
        perfil = ventana.edicion.archivo
        xml = ET.parse(perfil).getroot()
        editor.campo_api(xml).find("FieldValue").text = api
        nodos = xml.find("JoystickButtons")
        nodos.clear()
        for clave, nombre in acciones:
            boton = ET.SubElement(nodos, "JoystickButtons")
            ET.SubElement(boton, "InputMapping").text = clave
            ET.SubElement(boton, "ButtonName").text = nombre
        ET.ElementTree(xml).write(perfil, encoding="utf-8")
        self.escribir("system/resources/inputmapping/teknoparrot.yml", mapa.encode())
        ventana.cargar()
        self.root.update()
        return perfil

    def test_adaptar_previsualiza_y_guarda_street_fighter_para_su_jugador(self):
        acciones = [("Test", "Test"), ("Service1", "Service"), ("Coin1", "Coin"),
                    ("P1ButtonStart", "Player 1 Start"), ("P1ButtonUp", "Player 1 Up")]
        acciones += [(f"P1Button{i}", f"Player 1 Button {i}") for i in range(1, 7)]
        acciones += [("P2Button5", "Player 1 Button EX1"), ("P2Button6", "Player 1 Button EX2"),
                     ("P2Button1", "Player 2 Button 1")]
        mapa = ("prueba:\n  Test: l3\n  Service1: r3\n  P1Button1: west\n  P1Button2: north\n"
                "  P1Button3: south\n  P1Button4: east\n  P1Button5: rightshoulder\n  P1Button6: leftshoulder\n"
                "  P2Button5: rightshoulder\n  P2Button6: leftshoulder\n")
        perfil = self.preparar_acciones(acciones, mapa)
        ventana = self.ventana
        original = perfil.read_bytes()
        with patch("gestor_teknoparrot_editor_ui.messagebox.askyesno", return_value=False) as confirmar:
            ventana.adaptar.invoke()
        confirmar.assert_called_once()
        self.assertEqual(perfil.read_bytes(), original)
        propuestas = {a.nombre: ventana.tabla.set(str(a.indice), "asignacion") for a in ventana.edicion.acciones}
        self.assertEqual([propuestas[f"Player 1 Button {i}"] for i in range(1, 7)], ["X", "Y", "A", "B", "RB", "LB"])
        self.assertEqual(propuestas["Player 1 Button EX1"], "RB")
        self.assertEqual(propuestas["Player 1 Button EX2"], "LB")
        self.assertNotIn("Player 2 Button 1", propuestas)
        self.assertEqual([propuestas[k] for k in ("Test", "Service")], [editor.SIN_ASIGNAR] * 2)
        self.assertEqual(propuestas["Coin"], "View / Atrás")
        self.assertEqual(propuestas["Player 1 Up"], "Cruceta ↑")

        ventana.adaptar.invoke()
        xml = ET.parse(perfil).getroot()
        nodos = {n.findtext("InputMapping"): n for n in xml.findall("./JoystickButtons/JoystickButtons")}
        self.assertEqual(editor.campo_api(xml).findtext("FieldValue"), "XInput")
        self.assertEqual(nodos["P1Button2"].findtext("XInputButton/ButtonCode"), "-32768")
        self.assertEqual(nodos["P1Button1"].findtext("XInputButton/XInputIndex"), "2")
        self.assertIsNone(nodos["P2Button1"].find("XInputButton"))
        respaldo, = (self.raiz / "user/tecnotics-gestor/respaldos-mandos").iterdir()
        self.assertEqual((respaldo / perfil.relative_to(self.raiz)).read_bytes(), original)
        self.assertTrue(ventana.probar.instate(["!disabled"]))

    def test_adaptar_distingue_credito_de_servicio_en_contra_y_raiden(self):
        for nombre, clave in (("Service / Coin", "Service1"), ("Coin 1", "Coin1")):
            with self.subTest(credito=nombre):
                self.preparar_acciones([(clave, nombre), ("Test", "Test"), ("Service2", "Service 2"),
                                       ("P1Button1", "Player 1 Shoot")],
                                      "prueba:\n  Test: l3\n  Service2: r3\n  P1Button1: south\n")
                edicion = self.ventana.edicion
                asignaciones = editor.adaptar_mando(edicion)
                self.assertEqual(asignaciones, {0: "select", 1: "", 3: "south"})

    def test_cambio_de_api_respeta_los_controles_guardados_de_otro_jugador(self):
        ventana = self.ventana
        perfil = ventana.edicion.archivo
        xml = ET.parse(perfil).getroot()
        editor.campo_api(xml).find("FieldValue").text = "DirectInput"
        p2 = xml.findall("./JoystickButtons/JoystickButtons")[1]
        controles.asignar_input(p2, editor.opcion_fisica(self.directinput, "b0"))
        ET.ElementTree(xml).write(perfil, encoding="utf-8")
        original = perfil.read_bytes()
        ventana.cargar()
        with self.assertRaisesRegex(ValueError, "otras acciones guardadas"):
            editor.guardar_edicion(self.raiz, ventana.edicion, editor.adaptar_mando(ventana.edicion))
        self.assertEqual(perfil.read_bytes(), original)
        self.assertEqual(ventana.edicion.campo_api.findtext("FieldValue"), "DirectInput")

    def test_adaptar_directinput_prioriza_el_mapa_configurado_en_retrobat(self):
        self.escribir(controles.ES_INPUT,
                      b'<inputList><inputConfig type="joystick" deviceName="Encoder de prueba" '
                      b'deviceGUID="03000000790000000600000000000000">'
                      b'<input name="a" type="button" id="3" value="1" /></inputConfig></inputList>')
        self.escribir(controles.DI_DB, b"03000000790000000600000000000000,Encoder,a:b1,platform:Windows,\n")
        ventana = self.ventana
        ventana.mandos[self.directinput.etiqueta] = replace(self.directinput, usb=(0x0079, 6))
        ventana.mando.set(self.directinput.etiqueta)
        ventana.cargar()
        ventana.adaptar.invoke()
        nodo = ET.parse(ventana.edicion.archivo).find("./JoystickButtons/JoystickButtons/DirectInputButton")
        self.assertEqual(nodo.findtext("Button"), "51")
        self.assertEqual(nodo.findtext("JoystickGuid"), self.directinput.guid)

    def test_palanca_izquierda_sustituye_solo_las_direcciones_del_jugador(self):
        direcciones = ("Up", "Down", "Left", "Right")
        acciones = [(f"P1Button{d}", f"Player 1 {d}") for d in direcciones]
        acciones += [("P1Button1", "Player 1 Button 1"), ("P2Button1", "Player 2 Button 1")]
        mapa = "prueba:\n  P1Button1: west\n  P2Button1: south\n"
        perfil = self.preparar_acciones(acciones, mapa, api="XInput")
        ventana = self.ventana
        self.assertEqual(ventana.movimiento["values"], (editor.MAPA_JUEGO, editor.PALANCA_IZQUIERDA, editor.CRUCETA))
        ventana.asignar("rightshoulder", fila=4)
        ventana.guardar_edicion()
        ventana.jugador.current(1)
        ventana.cargar()
        ventana.guardar_edicion()
        p2_original = ET.parse(perfil).find("./JoystickButtons/JoystickButtons[6]")

        ventana.jugador.current(0)
        ventana.cargar()
        self.assertEqual(ventana.movimiento.get(), editor.CRUCETA)
        ventana.movimiento.set(editor.PALANCA_IZQUIERDA)
        ventana.adaptar.invoke()
        nodos = ET.parse(perfil).findall("./JoystickButtons/JoystickButtons")
        esperado = [("IsLeftThumbY", "false"), ("IsLeftThumbY", "true"),
                    ("IsLeftThumbX", "true"), ("IsLeftThumbX", "false")]
        for i, (direccion, (eje, negativo)) in enumerate(zip(direcciones, esperado)):
            with self.subTest(direccion=direccion):
                enlace = nodos[i].find("XInputButton")
                self.assertEqual(enlace.findtext(eje), "true")
                self.assertEqual(enlace.findtext("IsAxisMinus"), negativo)
                self.assertEqual(enlace.findtext("IsButton"), "false")
                self.assertEqual(enlace.findtext("XInputIndex"), "2")
                self.leer({"leftstick" + direccion.lower()})
                self.assertIn("activa", ventana.tabla.item(str(i), "tags"))
        self.assertEqual(nodos[4].findtext("XInputButton/ButtonCode"), "512")
        self.assertEqual(ET.tostring(nodos[5]), ET.tostring(p2_original))

        ventana.cargar()
        self.assertEqual(ventana.movimiento.get(), editor.PALANCA_IZQUIERDA)
        ventana.movimiento.set(editor.CRUCETA)
        ventana.adaptar.invoke()
        nodos = ET.parse(perfil).findall("./JoystickButtons/JoystickButtons")
        self.assertEqual([n.findtext("XInputButton/ButtonCode") for n in nodos[:4]], ["1", "2", "4", "8"])

    def test_ofrece_solo_los_controles_de_movimiento_completos(self):
        direcciones = ("Up", "Down", "Left", "Right")
        self.preparar_acciones([(f"P1Button{d}", f"Player 1 {d}") for d in direcciones],
                               "prueba:\n  P1ButtonUp: up\n", api="XInput")
        ventana = self.ventana
        ventana.mandos[self.xinput.etiqueta] = replace(self.xinput, mascarilla=0)
        ventana.cargar()
        self.assertEqual(ventana.movimiento["values"], (editor.MAPA_JUEGO, editor.PALANCA_IZQUIERDA))

        ventana.mando.set(self.directinput.etiqueta)
        ventana.cargar()
        self.assertTrue(ventana.movimiento.instate(["disabled"]))
        self.escribir(controles.ES_INPUT,
                      b'<inputList><inputConfig type="joystick" deviceName="Encoder de prueba">'
                      b'<input name="leftanalogleft" type="axis" id="0" value="-1" />'
                      b'<input name="leftanalogup" type="axis" id="1" value="-1" />'
                      b'</inputConfig></inputList>')
        ventana.cargar()
        self.assertEqual(ventana.movimiento["values"], (editor.MAPA_JUEGO, editor.PALANCA_IZQUIERDA))
        ventana.movimiento.set(editor.PALANCA_IZQUIERDA)
        ventana.adaptar.invoke()
        nodos = ET.parse(ventana.edicion.archivo).findall("./JoystickButtons/JoystickButtons/DirectInputButton")
        self.assertEqual([(n.findtext("Button"), n.findtext("IsAxisMinus")) for n in nodos],
                         [("4", "true"), ("4", "false"), ("0", "true"), ("0", "false")])
