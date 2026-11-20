# Estado del equipo. Cada línea "Nombre=Valor" se muestra en la pestaña Estado.
# Las líneas "OPT:id=1/0" indican qué optimizaciones están aplicadas.
$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [Text.Encoding]::UTF8

function SiNo($c, $si, $no) { if ($c) { $si } else { $no } }

$os = Get-CimInstance Win32_OperatingSystem
"Windows=$($os.Caption) ($($os.Version))"
"Memoria RAM={0:N1} GB en total, {1:N1} GB libres" -f ($os.TotalVisibleMemorySize / 1MB), ($os.FreePhysicalMemory / 1MB)
$disco = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
"Disco C:={0:N0} GB libres de {1:N0} GB" -f ($disco.FreeSpace / 1GB), ($disco.Size / 1GB)

$kiosco = Get-WindowsOptionalFeature -Online -FeatureName Client-EmbeddedShellLauncher
"Funciones de quiosco=" + (SiNo $kiosco 'Disponibles (Enterprise / LTSC): arranque sin logo de Windows' 'No disponibles en esta edición: se usará el método alternativo')

$u = Get-LocalUser -Name Arcade
"Usuario Arcade=" + (SiNo $u 'Creado' 'No creado')
$wl = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon'
"Inicio automático=" + (SiNo ($wl.AutoAdminLogon -eq '1') "Sí, como $($wl.DefaultUserName)" 'No')
"Modo Arcade=" + (SiNo (Test-Path 'C:\TecnoticsArcade\TecnoticsArcade.exe') 'Instalado en C:\TecnoticsArcade' 'No instalado')
$ini = 'C:\TecnoticsArcade\config.ini'
"PIN de mantenimiento=" + (SiNo ((Test-Path $ini) -and (Select-String -Path $ini -Pattern '^PinHash=.+' -Quiet)) 'Configurado' 'Sin configurar')

$mp = Get-MpComputerStatus
if ($mp) { "Antivirus: protección contra alteraciones=" + (SiNo $mp.IsTamperProtected 'Activada (no se puede apagar del todo por comandos)' 'Desactivada') }

# Estado de las optimizaciones
function Deshabilitado($nombres) {
    foreach ($n in $nombres) {
        $s = Get-Service -Name $n
        if ($s -and $s.StartType -ne 'Disabled') { return 0 }
    }
    return 1
}
"OPT:busqueda=" + (Deshabilitado 'WSearch')
"OPT:telemetria=" + (Deshabilitado 'DiagTrack', 'dmwappushservice')
"OPT:impresion=" + (Deshabilitado 'Spooler')
"OPT:errores=" + (Deshabilitado 'WerSvc')
"OPT:extras=" + (Deshabilitado 'MapsBroker', 'RetailDemo')
"OPT:sysmain=" + (Deshabilitado 'SysMain')
"OPT:actualizaciones=" + (Deshabilitado 'wuauserv')
$excl = (Get-MpPreference).ExclusionPath
"OPT:antivirus=" + (SiNo ($excl -contains 'C:\') 1 0)
$gd = Get-ItemProperty 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\GameDVR'
"OPT:gamebar=" + (SiNo ($gd.AllowGameDVR -eq 0) 1 0)
$nt = Get-ItemProperty 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\Explorer'
"OPT:notificaciones=" + (SiNo ($nt.DisableNotificationCenter -eq 1) 1 0)
$plan = (powercfg /getactivescheme) -join ' '
"OPT:energia=" + (SiNo ($plan -match '8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c') 1 0)
