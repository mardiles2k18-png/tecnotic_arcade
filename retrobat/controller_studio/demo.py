"""Demo sin hardware: python -m controller_studio.demo desde retrobat."""
import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace
from . import VistaMando, TEMA

def crear_ventana():
    root=tk.Tk()
    root.title("TECNOTICS ARCADE · Controller Studio")
    root.geometry("900x580")
    root.minsize(650,440)
    root.configure(bg=TEMA["bg"])
    tk.Label(root,text="TECNOTICS  ARCADE",bg=TEMA["bg"],fg=TEMA["selected"],
             font=("Segoe UI",22,"bold")).pack(anchor="w",padx=24,pady=(20,0))
    tk.Label(root,text="Laboratorio de controles  /  DEMOSTRACIÓN SIN HARDWARE",
             bg=TEMA["bg"],fg=TEMA["muted"],font=("Segoe UI",11)).pack(anchor="w",padx=24)
    bar=tk.Frame(root,bg=TEMA["bg"])
    bar.pack(fill="x",padx=24,pady=12)
    status=tk.StringVar(value="Selecciona una entrada para simular su pulsación.")
    selected=None
    def elegir(k):
        nonlocal selected
        selected=k
        vista.iluminar({k},k)
        status.set("Entrada simulada: "+k)
        root.after(250,lambda: vista.iluminar(set(),selected))
    vista=VistaMando(root,elegir)
    vista.pack(fill="both",expand=True,padx=24)
    xi=["up","down","left","right","start","select","l3","r3","leftshoulder",
        "rightshoulder","south","east","west","north","lefttrigger","righttrigger"]
    xi += [l+"stick"+d for l in ("left","right") for d in ("up","down","left","right")]
    def cargar(api):
        nonlocal selected
        selected=None
        keys=xi if api=="XInput" else ([f"b{i}" for i in range(16)]+
            [f"h0.{d}" for d in (1,2,4,8)]+[f"a{i}{s}" for i in range(8) for s in "-+"])
        vista.dibujar(SimpleNamespace(api=api,botones=16,crucetas=1,ejes=8),{k:k for k in keys})
        status.set("Modo simulado: "+api)
    ttk.Button(bar,text="Xbox / XInput",command=lambda:cargar("XInput")).pack(side="left")
    ttk.Button(bar,text="Genérico / DirectInput",command=lambda:cargar("DirectInput")).pack(side="left",padx=8)
    tk.Label(root,textvariable=status,bg=TEMA["bg"],fg=TEMA["text"],
             font=("Segoe UI",11)).pack(pady=16)
    cargar("XInput")
    return root


def main():
    crear_ventana().mainloop()

if __name__=="__main__":
    main()
