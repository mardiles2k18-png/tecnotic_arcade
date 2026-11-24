"""Punto de entrada del ejecutable independiente de Controller Studio."""
import argparse
from pathlib import Path
from tkinter import ttk
import traceback

from controller_studio import VistaMando
from controller_studio.demo import crear_ventana, main


def comprobar_demo():
    ventana = crear_ventana()
    errores = []
    ventana.report_callback_exception = lambda *error: errores.append(error[1])
    try:
        ventana.update()
        vista = next(hijo for hijo in ventana.winfo_children() if isinstance(hijo, VistaMando))

        def pulsar(entrada):
            x1, y1, x2, y2 = vista.coords(vista.botones[entrada])
            x, y = round((x1 + x2) / 2), round((y1 + y2) / 2)
            vista.event_generate("<Motion>", x=x, y=y)
            vista.event_generate("<Button-1>", x=x, y=y)
            ventana.update()
            if vista.elegido != entrada or entrada not in vista.activos:
                raise RuntimeError(f"La vista no registró el clic de {entrada}.")

        if vista.mando.api != "XInput":
            raise RuntimeError("La demo debe iniciar con la vista de Xbox.")
        pulsar("south")
        barra = next(hijo for hijo in ventana.winfo_children() if any(
            isinstance(nieto, ttk.Button) for nieto in hijo.winfo_children()))
        directo = next(boton for boton in barra.winfo_children() if "DirectInput" in boton.cget("text"))
        directo.invoke()
        ventana.geometry("650x440")
        ventana.update()
        if vista.mando.api != "DirectInput":
            raise RuntimeError("La demo no cambió a la vista de DirectInput.")
        pulsar("b0")
        if errores:
            raise RuntimeError(str(errores[0]))
    finally:
        ventana.destroy()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verificar", type=Path)
    informe = parser.parse_args().verificar
    if informe is None:
        main()
    else:
        try:
            comprobar_demo()
        except Exception:
            informe.write_text(traceback.format_exc(), encoding="utf-8")
            raise SystemExit(1) from None
        informe.write_text("OK\n", encoding="utf-8")
