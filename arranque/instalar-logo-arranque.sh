#!/bin/bash
# Cambia el logo que Batocera muestra en el primer instante del arranque
# (antes del vídeo) por el de Tecnotics.
#
# Uso, en la consola SSH de la máquina:
#   bash /userdata/system/tecnotics/instalar-logo-arranque.sh            -> instala el logo
#   bash /userdata/system/tecnotics/instalar-logo-arranque.sh restaurar  -> vuelve al logo original
#
# Antes, copia boot-logo.png y este script en \\IP\share\system\tecnotics\
# Al actualizar Batocera este cambio se pierde: vuelve a ejecutar el script.

set -e

ORIGEN="/userdata/system/tecnotics/boot-logo.png"
DESTINO="/usr/share/batocera/splash/boot-logo.png"
COPIA="/userdata/system/tecnotics/boot-logo-original-batocera.png"

mount -o remount,rw /

if [ "$1" = "restaurar" ]; then
    if [ ! -f "$COPIA" ]; then
        echo "No hay copia del logo original en $COPIA"
        exit 1
    fi
    cp "$COPIA" "$DESTINO"
    echo "Logo original restaurado."
else
    if [ ! -f "$ORIGEN" ]; then
        echo "No encuentro $ORIGEN"
        echo "Copia boot-logo.png en \\\\IP\\share\\system\\tecnotics\\ y vuelve a intentarlo."
        exit 1
    fi
    # Guarda una copia del logo de Batocera la primera vez
    [ -f "$COPIA" ] || cp "$DESTINO" "$COPIA"
    cp "$ORIGEN" "$DESTINO"
    echo "Logo de Tecnotics instalado."
fi

# Guarda el cambio para que sobreviva al reinicio
batocera-save-overlay
echo "Listo. Reinicia para verlo: reboot"
