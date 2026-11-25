"""Enumeración de mandos con las bibliotecas del sistema de Windows."""
import ctypes as c
from dataclasses import dataclass
import os
from uuid import UUID


@dataclass(frozen=True)
class Mando:
    nombre: str
    api: str
    indice: int
    guid: str = ""
    producto: str = ""
    usb: tuple[int, int] = (0, 0)
    botones: int = 0
    ejes: int = 0
    crucetas: int = 0
    especial: bool = False
    mascarilla: int = 0xFFFF
    ejes_xinput: frozenset[str] = frozenset({"IsLeftThumbX", "IsLeftThumbY", "IsRightThumbX", "IsRightThumbY",
                                          "IsLeftTrigger", "IsRightTrigger"})

    @property
    def etiqueta(self):
        return f"{self.nombre} · {self.api} {self.indice + 1}"


class EstadoGamepad(c.Structure):
    _fields_ = [("botones", c.c_uint16), ("lt", c.c_uint8), ("rt", c.c_uint8),
                ("lx", c.c_int16), ("ly", c.c_int16), ("rx", c.c_int16), ("ry", c.c_int16)]


class EstadoXInput(c.Structure):
    _fields_ = [("paquete", c.c_uint32), ("mando", EstadoGamepad)]


class CapacidadesXInput(c.Structure):
    _fields_ = [("tipo", c.c_uint8), ("subtipo", c.c_uint8), ("flags", c.c_uint16),
                ("mando", EstadoGamepad), ("vibracion", c.c_uint16 * 2)]


def dll_sistema(nombre):
    return c.WinDLL(nombre, winmode=0x00000800)  # LOAD_LIBRARY_SEARCH_SYSTEM32


def biblioteca_xinput():
    for nombre in ("xinput1_4.dll", "xinput9_1_0.dll"):
        try:
            return dll_sistema(nombre)
        except OSError:
            continue
    raise OSError("Windows no pudo cargar XInput.")


def funcion_estado_xinput(dll):
    estado = dll.XInputGetState
    estado.argtypes, estado.restype = (c.c_uint32, c.POINTER(EstadoXInput)), c.c_uint32
    return estado


def mandos_xinput():
    dll = biblioteca_xinput()
    estado = funcion_estado_xinput(dll)
    capacidades = dll.XInputGetCapabilities
    capacidades.argtypes, capacidades.restype = (c.c_uint32, c.c_uint32, c.POINTER(CapacidadesXInput)), c.c_uint32
    mandos = []
    tipos = {2: "Volante", 3: "Palanca arcade", 4: "Mando de vuelo", 5: "Alfombra de baile", 19: "Mando arcade"}
    for indice in range(4):
        muestra = EstadoXInput()
        if estado(indice, c.byref(muestra)) != 0:
            continue
        datos = CapacidadesXInput()
        leido = capacidades(indice, 0, c.byref(datos)) == 0
        subtipo = datos.subtipo if leido else 0
        nombre = tipos.get(subtipo, "Mando compatible con Xbox")
        if subtipo in {0, 1}:
            # Algunos mandos compatibles anuncian una máscara parcial aunque GetState lea todos los botones.
            mandos.append(Mando(nombre, "XInput", indice))
            continue
        ejes = {"IsLeftThumbX": datos.mando.lx, "IsLeftThumbY": datos.mando.ly, "IsRightThumbX": datos.mando.rx,
                "IsRightThumbY": datos.mando.ry, "IsLeftTrigger": datos.mando.lt, "IsRightTrigger": datos.mando.rt}
        mandos.append(Mando(nombre, "XInput", indice, especial=subtipo not in {3, 19},
                            mascarilla=datos.mando.botones | muestra.mando.botones,
                            ejes_xinput=frozenset(eje for eje, disponible in ejes.items() if disponible)))
    return mandos


class Guid(c.Structure):
    _fields_ = [("data1", c.c_uint32), ("data2", c.c_uint16), ("data3", c.c_uint16), ("data4", c.c_uint8 * 8)]


class DispositivoDI(c.Structure):
    _fields_ = [("tamano", c.c_uint32), ("instancia", Guid), ("producto", Guid), ("tipo", c.c_uint32),
                ("nombre", c.c_wchar * 260), ("nombre_producto", c.c_wchar * 260), ("driver", Guid),
                ("pagina_uso", c.c_uint16), ("uso", c.c_uint16)]


class CapacidadesDI(c.Structure):
    _fields_ = [("tamano", c.c_uint32), ("flags", c.c_uint32), ("tipo", c.c_uint32), ("ejes", c.c_uint32),
                ("botones", c.c_uint32), ("crucetas", c.c_uint32), ("force_feedback", c.c_uint32 * 5)]


