#!/bin/bash
# Configuración base de Batocera para las placas HP ProOne 400 G2 de Tecnotics Arcade.
# Ejecutar una vez por SSH después de instalar Batocera:
#   bash /userdata/system/tecnotics/configurar-placa-hp.sh
#
# Qué hace:
#  - Usa solo la salida trasera (HDMI-A-1) y desactiva la pantalla interna eDP-1,
#    que la placa detecta aunque no esté conectada y descoloca la imagen y el teclado.
#  - Coloca el monitor en la posición 0,0 en cada arranque (si no, los juegos de
#    Windows salen descentrados).
#  - Usa Proton como motor de Wine para los juegos de Windows (reproduce bien las cinemáticas).

set -e

batocera-settings-set global.videooutput HDMI-A-1
batocera-settings-set global.videooutput2 none
batocera-settings-set display.position left-right
batocera-settings-set windows.wine-runner wine-proton

echo "Configuración aplicada:"
grep -E '^(global\.videooutput2?|display\.position|windows\.wine-runner)=' /userdata/system/batocera.conf
echo "Reinicia para aplicarla: reboot"
