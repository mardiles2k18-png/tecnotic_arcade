# Instala o actualiza el Modo Arcade (lo llama el Configurador).
# Funciona en cualquier edición de Windows 10/11:
#   - Enterprise / LTSC / Education: Shell Launcher + Unbranded Boot + Custom Logon (oficial)
#   - Home / Pro: escritorio alternativo por usuario (el logo de Windows se ve un instante)
param(
    [string]$Origen,                       # carpeta con TecnoticsArcade.exe y logo.png
    [string]$RetroBat = 'C:\RetroBat\retrobat.exe',
    [string]$Segundos = '5',
    [string]$ComboBotones = '7,8',
    [string]$ComboSegundos = '3',
    [string]$TeclaSecreta = 'F12',
    [string]$PinSal = '',
    [string]$PinHash = ''
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$destino = 'C:\TecnoticsArcade'
$usuario = 'Arcade'
$reiniciar = $false
function Paso($t) { "`n=== $t" }

try {
# ---------------------------------------------------------------------------
Paso 'Copiando la pantalla de bienvenida'
New-Item -ItemType Directory -Force -Path $destino | Out-Null
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
if (-not $cfg.PinHash) { throw 'Falta el PIN de mantenimiento: escríbelo en el Configurador antes de instalar.' }
$cfg.Keys | ForEach-Object { "$_=$($cfg[$_])" } | Set-Content -Path $ini -Encoding ASCII
icacls $destino /inheritance:r /grant:r '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-545:(OI)(CI)RX' /Q | Out-Null
"   $ini (solo los administradores pueden modificarlo)"

# ---------------------------------------------------------------------------
Paso 'Usuario Arcade (sin contraseña ni permisos de administrador)'
if (-not (Get-LocalUser -Name $usuario -ErrorAction SilentlyContinue)) {
    New-LocalUser -Name $usuario -NoPassword -FullName 'Tecnotics Arcade' -Description 'Usuario del modo arcade' | Out-Null
    "   usuario creado"
} else { "   ya existía" }
Set-LocalUser -Name $usuario -UserMayChangePassword $false
Add-LocalGroupMember -SID 'S-1-5-32-545' -Member $usuario -ErrorAction SilentlyContinue
$sid = (Get-LocalUser -Name $usuario).SID.Value
icacls (Split-Path $RetroBat) /grant "${usuario}:(OI)(CI)M" /Q | Out-Null
"   permisos sobre $(Split-Path $RetroBat)"

# Perfil del usuario Arcade (se crea ya, para poder configurarlo sin iniciar sesión)
Add-Type -TypeDefinition @'
using System; using System.Runtime.InteropServices; using System.Text;
public static class PerfilTA {
    [DllImport("userenv.dll", CharSet = CharSet.Unicode)]
    public static extern int CreateProfile(string sid, string user, StringBuilder path, uint size);
}
'@ -ErrorAction SilentlyContinue
$sb = New-Object Text.StringBuilder 260
[void][PerfilTA]::CreateProfile($sid, $usuario, $sb, 260)
$perfil = (Get-CimInstance Win32_UserProfile | Where-Object { $_.SID -eq $sid }).LocalPath
"   perfil: $perfil"

# ---------------------------------------------------------------------------
Paso 'Inicio de sesión automático'
$wl = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon'
Set-ItemProperty $wl -Name AutoAdminLogon -Value '1'
Set-ItemProperty $wl -Name DefaultUserName -Value $usuario
Set-ItemProperty $wl -Name DefaultDomainName -Value $env:COMPUTERNAME
Set-ItemProperty $wl -Name DefaultPassword -Value ''
Remove-ItemProperty $wl -Name AutoLogonCount -ErrorAction SilentlyContinue
New-Item 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\Personalization' -Force | Out-Null
Set-ItemProperty 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\Personalization' -Name NoLockScreen -Value 1 -Type DWord
Set-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System' -Name EnableFirstLogonAnimation -Value 0 -Type DWord
"   Windows entra solo como $usuario, sin pantalla de bloqueo"

# Arranque sin logo ni animación de Windows (bcdedit funciona en todas las ediciones)
bcdedit /set '{globalsettings}' bootuxdisabled on | Out-Null
bcdedit /set '{bootmgr}' noerrordisplay on | Out-Null
"   arranque sin animación de Windows"

# ---------------------------------------------------------------------------
# Ajustes dentro del perfil Arcade: sin teclas especiales y (en Home/Pro) escritorio alternativo
$kiosco = $null
try { $kiosco = Get-WindowsOptionalFeature -Online -FeatureName Client-EmbeddedShellLauncher } catch { }

function EnColmena([scriptblock]$accion) {
    $cargada = Test-Path "Registry::HKEY_USERS\$sid"
    $raiz = "Registry::HKEY_USERS\$sid"
    if (-not $cargada) {
        reg load 'HKU\TA_Arcade' "$perfil\NTUSER.DAT" | Out-Null
        $raiz = 'Registry::HKEY_USERS\TA_Arcade'
    }
    try { & $accion $raiz }
    finally {
        if (-not $cargada) { [gc]::Collect(); Start-Sleep -Milliseconds 300; reg unload 'HKU\TA_Arcade' | Out-Null }
    }
}

Paso 'Ajustes del usuario Arcade'
EnColmena {
    param($raiz)
    $acc = "$raiz\Control Panel\Accessibility"
    New-Item "$acc\StickyKeys" -Force | Out-Null; Set-ItemProperty "$acc\StickyKeys" -Name Flags -Value '506'
    New-Item "$acc\Keyboard Response" -Force | Out-Null; Set-ItemProperty "$acc\Keyboard Response" -Name Flags -Value '122'
    New-Item "$acc\ToggleKeys" -Force | Out-Null; Set-ItemProperty "$acc\ToggleKeys" -Name Flags -Value '58'
    "   sin ventanas de teclas especiales ni teclas filtro"
    $w = "$raiz\Software\Microsoft\Windows NT\CurrentVersion\Winlogon"
    if (-not $kiosco) {
        New-Item $w -Force | Out-Null
        Set-ItemProperty $w -Name Shell -Value "$destino\TecnoticsArcade.exe"
        "   escritorio del usuario Arcade -> TecnoticsArcade.exe (método alternativo)"
    } else {
        Remove-ItemProperty $w -Name Shell -ErrorAction SilentlyContinue
    }
}

# ---------------------------------------------------------------------------
if ($kiosco) {
    Paso 'Funciones de quiosco (Enterprise / LTSC)'
    foreach ($f in 'Client-DeviceLockdown', 'Client-EmbeddedShellLauncher', 'Client-EmbeddedLogon', 'Client-EmbeddedBootExp') {
        if ((Get-WindowsOptionalFeature -Online -FeatureName $f).State -ne 'Enabled') {
            $r = Enable-WindowsOptionalFeature -Online -FeatureName $f -All -NoRestart
            if ($r.RestartNeeded) { $reiniciar = $true }
            "   $f activado"
        }
    }
    $el = 'HKLM:\SOFTWARE\Microsoft\Windows Embedded\EmbeddedLogon'
    New-Item -Path $el -Force | Out-Null
    foreach ($v in 'BrandingNeutral', 'HideAutoLogonUI', 'HideFirstLogonAnimation', 'AnimationDisabled', 'NoLockScreen', 'UIVerbosityLevel') {
        Set-ItemProperty $el -Name $v -Value 1 -Type DWord
    }
    "   sin pantallas de inicio de sesión (Custom Logon)"

    $sl = $null
    try { $sl = [wmiclass]'\\localhost\root\standardcimv2\embedded:WESL_UserSetting' } catch { }
    if (-not $sl) {
        "`nAVISO: Windows tiene que reiniciar para terminar de activar Shell Launcher."
        "Reinicia el equipo, abre otra vez el Configurador y pulsa de nuevo 'Instalar / actualizar'."
        exit 3
    }
    try { $sl.RemoveCustomShell($sid) | Out-Null } catch { }
    $sl.SetDefaultShell('explorer.exe', 0) | Out-Null
    $sl.SetCustomShell($sid, "$destino\TecnoticsArcade.exe", $null, $null, 0) | Out-Null
    $sl.SetEnabled($true) | Out-Null
    "   Shell Launcher: el usuario Arcade ve la bienvenida en lugar del escritorio"
}

"`nModo Arcade instalado."
if ($reiniciar) { "Windows necesita reiniciar para aplicar algunas funciones." }
"Reinicia el equipo para probarlo."
exit 0
} catch {
    "`nERROR: $($_.Exception.Message)"
    exit 1
}
