"""Lectura en vivo para comprobar y reasignar controles desde la ventana del gestor."""
import ctypes as c
from uuid import UUID

from gestor_mandos_windows import (EstadoXInput, Guid, abrir_directinput, biblioteca_xinput, dll_sistema,
                                    funcion_estado_xinput, metodo_com)
from gestor_teknoparrot_controles import BOTONES_XI


class LectorXInput:
    def __init__(self, indice):
        self.indice = indice
        self.estado = funcion_estado_xinput(biblioteca_xinput())

    def leer(self):
        estado = EstadoXInput()
        if self.estado(self.indice, c.byref(estado)) != 0:
            raise OSError("El mando XInput se desconectó.")
        mando = estado.mando
        activas = {pos for pos, (mascara, _) in BOTONES_XI.items() if mando.botones & mascara}
        for lado, x, y in (("left", mando.lx, mando.ly), ("right", mando.rx, mando.ry)):
            if abs(x) >= 17000:
                activas.add(f"{lado}stick{'left' if x < 0 else 'right'}")
            if abs(y) >= 17000:
                activas.add(f"{lado}stick{'down' if y < 0 else 'up'}")
        if mando.lt >= 95:
            activas.add("lefttrigger")
        if mando.rt >= 95:
            activas.add("righttrigger")
        return activas

    def cerrar(self):
        pass


class EstadoDI(c.Structure):
    _fields_ = [("ejes", c.c_int32 * 8), ("crucetas", c.c_uint32 * 4), ("botones", c.c_uint8 * 128)]


class ObjetoFormato(c.Structure):
    _fields_ = [("guid", c.POINTER(Guid)), ("offset", c.c_uint32), ("tipo", c.c_uint32), ("flags", c.c_uint32)]


class FormatoDI(c.Structure):
    _fields_ = [("tamano", c.c_uint32), ("tamano_objeto", c.c_uint32), ("flags", c.c_uint32),
                ("tamano_datos", c.c_uint32), ("cantidad", c.c_uint32), ("objetos", c.POINTER(ObjetoFormato))]


class RangoDI(c.Structure):
    _fields_ = [("tamano", c.c_uint32), ("tamano_cabecera", c.c_uint32), ("offset", c.c_uint32),
                ("tipo_objeto", c.c_uint32), ("minimo", c.c_int32), ("maximo", c.c_int32)]


def posiciones_di(estado, capacidades, rangos):
    activas = {f"b{i}" for i in range(min(capacidades.botones, 128)) if estado.botones[i] & 0x80}
    for i in range(min(capacidades.crucetas, 4)):
        angulo = estado.crucetas[i]
        if angulo < 36000:
            direccion = (angulo + 2250) // 4500 % 8
            mascaras = (1, 3, 2, 6, 4, 12, 8, 9)[direccion]
            activas.update(f"h{i}.{d}" for d in (1, 2, 4, 8) if mascaras & d)
    for i in rangos:
        valor = estado.ejes[i]
        if abs(valor) >= 17000:
            activas.add(f"a{i}{'-' if valor < 0 else '+'}")
    return activas


class LectorDirectInput:
    def __init__(self, mando, hwnd):
        self.mando = mando
        self.dispositivo = c.c_void_p()
        self.raiz = abrir_directinput()
        try:
            self._iniciar(mando.guid, hwnd)
        except BaseException:
            self.cerrar()
            raise

    def _iniciar(self, identidad, hwnd):
        dispositivo = self.dispositivo
        guid = Guid.from_buffer_copy(UUID(identidad).bytes_le)
        crear = metodo_com(self.raiz, 3, c.c_int32, c.POINTER(Guid), c.POINTER(c.c_void_p), c.c_void_p)
        if crear(self.raiz, c.byref(guid), c.byref(dispositivo), None) < 0:
            raise OSError("No se pudo abrir el mando DirectInput seleccionado.")
        # El formato conserva los offsets de DIJOYSTATE usados por TeknoParrot para ejes, POV y botones.
        opcional = 0x80FFFF00  # DIDFT_OPTIONAL | DIDFT_ANYINSTANCE
        ids = [Guid.from_buffer_copy(UUID(f"a36d02{fin}-c9f3-11cf-bfc7-444553540000").bytes_le)
               for fin in ("e0", "e1", "e2", "f4", "f5", "e3", "e4", "e4", "f2")]
        objetos = [ObjetoFormato(c.pointer(id_), i * 4, opcional | 3, 0x100) for i, id_ in enumerate(ids[:8])]
        objetos += [ObjetoFormato(c.pointer(ids[8]), 32 + i * 4, opcional | 16, 0) for i in range(4)]
        objetos += [ObjetoFormato(None, 48 + i, opcional | 12, 0) for i in range(128)]
        arreglo = (ObjetoFormato * len(objetos))(*objetos)
        formato = FormatoDI(c.sizeof(FormatoDI), c.sizeof(ObjetoFormato), 1, c.sizeof(EstadoDI), len(arreglo), arreglo)
        fijar_formato = metodo_com(dispositivo, 11, c.c_int32, c.POINTER(FormatoDI))
        if fijar_formato(dispositivo, c.byref(formato)) < 0:
            raise OSError("Windows no pudo preparar los ejes y botones DirectInput.")
        ancestro = dll_sistema("user32.dll").GetAncestor
        ancestro.argtypes, ancestro.restype = (c.c_void_p, c.c_uint32), c.c_void_p
        cooperacion = metodo_com(dispositivo, 13, c.c_int32, c.c_void_p, c.c_uint32)
        if cooperacion(dispositivo, ancestro(hwnd, 2) or hwnd, 0xA) < 0:
            raise OSError("La ventana no pudo obtener acceso al mando DirectInput.")
        fijar_rango = metodo_com(dispositivo, 6, c.c_int32, c.c_void_p, c.POINTER(RangoDI))
        self.rangos = []
        for i in range(8):
            rango = RangoDI(c.sizeof(RangoDI), 16, i * 4, 1, -32768, 32767)
            if fijar_rango(dispositivo, 4, c.byref(rango)) >= 0:
                self.rangos.append(i)
        self.adquirir = metodo_com(dispositivo, 7, c.c_int32)
        self.sondear = metodo_com(dispositivo, 25, c.c_int32)
        self.obtener = metodo_com(dispositivo, 9, c.c_int32, c.c_uint32, c.POINTER(EstadoDI))
        self.adquirir(dispositivo)

    def leer(self):
        estado = EstadoDI()
        dispositivo = self.dispositivo
        self.sondear(dispositivo)
        if self.obtener(dispositivo, c.sizeof(estado), c.byref(estado)) < 0:
            self.adquirir(dispositivo)
            self.sondear(dispositivo)
            if self.obtener(dispositivo, c.sizeof(estado), c.byref(estado)) < 0:
                raise OSError("El mando DirectInput dejó de responder.")
        return posiciones_di(estado, self.mando, self.rangos)

    def cerrar(self):
        if self.dispositivo:
            metodo_com(self.dispositivo, 8, c.c_int32)(self.dispositivo)
            metodo_com(self.dispositivo, 2, c.c_uint32)(self.dispositivo)
            self.dispositivo = c.c_void_p()
        if self.raiz:
            metodo_com(self.raiz, 2, c.c_uint32)(self.raiz)
            self.raiz = c.c_void_p()


def abrir_lector(mando, hwnd):
    return LectorXInput(mando.indice) if mando.api == "XInput" else LectorDirectInput(mando, hwnd)
