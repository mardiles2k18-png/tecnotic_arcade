# Aplica o deshace optimizaciones de Windows para el arcade.
#   -Accion aplicar|restaurar   -Opciones "busqueda,telemetria,..."
param(
    [string]$Accion = 'aplicar',
    [string]$Opciones = ''
)
$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$aplicar = $Accion -eq 'aplicar'

# Servicio -> tipo de inicio original de Windows (para restaurar)
function Servicios($lista) {
    foreach ($par in $lista) {
        $nombre, $original = $par
        if (-not (Get-Service -Name $nombre -ErrorAction SilentlyContinue)) { continue }
        if ($aplicar) {
            Stop-Service -Name $nombre -Force -ErrorAction SilentlyContinue
            sc.exe config $nombre start= disabled | Out-Null
            "   servicio $nombre desactivado"
        } else {
            sc.exe config $nombre start= $original | Out-Null
            if ($original -match 'auto') { Start-Service -Name $nombre -ErrorAction SilentlyContinue }
            "   servicio $nombre restaurado ($original)"
        }
    }
}

function Valor($ruta, $nombre, $valor) {
    if ($aplicar) {
        New-Item -Path $ruta -Force -ErrorAction SilentlyContinue | Out-Null
        Set-ItemProperty -Path $ruta -Name $nombre -Value $valor -Type DWord
    } else {
        Remove-ItemProperty -Path $ruta -Name $nombre -ErrorAction SilentlyContinue
    }
}

foreach ($op in ($Opciones -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ })) {
    "== $op"
    switch ($op) {
        'busqueda'   { Servicios @(,@('WSearch', 'delayed-auto')) }
        'telemetria' {
            Servicios @(@('DiagTrack', 'auto'), @('dmwappushservice', 'demand'))
            Valor 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection' 'AllowTelemetry' 0
        }
        'impresion'  { Servicios @(@('Spooler', 'auto'), @('Fax', 'demand')) }
        'errores'    {
            Servicios @(,@('WerSvc', 'demand'))
            Valor 'HKLM:\SOFTWARE\Microsoft\Windows\Windows Error Reporting' 'Disabled' 1
            Valor 'HKLM:\SOFTWARE\Microsoft\Windows\Windows Error Reporting' 'DontShowUI' 1
        }
        'extras'     { Servicios @(@('MapsBroker', 'delayed-auto'), @('RetailDemo', 'demand')) }
        'sysmain'    { Servicios @(,@('SysMain', 'auto')) }
        'actualizaciones' {
            Servicios @(@('wuauserv', 'demand'), @('UsoSvc', 'delayed-auto'))
            Valor 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU' 'NoAutoUpdate' 1
        }
        'antivirus'  {
            $raices = Get-PSDrive -PSProvider FileSystem | ForEach-Object { $_.Root }
            $tareas = Get-ScheduledTask -TaskPath '\Microsoft\Windows\Windows Defender\' -ErrorAction SilentlyContinue
            if ($aplicar) {
                foreach ($r in $raices) { Add-MpPreference -ExclusionPath $r -ErrorAction SilentlyContinue }
                $tareas | Disable-ScheduledTask -ErrorAction SilentlyContinue | Out-Null
                "   discos excluidos del análisis: $($raices -join ' ')"
                "   análisis programados desactivados"
                if (-not (Get-MpComputerStatus).IsTamperProtected) {
                    Valor 'HKLM:\SOFTWARE\Policies\Microsoft\Windows Defender' 'DisableAntiSpyware' 1
                    Valor 'HKLM:\SOFTWARE\Policies\Microsoft\Windows Defender\Real-Time Protection' 'DisableRealtimeMonitoring' 1
                    Set-MpPreference -DisableRealtimeMonitoring $true -ErrorAction SilentlyContinue
                    "   protección en tiempo real desactivada"
                } else {
                    "   AVISO: la protección contra alteraciones está activada; el antivirus sigue encendido pero ya no analiza los discos"
                }
            } else {
                foreach ($r in $raices) { Remove-MpPreference -ExclusionPath $r -ErrorAction SilentlyContinue }
                $tareas | Enable-ScheduledTask -ErrorAction SilentlyContinue | Out-Null
                Valor 'HKLM:\SOFTWARE\Policies\Microsoft\Windows Defender' 'DisableAntiSpyware' 0
                Valor 'HKLM:\SOFTWARE\Policies\Microsoft\Windows Defender\Real-Time Protection' 'DisableRealtimeMonitoring' 0
                Set-MpPreference -DisableRealtimeMonitoring $false -ErrorAction SilentlyContinue
                "   antivirus restaurado"
            }
        }
        'gamebar'    { Valor 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\GameDVR' 'AllowGameDVR' 0; "   Xbox Game Bar y grabación de juegos" }
        'notificaciones' {
            Valor 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\Explorer' 'DisableNotificationCenter' 1
            Valor 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\CurrentVersion\PushNotifications' 'NoToastApplicationNotification' 1
            "   notificaciones"
        }
        'energia'    {
            if ($aplicar) {
                powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c 2>$null
                if ($LASTEXITCODE -ne 0) { powercfg /duplicatescheme 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c | Out-Null; powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c }
                foreach ($t in 'standby-timeout-ac', 'monitor-timeout-ac', 'hibernate-timeout-ac', 'disk-timeout-ac') { powercfg /change $t 0 }
                powercfg /hibernate off
                "   alto rendimiento, sin suspender ni apagar pantalla, sin hibernación"
            } else {
                powercfg /setactive 381b4222-f694-41f0-9685-ff5bb260df2e
                powercfg /hibernate on
                "   plan equilibrado y hibernación restaurados"
            }
        }
        default { "   opción desconocida: $op" }
    }
}
"Listo."