class RutaHID(c.Structure):
    _fields_ = [("tamano", c.c_uint32), ("tamano_cabecera", c.c_uint32), ("objeto", c.c_uint32),
                ("tipo_objeto", c.c_uint32), ("clase", Guid), ("ruta", c.c_wchar * 260)]


def metodo_com(objeto, indice, resultado, *argumentos):
    tabla = c.cast(objeto, c.POINTER(c.POINTER(c.c_void_p))).contents
    return c.WINFUNCTYPE(resultado, c.c_void_p, *argumentos)(tabla[indice])


def datos_dispositivo(directinput, datos):
    crear = metodo_com(directinput, 3, c.c_int32, c.POINTER(Guid), c.POINTER(c.c_void_p), c.c_void_p)
    dispositivo = c.c_void_p()
    if crear(directinput, c.byref(datos.instancia), c.byref(dispositivo), None) < 0:
        return None
    try:
        ruta = RutaHID(tamano=c.sizeof(RutaHID), tamano_cabecera=16)
        get_prop = metodo_com(dispositivo, 5, c.c_int32, c.c_void_p, c.POINTER(RutaHID))
        # DIPROP_GUIDANDPATH se pasa como identificador 12 en lugar de un GUID real.
        if get_prop(dispositivo, 12, c.byref(ruta)) >= 0 and "ig_" in ruta.ruta.casefold():
            return None  # Windows también expone estos mandos a través de XInput.
        capacidades = CapacidadesDI(tamano=c.sizeof(CapacidadesDI))
        get_caps = metodo_com(dispositivo, 3, c.c_int32, c.POINTER(CapacidadesDI))
        if get_caps(dispositivo, c.byref(capacidades)) < 0:
            return None
        return capacidades
    finally:
        metodo_com(dispositivo, 2, c.c_uint32)(dispositivo)


def abrir_directinput():
    # dinput.h: IID_IDirectInput8W, DIRECTINPUT_VERSION, DI8DEVCLASS_GAMECTRL y DIEDFL_ATTACHEDONLY.
    iid = Guid.from_buffer_copy(UUID("BF798031-483A-4DA2-AA99-5D64ED369700").bytes_le)
    kernel = dll_sistema("kernel32.dll")
    modulo = kernel.GetModuleHandleW
    modulo.argtypes, modulo.restype = (c.c_wchar_p,), c.c_void_p
    crear = dll_sistema("dinput8.dll").DirectInput8Create
    crear.argtypes = (c.c_void_p, c.c_uint32, c.POINTER(Guid), c.POINTER(c.c_void_p), c.c_void_p)
    crear.restype = c.c_int32
    objeto = c.c_void_p()
    if crear(modulo(None), 0x800, c.byref(iid), c.byref(objeto), None) < 0:
        raise OSError("Windows no pudo iniciar DirectInput.")
    return objeto


def mandos_directinput():
    objeto = abrir_directinput()
    mandos = []
    callback = c.WINFUNCTYPE(c.c_int, c.POINTER(DispositivoDI), c.c_void_p)

    @callback
    def registrar(puntero, _):
        datos = puntero.contents
        capacidades = datos_dispositivo(objeto, datos)
        if capacidades and (capacidades.botones or capacidades.ejes or capacidades.crucetas):
            vidpid = datos.producto.data1
            usb = (vidpid & 0xFFFF, vidpid >> 16) if bytes(datos.producto)[10:] == b"PIDVID" else (0, 0)
            nombre = datos.nombre or datos.nombre_producto or "Mando USB"
            mandos.append(Mando(nombre, "DirectInput", len(mandos),
                                guid=str(UUID(bytes_le=bytes(datos.instancia))), producto=datos.nombre_producto, usb=usb,
                                botones=capacidades.botones, ejes=capacidades.ejes, crucetas=capacidades.crucetas,
                                especial=(datos.tipo & 0xFF) not in {0x14, 0x15, 0x18}))
        return 1

    try:
        enumerar = metodo_com(objeto, 4, c.c_int32, c.c_uint32, callback, c.c_void_p, c.c_uint32)
        if enumerar(objeto, 4, registrar, None, 1) < 0:
            raise OSError("Windows no pudo enumerar los mandos DirectInput.")
    finally:
        metodo_com(objeto, 2, c.c_uint32)(objeto)
    return mandos


def detectar_mandos():
    if os.name != "nt":
        raise OSError("La detección de mandos del arcade requiere Windows.")
    mandos, errores = [], []
    for detectar in (mandos_xinput, mandos_directinput):
        try:
            mandos.extend(detectar())
        except OSError as error:
            errores.append(str(error))
    if len(errores) == 2:
        raise OSError(" ".join(errores))
    return mandos, errores
