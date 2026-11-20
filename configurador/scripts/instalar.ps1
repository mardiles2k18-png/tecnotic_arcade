# Instala o actualiza el Modo Arcade en la cuenta actual (una sola cuenta).
# Lo llama el Configurador, que antes guarda de forma cifrada la contraseña
# para el inicio de sesión automático.
#
# Resultado:
#   - Windows entra solo con esta cuenta.
#   - El escritorio de la cuenta es la bienvenida de Tecnotics, que abre RetroBat.
#   - Con el PIN, la bienvenida abre el escritorio normal de Windows.
param(
    [string]$Origen,                       # carpeta con TecnoticsArcade.exe y logo.png
    [string]$Usuario = $env:USERNAME,
    [string]$RetroBat = 'C:\RetroBat\retrobat.exe',
    [string]$Segundos = '5',
    [string]$ComboBotones = '7,8',
    [string]$ComboSegundos = '3',
    [string]$TeclaSecreta = 'F12',
    [string]$PinSal = '',
    [string]$PinHash = '',
    [string]$OcultarBienvenida = '0'       # 1 = ocultar también la pantalla "Bienvenido" de Windows
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$destino = 'C:\TecnoticsArcade'
function Paso($t) { "`n=== $t" }

try {
# ---------------------------------------------------------------------------
Paso 'Limpiando la versión anterior (usuario Arcade)'
$viejo = Get-LocalUser -Name 'Arcade' -ErrorAction SilentlyContinue
try {
    $sl = [wmiclass]'\\localhost\root\standardcimv2\embedded:WESL_UserSetting'
    if ($viejo) { try { $sl.RemoveCustomShell($viejo.SID.Value) | Out-Null } catch { } }
    $sl.SetEnabled($false) | Out-Null
    "   Shell Launcher desactivado (ya no se usa)"
} catch { }
if ($viejo) {
    Get-CimInstance Win32_UserProfile | Where-Object { $_.SID -eq $viejo.SID.Value } | Remove-CimInstance -ErrorAction SilentlyContinue
    Remove-LocalUser -Name 'Arcade'
    "   usuario Arcade y su perfil eliminados"
} else { "   nada que limpiar" }

# ---------------------------------------------------------------------------
Paso 'Copiando la pantalla de bienvenida'
New-Item -ItemType Directory -Force -Path $destino | Out-Null
# Si la bienvenida está abierta (por ejemplo, en segundo plano), se cierra para poder reemplazarla
$abiertas = Get-Process -Name TecnoticsArcade -ErrorAction SilentlyContinue
if ($abiertas) {
    $abiertas | Stop-Process -Force
    $abiertas | Wait-Process -Timeout 10 -ErrorAction SilentlyContinue
    "   bienvenida anterior cerrada"
}
Copy-Item "$Origen\TecnoticsArcade.exe" "$destino\TecnoticsArcade.exe" -Force
Copy-Item "$Origen\logo.png" "$destino\logo.png" -Force
"   $destino\TecnoticsArcade.exe"

# ---------------------------------------------------------------------------
Paso 'Configuración'
$ini = "$destino\config.ini"
$cfg = [ordered]@{ RetroBat = ''; Segundos = ''; ComboBotones = ''; ComboSegundos = ''; TeclaSecreta = ''; Procesos = 'retrobat,emulationstation'; PinSal = ''; PinHash = '' }
if (Test-Path $ini) {
    foreach ($l in Get-Content $ini) { if ($l -match '^\s*([^#;=]+?)\s*=\s*(.*)$') { $cfg[$Matches[1]] = $Matches[2].Trim() } }
}
$cfg.RetroBat = $RetroBat; $cfg.Segundos = $Segundos; $cfg.ComboBotones = $ComboBotones
$cfg.ComboSegundos = $ComboSegundos; $cfg.TeclaSecreta = $TeclaSecreta
if ($PinHash) { $cfg.PinSal = $PinSal; $cfg.PinHash = $PinHash; "   PIN actualizado" }
if (-not $cfg.PinHash) { throw 'Falta el PIN del modo Windows.' }
$cfg.Keys | ForEach-Object { "$_=$($cfg[$_])" } | Set-Content -Path $ini -Encoding ASCII
icacls $destino /inheritance:r /grant:r '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-545:(OI)(CI)RX' /Q | Out-Null
"   $ini"

# ---------------------------------------------------------------------------
Paso "Escritorio de la cuenta $Usuario"
$w = 'HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Winlogon'
New-Item $w -Force -ErrorAction SilentlyContinue | Out-Null
Set-ItemProperty $w -Name Shell -Value "$destino\TecnoticsArcade.exe"
"   al iniciar sesión se abre la bienvenida en lugar del escritorio"
$acc = 'HKCU:\Control Panel\Accessibility'
New-Item "$acc\StickyKeys" -Force -ErrorAction SilentlyContinue | Out-Null; Set-ItemProperty "$acc\StickyKeys" -Name Flags -Value '506'
New-Item "$acc\Keyboard Response" -Force -ErrorAction SilentlyContinue | Out-Null; Set-ItemProperty "$acc\Keyboard Response" -Name Flags -Value '122'
New-Item "$acc\ToggleKeys" -Force -ErrorAction SilentlyContinue | Out-Null; Set-ItemProperty "$acc\ToggleKeys" -Name Flags -Value '58'
"   sin ventanas de teclas especiales ni teclas filtro"

# ---------------------------------------------------------------------------
Paso 'Inicio de sesión automático'
$wl = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon'
Set-ItemProperty $wl -Name DefaultUserName -Value $Usuario
Set-ItemProperty $wl -Name DefaultDomainName -Value $env:COMPUTERNAME
Remove-ItemProperty $wl -Name DefaultPassword -ErrorAction SilentlyContinue   # la contraseña va cifrada (LSA)
Remove-ItemProperty $wl -Name AutoLogonCount -ErrorAction SilentlyContinue
Set-ItemProperty $wl -Name AutoAdminLogon -Value '1'
New-Item 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\Personalization' -Force | Out-Null
Set-ItemProperty 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\Personalization' -Name NoLockScreen -Value 1 -Type DWord
Set-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System' -Name EnableFirstLogonAnimation -Value 0 -Type DWord
"   Windows entra solo como $Usuario, sin pantalla de bloqueo"

# ---------------------------------------------------------------------------
Paso 'Arranque sin logo de Windows'
bcdedit /set '{globalsettings}' bootuxdisabled on | Out-Null
bcdedit /set '{bootmgr}' noerrordisplay on | Out-Null
"   sin logo ni animación de carga de Windows"

$kiosco = $null
try { $kiosco = Get-WindowsOptionalFeature -Online -FeatureName Client-EmbeddedLogon } catch { }
$el = 'HKLM:\SOFTWARE\Microsoft\Windows Embedded\EmbeddedLogon'
if ($kiosco) {
    foreach ($f in 'Client-DeviceLockdown', 'Client-EmbeddedLogon', 'Client-EmbeddedBootExp') {
        if ((Get-WindowsOptionalFeature -Online -FeatureName $f).State -ne 'Enabled') {
            Enable-WindowsOptionalFeature -Online -FeatureName $f -All -NoRestart | Out-Null
            "   $f activado"
        }
    }
    New-Item -Path $el -Force | Out-Null
    foreach ($v in 'BrandingNeutral', 'HideFirstLogonAnimation', 'AnimationDisabled', 'NoLockScreen', 'UIVerbosityLevel') {
        Set-ItemProperty $el -Name $v -Value 1 -Type DWord
    }
    if ($OcultarBienvenida -eq '1') {
        Set-ItemProperty $el -Name HideAutoLogonUI -Value 1 -Type DWord
        "   pantalla 'Bienvenido' de Windows oculta"
    } else {
        Remove-ItemProperty $el -Name HideAutoLogonUI -ErrorAction SilentlyContinue
        "   pantalla 'Bienvenido' visible (modo seguro: si algo falla, se ve el motivo)"
    }
    "   sin animaciones ni botones en las pantallas de inicio de Windows"
} else {
    "   (edición sin funciones de quiosco: se omite Custom Logon)"
}

"`nModo Arcade instalado. Reinicia el equipo para probarlo."
exit 0
} catch {
    "`nERROR: $($_.Exception.Message)"
    exit 1
}
