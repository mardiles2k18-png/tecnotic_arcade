# Tecnotics Arcade - instalador del modo arcade para Windows 10 Enterprise LTSC
#
# Deja el equipo así:
#   - Al encender, entra solo en el usuario "Arcade" (sin contraseña ni pantallas de Windows)
#   - En vez del escritorio, el usuario Arcade ve la bienvenida de Tecnotics Arcade,
#     que abre RetroBat a los 5 segundos.
#   - El modo Windows está oculto: combinación secreta (mando) o F12 + PIN.
#     Con el PIN correcto aparece la pantalla de inicio de sesión para entrar con
#     la cuenta de administrador (Tecnotics), que tiene el escritorio normal.
#
# Uso (PowerShell como administrador, en la carpeta donde están estos archivos):
#   powershell -ExecutionPolicy Bypass -File .\instalar-modo-arcade.ps1
#   powershell -ExecutionPolicy Bypass -File .\instalar-modo-arcade.ps1 -Juegos 'C:\Juegos'
#
# Se puede ejecutar varias veces: solo cambia lo que falte. Para deshacerlo todo:
#   powershell -ExecutionPolicy Bypass -File .\desinstalar-modo-arcade.ps1

#Requires -RunAsAdministrator
param(
    [string]$Juegos = 'C:\Juegos',
    [string]$RetroBat = 'C:\RetroBat\retrobat.exe'
)

$ErrorActionPreference = 'Stop'
$origen  = $PSScriptRoot
$destino = 'C:\TecnoticsArcade'
$usuario = 'Arcade'
$reiniciar = $false

function Paso($texto) { Write-Host "`n=== $texto" -ForegroundColor Cyan }
function Ok($texto)   { Write-Host "   OK  $texto" -ForegroundColor Green }
function Aviso($texto){ Write-Host "   !!  $texto" -ForegroundColor Yellow }

