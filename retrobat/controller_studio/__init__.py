"""TECNOTICS Controller Studio — visualización independiente de hardware."""
import tkinter as tk

__version__ = "0.1.0"
TEMA = dict(bg="#080e1c", body="#23354e", edge="#52789d", button="#14243a",
            text="#f1f5f9", muted="#91a8c2", active="#00e676", selected="#00c8ff")
COLORS = {"south":"#22c55e","east":"#ef4444","west":"#60a5fa","north":"#facc15"}

class VistaMando(tk.Canvas):
    """Contrato compatible con el editor existente; elegir recibe el ID físico."""
    def __init__(self, panel, elegir, *, tema=None, **kwargs):
        self.tema = {**TEMA, **(tema or {})}
        super().__init__(panel, **({"bg":self.tema["bg"], "highlightthickness":0,
                                    "width":420,"height":320} | kwargs))
        self.elegir = elegir
        self.botones = {}
        self.etiquetas = {}
        self.activos = set()
        self.elegido = None
        self.mando = None
        self.nombres = {}
        self.bind("<Configure>", lambda e: self._redibujar())
        self.bind("<Button-1>", self._pulsar)
        self.bind("<Motion>", self._mover)
        self.bind("<Leave>", lambda e: self.configure(cursor=""))

    def _entrada_en(self, evento):
        x, y = self.canvasx(evento.x), self.canvasy(evento.y)
        for item in reversed(self.find_overlapping(x, y, x, y)):
            for etiqueta in self.gettags(item):
                if etiqueta.startswith("input_"):
                    return etiqueta.removeprefix("input_")
        return None

    def _pulsar(self, evento):
        entrada = self._entrada_en(evento)
        if entrada is not None:
            self.elegir(entrada)

    def _mover(self, evento):
        self.configure(cursor="hand2" if self._entrada_en(evento) is not None else "")

    def dibujar(self, mando, nombres):
        self.mando, self.nombres = mando, dict(nombres)
        self.activos, self.elegido = set(), None
        self._redibujar()

    def _redibujar(self):
        self.delete("all")
        self.botones.clear()
        self.etiquetas.clear()
        if self.mando is None:
            return
        t = self.tema
        xi = self.mando.api == "XInput"
        # DirectInput no presupone posiciones físicas ni marca del dispositivo.
        filas = (min(128, getattr(self.mando,"botones",0))+7)//8
        alto = 320 if xi else max(320, 105+filas*30+125)
        w, h = max(1,self.winfo_width()), max(1,self.winfo_height())
        s = min(w/420, h/alto) if w>1 and h>1 else 1
        ox, oy = (w-420*s)/2, (h-alto*s)/2
        def coords(*p):
            return [v*s+(ox if i%2==0 else oy) for i,v in enumerate(p)]
        def label(x,y,text,size=10, color=None):
            # La figura ya se mide en píxeles. Evita que Tk vuelva a escalar sus etiquetas por el DPI.
            pixeles = max(7, round(size * s * 4 / 3))
            return self.create_text(*coords(x,y),text=text,fill=color or t["text"],
                                    font=("Segoe UI", -pixeles, "bold"))
        def oval(x,y,r,fill,outline):
            return self.create_oval(*coords(x-r,y-r,x+r,y+r),fill=fill,outline=outline,width=2)
        def boton(k,txt,x,y,l=34,a=28,round_=True):
            if k not in self.nombres: return
            tag="input_"+k
            draw=self.create_oval if round_ else self.create_rectangle
            self.botones[k]=draw(*coords(x-l/2,y-a/2,x+l/2,y+a/2),
                fill=t["button"],outline=t["edge"],width=2,tags=(tag,))
            self.etiquetas[k]=label(x,y,txt,10,COLORS.get(k,t["text"]))
            self.addtag_withtag(tag,self.etiquetas[k])
        label(210,18,"TECNOTICS  /  CONTROLLER STUDIO",11,t["selected"])
        if xi:
            # Silueta vectorial y controles independientes.
            self.create_polygon(*coords(45,116,68,77,115,66,305,66,352,77,375,116,
                397,223,378,263,348,270,305,224,278,207,142,207,115,224,
                72,270,42,263,23,223),smooth=True,splinesteps=24,
                fill=t["body"],outline=t["edge"],width=3)
            for k,txt,x,y in [("lefttrigger","LT",100,42),("righttrigger","RT",320,42),
                              ("leftshoulder","LB",100,72),("rightshoulder","RB",320,72),
                              ("select","VIEW",180,105),("start","MENU",240,105)]:
                boton(k,txt,x,y,51,24,False)
            for k,txt,x,y in [("north","Y",320,106),("west","X",290,136),
                              ("east","B",350,136),("south","A",320,166)]:
                boton(k,txt,x,y,29,29)
            for k,txt,dx,dy in [("up","↑",0,-23),("down","↓",0,23),
                                 ("left","←",-23,0),("right","→",23,0)]:
                boton(k,txt,158+dx,190+dy,23,23,False)
            for x,y,lado,centro in [(100,130,"left","l3"),(252,190,"right","r3")]:
                oval(x,y,43,t["bg"],t["edge"])
                boton(centro,centro.upper(),x,y,31,31)
                for sufijo,txt,dx,dy in [("up","↑",0,-30),("down","↓",0,30),
                                         ("left","←",-30,0),("right","→",30,0)]:
                    boton(lado+"stick"+sufijo,txt,x+dx,y+dy,22,22)
        else:
            label(210,43,"DIRECTINPUT  /  Entradas físicas",10,t["muted"])
            for i in range(min(128,getattr(self.mando,"botones",0))):
                boton("b"+str(i),str(i+1),35+i%8*50,72+i//8*30,39,25,False)
            y=85+filas*30
            for i in range(min(4,getattr(self.mando,"crucetas",0))):
                for d,txt,dx,dy in [(1,"↑",0,-19),(2,"→",19,0),(4,"↓",0,19),(8,"←",-19,0)]:
                    boton(f"h{i}.{d}",txt,60+i*100+dx,y+dy,19,19,False)
            for i,eje in enumerate(("X","Y","Z","RX","RY","RZ","S1","S2")):
                for j,signo in enumerate(("-","+")):
                    boton(f"a{i}{signo}",eje+signo,30+i%4*104+j*46,y+50+i//4*29,43,24,False)
        for x,color,txt in [(100,t["active"],"Pulsado"),(250,t["selected"],"Seleccionado")]:
            oval(x,alto-20,5,color,color)
            label(x+44,alto-20,txt,9,t["muted"])
        self.iluminar(self.activos,self.elegido)

    def iluminar(self, activas, elegido=None):
        self.activos, self.elegido = set(activas), elegido
        t=self.tema
        for k,item in self.botones.items():
            color=t["active"] if k in self.activos else t["selected"] if k==elegido else t["button"]
            self.itemconfigure(item,fill=color,outline=t["selected"] if k==elegido else t["edge"])
            self.itemconfigure(self.etiquetas[k],fill=t["bg"] if color!=t["button"] else COLORS.get(k,t["text"]))
