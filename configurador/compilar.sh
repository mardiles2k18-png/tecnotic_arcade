#!/bin/bash
# Compila el Configurador (un solo .exe portable para Windows) desde Linux con Mono.
# Resultado: dist/TecnoticsArcadeConfigurador.exe
#
# Requisitos: mono-mcs, python3 con Pillow (para el icono).
# En Windows también se puede compilar con el csc.exe de .NET Framework 4 (ver LEEME.md).
set -e
cd "$(dirname "$0")"
RAIZ=..
OBJ=obj
# Se compila contra las librerías de referencia de .NET Framework 4.8 (las de Windows),
# para que cualquier función que no exista en Windows dé error aquí y no en el PC.
API=/usr/lib/mono/4.8-api
REFS="-nostdlib -r:$API/mscorlib.dll -r:$API/System.dll -r:$API/System.Core.dll -r:$API/System.Drawing.dll -r:$API/System.Windows.Forms.dll"
rm -rf "$OBJ"
mkdir -p "$OBJ" "$RAIZ/dist"

# 1. Pantalla de bienvenida
mcs -langversion:5 -optimize+ -target:winexe $REFS \
    -out:"$OBJ/TecnoticsArcade.exe" "$RAIZ/modo-arcade/TecnoticsArcade.cs"

# 2. Recursos: logo, icono y scripts (UTF-8 con BOM y CRLF, como los espera PowerShell 5.1)
cp "$RAIZ/logo/tecnotics-vertical.png" "$OBJ/logo.png"
python3 - "$OBJ" <<'EOF'
import sys, glob, os
from PIL import Image
obj = sys.argv[1]
logo = Image.open(os.path.join(obj, 'logo.png')).convert('RGBA')
lado = max(logo.size)
cuadro = Image.new('RGBA', (lado, lado), (0, 0, 0, 0))
cuadro.paste(logo, ((lado - logo.width) // 2, (lado - logo.height) // 2))
cuadro.save(os.path.join(obj, 'icono.ico'), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
for f in glob.glob('scripts/*.ps1'):
    s = open(f, encoding='utf-8-sig').read().replace('\r\n', '\n').replace('\n', '\r\n')
    open(os.path.join(obj, os.path.basename(f)), 'w', encoding='utf-8-sig', newline='').write(s)
EOF

RECURSOS="-resource:$OBJ/TecnoticsArcade.exe,TecnoticsArcade.exe -resource:$OBJ/logo.png,logo.png"
for f in "$OBJ"/*.ps1; do RECURSOS="$RECURSOS -resource:$f,$(basename "$f")"; done

# 3. Configurador
mcs -langversion:5 -optimize+ -target:winexe -win32icon:"$OBJ/icono.ico" \
    $REFS $RECURSOS \
    -out:"$RAIZ/dist/TecnoticsArcadeConfigurador.exe" Configurador.cs

echo "Listo: dist/TecnoticsArcadeConfigurador.exe"