# ------------------------------------------------------------------------------
Paso '1/7  Compilando la pantalla de bienvenida'
$csc = Join-Path ([Runtime.InteropServices.RuntimeEnvironment]::GetRuntimeDirectory()) 'csc.exe'
if (-not (Test-Path $csc)) { throw "No encuentro el compilador de .NET en $csc" }
New-Item -ItemType Directory -Force -Path $destino | Out-Null
& $csc /nologo /target:winexe /optimize "/out:$destino\TecnoticsArcade.exe" `
    /r:System.Windows.Forms.dll /r:System.Drawing.dll "$origen\TecnoticsArcade.cs"
if ($LASTEXITCODE -ne 0) { throw 'Error al compilar TecnoticsArcade.cs' }
Copy-Item "$origen\logo.png" "$destino\logo.png" -Force
Ok "$destino\TecnoticsArcade.exe"

# ------------------------------------------------------------------------------
Paso '2/7  Configuración y PIN de mantenimiento'
$ini = "$destino\config.ini"
$config = [ordered]@{
    RetroBat      = $RetroBat
    Segundos      = '5'
    ComboBotones  = '7,8'
    ComboSegundos = '3'
    TeclaSecreta  = 'F12'
    Procesos      = 'retrobat,emulationstation'
    PinSal        = ''
    PinHash       = ''
}
if (Test-Path $ini) {
    foreach ($linea in Get-Content $ini) {
        if ($linea -match '^\s*([^#;=]+?)\s*=\s*(.*)$') { $config[$Matches[1]] = $Matches[2].Trim() }
    }
}

$cambiarPin = $config.PinHash -eq ''
if (-not $cambiarPin) { $cambiarPin = (Read-Host '   Ya hay un PIN. ¿Quieres cambiarlo? (s/n)') -eq 's' }
if ($cambiarPin) {
    while ($true) {
        $s1 = Read-Host '   PIN nuevo (de 4 a 8 números)' -AsSecureString
        $s2 = Read-Host '   Repite el PIN' -AsSecureString
        $p1 = [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s1))
        $p2 = [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s2))
        if ($p1 -ne $p2) { Aviso 'Los PIN no coinciden.'; continue }
        if ($p1 -notmatch '^\d{4,8}$') { Aviso 'El PIN debe tener de 4 a 8 números.'; continue }
        break
    }
    $sal = -join (1..16 | ForEach-Object { '{0:x2}' -f (Get-Random -Maximum 256) })
    $sha = [Security.Cryptography.SHA256]::Create()
    $hash = -join ($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($sal + $p1)) | ForEach-Object { $_.ToString('x2') })
    $config.PinSal = $sal
    $config.PinHash = $hash
    Remove-Variable p1, p2
    Ok 'PIN guardado (cifrado)'
}
$config.Keys | ForEach-Object { "$_=$($config[$_])" } | Set-Content -Path $ini -Encoding ASCII
if (-not (Test-Path $config.RetroBat)) { Aviso "No existe $($config.RetroBat). Corrígelo en $ini" }

# Solo administradores pueden modificar la carpeta; el usuario Arcade solo puede leerla
icacls $destino /inheritance:r /grant:r '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-545:(OI)(CI)RX' /Q | Out-Null
Ok 'Permisos de C:\TecnoticsArcade'

# ------------------------------------------------------------------------------
Paso '3/7  Usuario Arcade (sin contraseña, sin permisos de administrador)'
if (-not (Get-LocalUser -Name $usuario -ErrorAction SilentlyContinue)) {
    New-LocalUser -Name $usuario -NoPassword -FullName 'Tecnotics Arcade' -Description 'Usuario del modo arcade' | Out-Null
    Ok "Usuario $usuario creado"
} else { Ok "El usuario $usuario ya existe" }
Set-LocalUser -Name $usuario -UserMayChangePassword $false
Add-LocalGroupMember -SID 'S-1-5-32-545' -Member $usuario -ErrorAction SilentlyContinue
$sid = (Get-LocalUser -Name $usuario).SID.Value

# ------------------------------------------------------------------------------
Paso '4/7  Permisos del usuario Arcade sobre RetroBat y los juegos'
foreach ($carpeta in @((Split-Path $config.RetroBat), $Juegos)) {
    if (Test-Path $carpeta) {
        icacls $carpeta /grant "${usuario}:(OI)(CI)M" /Q | Out-Null
        Ok "Lectura y escritura en $carpeta"
    } else { Aviso "No existe $carpeta (los juegos deben estar ahí para que Arcade pueda abrirlos)" }
}

# ------------------------------------------------------------------------------
Paso '5/7  Inicio de sesión automático y sin pantallas de Windows'
$wl = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon'
Set-ItemProperty $wl -Name AutoAdminLogon    -Value '1'
Set-ItemProperty $wl -Name DefaultUserName   -Value $usuario
Set-ItemProperty $wl -Name DefaultDomainName -Value $env:COMPUTERNAME
Set-ItemProperty $wl -Name DefaultPassword   -Value ''
Remove-ItemProperty $wl -Name AutoLogonCount -ErrorAction SilentlyContinue
Ok "Entra solo como $usuario"

$pol = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\Personalization'
New-Item -Path $pol -Force | Out-Null
Set-ItemProperty $pol -Name NoLockScreen -Value 1 -Type DWord
$sys = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System'
Set-ItemProperty $sys -Name EnableFirstLogonAnimation -Value 0 -Type DWord
Ok 'Sin pantalla de bloqueo ni animación de primer inicio'

# ------------------------------------------------------------------------------
Paso '6/7  Funciones de quiosco de Windows (Enterprise / LTSC)'
foreach ($f in 'Client-DeviceLockdown', 'Client-EmbeddedShellLauncher', 'Client-EmbeddedLogon', 'Client-EmbeddedBootExp') {
    $estado = (Get-WindowsOptionalFeature -Online -FeatureName $f).State
    if ($estado -ne 'Enabled') {
        $r = Enable-WindowsOptionalFeature -Online -FeatureName $f -All -NoRestart
        if ($r.RestartNeeded) { $reiniciar = $true }
        Ok "$f activado"
    } else { Ok "$f ya estaba activado" }
}

# Custom Logon: oculta la pantalla de bienvenida, animaciones y botones
$el = 'HKLM:\SOFTWARE\Microsoft\Windows Embedded\EmbeddedLogon'
New-Item -Path $el -Force | Out-Null
foreach ($v in 'BrandingNeutral', 'HideAutoLogonUI', 'HideFirstLogonAnimation', 'AnimationDisabled', 'NoLockScreen', 'UIVerbosityLevel') {
    Set-ItemProperty $el -Name $v -Value 1 -Type DWord
}
Ok 'Custom Logon configurado'

# Unbranded Boot: sin logo, animación ni textos de Windows al arrancar
bcdedit /set '{globalsettings}' bootuxdisabled on | Out-Null
bcdedit /set '{bootmgr}' noerrordisplay on | Out-Null
Ok 'Unbranded Boot configurado'

# ------------------------------------------------------------------------------
Paso '7/7  Shell Launcher: la bienvenida reemplaza al escritorio del usuario Arcade'
$sl = $null
try { $sl = [wmiclass]'\\localhost\root\standardcimv2\embedded:WESL_UserSetting' } catch { }
if (-not $sl) {
    Aviso 'Shell Launcher todavía no está disponible.'
    Aviso 'Reinicia el equipo y vuelve a ejecutar este instalador para terminar (el PIN no se vuelve a pedir si respondes "n").'
    exit 0
}
try { $sl.RemoveCustomShell($sid) | Out-Null } catch { }
$sl.SetDefaultShell('explorer.exe', 0) | Out-Null                          # resto de usuarios: escritorio normal
$sl.SetCustomShell($sid, "$destino\TecnoticsArcade.exe", $null, $null, 0) | Out-Null   # 0 = si se cierra, se vuelve a abrir
$sl.SetEnabled($true) | Out-Null
Ok "Usuario $usuario -> $destino\TecnoticsArcade.exe"

Write-Host "`nInstalación terminada." -ForegroundColor Green
if ($reiniciar) { Write-Host 'Windows necesita reiniciar para aplicar algunas funciones.' -ForegroundColor Yellow }
Write-Host 'Reinicia el equipo para probar el modo arcade: Restart-Computer'
