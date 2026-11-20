# Desactiva el Modo Arcade y deja Windows con su escritorio normal.
# No borra el usuario Arcade, RetroBat ni los juegos.
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$usuario = 'Arcade'
$u = Get-LocalUser -Name $usuario -ErrorAction SilentlyContinue

try {
    $sl = [wmiclass]'\\localhost\root\standardcimv2\embedded:WESL_UserSetting'
    if ($u) { try { $sl.RemoveCustomShell($u.SID.Value) | Out-Null } catch { } }
    $sl.SetEnabled($false) | Out-Null
    'Shell Launcher desactivado'
} catch { 'Shell Launcher no estaba activo' }

if ($u) {
    $sid = $u.SID.Value
    $perfil = (Get-CimInstance Win32_UserProfile | Where-Object { $_.SID -eq $sid }).LocalPath
    $cargada = Test-Path "Registry::HKEY_USERS\$sid"
    $raiz = "Registry::HKEY_USERS\$sid"
    if (-not $cargada -and $perfil -and (Test-Path "$perfil\NTUSER.DAT")) {
        reg load 'HKU\TA_Arcade' "$perfil\NTUSER.DAT" | Out-Null
        $raiz = 'Registry::HKEY_USERS\TA_Arcade'
    }
    Remove-ItemProperty "$raiz\Software\Microsoft\Windows NT\CurrentVersion\Winlogon" -Name Shell -ErrorAction SilentlyContinue
    if (-not $cargada) { [gc]::Collect(); Start-Sleep -Milliseconds 300; reg unload 'HKU\TA_Arcade' 2>$null | Out-Null }
    'Escritorio alternativo del usuario Arcade quitado'
}

$wl = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon'
Set-ItemProperty $wl -Name AutoAdminLogon -Value '0'
Remove-ItemProperty $wl -Name DefaultPassword -ErrorAction SilentlyContinue
'Inicio de sesión automático desactivado'

Remove-Item 'HKLM:\SOFTWARE\Microsoft\Windows Embedded\EmbeddedLogon' -Recurse -ErrorAction SilentlyContinue
bcdedit /set '{globalsettings}' bootuxdisabled off | Out-Null
bcdedit /set '{bootmgr}' noerrordisplay off | Out-Null
'Arranque y pantallas de Windows restaurados'
"`nModo Arcade desactivado. Reinicia el equipo."
