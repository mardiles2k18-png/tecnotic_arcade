#!/bin/bash
# Tecnotics Arcade - preparación automática de los juegos de Windows.
#
# Batocera ejecuta los scripts de /userdata/system/scripts/ al abrir y cerrar
# cada juego, con estos argumentos: evento sistema emulador núcleo rom
#
# Al abrir un juego de Windows por primera vez, este script:
#   1. crea su prefijo de Wine (si todavía no existe)
#   2. le instala Media Foundation si esta versión de Batocera lo trae (en la 44 no viene)
#   3. instala las librerías de LIBRERIAS_EXTRA con winetricks (si hay alguna)
# Después deja una marca en el prefijo y no vuelve a hacerlo para ese juego.
#
# También se puede ejecutar a mano para preparar todos los juegos existentes:
#   /userdata/system/scripts/tecnotics-wine.sh todos

# Librerías extra para todos los juegos, separadas por espacios.
# Ejemplo: LIBRERIAS_EXTRA="vcrun2022 d3dcompiler_47"
# winetricks las descarga de internet, así que hace falta conexión la primera vez.
LIBRERIAS_EXTRA=""

LOG="/userdata/system/logs/tecnotics-wine.log"
BOTELLAS="/userdata/system/wine-bottles/windows"
MF_DIR="/usr/wine/mf"
MARCA=".tecnotics-preparado"

log() { echo "$(date '+%F %T') $*" >> "$LOG"; }

# Carpeta de binarios de Wine para un runner (incluidos los personalizados)
bin_runner() {
    local runner="$1"
    if [ -x "/usr/wine/${runner}/bin/wine" ]; then
        echo "/usr/wine/${runner}/bin"
    elif [ -x "/userdata/system/wine/custom/${runner}/bin/wine" ]; then
        echo "/userdata/system/wine/custom/${runner}/bin"
    elif [ -x "/userdata/system/wine/custom/${runner}/files/bin/wine" ]; then
        echo "/userdata/system/wine/custom/${runner}/files/bin"
    fi
}

preparar_prefijo() {
    local prefijo="$1" runner="$2" bin
    [ -d "${prefijo}/drive_c" ] || return 0
    [ -e "${prefijo}/${MARCA}" ] && return 0

    bin="$(bin_runner "$runner")"
    if [ -z "$bin" ]; then
        log "No encuentro Wine para el runner '${runner}' (${prefijo})"
        return 1
    fi

    # Sin nada que instalar no se toca el prefijo ni se deja marca
    if [ ! -x "${MF_DIR}/mf-install.sh" ] && [ -z "$LIBRERIAS_EXTRA" ]; then
        return 0
    fi

    log "Preparando ${prefijo} con ${runner}"
    if [ -x "${MF_DIR}/mf-install.sh" ]; then
        if (cd "$MF_DIR" && WINEPREFIX="$prefijo" PATH="${bin}:$PATH" ./mf-install.sh) >> "$LOG" 2>&1; then
            log "Media Foundation instalado"
        else
            log "ERROR instalando Media Foundation"
            return 1
        fi
    else
        log "Media Foundation no está disponible en esta versión de Batocera, se omite"
    fi

    if [ -n "$LIBRERIAS_EXTRA" ]; then
        local winetricks="/usr/wine/winetricks"
        if [ ! -x "$winetricks" ]; then
            winetricks="/userdata/system/wine/winetricks"
            [ -x "$winetricks" ] || { mkdir -p /userdata/system/wine && \
                wget -qO "$winetricks" https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks && \
                chmod +x "$winetricks"; }
        fi
        # shellcheck disable=SC2086
        if WINEPREFIX="$prefijo" PATH="${bin}:$PATH" WINE="${bin}/wine" WINESERVER="${bin}/wineserver" \
            "$winetricks" -q $LIBRERIAS_EXTRA >> "$LOG" 2>&1; then
            log "Librerías instaladas: ${LIBRERIAS_EXTRA}"
        else
            log "ERROR instalando librerías: ${LIBRERIAS_EXTRA}"
        fi
    fi

    "${bin}/wineserver" -w 2>/dev/null
    touch "${prefijo}/${MARCA}"
    log "Listo: ${prefijo}"
}

# Prepara todos los prefijos que ya existan
preparar_todos() {
    local prefijo runner
    for prefijo in "${BOTELLAS}"/*/*.wine; do
        [ -d "$prefijo" ] || continue
        runner="$(basename "$(dirname "$prefijo")")"
        preparar_prefijo "$prefijo" "$runner"
    done
    # Juegos en formato .wine (el propio juego es el prefijo)
    for prefijo in /userdata/roms/windows/*.wine; do
        [ -d "$prefijo" ] || continue
        preparar_prefijo "$prefijo" "$(batocera-settings-get windows.wine-runner || echo wine-tkg)"
    done
}

EVENTO="$1"
SISTEMA="$2"
ROM="$5"

if [ "$EVENTO" = "todos" ]; then
    preparar_todos
    echo "Hecho. Detalles en ${LOG}"
    exit 0
fi

# Solo actúa al abrir juegos de Windows
[ "$EVENTO" = "gameStart" ] || exit 0
[ "$SISTEMA" = "windows" ] || exit 0
[ -n "$ROM" ] || exit 0

case "${ROM,,}" in
    *.wine)
        preparar_prefijo "$ROM" "$(batocera-settings-get windows.wine-runner || echo wine-tkg)"
        ;;
    *.pc|*.exe)
        nombre="$(basename "$ROM")"
        # Runner que usará este juego (misma lógica que batocera-wine)
        runner="$(batocera-settings-get "windows[\"${nombre}\"].wine-runner" "windows.wine-runner" "global.wine-runner")"
        case "$runner" in
            ""|lutris) runner="wine-tkg" ;;
            proton) runner="wine-proton" ;;
        esac
        # Si el juego nunca se abrió con ese runner, se crea su prefijo ahora
        if [ ! -d "${BOTELLAS}/${runner}/${nombre}.wine" ]; then
            log "Creando prefijo para ${nombre} (${runner})"
            batocera-wine windows createprefix "$ROM" >> "$LOG" 2>&1
        fi
        for prefijo in "${BOTELLAS}"/*/"${nombre}.wine"; do
            [ -d "$prefijo" ] || continue
            preparar_prefijo "$prefijo" "$(basename "$(dirname "$prefijo")")"
        done
        ;;
esac
exit 0
